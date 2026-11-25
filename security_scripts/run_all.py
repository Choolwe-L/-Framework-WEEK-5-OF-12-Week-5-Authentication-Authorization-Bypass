"""
Run the full FitTrack API authz/authn assessment suite against TARGET_URL.

    python run_all.py
    TARGET_URL=http://127.0.0.1:5000 python run_all.py

Point it at the vulnerable build to reproduce the findings, then at the
hardened build to confirm every finding is remediated.
Authorised lab use only.
"""
import test_broken_auth
import test_bola
import test_bfla
from common import BASE_URL, BOLD, RESET

if __name__ == "__main__":
    print(f"{BOLD}FitTrack API Security Assessment Suite{RESET}")
    print(f"Target: {BASE_URL}")

    # Broken Authentication
    test_broken_auth.test_weak_password_policy()
    test_broken_auth.test_username_enumeration()
    test_broken_auth.test_brute_force_protection()
    test_broken_auth.test_password_spray_poc()

    # BOLA then BFLA
    test_bola.run()
    test_bfla.run()

    total = (len(test_broken_auth.findings)
             + len(test_bola.findings)
             + len(test_bfla.findings))
    print(f"\n{BOLD}TOTAL FINDINGS: {total}{RESET}")
