#!/usr/bin/env python3
"""
ThreatNova CyberLabs - entry point.

Usage:
    python3 run.py                # runs on 0.0.0.0:8000
    PORT=9000 python3 run.py      # custom port

Zero external dependencies. Requires only Python 3.10+ standard library.
"""
import os
import sys

# ensure the project root is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import db, server            # noqa: E402
from app.seed import seed             # noqa: E402
from app.routes import register_all   # noqa: E402


def main():
    db.init_db()
    seed()
    app = register_all()
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "0.0.0.0")
    server.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
