import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'defect_detection.settings')
django.setup()

from core_inventory.models import Product

def update_guides():
    updates = {
        'Ceramic Insulator': "Looks like: A white ceramic coffee mug with a black rim. Select this if you are inspecting mugs.",
        'Polymer Container': "Looks like: A clear plastic water bottle. Select this for all transparent bottle inspections.",
        'Smart Display': "Looks like: A black rectangular smartphone screen or PCB board."
    }

    for name, guide in updates.items():
        try:
            # Case-insensitive search to be safe
            products = Product.objects.filter(name__iexact=name)
            if products.exists():
                for product in products:
                    product.visual_guide = guide
                    product.save()
                    print(f"Updated '{product.name}' with visual guide.")
            else:
                print(f"Product '{name}' not found.")
        except Exception as e:
            print(f"Error updating '{name}': {e}")

if __name__ == "__main__":
    update_guides()
