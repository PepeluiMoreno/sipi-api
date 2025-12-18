import sys
import os

# Ensure we can import from sipi-core
try:
    from sipi.db.models import Inmueble
    print("SUCCESS: Imported Inmueble from sipi.db.models")
    print(f"Path: {Inmueble}")
except ImportError as e:
    print(f"FAILURE: {e}")
except Exception as e:
    print(f"ERROR: {e}")
