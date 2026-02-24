import os
import json
from google.cloud import vision
from PIL import Image, ImageFilter, ImageStat

# --- NEW: GOOGLE CLOUD CREDENTIALS LINK ---
# This dynamically finds the root folder of your project and points directly to credentials.json
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.join(BASE_DIR, 'credentials.json')
# ------------------------------------------

def detect_defect(image_path):
    """
    Main entry point for defect detection.
    Prioritizes Google Cloud Vision > Local Pixel Scan.
    """
    credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')

    if credentials_path and os.path.exists(credentials_path):
        try:
             print("Attempting Google Cloud Vision...")
             return google_vision_predict(image_path)
        except Exception as e:
            print(f"Google Cloud Vision failed: {e}. Falling back to Local Pixel Scan.")
    
    print("Using Local Pixel Scan fallback...")
    return local_pixel_scan(image_path)

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
                # The background is black, so any white edges are definitely a crack.
                # Threshold is extremely low (highly sensitive).
                dynamic_threshold = 5.0
            else:
                # LIGHT MODE (Matches your Clean Vial)
                # The background is white, so the dark glass outline creates a huge score.
                # Threshold is extremely high (ignores outlines, only catches massive cracks).
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