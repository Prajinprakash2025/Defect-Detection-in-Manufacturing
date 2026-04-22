import cv2
import joblib
import numpy as np
import os
import json
from PIL import Image, ImageFilter, ImageStat, ImageChops, ImageDraw

# Suppress TensorFlow noise
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

# YOLO optional toggle
USE_YOLO = os.getenv("USE_YOLO", "0") == "1"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_PATH = os.path.join(BASE_DIR, 'ml_models', 'defect_classifier.pkl')

IMG_SIZE = 224

# Singleton caches
_CACHED_MODEL_DATA = None
_CACHED_FEATURE_EXTRACTOR = None


def load_feature_extractor():
    """Load the MobileNetV2 feature extractor (Keras SavedModel)."""
    global _CACHED_FEATURE_EXTRACTOR
    if _CACHED_FEATURE_EXTRACTOR is not None:
        return _CACHED_FEATURE_EXTRACTOR

    from tensorflow import keras
    feature_path = os.path.join(BASE_DIR, 'ml_models', 'feature_extractor.keras')
    if os.path.exists(feature_path):
        _CACHED_FEATURE_EXTRACTOR = keras.models.load_model(feature_path)
        print(f"[AI] Loaded deep feature extractor from {feature_path}")
        return _CACHED_FEATURE_EXTRACTOR

    # Fallback: create fresh MobileNetV2
    from tensorflow.keras.applications import MobileNetV2
    _CACHED_FEATURE_EXTRACTOR = MobileNetV2(
        input_shape=(IMG_SIZE, IMG_SIZE, 3),
        include_top=False,
        weights="imagenet",
        pooling="avg",
    )
    _CACHED_FEATURE_EXTRACTOR.trainable = False
    print("[AI] Created fresh MobileNetV2 feature extractor.")
    return _CACHED_FEATURE_EXTRACTOR


def load_local_ml_model():
    """Loads the model bundle from disk once and caches it."""
    global _CACHED_MODEL_DATA
    if _CACHED_MODEL_DATA is not None:
        return _CACHED_MODEL_DATA

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"ML Model not found at {MODEL_PATH}")

    _CACHED_MODEL_DATA = joblib.load(MODEL_PATH)
    return _CACHED_MODEL_DATA


def extract_deep_features(image_path):
    """
    Extract 1280-dim deep features from an image using MobileNetV2.
    """
    from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

    extractor = load_feature_extractor()
    img = cv2.imread(image_path)
    if img is None:
        return None

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img_resized = cv2.resize(img_rgb, (IMG_SIZE, IMG_SIZE))
    img_array = img_resized.astype(np.float32)
    img_preprocessed = preprocess_input(img_array)
    batch = np.expand_dims(img_preprocessed, axis=0)
    features = extractor.predict(batch, verbose=0)
    return features.flatten()


def get_smart_bounding_box(image_path):
    """Generates a focus box for the UI to highlight suspected anomalies."""
    try:
        with Image.open(image_path) as img:
            img = img.resize((400, 400)).convert('L')
            edges = img.filter(ImageFilter.FIND_EDGES)
            binary = edges.point(lambda p: 255 if p > 80 else 0)

            # Mask borders
            draw = ImageDraw.Draw(binary)
            draw.rectangle([0, 0, 400, 100], fill=0)
            draw.rectangle([0, 300, 400, 400], fill=0)
            draw.rectangle([0, 0, 100, 400], fill=0)
            draw.rectangle([300, 0, 400, 400], fill=0)

            bbox = binary.getbbox()
            if bbox:
                left, top, right, bottom = bbox
                return {
                    "left": float(max(0, ((left / 400) * 100) - 2)),
                    "top": float(max(0, ((top / 400) * 100) - 2)),
                    "width": float(min(100, (((right - left) / 400) * 100) + 4)),
                    "height": float(min(100, (((bottom - top) / 400) * 100) + 4))
                }
    except:
        pass
    return {"top": 45, "left": 45, "width": 10, "height": 10}


