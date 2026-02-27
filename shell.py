"""
Interactive shell with app context pre-loaded.

Usage:
    docker compose run api python shell.py   # inside Docker (connects to db service)
    python shell.py                          # local (DATABASE_URL must be set)

Available in the REPL:
    db          — active SQLAlchemy session (call db.close() when done)
    settings    — app settings object
    User        — User ORM model
"""

import code
import sys

# ── app context ──────────────────────────────────────────────────────────────
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User

db = SessionLocal()

namespace = {
    "db": db,
    "settings": settings,
    "User": User,
}

BANNER = """
PPP interactive shell
─────────────────────
  db        → SQLAlchemy session
  settings  → app config
  User      → User model

Example:
  db.query(User).all()
  db.query(User).filter(User.email == "x@y.com").first()
"""

# ── try IPython, fall back to stdlib REPL ────────────────────────────────────
try:
    from IPython import start_ipython
    from traitlets.config import Config

    cfg = Config()
    cfg.TerminalInteractiveShell.banner1 = BANNER
    start_ipython(argv=[], config=cfg, user_ns=namespace)
except ImportError:
    code.interact(banner=BANNER, local=namespace)
finally:
    db.close()
