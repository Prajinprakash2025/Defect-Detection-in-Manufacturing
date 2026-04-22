import zipfile
import os
import random

zip_path = r'c:\work\Defect Detection in Manufacturing\defect_detecter\ml_models\dataset\archive (9).zip'
output_base = r'c:\work\Defect Detection in Manufacturing\defect_detecter\ml_models\dataset'

# Items to include
items = ['cable', 'bottle', 'metal_nut']

def extract_maximal_merged_subset():
    # Create target folders
    bad_dir = os.path.join(output_base, 'bad')
    good_dir = os.path.join(output_base, 'good')
    os.makedirs(bad_dir, exist_ok=True)
    os.makedirs(good_dir, exist_ok=True)
    
    # Pre-clean to ensure exact counts
    for d in [bad_dir, good_dir]:
        for f in os.listdir(d):
            os.remove(os.path.join(d, f))
    
    with zipfile.ZipFile(zip_path, 'r') as z:
        all_zip_files = z.namelist()
        
        all_defective = []
        all_clean = []
        
        for item in items:
            print(f"Counting item: {item}...")
            
            # 1. Defective (Bad) samples
            bad_prefix = f"{item}/bad/"
            item_bad_files = [f for f in all_zip_files if f.startswith(bad_prefix) and f.endswith('.png')]
            all_defective.extend([(item, f) for f in item_bad_files])
            
            # 2. Clean (Good) samples
            good_prefix = f"{item}/good/"
            item_good_files = [f for f in all_zip_files if f.startswith(good_prefix) and f.endswith('.png')]
            all_clean.extend([(item, f) for f in item_good_files])
        
        # We want exactly 500 total. 
        # We take ALL available defective (~225)
        print(f"Total available defective: {len(all_defective)}")
        for item, f in all_defective:
            target_name = f"{item}_{os.path.basename(f)}"
            target_path = os.path.join(bad_dir, target_name)
            with z.open(f) as source, open(target_path, 'wb') as target:
                target.write(source.read())
        
        # We complement with clean to reach 500
        target_clean_count = 500 - len(all_defective)
        print(f"Extracting {target_clean_count} clean images...")
        selected_clean = random.sample(all_clean, min(len(all_clean), target_clean_count))
        for item, f in selected_clean:
            target_name = f"{item}_{os.path.basename(f)}"
            target_path = os.path.join(good_dir, target_name)
            with z.open(f) as source, open(target_path, 'wb') as target:
                target.write(source.read())

if __name__ == "__main__":
    extract_maximal_merged_subset()
    print("Maximal multi-object subsampling complete (Total: 500 images target reached).")
