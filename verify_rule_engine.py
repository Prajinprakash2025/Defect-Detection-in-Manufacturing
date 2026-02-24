import os
import django
from django.core.files.uploadedfile import SimpleUploadedFile

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'defect_detection.settings')
django.setup()

from django.test import Client
from accounts.models import CustomUser
from inspections.models import Inspection
from core_inventory.models import Batch

def verify_rules():
    print("Verifying Smart Rule Engine...")
    
    # Setup
    client = Client()
    user = CustomUser.objects.filter(role='inspector').first()
    if not user:
        user = CustomUser.objects.create_user('rule_tester', 'test@example.com', 'password', role='inspector')
    
    client.force_login(user)
    
    batch = Batch.objects.first()
    if not batch:
        print("No batch found, cannot verify.")
        return

    # Create dummy image content
    dummy_content = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x01\x44\x00\x3b'

    # Test 1: Defect Keyword
    print("\nTest 1: Uploading 'demo_defect.jpg'...")
    img_defect = SimpleUploadedFile("demo_defect.jpg", dummy_content, content_type="image/jpeg")
    
    response = client.post('/inspections/upload/', {
        'batch': batch.id,
        'image': img_defect
    }, follow=True)
    
    insp = Inspection.objects.latest('id')
    print(f"Result: ID={insp.id}, Status={insp.status}, Label={insp.prediction_label}, Conf={insp.confidence_score}")
    
    if insp.status == 'Defective' and insp.confidence_score == 0.96:
        print("PASS: Defect Rule worked.")
    else:
        print("FAIL: Defect Rule failed.")

    # Test 2: Clean Keyword
    print("\nTest 2: Uploading 'demo_clean.jpg'...")
    img_clean = SimpleUploadedFile("demo_clean.jpg", dummy_content, content_type="image/jpeg")
    
    response = client.post('/inspections/upload/', {
        'batch': batch.id,
        'image': img_clean
    }, follow=True)
    
    insp = Inspection.objects.latest('id')
    print(f"Result: ID={insp.id}, Status={insp.status}, Label={insp.prediction_label}, Conf={insp.confidence_score}")
    
    if insp.status == 'Non-Defective' and insp.confidence_score == 0.99:
        print("PASS: Clean Rule worked.")
    else:
        print("FAIL: Clean Rule failed.")

if __name__ == '__main__':
    verify_rules()
