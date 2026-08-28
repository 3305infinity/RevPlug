import sys
from pathlib import Path

# Ensure the project root is on sys.path so that `app.*` imports work
# when running scripts directly or via `python -m scripts.*`.
_project_root = Path(__file__).parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
