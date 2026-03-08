import os
import json
import joblib
import numpy as np
from PIL import Image, ImageFilter, ImageStat, ImageChops, ImageDraw

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_PATH = os.path.join(BASE_DIR, 'ml_models', 'defect_classifier.pkl')

def is_invalid_capture(features):
    """
    Lightweight heuristic to reject images that clearly are not product scans.
    Tuned on recent false positives (rooms/hands/blank shots).
    """
    brightness, edge_score, r_avg, g_avg, b_avg, skin_ratio = features

    # 1) Almost no edge information -> likely blank/blurred frame
    if edge_score < 18:
        return True, "too_low_edge_detail"

    # 2) Human/scene tones with low texture (rooms, hands in frame)
    if skin_ratio > 0.28 and edge_score < 35 and brightness < 120:
        return True, "non_product_scene_detected"

    return False, None

def extract_features_for_inference(image_path):
    """
    Extracts numerical features from an image to feed the ML model.
    Matches the exact logic used in `train_local_model.py`.
    """
    with Image.open(image_path) as img:
        # 1. Luminance (Brightness)
        gray_img = img.resize((400, 400)).convert('L')
        brightness = ImageStat.Stat(gray_img).mean[0]
        
        # 2. Texture / Edges
        edges = gray_img.filter(ImageFilter.FIND_EDGES)
        edge_score = ImageStat.Stat(edges).stddev[0]
        
        # 3. Color Profile (RGB Averages)
        img_rgb = img.convert('RGB')
        img_rgb.thumbnail((150, 150))
        stat = ImageStat.Stat(img_rgb)
        r_avg, g_avg, b_avg = stat.mean
        
        # 4. Skin Tone Ratio
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
        skin_ratio = skin_pixels / (w * h)
        
        return [brightness, edge_score, r_avg, g_avg, b_avg, skin_ratio]

def load_local_ml_model():
    """Loads the compiled Scikit-Learn `.pkl` model from disk."""
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError("Local ML Model not found! Please run `scripts/train_local_model.py` first.")
    return joblib.load(MODEL_PATH)


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
    Now entirely driven by a trained Random Forest Scikit-Learn classifier!
    """
    try:
        # 1. Extract Features from the incoming image
        features = extract_features_for_inference(image_path)

        # 1b. Hard gate obvious non-product captures before invoking ML
        invalid, reason = is_invalid_capture(features)
        if invalid:
            return {
                'label': 'Invalid / Unwanted Image',
                'confidence': 0.99,
                'is_defective': True,  # treat as a blocking failure, not a pass
                'raw_response': json.dumps({
                    "ai_backend": "heuristic_guard",
                    "features": features,
                    "reason": reason
                })
            }

        # 2. Load the Model
        clf = load_local_ml_model()
        
        # 3. Predict!
        prediction = clf.predict([features])[0]
        probabilities = clf.predict_proba([features])[0]
        confidence = max(probabilities)
        
        # 4. Format the standard system response based on the ML prediction
        if prediction == "Background":
             return {
                'label': 'Invalid / Unwanted Image',
                'confidence': round(confidence, 2),
                'is_defective': True,  # treat background/unwanted frames as blocking errors
                'raw_response': json.dumps({
                    "ai_backend": "sklearn_random_forest", 
                    "features": features,
                    "reason": "background_class_predicted"
                })
             }
             
        elif prediction == "Product_Defective":
             result = {
                'label': 'Physical Crack Detected',
                'confidence': round(confidence, 2),
                'is_defective': True,
                'raw_response': json.dumps({
                    "ai_backend": "sklearn_random_forest", 
                    "features": features
                })
             }
             
        else:
             # Default assumption for Product_Clean
             result = {
                'label': 'Clean Surface Verified',
                'confidence': round(confidence, 2),
                'is_defective': False,
                'raw_response': json.dumps({
                    "ai_backend": "sklearn_random_forest", 
                    "features": features
                })
             }
             
        # --- Inject crack coordinates if defective ---
        if result.get('is_defective'):
            bbox = get_smart_bounding_box(image_path)
            raw_dict = json.loads(result['raw_response'])
            raw_dict['bbox'] = bbox
            result['raw_response'] = json.dumps(raw_dict)

        return result
        
    except Exception as e:
        print(f"Machine Learning Pipeline Error: {e}")
        return {
            'is_defective': True, # Fail safe
            'confidence': 0.99,
            'label': 'System Error',
            'raw_response': json.dumps({"error": str(e)})
        }
