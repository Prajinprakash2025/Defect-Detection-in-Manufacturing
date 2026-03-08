import os
from PIL import Image, ImageDraw

os.makedirs('media/test_images', exist_ok=True)

print("Generating synthetic images for testing...")

def draw_synthetic_part(color=(200, 200, 80), defect=False):
    img = Image.new('RGB', (400, 400), color=(120, 120, 120)) # Factory background
    draw = ImageDraw.Draw(img)
    # Draw the main "gear"
    draw.ellipse([100, 100, 300, 300], fill=color)
    draw.ellipse([150, 150, 250, 250], fill=(120, 120, 120)) # Hole in middle
    
    if defect:
        # Add high-contrast jagged lines to simulate physical cracks
        draw.line([160, 100, 180, 200, 150, 300], fill=(20, 20, 20), width=6)
        draw.line([250, 120, 220, 180], fill=(20, 20, 20), width=4)
        print(" -> Generated Defective Part")
    else:
        print(" -> Generated Clean Part")
        
    return img

clean = draw_synthetic_part(defect=False)
clean.save('media/test_images/synthetic_clean.jpg')

defect = draw_synthetic_part(defect=True)
defect.save('media/test_images/synthetic_defect.jpg')

clean2 = draw_synthetic_part(color=(150, 180, 200), defect=False) # Blueish metal
clean2.save('media/test_images/synthetic_clean_blue.jpg')

defect2 = draw_synthetic_part(color=(150, 180, 200), defect=True) # Blueish metal crack
defect2.save('media/test_images/synthetic_defect_blue.jpg')

print("Images generated successfully in media/test_images/")
