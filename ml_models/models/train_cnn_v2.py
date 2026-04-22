"""
train_cnn_v2.py - Production-grade CNN Defect Classifier
========================================================
Uses MobileNetV2 backbone with careful training strategy for small datasets.
Key improvements:
  - Only trains the classification head (backbone fully frozen)
  - Heavy data augmentation to compensate for small dataset
  - Class-weight balancing (275 good vs 225 bad)
  - Longer patience for early stopping
"""

import os, sys, json
import numpy as np

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, callbacks
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from sklearn.metrics import classification_report, confusion_matrix
import joblib

# -- paths -----------------------------------------------------------------
BASE       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET    = os.path.join(BASE, "dataset")
OUT_KERAS  = os.path.join(BASE, "defect_cnn_model.keras")
OUT_PKL    = os.path.join(BASE, "defect_classifier.pkl")

IMG_SIZE   = 224
BATCH      = 8           # small batch for small dataset
SEED       = 42

# -- class weights (275 good, 225 bad) ------------------------------------
total = 500
n_good, n_bad = 275, 225
class_weight = {
    0: total / (2 * n_good),   # 0.909
    1: total / (2 * n_bad),    # 1.111
}
print(f"Class weights: {class_weight}")

# -- data generators -------------------------------------------------------
train_datagen = ImageDataGenerator(
    rescale=1.0 / 255,
    rotation_range=90,
    width_shift_range=0.15,
    height_shift_range=0.15,
    shear_range=0.1,
    zoom_range=0.2,
    horizontal_flip=True,
    vertical_flip=True,
    brightness_range=[0.75, 1.25],
    channel_shift_range=20,
    fill_mode="nearest",
    validation_split=0.20,
)

val_datagen = ImageDataGenerator(
    rescale=1.0 / 255,
    validation_split=0.20,
)

print("Loading dataset ...")

train_gen = train_datagen.flow_from_directory(
    DATASET,
    target_size=(IMG_SIZE, IMG_SIZE),
    batch_size=BATCH,
    class_mode="binary",
    subset="training",
    seed=SEED,
    shuffle=True,
    classes=["good", "bad"],
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
print(f"  Class map  : {train_gen.class_indices}")

# -- build model -----------------------------------------------------------
base = MobileNetV2(
    input_shape=(IMG_SIZE, IMG_SIZE, 3),
    include_top=False,
    weights="imagenet",
)
base.trainable = False     # FULLY FROZEN - critical for small datasets

model = keras.Sequential([
    base,
    layers.GlobalAveragePooling2D(),
    layers.Dense(256, activation="relu",
                 kernel_regularizer=keras.regularizers.l2(0.01)),
    layers.Dropout(0.5),
    layers.Dense(128, activation="relu",
                 kernel_regularizer=keras.regularizers.l2(0.01)),
    layers.Dropout(0.4),
    layers.Dense(64, activation="relu",
                 kernel_regularizer=keras.regularizers.l2(0.01)),
    layers.Dropout(0.3),
    layers.Dense(1, activation="sigmoid"),
])

model.compile(
    optimizer=keras.optimizers.Adam(learning_rate=1e-3),
    loss="binary_crossentropy",
    metrics=["accuracy"],
)
model.summary()

# -- callbacks -------------------------------------------------------------
early_stop = callbacks.EarlyStopping(
    monitor="val_accuracy", patience=15, restore_best_weights=True,
    mode="max", verbose=1,
)
reduce_lr = callbacks.ReduceLROnPlateau(
    monitor="val_loss", factor=0.5, patience=5, min_lr=1e-6, verbose=1,
)

# -- Phase 1: Train classification head ------------------------------------
print("\n=== Phase 1: Training Classification Head (backbone frozen) ===")
history = model.fit(
    train_gen,
    validation_data=val_gen,
    epochs=80,
    class_weight=class_weight,
    callbacks=[early_stop, reduce_lr],
)

# -- Phase 2: Fine-tune ONLY last 10 layers of backbone --------------------
print("\n=== Phase 2: Fine-tuning last 10 backbone layers ===")
base.trainable = True
for layer in base.layers[:-10]:
    layer.trainable = False

# Recompile with very low learning rate
model.compile(
    optimizer=keras.optimizers.Adam(learning_rate=1e-5),
    loss="binary_crossentropy",
    metrics=["accuracy"],
)

early_stop_ft = callbacks.EarlyStopping(
    monitor="val_accuracy", patience=10, restore_best_weights=True,
    mode="max", verbose=1,
)
reduce_lr_ft = callbacks.ReduceLROnPlateau(
    monitor="val_loss", factor=0.5, patience=4, min_lr=1e-7, verbose=1,
)

history_ft = model.fit(
    train_gen,
    validation_data=val_gen,
    epochs=30,
    class_weight=class_weight,
    callbacks=[early_stop_ft, reduce_lr_ft],
)

# -- Evaluation ------------------------------------------------------------
print("\n=== Final Evaluation ===")
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

# -- Quick test on a few real images ---------------------------------------
print("\n=== Quick Sanity Check ===")
good_dir = os.path.join(DATASET, "good")
bad_dir = os.path.join(DATASET, "bad")

def predict_single(path, true_label):
    img = keras.utils.load_img(path, target_size=(IMG_SIZE, IMG_SIZE))
    arr = keras.utils.img_to_array(img) / 255.0
    arr = np.expand_dims(arr, 0)
    prob_bad = float(model.predict(arr, verbose=0)[0][0])
    pred_label = "BAD" if prob_bad > 0.5 else "GOOD"
    status = "OK" if pred_label == true_label else "WRONG"
    print(f"  [{status}] {os.path.basename(path):40s} -> prob_bad={prob_bad:.4f}  pred={pred_label}  true={true_label}")
    return pred_label == true_label

correct = 0
total_tests = 0
for f in sorted(os.listdir(good_dir))[:10]:
    if predict_single(os.path.join(good_dir, f), "GOOD"):
        correct += 1
    total_tests += 1

for f in sorted(os.listdir(bad_dir))[:10]:
    if predict_single(os.path.join(bad_dir, f), "BAD"):
        correct += 1
    total_tests += 1

print(f"\nSanity check: {correct}/{total_tests} correct ({100*correct/total_tests:.0f}%)")

# -- Save model ------------------------------------------------------------
model.save(OUT_KERAS)
print(f"\nKeras model saved: {OUT_KERAS}")

# -- Create PKL wrapper for ai_service.py compatibility --------------------
class KerasCNNWrapper:
    def __init__(self, keras_path):
        self.keras_path = keras_path
        self._model = None
    def _load(self):
        if self._model is None:
            self._model = keras.models.load_model(self.keras_path)
        return self._model
    def predict_proba_from_image(self, image_path):
        m = self._load()
        img = keras.utils.load_img(image_path, target_size=(224, 224))
        arr = keras.utils.img_to_array(img) / 255.0
        arr = np.expand_dims(arr, 0)
        p_bad = float(m.predict(arr, verbose=0)[0][0])
        return np.array([[1.0 - p_bad, p_bad]])

class DummyScaler:
    def transform(self, X): return X

wrapper = KerasCNNWrapper(OUT_KERAS)
model_info = {
    "model": wrapper,
    "scaler": DummyScaler(),
    "label_map": {0: "Product_Clean", 1: "Product_Defective"},
    "backend": "keras_cnn",
}
joblib.dump(model_info, OUT_PKL)
print(f"PKL wrapper saved: {OUT_PKL}")
print("\nTraining complete! Restart Django to use the new model.")
