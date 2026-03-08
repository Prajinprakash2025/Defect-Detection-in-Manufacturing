import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'defect_detection.settings')
django.setup()

from inspections.services.ai_service import detect_defect, demo_fallback_predict

def test_ai_logic():
    print("Testing AI Service Logic...")
    
    # 1. Test Demo Fallback - Defective Keyword
    print("\n[Test 1] Demo Fallback: 'crack_test.jpg'")
    result = demo_fallback_predict("crack_test.jpg")
    print(f"Result: {result}")
    if result['is_defective'] and result['confidence'] >= 0.90:
        print("PASS: Correctly identified as defective.")
    else:
        print("FAIL: Should be defective.")

    # 2. Test Demo Fallback - Non-Defective
    print("\n[Test 2] Demo Fallback: 'normal_part.jpg'")
    result = demo_fallback_predict("normal_part.jpg")
    print(f"Result: {result}")
    if not result['is_defective']:
        print("PASS: Correctly identified as non-defective.")
    else:
        print("FAIL: Should be non-defective.")

    # 3. Test Threshold Logic Simulation
    print("\n[Test 3] Threshold Verification (Simulated)")
    # Scenario: AI says defective but confidence 0.55 (Should be Non-Defective)
    ai_output_low_conf = {
        'label': 'Defective',
        'confidence': 0.55,
        'is_defective': True
    }
    
    # Simulate View Logic
    is_defective = ai_output_low_conf['is_defective']
    confidence = ai_output_low_conf['confidence']
    
    if is_defective and confidence >= 0.60:
        status = 'Defective'
    else:
        status = 'Non-Defective'
        
    print(f"Input: {ai_output_low_conf}")
    print(f"Final Status: {status}")
    
    if status == 'Non-Defective':
        print("PASS: Threshold logic worked (Downgraded to Non-Defective).")
    else:
        print("FAIL: Threshold logic failed.")

    # Scenario: AI says defective with confidence 0.65 (Should be Defective)
    ai_output_high_conf = {
        'label': 'Defective',
        'confidence': 0.65,
        'is_defective': True
    }
    
    is_defective = ai_output_high_conf['is_defective']
    confidence = ai_output_high_conf['confidence']
    
    if is_defective and confidence >= 0.60:
        status = 'Defective'
    else:
        status = 'Non-Defective'

    print(f"Input: {ai_output_high_conf}")
    print(f"Final Status: {status}")
    
    if status == 'Defective':
        print("PASS: Threshold logic worked (Kept as Defective).")
    else:
        print("FAIL: Threshold logic failed.")

if __name__ == "__main__":
    test_ai_logic()
