import os
import django
import random
from django.utils import timezone
from datetime import timedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'defect_detection.settings')
django.setup()

from accounts.models import CustomUser
from core_inventory.models import Product, Batch
from inspections.models import Inspection, Defect, Alert

def populate():
    print("Starting data population...")

    # 1. Create/Get Product
    product, created = Product.objects.get_or_create(
        name="Metal Gear",
        defaults={'category': 'Automotive', 'description': 'High precision metal gear for transmission.'}
    )
    print(f"Product: {product.name} (Created: {created})")

    # 2. Create Batches
    batch_suffixes = ['A', 'B', 'C', 'D', 'E']
    batches = []
    base_date = timezone.now().date()
    
    for suffix in batch_suffixes:
        batch_num = f"BATCH-2026-FEB{suffix}"
        batch, created = Batch.objects.get_or_create(
            batch_number=batch_num,
            defaults={
                'product': product,
                'manufacture_date': base_date - timedelta(days=random.randint(0, 5)),
                'quantity': 1000
            }
        )
        batches.append(batch)
        print(f"Batch: {batch.batch_number} (Created: {created})")

    # 3. Create Users (Ensure they exist)
    users = {
        'admin': ('admin', 'admin@example.com', 'admin'),
        'manager': ('manager', 'manager@example.com', 'manager'),
        'inspector': ('inspector', 'inspector@example.com', 'inspector')
    }
    
    user_objects = {}
    for role, (username, email, role_val) in users.items():
        if not CustomUser.objects.filter(username=username).exists():
            user = CustomUser.objects.create_user(username=username, email=email, password='password123', role=role_val)
            print(f"User created: {username} ({role_val})")
        else:
            user = CustomUser.objects.get(username=username)
            # Update role just in case
            if user.role != role_val:
                user.role = role_val
                user.save()
            print(f"User exists: {username}")
        user_objects[role] = user

    # 4. Create Mock Inspections
    # Use 'test_image.jpg' if exists, else create a dummy one if needed or just use a placeholder path
    # Assuming 'test_image.jpg' is in media or root. For Safety, we will just use a string path that won't break 
    # if file doesn't exist, but 'test_image.jpg' is likely in root from `list_dir`.
    # Let's copy it to media/inspection_images if possible, or just reference it.
    
    image_path = 'inspection_images/demo_defect.jpg'
    
    # Generate 10 inspections
    for i in range(10):
        batch = random.choice(batches)
        inspector = user_objects['inspector']
        
        is_defective = random.choice([True, False])
        status = 'Defective' if is_defective else 'Non-Defective'
        
        inspection = Inspection.objects.create(
            batch=batch,
            uploaded_by=inspector,
            image=image_path,
            prediction_label='Scratch' if is_defective else 'Clean',
            confidence_score=random.uniform(0.85, 0.99) if is_defective else random.uniform(0.90, 0.99),
            status=status,
            timestamp=timezone.now() - timedelta(minutes=random.randint(1, 120))
        )
        
        if is_defective:
            Defect.objects.create(
                inspection=inspection,
                defect_type='Scratch',
                severity=random.choice(['Low', 'Medium', 'High'])
            )
            Alert.objects.create(
                inspection=inspection,
                message=f"Defect detected in {batch.batch_number}",
                alert_status='Unread'
            )
            
    print(f"Created 10 mock inspections.")
    print("Data population complete.")

if __name__ == '__main__':
    populate()