def detect_defect(image_path):
    """
    Main AI Pipeline.
    Uses MobileNetV2 deep features + trained ensemble classifier.
    """
    try:
        # 1. Load model bundle
        model_data = load_local_ml_model()
        clf = model_data['model']
        scaler = model_data['scaler']
        backend = model_data.get('backend', 'sklearn_mlp')

        if backend == 'deep_ensemble':
            # ── Deep Feature Ensemble Path ────────────────────────
            features = extract_deep_features(image_path)
            if features is None:
                return {
                    'label': 'Invalid Capture',
                    'confidence': 0.99,
                    'is_defective': True,
                    'raw_response': json.dumps({"reason": "image_read_failed"})
                }
            features_scaled = scaler.transform([features])
            # Apply PCA if present in model bundle
            pca = model_data.get('pca')
            if pca is not None:
                features_scaled = pca.transform(features_scaled)
            probs = clf.predict_proba(features_scaled)[0]
            clean_prob = float(probs[0])
            defective_prob = float(probs[1])
            ai_backend = "deep_ensemble"

        elif backend == 'keras_cnn':
            # ── Keras CNN wrapper path ────────────────────────────
            probs = clf.predict_proba_from_image(image_path)
            clean_prob = float(probs[0][0])
            defective_prob = float(probs[0][1])
            ai_backend = "keras_cnn"

        else:
            # ── Legacy MLP path ───────────────────────────────────
            features = extract_legacy_features(image_path)
            if features is None or len(features) < 80:
                return {
                    'label': 'Invalid Capture',
                    'confidence': 0.99,
                    'is_defective': True,
                    'raw_response': json.dumps({"reason": "feature_extraction_failed"})
                }
            features_scaled = scaler.transform([features])
            probs = clf.predict_proba(features_scaled)[0]
            clean_prob = float(probs[0])
            defective_prob = float(probs[1])
            ai_backend = "sklearn_mlp"

        # ── Decision Logic ────────────────────────────────────────
        if defective_prob > 0.55:
            label = 'Physical Crack Detected'
            is_def = True
            conf = defective_prob
        else:
            label = 'Clean Surface Verified'
            is_def = False
            conf = clean_prob

        result = {
            'label': label,
            'confidence': float(round(conf, 2)),
            'is_defective': is_def,
            'raw_response': json.dumps({
                "ai_backend": ai_backend,
                "defective_probability": round(defective_prob, 4),
                "clean_probability": round(clean_prob, 4),
            })
        }

        if is_def:
            raw_dict = json.loads(result['raw_response'])
            raw_dict['bbox'] = get_smart_bounding_box(image_path)
            result['raw_response'] = json.dumps(raw_dict)

        return result

    except Exception as e:
        print(f"AI Pipeline Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            'is_defective': True,
            'confidence': 0.99,
            'label': 'System Error',
            'raw_response': json.dumps({"error": str(e)})
        }


# ── Legacy feature extraction (kept as fallback) ──────────────────────
def extract_legacy_features(image_path):
    """88-feature extraction using OpenCV (legacy MLP model)."""
    try:
        img = cv2.imread(image_path)
        if img is None: return None
        img_resized = cv2.resize(img, (224, 224))

        hsv = cv2.cvtColor(img_resized, cv2.COLOR_BGR2HSV)
        h_hist = cv2.calcHist([hsv], [0], None, [16], [0, 180]).flatten().tolist()
        s_hist = cv2.calcHist([hsv], [1], None, [16], [0, 256]).flatten().tolist()
        v_hist = cv2.calcHist([hsv], [2], None, [16], [0, 256]).flatten().tolist()

        b, g, r = cv2.split(img_resized)
        stats = []
        for chan in [b, g, r, hsv[:,:,0], hsv[:,:,1], hsv[:,:,2]]:
            stats.append(float(np.mean(chan)))
            stats.append(float(np.std(chan)))
            stats.append(float(np.max(chan) - np.min(chan)))
            stats.append(float(np.median(chan)))

        gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
        edges_low = cv2.Canny(gray, 50, 100)
        edges_high = cv2.Canny(gray, 150, 200)
        edge_stats = [
            float(np.sum(edges_low > 0) / (224 * 224)),
            float(np.sum(edges_high > 0) / (224 * 224))
        ]
        laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=5)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=5)
        sobel_mag = np.sqrt(sobelx**2 + sobely**2)
        sobel_stats = [float(np.mean(sobel_mag)), float(np.std(sobel_mag))]

        moments = cv2.moments(gray)
        hu_moments_raw = cv2.HuMoments(moments).flatten()
        hu_moments = (-np.sign(hu_moments_raw) * np.log10(np.abs(hu_moments_raw) + 1e-10)).tolist()

        diff_r = gray[:, 1:] - gray[:, :-1]
        diff_d = gray[1:, :] - gray[:-1, :]
        texture_stats = [float(np.mean(np.abs(diff_r))), float(np.std(diff_r)),
                         float(np.mean(np.abs(diff_d))), float(np.std(diff_d))]

        return h_hist + s_hist + v_hist + stats + edge_stats + [laplacian_var] + sobel_stats + hu_moments + texture_stats

    except Exception as e:
        print(f"Feature Extraction Error: {e}")
        return None
