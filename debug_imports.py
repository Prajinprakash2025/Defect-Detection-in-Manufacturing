import sys
import os

print("Executable:", sys.executable)
print("CWD:", os.getcwd())
print("Path:")
for p in sys.path:
    print(p)

try:
    import django
    print("Django version:", django.get_version())
    print("Django file:", django.__file__)
except ImportError as e:
    print("Django import failed:", e)

try:
    import rest_framework
    print("DRF file:", rest_framework.__file__)
except ImportError as e:
    print("DRF import failed:", e)
