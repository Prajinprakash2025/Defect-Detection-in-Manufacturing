import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'defect_detection.settings')
django.setup()

from core_inventory.models import Product, Batch
from inspections.models import Inspection
from django.core.files.uploadedfile import SimpleUploadedFile

def verify_backend():
    print("Verifying Backend Logic...")
    
    # 1. Create Product
    product = Product.objects.create(name="Test Widget", category="Parts", description="Test Desc")
    print(f"[PASS] Product Created: {product.name}")

    # 2. Create Batch
    batch = Batch.objects.create(product=product, batch_number="TW-001", quantity=100)
    print(f"[PASS] Batch Created: {batch.batch_number}")

    # 3. Create Inspection linked to Batch
    with open('test_image.jpg', 'rb') as f:
        image = SimpleUploadedFile("test.jpg", f.read(), content_type="image/jpeg")
    
    inspection = Inspection.objects.create(batch=batch, image=image, uploaded_by_id=1) # Assuming admin is ID 1
    print(f"[PASS] Inspection Created linked to Batch: {inspection.batch.batch_number}")

    if inspection.batch.batch_number == "TW-001":
        print("Backend Verification SUCCESS!")
    else:
        print("Backend Verification FAILED!")

if __name__ == "__main__":
    verify_backend()
