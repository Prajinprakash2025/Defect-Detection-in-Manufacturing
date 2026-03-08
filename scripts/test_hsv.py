import os
from PIL import Image

image_dir = r"c:\work\Defect Detection in Manufacturing\defect_detecter\media\inspection_images"

def check_hsv(image_path):
    try:
        with Image.open(image_path) as img:
            img = img.convert('HSV')
            img.thumbnail((150, 150))
            pixels = img.load()
            width, height = img.size
            
            skin_pixels = 0
            yellow_pixels = 0
            total_pixels = width * height
            
            for x in range(width):
                for y in range(height):
                    h, s, v = pixels[x, y]
                    
                    # Pillow HSV: H=0-255, S=0-255, V=0-255
                    # Skin Hue is usually 0-25 (0 to 35 degrees)
                    # Yellow Hue is usually 35-60 (50 to 85 degrees)
                    
                    if 0 < h < 25 and s > 40 and v > 40:
                        skin_pixels += 1
                    if 25 <= h < 60 and s > 40 and v > 40:
                        yellow_pixels += 1
                        
            skin_percentage = (skin_pixels / total_pixels) * 100
            yellow_percentage = (yellow_pixels / total_pixels) * 100
            
            # Print if it has significant skin or yellow
            if skin_percentage > 2 or yellow_percentage > 2:
                print(f"{os.path.basename(image_path)}: Skin={skin_percentage:.1f}%, Yellow={yellow_percentage:.1f}%")
                
    except Exception as e:
        pass

for f in ['live_scan_1772343092420.jpg', 'defect_image.jpg', 'images.jfif']:
    check_hsv(os.path.join(image_dir, f))

print("\n--- Testing Hand Image Again ---")
check_hsv(r"C:\Users\HP\.gemini\antigravity\brain\4787dc21-19ca-4281-b39f-3ee2c40cb9d4\uploaded_media_1772343014834.png")

