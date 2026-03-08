import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'defect_detection.settings')
django.setup()

from django.test import RequestFactory, Client
from django.contrib.auth import get_user_model
from core_inventory.models import Product, Batch
from core_inventory.views import product_list, batch_list
from django.urls import reverse

User = get_user_model()

def verify_upgrade():
    print("Verifying Products and Batches Upgrade...")

    # 1. Verify Model Fields
    print("\n1. Verifying Model Fields...")
    product_fields = [f.name for f in Product._meta.get_fields()]
    batch_fields = [f.name for f in Batch._meta.get_fields()]

    required_product_fields = ['description', 'material_type', 'handling_guidelines']
    required_batch_fields = ['status', 'inspector_notes']

    all_fields_present = True
    for field in required_product_fields:
        if field not in product_fields:
            print(f"FAIL: Product model missing field '{field}'")
            all_fields_present = False
        else:
            print(f"PASS: Product model has field '{field}'")

    for field in required_batch_fields:
        if field not in batch_fields:
            print(f"FAIL: Batch model missing field '{field}'")
            all_fields_present = False
        else:
            print(f"PASS: Batch model has field '{field}'")
    
    if all_fields_present:
        print("Model verification successful.")

    # 2. Verify View Access and Template Content
    print("\n2. Verifying View Access and Template Content...")
    
    # Create users
    admin_user, _ = User.objects.get_or_create(username='test_admin', role='admin')
    inspector_user, _ = User.objects.get_or_create(username='test_inspector', role='inspector')
    
    # Create test data
    product, _ = Product.objects.get_or_create(
        name='Test Product', 
        category='Test Category',
        defaults={
            'description': 'Test Description', 
            'material_type': 'Steel', 
            'handling_guidelines': 'Handle with care'
        }
    )
    batch, _ = Batch.objects.get_or_create(
        product=product, 
        batch_number='BATCH-001', 
        quantity=100,
        defaults={'status': 'Active', 'inspector_notes': 'Verified ok'}
    )

    client = Client()

    # Test Product List as Inspector
    print("\nTesting Product List as Inspector (Non-Admin)...")
    client.force_login(inspector_user)
    response = client.get(reverse('product_list'))
    
    if response.status_code == 200:
        print("PASS: Inspector can access product_list")
        content = response.content.decode()
        if 'card h-100' in content:
            print("PASS: Template uses cards")
        else:
            print("FAIL: Template does not exist or does not use cards")
        
        if 'Test Description' in content:
             print("PASS: Description displayed")
        
        if 'Add Product' in content:
            print("FAIL: Inspector sees 'Add Product' button")
        else:
            print("PASS: Inspector does NOT see 'Add Product' button")
    else:
        print(f"FAIL: Inspector cannot access product_list (Status: {response.status_code})")

    # Test Batch List as Inspector
    print("\nTesting Batch List as Inspector (Non-Admin)...")
    response = client.get(reverse('batch_list'))
    
    if response.status_code == 200:
        print("PASS: Inspector can access batch_list")
        content = response.content.decode()
        if 'card h-100' in content:
            print("PASS: Template uses cards")
        
        if 'Verified ok' in content:
             print("PASS: Inspector notes displayed")

        if 'Edit' in content and 'Delete' in content: # Simple check for link text
             # Note: logic check might need to be more robust if 'Edit' is used elsewhere, 
             # but here we check for the specific admin buttons.
             # In the template: <a ...>Edit</a>
             if 'btn-outline-danger' in content: # Delete button class
                 print("FAIL: Inspector sees Delete button")
             else:
                 print("PASS: Inspector does NOT see Delete button")
    else:
        print(f"FAIL: Inspector cannot access batch_list")

    # Test Product List as Admin
    print("\nTesting Product List as Admin...")
    client.force_login(admin_user)
    response = client.get(reverse('product_list'))
    if 'Add Product' in response.content.decode():
        print("PASS: Admin sees 'Add Product' button")
    else:
        print("FAIL: Admin does not see 'Add Product' button")

    # Test Batch List as Admin
    print("\nTesting Batch List as Admin...")
    response = client.get(reverse('batch_list'))
    content = response.content.decode()
    if 'btn-outline-danger' in content:
        print("PASS: Admin sees Delete button")
    else:
        print("FAIL: Admin does not see Delete button")

if __name__ == "__main__":
    verify_upgrade()
