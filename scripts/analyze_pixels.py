import os
from PIL import Image

image_path = r"C:\Users\HP\.gemini\antigravity\brain\4787dc21-19ca-4281-b39f-3ee2c40cb9d4\uploaded_media_1772343014834.png"

with Image.open(image_path) as img:
    img = img.convert('RGB')
    img.thumbnail((150, 150))
    pixels = img.load()
    width, height = img.size
    
    samples = []
    r_sum, g_sum, b_sum = 0, 0, 0
    valid_skin = 0
    total_pixels = width * height
    
    for x in range(width):
        for y in range(height):
            r, g, b = pixels[x, y]
            if x % 15 == 0 and y % 15 == 0:
                samples.append((r,g,b))
            
            if (r > 60 and g > 40 and b > 20 and max(r, g, b) - min(r, g, b) > 10 and r > g and r > b):
                valid_skin += 1
                
    with open("scripts/analyze_out.txt", "w", encoding="utf-8") as f:
        f.write(f"Total Pixels: {total_pixels}\n")
        f.write(f"Valid Skin: {valid_skin} ({(valid_skin/total_pixels)*100:.2f}%)\n")
        f.write(f"Samples: {samples}\n")
