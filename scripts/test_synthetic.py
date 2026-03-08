import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'defect_detection.settings')
django.setup()
from inspections.services.ai_service import detect_defect

image_dir = r"c:\work\Defect Detection in Manufacturing\defect_detecter\media\test_images"
for f in os.listdir(image_dir):
    path = os.path.join(image_dir, f)
    res = detect_defect(path)
    print(f"{f}: {res.get('label')} (Confidence: {res.get('confidence')})")
