import os, sys

# repo root (../ from tests/)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")

# Ensure both the repo root and src/ are importable
for p in (ROOT, SRC):
    if p not in sys.path:
        sys.path.insert(0, p)