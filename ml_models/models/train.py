import os
import cv2
import numpy as np
import joblib
import random
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report

def extract_features_from_image(img):
    """88-feature extraction logic."""
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

def augment_image(img):
    """Augmentation."""
    augs = [img] 
    augs.append(cv2.flip(img, 1)) 
    augs.append(cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE))
    augs.append(cv2.rotate(img, cv2.ROTATE_180))
    return augs

def train_model():
    dataset_path = r'c:\work\Defect Detection in Manufacturing\defect_detecter\ml_models\dataset'
    classes = ['good', 'bad']
    
    X = []
    y = []
    
    for cls in classes:
        dir_path = os.path.join(dataset_path, cls)
        print(f"Loading and Augmenting: {cls}...")
        for img_name in os.listdir(dir_path):
            img_path = os.path.join(dir_path, img_name)
            img = cv2.imread(img_path)
            if img is not None:
                variations = augment_image(img)
                for var in variations:
                    features = extract_features_from_image(var)
                    if features:
                        X.append(features)
                        y.append(0 if cls == 'good' else 1)
                
    X = np.array(X, dtype=np.float32)
    y = np.array(y, dtype=np.int32)
    
    print(f"Final Augmented pool: {len(X)} samples")
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.15, random_state=42, stratify=y)
    
    print("Training Optimized MLP...")
    # More regularization to avoid overfitting on the reflection/lighting
    mlp = MLPClassifier(
        hidden_layer_sizes=(128, 64, 32), 
        max_iter=3000, 
        alpha=0.005, # Increased regularization
        activation='relu', 
        solver='adam', 
        random_state=42,
        verbose=False,
        early_stopping=True,
        n_iter_no_change=100
    )
    
    mlp.fit(X_train, y_train)
    
    print("\nTraining Metrics:")
    y_pred = mlp.predict(X_test)
    print(classification_report(y_test, y_pred))
    
    model_info = {
        'model': mlp,
        'scaler': scaler,
        'label_map': {0: 'Product_Clean', 1: 'Product_Defective'}
    }
    dump_path = r'c:\work\Defect Detection in Manufacturing\defect_detecter\ml_models\defect_classifier.pkl'
    joblib.dump(model_info, dump_path)
    print(f"Model saved to {dump_path}")

from sklearn.preprocessing import StandardScaler

if __name__ == "__main__":
    train_model()
