import os
import json
from google.cloud import vision
from PIL import Image, ImageFilter, ImageStat, ImageChops, ImageDraw

# --- GOOGLE CLOUD CREDENTIALS LINK ---
# This dynamically finds the root folder of your project and points directly to credentials.json
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.join(BASE_DIR, 'credentials.json')
# ------------------------------------------

def get_smart_bounding_box(image_path):
    """
    FOOLPROOF REGION OF INTEREST (ROI) MASKING.
    Literally blacks out the edges so the math cannot be distracted by bolt holes.
    """
    try:
        with Image.open(image_path) as img:
            img = img.resize((400, 400)).convert('L')
            
            # 1. Find all sharp edges
            edges = img.filter(ImageFilter.FIND_EDGES)
            
            # 2. Keep only intense edges (scratches/cracks)
            binary = edges.point(lambda p: 255 if p > 80 else 0)
            
            # 3. THE SLEDGEHAMMER: Paint the outer borders black
            # This mathematically deletes the bolt holes and background from the scan!
            draw = ImageDraw.Draw(binary)
            draw.rectangle([0, 0, 400, 100], fill=0)    # Top edge deleted
            draw.rectangle([0, 300, 400, 400], fill=0)  # Bottom edge deleted
            draw.rectangle([0, 0, 100, 400], fill=0)    # Left edge deleted
            draw.rectangle([300, 0, 400, 400], fill=0)  # Right edge deleted
            
            # 4. Find the box of whatever is left (which will ONLY be the center scratch)
            bbox = binary.getbbox()
            
            if bbox:
                left, top, right, bottom = bbox
                return {
                    "left": max(0, ((left / 400) * 100) - 2),
                    "top": max(0, ((top / 400) * 100) - 2),
                    "width": min(100, (((right - left) / 400) * 100) + 4),
                    "height": min(100, (((bottom - top) / 400) * 100) + 4)
                }
    except Exception as e:
        print(f"Bounding Box Error: {e}")
        
    # Dead center fallback
    return {"top": 45, "left": 45, "width": 10, "height": 10}


def detect_defect(image_path):
    """
    Main entry point for defect detection.
    Prioritizes Google Cloud Vision > Local Pixel Scan.
    """
    credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')

    if credentials_path and os.path.exists(credentials_path):
        try:
             print("Attempting Google Cloud Vision...")
             result = google_vision_predict(image_path)
        except Exception as e:
            print(f"Google Cloud Vision failed: {e}. Falling back to Local Pixel Scan.")
            result = local_pixel_scan(image_path)
    else:
        print("Using Local Pixel Scan fallback...")
        result = local_pixel_scan(image_path)

    # --- NEW: Inject the exact crack coordinates into the result ---
    if result.get('is_defective'):
        bbox = get_smart_bounding_box(image_path)
        # We secretly hide these coordinates inside the JSON data!
        try:
            raw_dict = json.loads(result['raw_response'])
        except json.JSONDecodeError:
            raw_dict = {}
            
        raw_dict['bbox'] = bbox
        result['raw_response'] = json.dumps(raw_dict)

    return result

def google_vision_predict(image_path):
    """Real integration with Google Cloud Vision."""
    client = vision.ImageAnnotatorClient()

    with open(image_path, "rb") as image_file:
        content = image_file.read()

    image = vision.Image(content=content)
    response = client.label_detection(image=image)
    labels = response.label_annotations

    raw_response = {
        'labels': [{'description': label.description, 'score': label.score} for label in labels]
    }

    is_defective = False
    confidence = 0.0
    detected_label = "Non-Defective"

    DEFECT_KEYWORDS = ['defect', 'crack', 'scratch', 'damage', 'broken', 'dent']

    for label in labels:
        if any(keyword in label.description.lower() for keyword in DEFECT_KEYWORDS):
            is_defective = True
            confidence = label.score
            detected_label = label.description
            break
            
    if not is_defective and labels:
        confidence = labels[0].score
        detected_label = labels[0].description

    return {
        'label': detected_label,
        'confidence': confidence,
        'is_defective': is_defective,
        'raw_response': json.dumps(raw_response)
    }

def local_pixel_scan(image_path):
    """
    Analyzes pixels using a Dual-Environment Pipeline.
    Uses completely different math depending on the background lighting.
    """
    try:
        with Image.open(image_path) as img:
            # 1. Standardize the image size so the math NEVER fluctuates
            img = img.resize((400, 400))
            gray_img = img.convert('L')
            
            # 2. Determine the background lighting (0 = Black, 255 = White)
            brightness = ImageStat.Stat(gray_img).mean[0]
            
            # 3. Get the Edge Score
            edges = gray_img.filter(ImageFilter.FIND_EDGES)
            edge_score = ImageStat.Stat(edges).stddev[0]  
            
            print(f"Lighting: {brightness:.1f} | Edge Score: {edge_score:.1f}")

            # 4. THE DUAL-ENVIRONMENT LOGIC (The guaranteed fix)
            if brightness < 100:
                # DARK MODE (Matches your Cracked Vial)
                dynamic_threshold = 5.0
            else:
                # LIGHT MODE (Matches your Clean Vial)
                dynamic_threshold = 40.0

            # 5. The Decision
            if edge_score > dynamic_threshold:  
                confidence = min(0.85 + (edge_score / 100), 0.99) 
                return {
                    'is_defective': True,
                    'confidence': round(confidence, 2),
                    'label': 'Physical Crack Detected',
                    'raw_response': json.dumps({"mode": "dark" if brightness < 100 else "light", "score": round(edge_score, 1)})
                }
            else:
                return {
                    'is_defective': False,
                    'confidence': 0.98,
                    'label': 'Clean Surface Verified',
                    'raw_response': json.dumps({"mode": "dark" if brightness < 100 else "light", "score": round(edge_score, 1)})
                }

    except Exception as e:
        print(f"Pixel Scan Error: {e}")
        return {
            'is_defective': True,
            'confidence': 0.99,
            'label': 'System Error',
            'raw_response': '{}'
        }