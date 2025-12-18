import os
import re

TARGET_DIR = "../sipi-core/src/sipi/db"

def refactor_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace 'from app.db' with 'from sipi.db'
    new_content = re.sub(r'from app\.db', 'from sipi.db', content)
    # Replace 'import app.db' with 'import sipi.db'
    new_content = re.sub(r'import app\.db', 'import sipi.db', new_content)
    
    if content != new_content:
        print(f"Updating {filepath}")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)

def main():
    print(f"Scanning {TARGET_DIR}...")
    for root, dirs, files in os.walk(TARGET_DIR):
        for file in files:
            if file.endswith(".py"):
                refactor_file(os.path.join(root, file))
    print("Refactoring complete.")

if __name__ == "__main__":
    main()
