"""
Step 2 (FAST): Train classifier on MobileNetV2 features
Skips SVM (too slow), uses RF + GB + LR ensemble. Should finish in ~2 minutes.
"""
import os, sys, time
import numpy as np
import joblib
from collections import Counter

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)

from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NPZ_PATH = os.path.join(BASE, "deep_features.npz")
OUT_PKL = os.path.join(BASE, "defect_classifier.pkl")
FE_PATH = os.path.join(BASE, "feature_extractor.keras")
SEED = 42

print("Step 2: Training Classifier")
print("=" * 50)

# Load
print("Loading features ...")
data = np.load(NPZ_PATH)
X, y = data['X'], data['y']
print(f"  X={X.shape}, y={y.shape}, classes={dict(Counter(y))}")

# Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.15, random_state=SEED, stratify=y
)
print(f"  Train={len(X_train)}, Test={len(X_test)}")

# Scale + PCA
print("Scaling + PCA (1280 -> 100) ...")
scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

pca = PCA(n_components=100, random_state=SEED)
X_train_p = pca.fit_transform(X_train_s)
X_test_p = pca.transform(X_test_s)
print(f"  Variance retained: {pca.explained_variance_ratio_.sum():.2%}")

# 1. Logistic Regression
print("\nTraining Logistic Regression ...")
t0 = time.time()
lr = LogisticRegression(C=1.0, max_iter=2000, random_state=SEED,
                         class_weight='balanced', solver='lbfgs')
lr.fit(X_train_p, y_train)
lr_acc = lr.score(X_test_p, y_test)
print(f"  LR Accuracy: {lr_acc:.4f} ({time.time()-t0:.1f}s)")

# 2. Random Forest
print("Training Random Forest ...")
t0 = time.time()
rf = RandomForestClassifier(n_estimators=500, max_depth=25,
                             min_samples_split=3, random_state=SEED,
                             class_weight='balanced', n_jobs=-1)
rf.fit(X_train_p, y_train)
rf_acc = rf.score(X_test_p, y_test)
print(f"  RF Accuracy: {rf_acc:.4f} ({time.time()-t0:.1f}s)")

# 3. Gradient Boosting
print("Training Gradient Boosting ...")
t0 = time.time()
gb = GradientBoostingClassifier(n_estimators=300, learning_rate=0.05,
                                 max_depth=5, subsample=0.8, random_state=SEED)
gb.fit(X_train_p, y_train)
gb_acc = gb.score(X_test_p, y_test)
print(f"  GB Accuracy: {gb_acc:.4f} ({time.time()-t0:.1f}s)")

# 4. Ensemble
print("Training Ensemble ...")
t0 = time.time()
ensemble = VotingClassifier(
    estimators=[('lr', lr), ('rf', rf), ('gb', gb)],
    voting='soft',
)
ensemble.fit(X_train_p, y_train)
ens_acc = ensemble.score(X_test_p, y_test)
print(f"  Ensemble Accuracy: {ens_acc:.4f} ({time.time()-t0:.1f}s)")

# Results
results = [("LR", lr_acc, lr), ("RF", rf_acc, rf),
           ("GB", gb_acc, gb), ("Ensemble", ens_acc, ensemble)]
results.sort(key=lambda x: x[1], reverse=True)

print(f"\n{'='*50}")
print("RESULTS SUMMARY:")
for nm, ac, _ in results:
    bar = "#" * int(ac * 40)
    print(f"  {nm:12s}: {ac:.4f}  {bar}")

final_name, final_acc, final_model = results[0]
if final_name != "Ensemble" and ens_acc >= final_acc - 0.01:
    final_name, final_acc, final_model = "Ensemble", ens_acc, ensemble

print(f"\n  >>> SELECTED: {final_name} ({final_acc:.4f}) <<<")

# Report
print(f"\n=== Classification Report ===")
y_pred = final_model.predict(X_test_p)
print(classification_report(y_test, y_pred, target_names=["Good", "Defective"]))
cm = confusion_matrix(y_test, y_pred)
print(f"Confusion Matrix:\n{cm}")
print(f"  Good correct:      {cm[0][0]}/{cm[0].sum()} ({100*cm[0][0]/cm[0].sum():.0f}%)")
print(f"  Defective correct: {cm[1][1]}/{cm[1].sum()} ({100*cm[1][1]/cm[1].sum():.0f}%)")

# Save
model_info = {
    "model": final_model,
    "scaler": scaler,
    "pca": pca,
    "label_map": {0: "Product_Clean", 1: "Product_Defective"},
    "backend": "deep_ensemble",
    "feature_extractor_path": FE_PATH,
    "img_size": 224,
}
joblib.dump(model_info, OUT_PKL)
print(f"\nModel saved: {OUT_PKL}")
print(f"Final accuracy: {final_acc:.4f}")
print("DONE! Restart Django to use the new model.")
