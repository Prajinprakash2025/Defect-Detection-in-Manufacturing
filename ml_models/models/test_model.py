"""Quick test to verify the new model works correctly."""
import os, sys, json
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
sys.stdout.reconfigure(line_buffering=True)

sys.path.insert(0, r'c:\work\Defect Detection in Manufacturing\defect_detecter')

from inspections.services.ai_service import detect_defect

good_img = r'c:\work\Defect Detection in Manufacturing\defect_detecter\ml_models\dataset\good\bottle_test_good_000.png'
bad_img = r'c:\work\Defect Detection in Manufacturing\defect_detecter\ml_models\dataset\bad\bottle_test_broken_large_000.png'

print("=== Testing GOOD bottle ===")
r = detect_defect(good_img)
print("  Label:", r['label'])
print("  Defective:", r['is_defective'])
print("  Confidence:", r['confidence'])
print()

print("=== Testing BAD bottle ===")
r = detect_defect(bad_img)
print("  Label:", r['label'])
print("  Defective:", r['is_defective'])
print("  Confidence:", r['confidence'])
print()

# Test more
print("=== Batch Test (5 good + 5 bad) ===")
good_dir = r'c:\work\Defect Detection in Manufacturing\defect_detecter\ml_models\dataset\good'
bad_dir = r'c:\work\Defect Detection in Manufacturing\defect_detecter\ml_models\dataset\bad'

correct = 0
total = 0

for f in sorted(os.listdir(good_dir))[:5]:
    r = detect_defect(os.path.join(good_dir, f))
    ok = "OK" if not r['is_defective'] else "WRONG"
    print(f"  [{ok}] {f:40s} -> {r['label']} ({r['confidence']})")
    if not r['is_defective']: correct += 1
    total += 1

for f in sorted(os.listdir(bad_dir))[:5]:
    r = detect_defect(os.path.join(bad_dir, f))
    ok = "OK" if r['is_defective'] else "WRONG"
    print(f"  [{ok}] {f:40s} -> {r['label']} ({r['confidence']})")
    if r['is_defective']: correct += 1
    total += 1

print(f"\nResult: {correct}/{total} correct ({100*correct/total:.0f}%)")
