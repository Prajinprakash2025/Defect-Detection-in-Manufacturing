import os
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'defect_detection.settings')
django.setup()

from django.test import Client, RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from inspections.models import Inspection, Defect, Alert
from core_inventory.models import Batch, Product
from PIL import Image
import io
from unittest.mock import patch

def create_test_image(filename, size=(100, 100), color=(255, 0, 0)):
    """Creates a dummy image in memory."""
    file_obj = io.BytesIO()
    image = Image.new("RGB", size, color)
    image.save(file_obj, format='JPEG')
    file_obj.seek(0)
    return SimpleUploadedFile(filename, file_obj.read(), content_type='image/jpeg')

def verification():
    print("=== Starting Feature Verification ===")
    
    # Setup User
    User = get_user_model()
    admin_user, _ = User.objects.get_or_create(username='admin_test', role='admin')
    admin_user.set_password('pass')
    admin_user.save()
    
    client = Client()
    client.force_login(admin_user)
    
    # Setup Data
    product, _ = Product.objects.get_or_create(name="TestWidget", category="Test", description="Desc")
    batch, _ = Batch.objects.get_or_create(product=product, batch_number="BATCH-TEST", quantity=100)
    
    # --- Test 1: Image Preprocessing ---
    print("\n[Test 1] Image Preprocessing (Resize & Contrast)")
    img_file = create_test_image("clean_product.jpg", size=(100, 200)) # Non-square
    
    # Upload
    response = client.post(reverse('upload_inspection'), {
        'batch': batch.id,
        'image': img_file
    }, follow=True)
    
    if response.status_code == 200:
        # Get the inspection
        inspection = Inspection.objects.filter(batch=batch).order_by('-id').first()
        if inspection:
            # Check Image Size
            processed_img = Image.open(inspection.image.path)
            print(f"Original Size: (100, 200) -> Processed Size: {processed_img.size}")
            
            if processed_img.size == (640, 640):
                print("✓ Image Resized Correctly")
            else:
                print(f"✗ Image Resize Failed: {processed_img.size}")
                
            # Check Status (should be Non-Defective for 'clean_product.jpg' via demo fallback)
            print(f"Initial Status: {inspection.status}")
        else:
            print("✗ Inspection creation failed")
            return
    else:
        print(f"✗ Upload failed with status {response.status_code}")
        return

    # --- Test 2: Feedback Loop (Verify Result) ---
    print("\n[Test 2] Feedback Loop (Verify Result)")
    
    # Ensure we are working with a Non-Defective inspection
    if inspection.status != 'Non-Defective':
        print("Skipping Test 2: Inspection is already Defective (unexpected for clean_product.jpg)")
    else:
        # Call Verify Result
        verify_url = reverse('verify_result', args=[inspection.id])
        resp = client.post(verify_url, follow=True)
        
        inspection.refresh_from_db()
        
        print(f"Status after Verify: {inspection.status}")
        print(f"Is Training Data: {inspection.is_training_data}")
        defect_count = Defect.objects.filter(inspection=inspection).count()
        print(f"Defect Count: {defect_count}")
        
        if inspection.status == 'Defective' and inspection.is_training_data and defect_count > 0:
            print("✓ Feedback Loop Verified Successfully")
        else:
            print("✗ Feedback Loop Verification Failed")

    # --- Test 3: Confidence Threshold Mock (Updated to 0.80) ---
    print("\n[Test 3] Confidence Threshold Logic (Threshold=0.80)")
    # Case A: 0.75 Confidence (Should Fail)
    with patch('inspections.views.detect_defect') as mock_ai:
        mock_ai.return_value = {
            'label': 'Crack Detected',
            'confidence': 0.75, # Below 0.80
            'is_defective': True,
            'raw_response': '{}'
        }
        
        img_file_low = create_test_image("low_conf.jpg")
        client.post(reverse('upload_inspection'), {
            'batch': batch.id,
            'image': img_file_low
        })
        
        inspection_low = Inspection.objects.filter(batch=batch).order_by('-id').first()
        print(f"Mock A (0.75): Status={inspection_low.status} (Expected: Non-Defective)")
        
        if inspection_low.status == 'Non-Defective':
             print("✓ Low Confidence Downgrade Verified")
        else:
             print("✗ Low Confidence Downgrade Failed")

    # Case B: 0.81 Confidence (Should Pass)
    with patch('inspections.views.detect_defect') as mock_ai:
        mock_ai.return_value = {
            'label': 'Crack Detected',
            'confidence': 0.81, # Above 0.80
            'is_defective': True,
            'raw_response': '{}'
        }
        
        img_file_high = create_test_image("high_conf.jpg")
        client.post(reverse('upload_inspection'), {
            'batch': batch.id,
            'image': img_file_high
        })
        
        inspection_high = Inspection.objects.filter(batch=batch).order_by('-id').first()
        print(f"Mock B (0.81): Status={inspection_high.status} (Expected: Defective)")
        
        if inspection_high.status == 'Defective':
             print("✓ High Confidence Pass Verified")
        else:
             print("✗ High Confidence Pass Failed")

    # --- Test 4: Reverse Feedback Loop (Defective -> Non-Defective) ---
    print("\n[Test 4] Reverse Feedback Loop")
    # Use inspection_high from Test 3 (which is Defective)
    target_inspection = inspection_high
    
    # Add dummy defect/alert to verify cleanup
    Defect.objects.create(inspection=target_inspection, defect_type="False Positive", severity="Low")
    Alert.objects.create(inspection=target_inspection, message="False Alarm")
    
    print("Set inspection to Defective with defects/alerts.")
    
    # Correct it back to Non-Defective via AJAX
    verify_url = reverse('verify_result', args=[target_inspection.id])
    resp = client.post(verify_url, 
        data={'action': 'mark_non_defective'}, 
        content_type='application/json'
    )
    
    target_inspection.refresh_from_db()
    
    print(f"Status after Verify: {target_inspection.status}")
    print(f"Is Manually Verified: {target_inspection.is_manually_verified}")
    defect_count = Defect.objects.filter(inspection=target_inspection).count()
    alert_count = Alert.objects.filter(inspection=target_inspection).count()
    print(f"Remaining Defects: {defect_count}, Remaining Alerts: {alert_count}")
    
    if target_inspection.status == 'Non-Defective' and defect_count == 0 and alert_count == 0 and target_inspection.is_manually_verified:
        print("✓ Reverse Feedback Loop Verified (Cleaned up records)")
    else:
        print("✗ Reverse Feedback Loop Failed")

    # --- Test 5: Manual Defect Verification (Non-Defective -> Defective with Type) ---
    print("\n[Test 5] Manual Defect Verification with Type")
    # Start with a Non-Defective
    inspection_3 = Inspection.objects.create(
        batch=batch,
        uploaded_by=admin_user,
        image=img_file_high,
        status='Non-Defective'
    )
    
    verify_url_3 = reverse('verify_result', args=[inspection_3.id])
    resp = client.post(verify_url_3,
        data={'action': 'mark_defective', 'defect_type': 'Dent'},
        content_type='application/json'
    )
    
    inspection_3.refresh_from_db()
    defect = Defect.objects.filter(inspection=inspection_3).first()
    
    print(f"Status: {inspection_3.status}")
    print(f"Is Manually Verified: {inspection_3.is_manually_verified}")
    print(f"Defect Type: {defect.defect_type if defect else 'None'}")
    
    if inspection_3.status == 'Defective' and defect and defect.defect_type == 'Dent' and inspection_3.is_manually_verified:
        print("✓ Manual Defect Verification Verified")
    else:
        print("✗ Manual Defect Verification Failed")

if __name__ == "__main__":
    verification()
