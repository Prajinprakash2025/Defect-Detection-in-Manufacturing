"""
train_cnn.py  —  CNN-based Defect Classifier  (TensorFlow / Keras)
=================================================================
Uses MobileNetV2 transfer learning for high-accuracy bottle defect detection.
Produces a Keras model (.keras) AND a scikit-learn-compatible .pkl wrapper
so the existing Django `ai_service.py` can load it without changes.

Dataset layout expected:
    ml_models/dataset/good/   — images of good (clean) bottles
    ml_models/dataset/bad/    — images of defective bottles
"""

import os
import sys
import json
import joblib
import numpy as np

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"          # suppress TF info spam

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, callbacks
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from sklearn.metrics import classification_report, confusion_matrix

# ── paths ────────────────────────────────────────────────────────────
BASE       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET    = os.path.join(BASE, "dataset")
OUT_KERAS  = os.path.join(BASE, "defect_cnn_model.keras")
OUT_PKL    = os.path.join(BASE, "defect_classifier.pkl")      # replaces old model

IMG_SIZE   = 224
BATCH      = 16
EPOCHS     = 30            # early-stopping will cut it short if we converge
SEED       = 42

# ── 1.  data generators (heavy augmentation) ────────────────────────
train_datagen = ImageDataGenerator(
    rescale=1.0 / 255,
    rotation_range=40,
    width_shift_range=0.2,
    height_shift_range=0.2,
    shear_range=0.15,
    zoom_range=0.25,
    horizontal_flip=True,
    vertical_flip=True,
    brightness_range=[0.7, 1.3],
    fill_mode="nearest",
    validation_split=0.20,          # 80 / 20 split
)

val_datagen = ImageDataGenerator(
    rescale=1.0 / 255,
    validation_split=0.20,
)

print("Loading dataset …")

train_gen = train_datagen.flow_from_directory(
    DATASET,
    target_size=(IMG_SIZE, IMG_SIZE),
    batch_size=BATCH,
    class_mode="binary",               # good=0  bad=1  (alphabetical)
    subset="training",
    seed=SEED,
    shuffle=True,
    classes=["good", "bad"],            # force:  0 → good,  1 → bad
)

val_gen = val_datagen.flow_from_directory(
    DATASET,
    target_size=(IMG_SIZE, IMG_SIZE),
    batch_size=BATCH,
    class_mode="binary",
    subset="validation",
    seed=SEED,
    shuffle=False,
    classes=["good", "bad"],
)

print(f"  Training   : {train_gen.samples} images")
print(f"  Validation : {val_gen.samples}   images")
print(f"  Class map  : {train_gen.class_indices}")        # {good: 0, bad: 1}

# ── 2.  build model (MobileNetV2 backbone, frozen) ──────────────────
base = MobileNetV2(
    input_shape=(IMG_SIZE, IMG_SIZE, 3),
    include_top=False,
    weights="imagenet",
)
base.trainable = False                                    # freeze backbone

model = keras.Sequential([
    base,
    layers.GlobalAveragePooling2D(),
    layers.BatchNormalization(),
    layers.Dropout(0.4),
    layers.Dense(128, activation="relu"),
    layers.BatchNormalization(),
    layers.Dropout(0.3),
    layers.Dense(1, activation="sigmoid"),                # binary
])

model.compile(
    optimizer=keras.optimizers.Adam(learning_rate=1e-3),
    loss="binary_crossentropy",
    metrics=["accuracy"],
)
model.summary()

# ── 3.  train (frozen backbone) ─────────────────────────────────────
early_stop = callbacks.EarlyStopping(
    monitor="val_accuracy", patience=6, restore_best_weights=True,
)
reduce_lr = callbacks.ReduceLROnPlateau(
    monitor="val_loss", factor=0.5, patience=3, min_lr=1e-6,
)

print("\n=== Phase 1 — Feature Extractor Training ===")
history = model.fit(
    train_gen,
    validation_data=val_gen,
    epochs=EPOCHS,
    callbacks=[early_stop, reduce_lr],
)

# ── 4.  fine-tune (unfreeze last 30 layers) ─────────────────────────
print("\n=== Phase 2 — Fine-Tuning Top Layers ===")
base.trainable = True
for layer in base.layers[:-30]:
    layer.trainable = False

model.compile(
    optimizer=keras.optimizers.Adam(learning_rate=1e-5),       # low lr
    loss="binary_crossentropy",
    metrics=["accuracy"],
)

fine_tune_epochs = 20
history_ft = model.fit(
    train_gen,
    validation_data=val_gen,
    epochs=fine_tune_epochs,
    callbacks=[early_stop, reduce_lr],
)

# ── 5.  evaluate ────────────────────────────────────────────────────
print("\n=== Evaluation ===")
val_gen.reset()
y_pred_prob = model.predict(val_gen, verbose=0).flatten()
y_pred = (y_pred_prob > 0.5).astype(int)
y_true = val_gen.classes

print(classification_report(y_true, y_pred, target_names=["Good", "Defective"]))
cm = confusion_matrix(y_true, y_pred)
print(f"Confusion Matrix:\n{cm}")

val_loss, val_acc = model.evaluate(val_gen, verbose=0)
print(f"\nFinal val_accuracy : {val_acc:.4f}")
print(f"Final val_loss     : {val_loss:.4f}")

# ── 6.  save Keras model ────────────────────────────────────────────
model.save(OUT_KERAS)
print(f"\nKeras model saved → {OUT_KERAS}")


# ── 7.  create .pkl wrapper (drop-in for ai_service.py) ─────────────
class KerasCNNClassifierWrapper:
    """
    Scikit-learn–compatible wrapper so ai_service.py can call:
        clf.predict_proba(features_scaled)
    Instead of features, it accepts the image path directly (see ai_service).
    The wrapper stores the Keras model path and loads it lazily.
    """
    def __init__(self, keras_model_path):
        self.keras_model_path = keras_model_path
        self._model = None

    def _load(self):
        if self._model is None:
            self._model = keras.models.load_model(self.keras_model_path)
        return self._model

    def predict_proba_from_image(self, image_path):
        """Run the CNN directly on an image and return [[p_good, p_bad]]."""
        m = self._load()
        img = keras.utils.load_img(image_path, target_size=(IMG_SIZE, IMG_SIZE))
        arr = keras.utils.img_to_array(img) / 255.0
        arr = np.expand_dims(arr, 0)
        prob_bad = float(m.predict(arr, verbose=0)[0][0])
        prob_good = 1.0 - prob_bad
        return np.array([[prob_good, prob_bad]])        # shape (1, 2)


class DummyScaler:
    """No-op scaler so the existing code path `scaler.transform([features])` works."""
    def transform(self, X):
        return X


wrapper = KerasCNNClassifierWrapper(OUT_KERAS)
model_info = {
    "model": wrapper,
    "scaler": DummyScaler(),
    "label_map": {0: "Product_Clean", 1: "Product_Defective"},
    "backend": "keras_cnn",
}
joblib.dump(model_info, OUT_PKL)
print(f"PKL wrapper saved → {OUT_PKL}")
print("\n✅  Training complete!  Restart Django to pick up the new model.")
