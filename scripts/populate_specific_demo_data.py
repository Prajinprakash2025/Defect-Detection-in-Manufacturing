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

def populate_specific():
    print("Starting specific demo data population...")

    # 1. Create Products
    products_data = [
        {'name': 'Polymer Container', 'category': 'Plastic', 'desc': 'High-durability storage container.'},
        {'name': 'Smart Display Unit', 'category': 'Electronics', 'desc': 'Touchscreen display module.'},
        {'name': 'Ceramic Insulator', 'category': 'Industrial Ceramics', 'desc': 'High-voltage insulator.'}
    ]
    
    products = {}
    for p_data in products_data:
        product, created = Product.objects.get_or_create(
            name=p_data['name'],
            defaults={'category': p_data['category'], 'description': p_data['desc']}
        )
        products[p_data['name']] = product
        print(f"Product: {product.name} (Created: {created})")

    # 2. Create Batches
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    last_week = today - timedelta(days=7)
    
    batches_data = [
        {'batch_num': 'BATCH-PLA-2026', 'prod': 'Polymer Container', 'qty': 5000, 'date': today},
        {'batch_num': 'BATCH-ELEC-X1', 'prod': 'Smart Display Unit', 'qty': 500, 'date': yesterday},
        {'batch_num': 'BATCH-CER-900', 'prod': 'Ceramic Insulator', 'qty': 2000, 'date': last_week}
    ]
    
    created_batches = []
    for b_data in batches_data:
        batch, created = Batch.objects.get_or_create(
            batch_number=b_data['batch_num'],
            defaults={
                'product': products[b_data['prod']],
                'manufacture_date': b_data['date'],
                'quantity': b_data['qty']
            }
        )
        created_batches.append(batch)
        print(f"Batch: {batch.batch_number} (Created: {created})")

    # 3. Create Inspections
    # Get an inspector
    try:
        inspector = CustomUser.objects.filter(role='inspector').first()
        if not inspector:
            inspector = CustomUser.objects.filter(is_superuser=True).first()
    except Exception as e:
        print(f"Error getting user: {e}")
        return

    image_path = 'inspection_images/demo_defect.jpg' # Reuse logic

    for batch in created_batches:
        print(f"Creating inspections for {batch.batch_number}...")
        for i in range(3):
            is_defective = random.choice([True, False])
            status = 'Defective' if is_defective else 'Non-Defective'
            
            inspection = Inspection.objects.create(
                batch=batch,
                uploaded_by=inspector,
                image=image_path,
                prediction_label='Crack/Dent' if is_defective else 'Clean',
                confidence_score=random.uniform(0.85, 0.99) if is_defective else random.uniform(0.90, 0.99),
                status=status,
                timestamp=timezone.now() - timedelta(minutes=random.randint(1, 1440)) # Random time in last 24h
            )
            
            if is_defective:
                Defect.objects.create(
                    inspection=inspection,
                    defect_type=random.choice(['Crack', 'Scratch', 'Dent']),
                    severity=random.choice(['Low', 'Medium', 'High'])
                )
                Alert.objects.create(
                    inspection=inspection,
                    message=f"Defect detected in {batch.batch_number}",
                    alert_status='Unread'
                )
    
    print("Specific demo data population complete.")

if __name__ == '__main__':
    populate_specific()
