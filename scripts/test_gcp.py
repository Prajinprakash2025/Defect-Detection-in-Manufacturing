import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'defect_detection.settings')
django.setup()

from inspections.services.ai_service import detect_defect

print("Testing Google Cloud Vision Integration with provided credentials.json...")

image_path = r"c:\work\Defect Detection in Manufacturing\defect_detecter\media\inspection_images\defect_image.jpg"

try:
    if not os.path.exists(image_path):
        print(f"Error: Could not find image at {image_path}")
    else:
        result = detect_defect(image_path)
        print("\n=== AI Service Result ===")
        print(f"Defective: {result.get('is_defective')}")
        print(f"Label: {result.get('label')}")
        print(f"Confidence: {result.get('confidence')}")
        print(f"Raw Response: {result.get('raw_response')}")
except Exception as e:
    print(f"Error occurred during testing: {e}")
