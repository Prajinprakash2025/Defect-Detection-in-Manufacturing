import os
from PIL import Image

image_dir = r"c:\work\Defect Detection in Manufacturing\defect_detecter\media\inspection_images"

def test_heuristic(image_path):
    try:
        with Image.open(image_path) as img:
            img = img.convert('RGB')
            img.thumbnail((150, 150))
            pixels = img.load()
            width, height = img.size
            
            skin_pixels = 0
            total_pixels = width * height
            
            samples = []
            
            for x in range(width):
                for y in range(height):
                    r, g, b = pixels[x, y]
                    if x % 20 == 0 and y % 20 == 0:
                        samples.append((r,g,b))
                    if (r > 60 and g > 40 and b > 20 and
                        max(r, g, b) - min(r, g, b) > 10 and
                        r > g and r > b):
                        skin_pixels += 1
                        
            skin_percentage = (skin_pixels / total_pixels) * 100
            if skin_percentage > 2.0:
                 print(f"{os.path.basename(image_path)}: Skin={skin_percentage:.2f}%")
                 print(f"   Samples: {samples[:5]}")
    except Exception as e:
        pass

for f in os.listdir(image_dir):
    if f.lower().endswith(('.png', '.jpg', '.jpeg', '.jfif')):
        test_heuristic(os.path.join(image_dir, f))

print("\n--- Testing Hand Image Again ---")
test_heuristic(r"C:\Users\HP\.gemini\antigravity\brain\4787dc21-19ca-4281-b39f-3ee2c40cb9d4\uploaded_media_1772343014834.png")

