"""Make backend modules importable and ensure .env is found regardless of
where pytest is invoked from (config.py resolves env_file relative to cwd)."""
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)
