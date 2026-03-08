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

print("Running ML Defect Classifier on existing images...\n")
for f in files_to_test + os.listdir(image_dir)[:10]:
    path = os.path.join(image_dir, f)
    if os.path.isfile(path):
        try:
            result = detect_defect(path)
            label = result.get('label')
            
            if not result.get('is_defective') and label == 'Invalid / Unwanted Image':
                print(f"[REJECTED] {f[:30]:<30} -> {label}")
            else:
                print(f"[  PASS  ] {f[:30]:<30} -> {label}")
        except Exception as e:
            print(f"[ ERROR  ] {f[:30]:<30} -> {e}")
