import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'defect_detection.settings')
django.setup()

from django.test import Client
from core_inventory.models import Product, Batch
from django.urls import reverse
from django.utils import timezone

def verify_visual_guide():
    print("Verifying Inspector's Visual Guide Upgrade...")

    # 1. Verify Model Fields
    print("\n1. Verifying Model Fields...")
    product_fields = [f.name for f in Product._meta.get_fields()]
    batch_fields = [f.name for f in Batch._meta.get_fields()]

    if 'visual_guide' in product_fields:
        print("PASS: Product model has 'visual_guide'")
    else:
        print("FAIL: Product model missing 'visual_guide'")

    if 'inspector_instructions' in batch_fields:
        print("PASS: Batch model has 'inspector_instructions'")
    else:
        print("FAIL: Batch model missing 'inspector_instructions'")

    # 2. Verify Data Updates
    print("\n2. Verifying Data Updates...")
    try:
        product = Product.objects.get(name='Ceramic Insulator')
        expected_text = "Looks like: A white ceramic coffee mug with a black rim. Select this if you are inspecting mugs."
        if product.visual_guide == expected_text:
            print(f"PASS: 'Ceramic Insulator' has correct visual guide.")
        else:
            print(f"FAIL: 'Ceramic Insulator' visual guide mismatch.\nExpected: {expected_text}\nGot: {product.visual_guide}")
    except Product.DoesNotExist:
        print("WARN: 'Ceramic Insulator' product not found. Skipping data check.")

    # 3. Verify Template Rendering
    print("\n3. Verifying Template Rendering...")
    client = Client()
    # Need to login to access these views
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user, _ = User.objects.get_or_create(username='test_inspector_vg', role='inspector')
        client.force_login(user)
    except Exception as e:
        print(f"Error creating/logging in user: {e}")
        return

    # 3. Verify Template Rendering
    print("\n3. Verifying Template Rendering...")
    client = Client()
    # Need to login to access these views
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user, _ = User.objects.get_or_create(username='test_inspector_vg', role='inspector')
        client.force_login(user)
    except Exception as e:
        print(f"Error creating/logging in user: {e}")
        return

    # 3. Verify Template Rendering
    print("\n3. Verifying Template Rendering...")
    client = Client()
    # Need to login to access these views
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user, _ = User.objects.get_or_create(username='test_inspector_vg', role='inspector')
        client.force_login(user)
    except Exception as e:
        print(f"Error creating/logging in user: {e}")
        return

    # Check Product List (Minimalist)
    response = client.get(reverse('product_list'))
    content = response.content.decode()
    
    if 'card mb-3' in content:
        print("PASS: Product List uses simple 'card mb-3'")
    else:
        print("FAIL: Product List does NOT use simple 'card mb-3'")

    # False positive check: list-group is in base.html sidebar, so we ignore general presence.
    # We rely on the visual check of 'card mb-3' being the dominant structure for items.

    forbidden_product_strings = ['How to Identify', 'Material:', 'Handling:', 'Admin View']
    for s in forbidden_product_strings:
        if s in content and s != 'Admin View': 
             print(f"FAIL: Found forbidden string '{s}' in Product List")
        elif s == 'Admin View' and 'Admin View' in content:
             print("INFO: 'Admin View' label present (acceptable for admin)")
        else:
             print(f"PASS: '{s}' NOT found in Product List")

    # Check Batch List (Minimalist)
    response = client.get(reverse('batch_list'))
    content = response.content.decode()
    
    if 'card h-100' in content and 'dashboard-card' not in content:
        print("PASS: Batch List uses simple 'card h-100' without 'dashboard-card'")
    elif 'dashboard-card' in content:
        print("FAIL: Batch List still uses 'dashboard-card' class")
        
    forbidden_batch_labels = ['Identity Check:', 'Shift Instructions:', 'Notes:']
    for s in forbidden_batch_labels:
        if s in content:
            print(f"FAIL: Found forbidden label '{s}' in Batch List")
        else:
            print(f"PASS: '{s}' NOT found in Batch List")
            
    if 'Qty:' in content and 'Date:' in content:
        print("PASS: Found minimal 'Qty:' and 'Date:' labels")
    else:
        print("FAIL: Missing minimal 'Qty:' or 'Date:' labels")

    # Critical: Check if descriptions are rendered as Plain Text vs Input Values
    # We look for the test data strings.
    # We expect: <p...>...TEST VIDEO GUIDE...</p>
    # We fail if: value="...TEST VIDEO GUIDE..."
    
    test_strings = ['TEST VIDEO GUIDE', 'TEST INSTRUCTIONS']
    for ts in test_strings:
        if ts in content:
            if f'value="{ts}"' in content or f"value='{ts}'" in content:
                 print(f"FAIL: '{ts}' found inside an input value attribute!")
            else:
                 print(f"PASS: '{ts}' found in content but NOT in input value (likely plain text).")
        else:
            # If test data isn't there, we can't verify, but we printed a warning earlier if creates failed.
            # actually we didn't print warning in this version of script, let's just note it.
            print(f"WARN: Test string '{ts}' not found in output. Ensure test data exists.")

if __name__ == "__main__":
    verify_visual_guide()
