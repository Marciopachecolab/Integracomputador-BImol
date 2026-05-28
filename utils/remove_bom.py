import os
from pathlib import Path

def remove_bom_from_files(root_dir):
    """
    Remove UTF-8 BOM (\xef\xbb\xbf) from all .py files in directory recursively.
    """
    count = 0
    cleaned = 0
    errors = 0
    
    print(f"Searching for .py files in: {root_dir}")
    
    for path in Path(root_dir).rglob('*.py'):
        if 'venv' in path.parts or '.git' in path.parts or '__pycache__' in path.parts:
            continue
            
        count += 1
        try:
            with open(path, 'rb') as f:
                content = f.read()
                
            if content.startswith(b'\xef\xbb\xbf'):
                print(f"BOM found in: {path}")
                
                # Remove first 3 bytes
                clean_content = content[3:]
                
                with open(path, 'wb') as f:
                    f.write(clean_content)
                    
                print(f"✅ BOM removed from: {path}")
                cleaned += 1
                
        except Exception as e:
            print(f"❌ Error processing {path}: {e}")
            errors += 1

    print(f"\nSummary:")
    print(f"Scanned: {count} files")
    print(f"Cleaned: {cleaned} files")
    print(f"Errors: {errors}")

if __name__ == "__main__":
    # Start from current directory
    root = os.getcwd()
    remove_bom_from_files(root)
