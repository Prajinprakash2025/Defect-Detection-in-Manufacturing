from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Inspection, Defect, Alert
from core_inventory.models import Batch
from .forms import InspectionForm
from .services.ai_service import detect_defect
from PIL import Image, ImageEnhance
import os

# --- CONFIGURATION ---
# Lower this to catch more defects (higher recall), raise it to avoid false alarms (higher precision)
CONFIDENCE_THRESHOLD = 0.80 
# ---------------------

@login_required
def upload_inspection(request):
    # Manager cannot upload inspections
    if request.user.role == 'manager':
        messages.error(request, "Managers are not authorized to upload inspections.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = InspectionForm(request.POST, request.FILES)
        if form.is_valid():
            inspection = form.save(commit=False)
            inspection.uploaded_by = request.user
            inspection.save()

            # --- Image Preprocessing (Pillow) ---
            image_path = inspection.image.path
            try:
                with Image.open(image_path) as img:
                    # 1. Resize to standard square (640x640)
                    img = img.resize((640, 640))
                    
                    # 2. Contrast Enhancement
                    enhancer = ImageEnhance.Contrast(img)
                    img = enhancer.enhance(1.2) # Slight enhancement (20%)
                    
                    img.save(image_path)
            except Exception as e:
                print(f"Preprocessing Error: {e}")

            # Process Image with AI
            # image_path is already set
            ai_result = detect_defect(image_path)
            
            # --- DEBUG LOGGING ---
            print("AI RESULT:", ai_result)
            # ---------------------

            # Update Inspection Record
            inspection.prediction_label = ai_result.get('label', 'Unknown')
            inspection.confidence_score = ai_result.get('confidence', 0.0)
            inspection.raw_prediction_json = ai_result.get('raw_response', '{}')
            
            # Threshold Logic
            # Requirement: If 'Detected' in label AND confidence >= 0.80 -> Defective
            label = inspection.prediction_label
            is_defective = ai_result.get('is_defective', False)
            confidence = float(ai_result.get('confidence', 0.0))
            
            # Combined Logic: AI Flag OR Explicit "Detected" keyword, PLUS Threshold check
            if (is_defective or "Detected" in label) and confidence >= CONFIDENCE_THRESHOLD:
                inspection.status = 'Defective'
            else:
                inspection.status = 'Non-Defective'
                # If AI said defective but confidence was low, we mark non-defective
                if is_defective:
                    print(f"Downgrading to Non-Defective due to low confidence: {confidence}")

            inspection.save()

            # Create Defect Record if defective
            if inspection.status == 'Defective':
                defect_type = "Defect Detected" # Generic for now unless simplified
                # Try to parse specific defect type if available in label
                label = inspection.prediction_label.lower()
                if "crack" in label: defect_type = "Crack"
                elif "scratch" in label: defect_type = "Scratch"
                elif "dent" in label: defect_type = "Dent"
                elif "discoloration" in label: defect_type = "Discoloration"
                
                Defect.objects.create(
                    inspection=inspection,
                    defect_type=defect_type,
                    severity='High' if inspection.confidence_score > 0.9 else 'Medium'
                )
                
                # Create Alert
                Alert.objects.create(
                    inspection=inspection,
                    message=f"Defect '{defect_type}' detected in Batch {inspection.batch.batch_number} with {int(inspection.confidence_score*100)}% confidence.",
                    alert_status='Unread'
                )
                messages.warning(request, f"Defect Detected! {inspection.prediction_label}")
            else:
                messages.success(request, "Inspection Passed. No defects detected.")

            return redirect('inspection_list')
    else:
        form = InspectionForm()
    
    return render(request, 'inspections/upload.html', {'form': form})

@login_required
def verify_result(request, pk):
    # Admin Only
    if request.user.role != 'admin':
        messages.error(request, "Permission Denied.")
        return redirect('inspection_detail', pk=pk)

    inspection = get_object_or_404(Inspection, pk=pk)
    
    if request.method == 'POST':
        # Check if AJAX/JSON request
        import json
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json'
        
        if is_ajax:
            try:
                data = json.loads(request.body)
                action = data.get('action') # 'mark_defective' or 'mark_non_defective'
                
                response_data = {'success': False, 'message': 'Invalid Action'}
                
                if action == 'mark_defective':
                    defect_type_input = data.get('defect_type', 'Human Verified Defect')
                    
                    inspection.status = 'Defective'
                    inspection.is_training_data = True
                    inspection.is_manually_verified = True
                    inspection.save()
                    
                    Defect.objects.create(
                        inspection=inspection,
                        defect_type=defect_type_input,
                        severity='High' # Admins usually flag important things
                    )
                    
                    Alert.objects.create(
                        inspection=inspection,
                        message=f"Manual Verification: Marked as Defective ({defect_type_input}) by Admin.",
                        alert_status='Unread'
                    )
                    
                    response_data = {'success': True, 'message': 'Marked as Defective', 'new_status': 'Defective'}
                    
                elif action == 'mark_non_defective':
                    inspection.status = 'Non-Defective'
                    inspection.is_training_data = True
                    inspection.is_manually_verified = True
                    inspection.save()
                    
                    Defect.objects.filter(inspection=inspection).delete()
                    Alert.objects.filter(inspection=inspection).delete()
                    
                    response_data = {'success': True, 'message': 'Marked as Non-Defective', 'new_status': 'Non-Defective'}
                
                from django.http import JsonResponse
                return JsonResponse(response_data)
            except Exception as e:
                from django.http import JsonResponse
                return JsonResponse({'success': False, 'message': str(e)}, status=400)

        # Fallback for standard FORM POST (Legacy support or non-JS)
        if inspection.status == 'Non-Defective':
            # Case 1: False Negative (AI missed it) -> Mark as Defective
            inspection.status = 'Defective'
            inspection.is_training_data = True # Mark as High-Value
            inspection.is_manually_verified = True
            inspection.save()
            
            # Create Defect Record
            Defect.objects.create(
                inspection=inspection,
                defect_type="Human Verified Defect",
                severity='Medium'
            )
            
            # Create Alert
            Alert.objects.create(
                inspection=inspection,
                message=f"Correction: Inspection {inspection.id} marked as Defective by Admin.",
                alert_status='Unread'
            )
            
            messages.success(request, "Status manually updated by Admin: Marked as Defective.")
            
        elif inspection.status == 'Defective':
             # Case 2: False Positive (AI was wrong) -> Mark as Non-Defective
            inspection.status = 'Non-Defective'
            inspection.is_training_data = True # Still high value as a negative example
            inspection.is_manually_verified = True
            inspection.save()
            
            # Application Logic: Remove invalid defective records
            # Delete associated Defects
            deleted_defects = Defect.objects.filter(inspection=inspection).delete()
            
            # Delete associated Alerts
            deleted_alerts = Alert.objects.filter(inspection=inspection).delete()
            
            messages.success(request, f"Status manually updated by Admin: Marked as Non-Defective. Cleaned up {deleted_defects[0]} defects and {deleted_alerts[0]} alerts.")
    
    return redirect('inspection_detail', pk=pk)

@login_required
def inspection_list(request):
    inspections = Inspection.objects.all().order_by('-timestamp')
    
    # Role-Based Filtering: Inspectors see only their own inspections
    if request.user.role == 'inspector':
        inspections = inspections.filter(uploaded_by=request.user)
    
    batches = Batch.objects.all() # For filter dropdown

    # Filtering
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    status = request.GET.get('status')
    batch_id = request.GET.get('batch')
    inspector = request.GET.get('inspector')

    if date_from:
        inspections = inspections.filter(timestamp__date__gte=date_from)
    if date_to:
        inspections = inspections.filter(timestamp__date__lte=date_to)
    if status:
        inspections = inspections.filter(status=status)
    if batch_id:
        inspections = inspections.filter(batch_id=batch_id)
    if inspector:
        inspections = inspections.filter(uploaded_by__username__icontains=inspector)

    context = {
        'inspections': inspections,
        'batches': batches,
    }
    return render(request, 'inspections/list.html', context)

@login_required
def inspection_detail(request, pk):
    inspection = get_object_or_404(Inspection, pk=pk)
    return render(request, 'inspections/detail.html', {'inspection': inspection})

@login_required
def delete_inspection(request, pk):
    inspection = get_object_or_404(Inspection, pk=pk)
    
    # Strict Role Check: Only Admin can delete
    if request.user.role != 'admin':
        messages.error(request, "Permission Denied: Only Admins can delete inspections.")
        return redirect('inspection_list')
    
    if request.method == 'POST':
        inspection.delete()
        messages.success(request, "Inspection deleted successfully.")
        return redirect('inspection_list')
    
    # If GET, show confirmation page (or just redirect if using modal/post form directly)
    # For now, we will handle deletion via POST form in the list view for safety.
    return redirect('inspection_list')

@login_required
def alert_list(request):
    alerts = Alert.objects.all().order_by('-created_at')
    return render(request, 'inspections/alerts.html', {'alerts': alerts})

@login_required
def export_report(request):
    import csv
    from django.http import HttpResponse

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="inspection_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Batch', 'Dimensions', 'Prediction', 'Confidence', 'Status', 'Date', 'Inspector'])

    inspections = Inspection.objects.all().values_list(
        'id', 'batch__batch_number', 'prediction_label', 'confidence_score', 'status', 'timestamp', 'uploaded_by__username'
    )
    
    for ins in inspections:
        writer.writerow(ins)

    return response

@login_required
def user_management(request):
    # Admin Only
    if request.user.role != 'admin':
        messages.error(request, "Permission Denied: Only Admins can manage users.")
        return redirect('dashboard')

    from django.contrib.auth import get_user_model
    User = get_user_model()
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'inspections/user_management.html', {'users': users})

@login_required
def change_user_role(request, pk):
    # Admin Only
    if request.user.role != 'admin':
        messages.error(request, "Permission Denied.")
        return redirect('dashboard')
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user_to_edit = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        new_role = request.POST.get('role')
        # Basic validation
        if new_role in ['admin', 'manager', 'inspector']:
            user_to_edit.role = new_role
            user_to_edit.save()
            messages.success(request, f"Role for {user_to_edit.username} updated to {new_role}.")
        else:
            messages.error(request, "Invalid role selected.")
            
    return redirect('user_management')

