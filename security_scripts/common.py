"""Shared helpers for the FitTrack API security test scripts."""
import os
import requests

BASE_URL = os.environ.get("TARGET_URL", "http://127.0.0.1:5000")
TIMEOUT = 8

# ANSI colours for readable console output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def login(username, password):
    """Return (token, role, status_code) for a login attempt."""
    r = requests.post(f"{BASE_URL}/api/login",
                      json={"username": username, "password": password},
                      timeout=TIMEOUT)
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    return body.get("token"), body.get("role"), r.status_code


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def vuln(msg):
    print(f"  {RED}[VULNERABLE]{RESET} {msg}")


def safe(msg):
    print(f"  {GREEN}[SECURE]{RESET}    {msg}")


def info(msg):
    print(f"  {YELLOW}[INFO]{RESET}      {msg}")


def banner(title):
    print(f"\n{BOLD}=== {title} ==={RESET}")
    print(f"  Target: {BASE_URL}")
