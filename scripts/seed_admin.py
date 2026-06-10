#!/usr/bin/env python
"""Create the initial admin account for LuminaDx.

Usage (from repo root):
    python scripts/seed_admin.py

Set ADMIN_EMAIL / ADMIN_PASSWORD / ADMIN_NAME env vars to override defaults.
Never use the defaults in production — they are for local dev only.
"""
import os
import sys
from pathlib import Path

# Ensure backend package is on the path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from core.auth_utils import hash_password
from core.database import User, init_db, SessionLocal

ADMIN_EMAIL    = os.environ.get("ADMIN_EMAIL",    "admin@luminadx.local")
ADMIN_NAME     = os.environ.get("ADMIN_NAME",     "LuminaDx Admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "ChangeMe123!")

if ADMIN_PASSWORD == "ChangeMe123!" and not os.environ.get("ADMIN_PASSWORD"):
    print("WARNING: Using default admin password. Set ADMIN_PASSWORD env var before deploying.")

init_db()
db = SessionLocal()

existing = db.query(User).filter(User.email == ADMIN_EMAIL).first()
if existing:
    print(f"Admin account already exists: {ADMIN_EMAIL}")
    db.close()
    sys.exit(0)

admin = User(
    email=ADMIN_EMAIL,
    full_name=ADMIN_NAME,
    hashed_password=hash_password(ADMIN_PASSWORD),
    role="admin",
)
db.add(admin)
db.commit()
print(f"Admin account created: {ADMIN_EMAIL}")
print(f"Name: {ADMIN_NAME}")
print(f"Role: admin")
print()
print("To create doctor accounts, POST to /api/auth/users with the admin cookie.")
db.close()
