import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'defect_detection.settings')
django.setup()

from inspections.models import Inspection, Defect, Alert

def cleanup():
    print("Starting cleanup of old inspections (#1-#22)...")
    
    # Delete IDs 1 through 22
    inspections_to_delete = Inspection.objects.filter(id__lte=22)
    count = inspections_to_delete.count()
    
    if count > 0:
        inspections_to_delete.delete()
        print(f"✓ Successfully deleted {count} old inspection records (IDs 1-22).")
    else:
        print("No records found in range 1-22.")
        
    # Optional: Delete any with "Unknown" label if requested, but user said "like IDs #1-#22"
    # We will stick to the ID range for safety unless user specified otherwise.
    
    print("Cleanup complete.")

if __name__ == "__main__":
    cleanup()
