import os
import re

TARGET_DIR = "app"

def refactor_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = content
    
    # Replace imports
    # from sipi.db.models -> from sipi.db.models
    new_content = re.sub(r'from app\.db\.models', 'from sipi.db.models', new_content)
    # from sipi.db.base -> from sipi.db.base
    new_content = re.sub(r'from app\.db\.base', 'from sipi.db.base', new_content)
    # from sipi.db.mixins -> from sipi.db.mixins
    new_content = re.sub(r'from app\.db\.mixins', 'from sipi.db.mixins', new_content)
    
    # Also handle 'import sipi.db.models' etc if they exist
    new_content = re.sub(r'import app\.db\.models', 'import sipi.db.models', new_content)

    # Handle cases where `app.db` is imported and used as prefix?
    # e.g. `from sipi.db import models` -> `from sipi.db import models`
    # Handler 'from sipi.db import'
    new_content = re.sub(r'from app\.db import', 'from sipi.db import', new_content)

    # Specific handling for sessions if they are imported via full path
    # from sipi.db.sessions -> from sipi.db.sessions
    new_content = re.sub(r'from app\.db\.sessions', 'from sipi.db.sessions', new_content)
    new_content = re.sub(r'import app\.db\.sessions', 'import sipi.db.sessions', new_content)

    if content != new_content:
        print(f"Updating {filepath}")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)

def main():
    print(f"Scanning project root...")
    ignore_dirs = {'.git', 'venv', '__pycache__', '.vscode', '.idea', 'sipi-core'}
    
    for root, dirs, files in os.walk("."):
        # Modify dirs in-place to skip ignored directories
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        for file in files:
            if file.endswith(".py"):
                refactor_file(os.path.join(root, file))
    print("Refactoring complete.")

if __name__ == "__main__":
    main()
