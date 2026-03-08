from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Inspection, Defect, Alert
from core_inventory.models import Batch
from .forms import InspectionForm
from .services.ai_service import detect_defect
from PIL import Image, ImageEnhance
import os
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.http import HttpResponse
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model

# --- CONFIGURATION ---
# UPDATED: Lowered to 0.50 to accommodate the newly trained Local Random Forest Machine Learning Model
CONFIDENCE_THRESHOLD = 0.50 
# ---------------------

@login_required
def upload_inspection(request):
    # Manager cannot upload inspections
    if request.user.role == 'manager':
        messages.error(request, "Managers are not authorized to upload inspections.")
        return redirect('dashboard')

    if request.method == 'POST':
        # Get the batch ID and the LIST of uploaded images
        batch_id = request.POST.get('batch')
        images = request.FILES.getlist('images') # Notice we use getlist() for bulk uploads!

        if not batch_id or not images:
            messages.error(request, "Please select a batch and upload at least one image.")
            return redirect('upload_inspection')

        batch = get_object_or_404(Batch, id=batch_id)
        
        # Track our bulk results
        defects_found = 0
        passed_found = 0

        # --- THE BULK UPLOAD LOOP ---
        for img_file in images:
            # 1. Create the Inspection Record
            inspection = Inspection.objects.create(
                batch=batch,
                uploaded_by=request.user,
                image=img_file
            )

            # 2. Image Preprocessing (Pillow)
            image_path = inspection.image.path
            try:
                with Image.open(image_path) as img:
                    img = img.resize((640, 640))
                    enhancer = ImageEnhance.Contrast(img)
                    img = enhancer.enhance(1.2) 
                    img.save(image_path)
            except Exception as e:
                print(f"Preprocessing Error: {e}")

            # 3. Real AI Processing
            print(f"Sending image to AI: {inspection.image.name}")
            ai_result = detect_defect(image_path)
            
            # 4. Update Inspection Record
            inspection.prediction_label = ai_result.get('label', 'Unknown')
            inspection.confidence_score = ai_result.get('confidence', 0.0)
            inspection.raw_prediction_json = ai_result.get('raw_response', '{}')
            
            label = inspection.prediction_label
            is_defective = ai_result.get('is_defective', False)
            confidence = float(ai_result.get('confidence', 0.0))
            
            # Combined Logic: AI Flag OR Explicit "Detected" keyword
            if (is_defective or "Detected" in label) and confidence >= CONFIDENCE_THRESHOLD:
                inspection.status = 'Defective'
                defects_found += 1
            else:
                inspection.status = 'Non-Defective'
                passed_found += 1

            inspection.save()

            # 5. Create Defect & Alert Records if defective
            if inspection.status == 'Defective':
                defect_type = "Defect Detected"
                label_lower = label.lower()
                if "crack" in label_lower: defect_type = "Crack"
                elif "scratch" in label_lower: defect_type = "Scratch"
                elif "dent" in label_lower: defect_type = "Dent"
                elif "discoloration" in label_lower: defect_type = "Discoloration"
                
                Defect.objects.create(
                    inspection=inspection,
                    defect_type=defect_type,
                    severity='High' if confidence > 0.97 else 'Medium'
                )
                
                Alert.objects.create(
                    inspection=inspection,
                    message=f"Defect '{defect_type}' detected in Batch {batch.batch_number} with {int(confidence*100)}% confidence.",
                    alert_status='Unread'
                )
        
        # --- END OF LOOP ---

        # Final Summary Notification & EMAIL TRIGGER
        if defects_found > 0:
            messages.warning(request, f"Bulk Scan Complete: {defects_found} defects found! {passed_found} passed.")
            
            # --- NEW: SEND EMERGENCY EMAIL ---
            try:
                subject = f"🚨 URGENT: Defects Detected in Batch {batch.batch_number}"
                message = f"Factory Manager Alert,\n\nDuring the latest AI scan of Batch {batch.batch_number} ({batch.product.name}), the system detected {defects_found} defective items.\n\nPlease log in to the DetectAI Dashboard immediately to review the images and halt the production line if necessary.\n\n- DetectAI Automated System"
                
                # IMPORTANT: Put your own email in the brackets below so you receive the test alert!
                send_mail(
                    subject,
                    message,
                    settings.EMAIL_HOST_USER,
                    ['YOUR_PERSONAL_EMAIL@gmail.com'], # <-- Replace with your real email!
                    fail_silently=False,
                )
                print("Emergency email successfully sent to manager!")
            except Exception as e:
                print(f"Failed to send email: {e}")
            # ---------------------------------
            
        else:
            messages.success(request, f"Bulk Scan Complete: All {passed_found} items passed inspection.")

        return redirect('inspection_list')

    else:
        # Pass batches to the template for the dropdown menu
        batches = Batch.objects.all()
        return render(request, 'inspections/upload.html', {'batches': batches})

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
    User = get_user_model()
    
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
    assignee = request.GET.get('assignee')
    action = request.POST.get('action') if request.method == 'POST' else None

    # Assignment action (admin/manager)
    if action == 'assign' and request.user.role in ['admin', 'manager']:
        ins_id = request.POST.get('inspection_id')
        user_id = request.POST.get('assignee_id')
        if ins_id and user_id:
            try:
                ins = Inspection.objects.get(id=ins_id)
                assignee_user = User.objects.get(id=user_id)
                ins.assigned_to = assignee_user
                ins.save()
                messages.success(request, f"Assigned inspection #{ins.id} to {assignee_user.username}.")
            except Inspection.DoesNotExist:
                messages.error(request, "Inspection not found.")
            except User.DoesNotExist:
                messages.error(request, "User not found.")
        return redirect('inspection_list')

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
    if assignee:
        inspections = inspections.filter(assigned_to__id=assignee)

    context = {
        'inspections': inspections,
        'batches': batches,
        'users': User.objects.all(),
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
    
    return redirect('inspection_list')

@login_required
def bulk_delete_inspections(request):
    # Strict Role Check: Only Admin can delete
    if request.user.role != 'admin':
        messages.error(request, "Permission Denied: Only Admins can delete inspections.")
        return redirect('inspection_list')
        
    if request.method == 'POST':
        inspection_ids = request.POST.getlist('inspection_ids')
        if inspection_ids:
            inspections_to_delete = Inspection.objects.filter(id__in=inspection_ids)
            count = inspections_to_delete.count()
            inspections_to_delete.delete()
            if count > 0:
                messages.success(request, f"Successfully deleted {count} inspection(s).")
        else:
            messages.warning(request, "No inspections were selected for deletion.")
            
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

@login_required
def report_preview(request):
    # Get all inspections for the preview table
    inspections = Inspection.objects.all().order_by('-timestamp')
    
    # Calculate some quick stats for the report header
    total = inspections.count()
    defective = inspections.filter(status='Defective').count()
    
    context = {
        'inspections': inspections,
        'total_scanned': total,
        'total_defective': defective,
    }
    return render(request, 'inspections/report_preview.html', context)



@login_required
def export_pdf_report(request):
    # 1. Get the exact same data we use for the preview page
    inspections = Inspection.objects.all().order_by('-timestamp')
    total = inspections.count()
    defective = inspections.filter(status='Defective').count()
    
    context = {
        'inspections': inspections,
        'total_scanned': total,
        'total_defective': defective,
    }
    
    # 2. Load a special, print-friendly HTML template
    template = get_template('inspections/pdf_template.html')
    html = template.render(context)
    
    # 3. Create the PDF response
    response = HttpResponse(content_type='application/pdf')
    # Change 'attachment' to 'inline' if you want it to open in the browser instead of downloading directly
    response['Content-Disposition'] = 'attachment; filename="DetectAI_Factory_Report.pdf"'
    
    # 4. Convert HTML to PDF
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse('We had some errors generating the PDF')
    return response
