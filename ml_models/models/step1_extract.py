"""
Step 1: Extract deep features from dataset using MobileNetV2
Saves features to a .npz file for Step 2 to train on.
"""
import os, sys, time
import numpy as np
import cv2

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

print("Step 1: Feature Extraction")
print("=" * 50)

import tensorflow as tf
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET = os.path.join(BASE, "dataset")
OUT_NPZ = os.path.join(BASE, "deep_features.npz")
IMG_SIZE = 224

# Load model
print("Loading MobileNetV2 ...")
t0 = time.time()
model = MobileNetV2(
    input_shape=(IMG_SIZE, IMG_SIZE, 3),
    include_top=False,
    weights="imagenet",
    pooling="avg",
)
model.trainable = False
print(f"  Loaded in {time.time()-t0:.1f}s")

# Save feature extractor
fe_path = os.path.join(BASE, "feature_extractor.keras")
model.save(fe_path)
print(f"  Saved feature extractor to {fe_path}")

# Process images
classes = {"good": 0, "bad": 1}
all_features = []
all_labels = []

for cls_name, cls_label in classes.items():
    cls_dir = os.path.join(DATASET, cls_name)
    files = sorted([f for f in os.listdir(cls_dir) 
                     if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))])
    print(f"\nProcessing {cls_name}: {len(files)} files")
    
    batch_imgs = []
    batch_labels = []
    
    for i, fname in enumerate(files):
        img = cv2.imread(os.path.join(cls_dir, fname))
        if img is None:
            continue
        
        # Original + augmented versions
        variants = [
            img,
            cv2.flip(img, 1),
            cv2.flip(img, 0),
            cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE),
            cv2.rotate(img, cv2.ROTATE_180),
        ]
        
        for v in variants:
            rgb = cv2.cvtColor(v, cv2.COLOR_BGR2RGB)
            resized = cv2.resize(rgb, (IMG_SIZE, IMG_SIZE))
            processed = preprocess_input(resized.astype(np.float32))
            batch_imgs.append(processed)
            batch_labels.append(cls_label)
        
        # Extract in batches of 64
        if len(batch_imgs) >= 64:
            batch_arr = np.array(batch_imgs)
            feats = model.predict(batch_arr, verbose=0, batch_size=32)
            all_features.append(feats)
            all_labels.extend(batch_labels)
            batch_imgs = []
            batch_labels = []
            print(f"  ... {i+1}/{len(files)} done ({len(all_labels)} total)")
    
    # Process remaining
    if batch_imgs:
        batch_arr = np.array(batch_imgs)
        feats = model.predict(batch_arr, verbose=0, batch_size=32)
        all_features.append(feats)
        all_labels.extend(batch_labels)
        print(f"  ... {len(files)}/{len(files)} done ({len(all_labels)} total)")

X = np.vstack(all_features)
y = np.array(all_labels)

print(f"\nFinal: X={X.shape}, y={y.shape}")
print(f"Good: {np.sum(y==0)}, Bad: {np.sum(y==1)}")

np.savez_compressed(OUT_NPZ, X=X, y=y)
print(f"Saved to {OUT_NPZ}")
print("Step 1 complete!")
