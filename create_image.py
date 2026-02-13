from PIL import Image, ImageDraw

def create_dummy_image():
    img = Image.new('RGB', (200, 200), color = (73, 109, 137))
    d = ImageDraw.Draw(img)
    d.text((10,10), "Test Image", fill=(255,255,0))
    img.save('test_image.jpg')
    print("test_image.jpg created")

if __name__ == "__main__":
    create_dummy_image()
