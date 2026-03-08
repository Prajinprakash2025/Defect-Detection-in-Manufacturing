import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'defect_detection.settings')
django.setup()

from inspections.services.ai_service import detect_defect

image_path = r"C:\Users\HP\.gemini\antigravity\brain\4787dc21-19ca-4281-b39f-3ee2c40cb9d4\uploaded_media_1772343014834.png"

print("--- Testing Hand Image ---")
result = detect_defect(image_path)
print(f"Result: {result}")
if result.get('label') == 'Invalid / Unwanted Image' and not result.get('is_defective'):
    print("✅ SUCCESS: Hand was detected and marked as non-defective/unwanted.")
else:
    print("❌ FAILURE: Hand was not properly filtered.")
