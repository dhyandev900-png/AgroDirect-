import os
from PIL import Image

# ⚠️ CHECK YOUR PATH
DATASET_DIR = '/Users/dhyandevaiah/AgroDirect_ML_Dataset'

fixed_count = 0
deleted_count = 0

print("Sanitizing dataset (fixing headers and EXIF data)...")
for root, dirs, files in os.walk(DATASET_DIR):
    for file in files:
        if file.lower().endswith(('.png', '.jpg', '.jpeg')):
            filepath = os.path.join(root, file)
            try:
                # Open and convert to standard RGB (strips EXIF and weird encodings)
                img = Image.open(filepath).convert('RGB')
                
                # Save it back as a clean baseline JPEG, overwriting the old one
                img.save(filepath, 'JPEG', quality=95)
                fixed_count += 1
            except Exception as e:
                print(f"Deleting unreadable file: {filepath}")
                os.remove(filepath)
                deleted_count += 1

print(f"\nSanitization complete! Fixed {fixed_count} images. Deleted {deleted_count} unreadable images.")