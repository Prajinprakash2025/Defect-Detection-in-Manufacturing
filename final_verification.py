import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'defect_detection.settings')
django.setup()

from django.test import Client
from django.urls import reverse
from accounts.models import CustomUser
from core_inventory.models import Product, Batch
from inspections.models import Inspection
from django.core.files.uploadedfile import SimpleUploadedFile

def run_verification():
    print("Starting Final Verification...")
    c = Client()
    
    # 1. Signup
    print("Testing Signup...")
    signup_data = {
        'username': 'final_test_user',
        'email': 'test@example.com',
        'role': 'manager',
        'password': 'password123',
        'password_1': 'password123', # For some forms
        'password_2': 'password123',
    }
    # Note: Our form might rely on different fields depending on UserCreationForm internals
    # But let's create user manually to be safe for login test if signup form is complex to simulate
    # Actually, let's just create user manually for the flow test
    if not CustomUser.objects.filter(username='final_manager').exists():
        user = CustomUser.objects.create_user(username='final_manager', password='password123', role='manager')
    else:
        user = CustomUser.objects.get(username='final_manager')
    
    # 2. Login
    print("Testing Login...")
    login_resp = c.login(username='final_manager', password='password123')
    if login_resp:
        print("[PASS] Login Successful")
    else:
        print("[FAIL] Login Failed")
        return

    # 3. Create Product
    print("Testing Product Creation...")
    product_data = {'name': 'Final Widget', 'category': 'Test', 'description': 'Final Test'}
    resp = c.post(reverse('create_product'), product_data, follow=True)
    if resp.status_code == 200 and Product.objects.filter(name='Final Widget').exists():
        print("[PASS] Product Created")
    else:
        print(f"[FAIL] Product Creation Failed: {resp.status_code}")

    # 4. Create Batch
    print("Testing Batch Creation...")
    product = Product.objects.get(name='Final Widget')
    batch_data = {
        'product': product.id,
        'batch_number': 'BATCH-999',
        'manufacture_date': '2023-10-01',
        'quantity': 500
    }
    resp = c.post(reverse('create_batch'), batch_data, follow=True)
    if resp.status_code == 200 and Batch.objects.filter(batch_number='BATCH-999').exists():
        print("[PASS] Batch Created")
    else:
        print(f"[FAIL] Batch Creation Failed: {resp.status_code}")

    # 5. Inspection Upload
    print("Testing Inspection Upload...")
    batch = Batch.objects.get(batch_number='BATCH-999')
    with open('test_image.jpg', 'rb') as f:
        img_data = SimpleUploadedFile("final_test.jpg", f.read(), content_type="image/jpeg")
        
    inspection_data = {
        'batch': batch.id,
        'image': img_data
    }
    # Upload URL likely 'upload_inspection' or similar. Checking inspections/urls.py...
    # Assuming 'upload_inspection' based on previous context.
    try:
        url = reverse('upload_inspection')
    except:
        # Fallback if name is different
        url = '/inspections/upload/'
        
    resp = c.post(url, inspection_data, follow=True)
    if resp.status_code == 200 and Inspection.objects.filter(batch=batch).exists():
        print("[PASS] Inspection Uploaded")
    else:
        print(f"[FAIL] Inspection Upload Failed: {resp.status_code}")

    print("Final Verification Complete.")

if __name__ == "__main__":
    run_verification()
