import os
from PIL import Image, ImageStat, ImageFilter

image_dir = r"c:\work\Defect Detection in Manufacturing\defect_detecter\media\inspection_images"

def get_stats(image_path):
    try:
        with Image.open(image_path) as img:
            img = img.resize((400, 400))
            gray_img = img.convert('L')
            
            brightness = ImageStat.Stat(gray_img).mean[0]
            
            edges = gray_img.filter(ImageFilter.FIND_EDGES)
            edge_score = ImageStat.Stat(edges).stddev[0]
            
            img_rgb = img.convert('RGB')
            img_rgb.thumbnail((150, 150))
            pixels = img_rgb.load()
            w, h = img_rgb.size
            skin_pixels = 0
            for x in range(w):
                for y in range(h):
                    r, g, b = pixels[x, y]
                    if (r > 60 and g > 40 and b > 20 and
                        max(r, g, b) - min(r, g, b) > 10 and
                        r > g and r > b):
                        skin_pixels += 1
            skin_p = (skin_pixels / (w*h)) * 100
            
            print(f"{os.path.basename(image_path):<30} | L: {brightness:5.1f} | E: {edge_score:5.1f} | Skin: {skin_p:4.1f}%")
    except Exception as e:
        pass

files = [
    'live_scan_1772343092420.jpg',
    'live_scan_1772343133340.jpg',
    'live_scan_1772343175399.jpg',
    'live_scan_1772347748187.jpg',
    'defect_image.jpg',
    'images.jfif',
    'test.jpg'
]

for f in files:
    get_stats(os.path.join(image_dir, f))
    
print("-" * 60)
get_stats(r"C:\Users\HP\.gemini\antigravity\brain\4787dc21-19ca-4281-b39f-3ee2c40cb9d4\uploaded_media_1772343014834.png")
