"""
train_final.py  -  Production Defect Classifier (Optimized)
===========================================================
Uses MobileNetV2 as a fixed feature extractor + ensemble classifier.
Optimized for CPU: batch prediction, less augmentation.
"""

import os, sys, json, time
import numpy as np
import joblib
import cv2
import random
from collections import Counter

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.metrics import classification_report, confusion_matrix

# ---- paths ----------------------------------------------------------------
BASE       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET    = os.path.join(BASE, "dataset")
OUT_PKL    = os.path.join(BASE, "defect_classifier.pkl")

IMG_SIZE   = 224
SEED       = 42
random.seed(SEED)
np.random.seed(SEED)

# ---- 1. Build Feature Extractor ------------------------------------------
print("Loading MobileNetV2 ...")
t0 = time.time()
base_model = MobileNetV2(
    input_shape=(IMG_SIZE, IMG_SIZE, 3),
    include_top=False,
    weights="imagenet",
    pooling="avg",
)
base_model.trainable = False
print(f"  Loaded in {time.time()-t0:.1f}s  (output: {base_model.output_shape[-1]}-dim)")


def load_and_augment(img_path):
    """Load image + create augmented versions. Returns list of BGR images."""
    img = cv2.imread(img_path)
    if img is None:
        return []
    imgs = [img]
    imgs.append(cv2.flip(img, 1))                          # h-flip
    imgs.append(cv2.flip(img, 0))                          # v-flip
    imgs.append(cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE))  # 90 CW
    imgs.append(cv2.rotate(img, cv2.ROTATE_180))           # 180
    return imgs


def batch_extract_features(images, batch_size=32):
    """Extract features from a list of BGR images using batch prediction."""
    all_features = []
    for i in range(0, len(images), batch_size):
        batch_imgs = images[i:i+batch_size]
        processed = []
        for img in batch_imgs:
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            resized = cv2.resize(rgb, (IMG_SIZE, IMG_SIZE))
            arr = resized.astype(np.float32)
            processed.append(preprocess_input(arr))
        batch_arr = np.array(processed)
        feats = base_model.predict(batch_arr, verbose=0)
        all_features.append(feats)
    return np.vstack(all_features)


# ---- 2. Load Dataset -----------------------------------------------------
print("\nLoading and augmenting dataset ...")
t0 = time.time()

classes = {"good": 0, "bad": 1}
all_images = []
all_labels = []

for cls_name, cls_label in classes.items():
    cls_dir = os.path.join(DATASET, cls_name)
    files = sorted([f for f in os.listdir(cls_dir) 
                     if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))])
    print(f"  {cls_name}: {len(files)} images")
    
    for fname in files:
        fpath = os.path.join(cls_dir, fname)
        augmented = load_and_augment(fpath)
        for aug_img in augmented:
            all_images.append(aug_img)
            all_labels.append(cls_label)

y = np.array(all_labels, dtype=np.int32)
print(f"  Total samples: {len(all_images)} ({time.time()-t0:.1f}s)")
print(f"  Class distribution: {Counter(y)}")

# ---- 3. Extract Features (batched) ----------------------------------------
print("\nExtracting MobileNetV2 features (batched) ...")
t0 = time.time()
X = batch_extract_features(all_images, batch_size=32)
print(f"  Done: {X.shape} in {time.time()-t0:.1f}s")

# ---- 4. Train/Test Split --------------------------------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.15, random_state=SEED, stratify=y
)
print(f"\nTrain: {len(X_train)}, Test: {len(X_test)}")

# ---- 5. Scale Features ---------------------------------------------------
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# ---- 6. Train Classifiers ------------------------------------------------
print("\n=== Training Classifiers ===")

print("  SVM ...")
svm = SVC(kernel='rbf', C=10.0, gamma='scale', probability=True,
          random_state=SEED, class_weight='balanced')
svm.fit(X_train_scaled, y_train)
svm_acc = svm.score(X_test_scaled, y_test)
print(f"    SVM accuracy: {svm_acc:.4f}")

print("  Random Forest ...")
rf = RandomForestClassifier(n_estimators=300, max_depth=20,
                             min_samples_split=5, random_state=SEED,
                             class_weight='balanced', n_jobs=-1)
rf.fit(X_train_scaled, y_train)
rf_acc = rf.score(X_test_scaled, y_test)
print(f"    RF accuracy:  {rf_acc:.4f}")

print("  Gradient Boosting ...")
gb = GradientBoostingClassifier(n_estimators=200, learning_rate=0.05,
                                 max_depth=5, subsample=0.8, random_state=SEED)
gb.fit(X_train_scaled, y_train)
gb_acc = gb.score(X_test_scaled, y_test)
print(f"    GB accuracy:  {gb_acc:.4f}")

print("  Ensemble ...")
ensemble = VotingClassifier(
    estimators=[('svm', svm), ('rf', rf), ('gb', gb)],
    voting='soft',
)
ensemble.fit(X_train_scaled, y_train)
ens_acc = ensemble.score(X_test_scaled, y_test)
print(f"    Ensemble accuracy: {ens_acc:.4f}")

# Pick best
best_name, best_acc, final_model = "Ensemble", ens_acc, ensemble
for nm, ac, mdl in [("SVM", svm_acc, svm), ("RF", rf_acc, rf), ("GB", gb_acc, gb)]:
    if ac > best_acc + 0.02:
        best_name, best_acc, final_model = nm, ac, mdl

print(f"\n  Using: {best_name} ({best_acc:.4f})")

# ---- 7. Full Report -------------------------------------------------------
print("\n=== Classification Report ===")
y_pred = final_model.predict(X_test_scaled)
print(classification_report(y_test, y_pred, target_names=["Good", "Defective"]))
cm = confusion_matrix(y_test, y_pred)
print(f"Confusion Matrix:\n{cm}\n")

# ---- 8. Sanity Check -------------------------------------------------------
print("=== Sanity Check (10 good + 10 bad) ===")
correct = 0
total = 0
for cls_name, cls_label in classes.items():
    cls_dir = os.path.join(DATASET, cls_name)
    files = sorted(os.listdir(cls_dir))[:10]
    for fname in files:
        fpath = os.path.join(cls_dir, fname)
        img = cv2.imread(fpath)
        if img is None: continue
        feats = batch_extract_features([img], batch_size=1)
        feats_scaled = scaler.transform(feats)
        probs = final_model.predict_proba(feats_scaled)[0]
        pred = "BAD" if np.argmax(probs) == 1 else "GOOD"
        true = "BAD" if cls_label == 1 else "GOOD"
        ok = "OK" if pred == true else "WRONG"
        print(f"  [{ok}] {fname:40s} p_good={probs[0]:.3f} p_bad={probs[1]:.3f} pred={pred} true={true}")
        if pred == true: correct += 1
        total += 1
print(f"\nSanity: {correct}/{total} ({100*correct/total:.0f}%)")

# ---- 9. Save Model -------------------------------------------------------
# Save feature extractor
fe_path = os.path.join(BASE, "feature_extractor")
base_model.save(fe_path)
print(f"\nFeature extractor saved: {fe_path}")

# Save PKL bundle
model_info = {
    "model": final_model,
    "scaler": scaler,
    "label_map": {0: "Product_Clean", 1: "Product_Defective"},
    "backend": "deep_ensemble",
    "feature_extractor_path": fe_path,
    "img_size": IMG_SIZE,
}
joblib.dump(model_info, OUT_PKL)
print(f"Model saved: {OUT_PKL}")
print(f"\nFinal accuracy: {best_acc:.4f}")
print("Done! Restart Django to use the new model.")
