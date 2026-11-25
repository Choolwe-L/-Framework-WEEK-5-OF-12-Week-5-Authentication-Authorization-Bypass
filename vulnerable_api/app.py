"""
FitTrack API - VULNERABLE build (TARGET of the assessment)
===========================================================
Week 5: Authentication & Authorization Bypass Testing

WARNING: This application is INTENTIONALLY INSECURE. It exists only as a
controlled lab target so the security scripts in ../security_scripts can
demonstrate BOLA, BFLA and Broken Authentication findings.

Do NOT deploy this build. The secure counterpart lives in ../hardened_api.

Deliberate flaws (mapped to OWASP API Security Top 10):
  * API2:2019 Broken User Authentication
      - no password policy (accepts "123")
      - no rate limiting / lockout on login (brute-force friendly)
      - predictable, non-expiring, unsigned token (base64 of user id)
      - username enumeration via distinct error messages
  * API1:2019 Broken Object Level Authorization (BOLA / IDOR)
      - GET /api/users/<id>/workouts returns any user's data by id,
        with no ownership check
  * API5:2019 Broken Function Level Authorization (BFLA)
      - /api/admin/* trusts a client-supplied role and never verifies it
        server-side; any authenticated user can reach admin functions
"""

import base64
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- In-memory "database" -------------------------------------------------
USERS = {
    1: {"id": 1, "username": "alice",   "password": "Sunshine2024!", "role": "user",  "email": "alice@fit.example"},
    2: {"id": 2, "username": "bob",     "password": "password",      "role": "user",  "email": "bob@fit.example"},
    3: {"id": 3, "username": "admin",   "password": "admin",         "role": "admin", "email": "admin@fit.example"},
}

WORKOUTS = {
    1: [{"date": "2026-11-01", "type": "Run",    "distance_km": 5.2, "hr_avg": 148, "notes": "Morning 5k"}],
    2: [{"date": "2026-11-02", "type": "Cycling", "distance_km": 22.0, "hr_avg": 132, "notes": "River loop"}],
    3: [{"date": "2026-11-03", "type": "Swim",   "distance_km": 1.5, "hr_avg": 120, "notes": "Pool session"}],
}


# --- Insecure helpers -----------------------------------------------------
def make_token(user):
    """VULN: unsigned, reversible 'token' = base64(user_id:role). Forgeable."""
    raw = f"{user['id']}:{user['role']}".encode()
    return base64.b64encode(raw).decode()


def parse_token(token):
    """Decode without any signature verification."""
    try:
        raw = base64.b64decode(token.encode()).decode()
        uid, role = raw.split(":")
        return {"id": int(uid), "role": role}
    except Exception:
        return None


def current_user():
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "").strip()
    return parse_token(token)


# --- Routes ---------------------------------------------------------------
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username")
    password = data.get("password")
    # VULN: no password complexity requirement at all
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400
    new_id = max(USERS) + 1
    USERS[new_id] = {"id": new_id, "username": username, "password": password,
                     "role": "user", "email": f"{username}@fit.example"}
    WORKOUTS[new_id] = []
    return jsonify({"message": "registered", "id": new_id}), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username")
    password = data.get("password")
    user = next((u for u in USERS.values() if u["username"] == username), None)
    # VULN: username enumeration - different messages for the two cases
    if not user:
        return jsonify({"error": "no such user"}), 404
    if user["password"] != password:
        return jsonify({"error": "wrong password"}), 401
    # VULN: no rate limiting, no lockout -> brute force friendly
    return jsonify({"token": make_token(user), "role": user["role"]}), 200


@app.route("/api/me", methods=["GET"])
def me():
    u = current_user()
    if not u:
        return jsonify({"error": "unauthenticated"}), 401
    return jsonify(USERS.get(u["id"], {})), 200


@app.route("/api/users/<int:user_id>/workouts", methods=["GET"])
def get_workouts(user_id):
    u = current_user()
    if not u:
        return jsonify({"error": "unauthenticated"}), 401
    # VULN (BOLA/IDOR): no check that u['id'] == user_id.
    # Any authenticated user can read any other user's workouts by id.
    return jsonify({"user_id": user_id, "workouts": WORKOUTS.get(user_id, [])}), 200


@app.route("/api/admin/users", methods=["GET"])
def admin_users():
    u = current_user()
    if not u:
        return jsonify({"error": "unauthenticated"}), 401
    # VULN (BFLA): trusts the role embedded in the forgeable client token and
    # performs no real authorization. A regular user who forges role=admin,
    # or simply any authenticated caller, reaches this admin-only data.
    return jsonify({"users": list(USERS.values())}), 200


@app.route("/api/admin/users/<int:user_id>", methods=["DELETE"])
def admin_delete(user_id):
    u = current_user()
    if not u:
        return jsonify({"error": "unauthenticated"}), 401
    # VULN (BFLA): destructive admin action with no server-side role check.
    USERS.pop(user_id, None)
    WORKOUTS.pop(user_id, None)
    return jsonify({"message": f"user {user_id} deleted"}), 200


@app.route("/health")
def health():
    return jsonify({"status": "ok", "build": "VULNERABLE-do-not-deploy"}), 200


if __name__ == "__main__":
    # Bind to localhost only; this is a lab target.
    app.run(host="127.0.0.1", port=5000, debug=False)
