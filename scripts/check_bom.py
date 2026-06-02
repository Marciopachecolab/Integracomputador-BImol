
import os
from pathlib import Path

def check_encoding(start_path):
    issues = []
    for root, dirs, files in os.walk(start_path):
        if '.git' in dirs:
            dirs.remove('.git')
        if '__pycache__' in dirs:
            dirs.remove('__pycache__')
        
        for file in files:
            if not file.endswith(('.py', '.json', '.md', '.txt', '.csv')):
                continue
                
            path = os.path.join(root, file)
            try:
                with open(path, 'rb') as f:
                    raw = f.read()
                    
                if raw.startswith(b'\xef\xbb\xbf'):
                    issues.append(f"[BOM DETECTED] {path}")
                    
                try:
                    raw.decode('utf-8')
                except UnicodeDecodeError:
                    issues.append(f"[INVALID UTF-8] {path}")
                    
            except Exception as e:
                issues.append(f"[ERROR READING] {path}: {e}")
                
    return issues

if __name__ == "__main__":
    start_dir = Path(__file__).resolve().parent.parent  # = repositório raiz
    print(f"Checking {start_dir}...")
    problems = check_encoding(start_dir)
    if problems:
        print("Issues found:")
        for p in problems:
            print(p)
    else:
        print("No encoding issues found.")
