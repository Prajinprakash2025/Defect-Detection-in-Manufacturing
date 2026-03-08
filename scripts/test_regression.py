import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'defect_detection.settings')
django.setup()

from inspections.services.ai_service import detect_defect

image_dir = r"c:\work\Defect Detection in Manufacturing\defect_detecter\media\inspection_images"

files_to_test = [
    'live_scan_1772343092420.jpg', 
    'defect_image.jpg', 
    'images.jfif', 
    'test.jpg'
]

for f in files_to_test + os.listdir(image_dir)[:5]:
    path = os.path.join(image_dir, f)
    if os.path.isfile(path):
        result = detect_defect(path)
        if not result.get('is_defective') and result.get('label') == 'Invalid / Unwanted Image':
            print(f"❌ FAILURE: {f} was incorrectly marked as Unwanted!")
        else:
            print(f"✅ PASS: {f} processed correctly. Label: {result.get('label')}")
