"""
FitTrack API - HARDENED build (the remediated deliverable)
===========================================================
Week 5: Authentication & Authorization Bypass Testing

This is the securely-configured counterpart to ../vulnerable_api/app.py.
Every deliberate flaw in the vulnerable build is remediated here. Run the
scripts in ../security_scripts against this build to confirm the fixes.

Security controls applied:
  * API2 Broken Authentication
      - bcrypt password hashing (never store plaintext)
      - enforced password policy (length + complexity)
      - signed, expiring JWTs (HS256) with a server-held secret
      - per-account login rate limiting + temporary lockout
      - uniform error messages (no username enumeration)
  * API1 BOLA / IDOR
      - ownership enforced: a user may only read their own object unless admin
  * API5 BFLA
      - role is read from the verified JWT claims (server-trusted), not the
        client; admin routes gated by an @require_role("admin") decorator

Secrets come from environment variables (see .env.example). No secret is
hard-coded.
"""

import os
import re
import time
import datetime
from functools import wraps

import bcrypt
import jwt
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- Configuration (from environment, never hard-coded) -------------------
JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    # Fail closed: refuse to start without a configured secret.
    raise RuntimeError("JWT_SECRET environment variable is required")
JWT_ALGO = "HS256"
TOKEN_TTL_MINUTES = int(os.environ.get("TOKEN_TTL_MINUTES", "30"))

MAX_FAILED_LOGINS = 5
LOCKOUT_SECONDS = 300
PASSWORD_MIN_LEN = 12

# --- In-memory "database" (passwords stored as bcrypt hashes) -------------
def _hash(pw: str) -> bytes:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt())

USERS = {
    1: {"id": 1, "username": "alice", "pw_hash": _hash("Sunshine2024!Strong"), "role": "user",  "email": "alice@fit.example"},
    2: {"id": 2, "username": "bob",   "pw_hash": _hash("Str0ng-Passphrase-99"), "role": "user",  "email": "bob@fit.example"},
    3: {"id": 3, "username": "admin", "pw_hash": _hash("Adm1n-Console-Key-77"), "role": "admin", "email": "admin@fit.example"},
}

WORKOUTS = {
    1: [{"date": "2026-11-01", "type": "Run",     "distance_km": 5.2,  "hr_avg": 148, "notes": "Morning 5k"}],
    2: [{"date": "2026-11-02", "type": "Cycling", "distance_km": 22.0, "hr_avg": 132, "notes": "River loop"}],
    3: [{"date": "2026-11-03", "type": "Swim",    "distance_km": 1.5,  "hr_avg": 120, "notes": "Pool session"}],
}

# login attempt tracking: username -> {"fails": int, "until": epoch}
_LOGIN_STATE = {}


# --- Security helpers ------------------------------------------------------
def password_is_strong(pw: str) -> bool:
    if not pw or len(pw) < PASSWORD_MIN_LEN:
        return False
    checks = [
        re.search(r"[a-z]", pw),
        re.search(r"[A-Z]", pw),
        re.search(r"\d", pw),
        re.search(r"[^A-Za-z0-9]", pw),
    ]
    return all(checks)


def issue_token(user: dict) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": user["id"],
        "role": user["role"],
        "iat": now,
        "exp": now + datetime.timedelta(minutes=TOKEN_TTL_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def verify_token():
    """Return trusted claims from a validly-signed, unexpired JWT, else None."""
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "").strip()
    if not token:
        return None
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.PyJWTError:
        return None


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        claims = verify_token()
        if not claims:
            return jsonify({"error": "unauthenticated"}), 401
        request.claims = claims
        return fn(*args, **kwargs)
    return wrapper


def require_role(role):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            claims = verify_token()
            if not claims:
                return jsonify({"error": "unauthenticated"}), 401
            # Role comes from the SERVER-VERIFIED token, not the client body.
            if claims.get("role") != role:
                return jsonify({"error": "forbidden"}), 403
            request.claims = claims
            return fn(*args, **kwargs)
        return wrapper
    return deco


# --- Routes ----------------------------------------------------------------
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400
    if any(u["username"] == username for u in USERS.values()):
        return jsonify({"error": "username unavailable"}), 409
    if not password_is_strong(password):
        return jsonify({
            "error": "weak password",
            "policy": f"min {PASSWORD_MIN_LEN} chars incl. upper, lower, digit, symbol",
        }), 400
    new_id = max(USERS) + 1
    USERS[new_id] = {"id": new_id, "username": username, "pw_hash": _hash(password),
                     "role": "user", "email": f"{username}@fit.example"}
    WORKOUTS[new_id] = []
    return jsonify({"message": "registered", "id": new_id}), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    # Rate limit / lockout per account
    state = _LOGIN_STATE.get(username, {"fails": 0, "until": 0})
    if state["until"] > time.time():
        return jsonify({"error": "too many attempts, try again later"}), 429

    user = next((u for u in USERS.values() if u["username"] == username), None)
    ok = bool(user) and bcrypt.checkpw(password.encode(), user["pw_hash"])

    if not ok:
        state["fails"] += 1
        if state["fails"] >= MAX_FAILED_LOGINS:
            state["until"] = time.time() + LOCKOUT_SECONDS
            state["fails"] = 0
        _LOGIN_STATE[username] = state
        # Uniform message -> no username enumeration
        return jsonify({"error": "invalid credentials"}), 401

    _LOGIN_STATE.pop(username, None)  # reset on success
    return jsonify({"token": issue_token(user), "role": user["role"]}), 200


@app.route("/api/me", methods=["GET"])
@require_auth
def me():
    uid = request.claims["sub"]
    u = {k: v for k, v in USERS.get(uid, {}).items() if k != "pw_hash"}
    return jsonify(u), 200


@app.route("/api/users/<int:user_id>/workouts", methods=["GET"])
@require_auth
def get_workouts(user_id):
    claims = request.claims
    # BOLA fix: only the owner (or an admin) may read the object.
    if claims["sub"] != user_id and claims.get("role") != "admin":
        return jsonify({"error": "forbidden"}), 403
    return jsonify({"user_id": user_id, "workouts": WORKOUTS.get(user_id, [])}), 200


@app.route("/api/admin/users", methods=["GET"])
@require_role("admin")
def admin_users():
    safe = [{k: v for k, v in u.items() if k != "pw_hash"} for u in USERS.values()]
    return jsonify({"users": safe}), 200


@app.route("/api/admin/users/<int:user_id>", methods=["DELETE"])
@require_role("admin")
def admin_delete(user_id):
    USERS.pop(user_id, None)
    WORKOUTS.pop(user_id, None)
    return jsonify({"message": f"user {user_id} deleted"}), 200


@app.route("/health")
def health():
    return jsonify({"status": "ok", "build": "hardened"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
