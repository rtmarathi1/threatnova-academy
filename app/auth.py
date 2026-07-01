"""
Authentication, password hashing, and session management.

Passwords: PBKDF2-HMAC-SHA256 with per-user salt (stdlib hashlib).
Sessions: random opaque token stored server-side, referenced by an HttpOnly cookie.
CSRF: per-session token required on all state-changing POST requests.
"""
from __future__ import annotations

import hmac
import hashlib
import secrets
from datetime import datetime, timedelta

from . import db
from .server import redirect

SESSION_COOKIE = "tn_session"
SESSION_DAYS = 7
PBKDF2_ROUNDS = 120_000


# --------------------------------------------------------------------------- #
# Password hashing
# --------------------------------------------------------------------------- #
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${PBKDF2_ROUNDS}${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, rounds, salt, digest = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(rounds))
        return hmac.compare_digest(dk.hex(), digest)
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# Users
# --------------------------------------------------------------------------- #
def create_user(name, email, password, role="STUDENT"):
    return db.execute(
        "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
        (name.strip(), email.strip().lower(), hash_password(password), role),
    )


def get_user_by_email(email):
    return db.query_one("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))


def get_user_by_id(uid):
    return db.query_one("SELECT * FROM users WHERE id = ?", (uid,))


def authenticate(email, password):
    user = get_user_by_email(email)
    if user and verify_password(password, user["password_hash"]):
        return user
    return None


# --------------------------------------------------------------------------- #
# Sessions
# --------------------------------------------------------------------------- #
def create_session(user_id):
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(24)
    expires = (datetime.utcnow() + timedelta(days=SESSION_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
    db.execute(
        "INSERT INTO sessions (token, user_id, csrf, expires_at) VALUES (?, ?, ?, ?)",
        (token, user_id, csrf, expires),
    )
    return token


def get_session(token):
    if not token:
        return None
    row = db.query_one(
        "SELECT * FROM sessions WHERE token = ? AND expires_at > datetime('now')",
        (token,),
    )
    return row


def destroy_session(token):
    if token:
        db.execute("DELETE FROM sessions WHERE token = ?", (token,))


def load_user_middleware(req):
    """Middleware: attach req.user and req.session from the session cookie."""
    token = req.cookies.get(SESSION_COOKIE)
    sess = get_session(token)
    if sess:
        req.session = sess
        req.user = get_user_by_id(sess["user_id"])
    return None


# --------------------------------------------------------------------------- #
# Access control helpers
# --------------------------------------------------------------------------- #
def login_required(req):
    """Return a redirect Response if not logged in, else None."""
    if not req.user:
        return redirect(f"/login?next={req.path}")
    return None


def require_role(req, *roles):
    if not req.user:
        return redirect(f"/login?next={req.path}")
    if req.user["role"] not in roles:
        from .server import Response
        return Response("<h1>403</h1><p>You do not have access to this area.</p>", status=403)
    return None


def check_csrf(req):
    """Validate CSRF token on POST. Returns Response on failure, else None."""
    if req.method == "POST":
        token = req.form.get("csrf")
        if not req.session or not token or not hmac.compare_digest(token, req.session["csrf"]):
            from .server import Response
            return Response("<h1>400</h1><p>Invalid or missing CSRF token.</p>", status=400)
    return None
