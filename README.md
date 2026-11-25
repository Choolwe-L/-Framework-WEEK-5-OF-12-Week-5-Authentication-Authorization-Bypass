# Fitness API Security Assessment & Hardening Framework
### Week 5 of 12 — Authentication & Authorization Bypass Testing

An authorised, self-contained lab that assesses a fitness-tracking API for the
OWASP API Security Top 10 authentication/authorization flaws, then hardens it.

> ⚠️ **Educational / authorised use only.** The `vulnerable_api` build is
> intentionally insecure and exists solely as a controlled test target. Do not
> deploy it or run these scripts against any system you do not own or have
> written permission to test.

## What's inside

| Path | Purpose |
|------|---------|
| `vulnerable_api/` | Intentionally insecure FitTrack API — the assessment **target** |
| `hardened_api/` | Remediated, securely configured build (JWT, bcrypt, RBAC, rate limiting) |
| `security_scripts/` | Custom Python tools that test for BOLA, BFLA, and Broken Authentication |
| `report/PENTEST_REPORT.md` | Full penetration test report with findings, PoCs, and remediation verification |
| `report/assessment_evidence.txt` | Captured console output from live runs against both builds |
| `deployment/` | Docker Compose for cloud-ready deployment of the hardened build |
| `.github/workflows/security-suite.yml` | CI that reproduces findings on the vulnerable build and fails if the hardened build ever regresses |

## Vulnerabilities assessed

- **API1:2019 — Broken Object Level Authorization (BOLA/IDOR):** read any user's
  workouts by tampering the id in `/api/users/<id>/workouts`.
- **API2:2019 — Broken User Authentication:** weak password policy, username
  enumeration, no brute-force protection, admin account crackable by spray.
- **API5:2019 — Broken Function Level Authorization (BFLA):** regular users reach
  admin endpoints; unsigned tokens allow admin-role forgery.

**Result:** 9 findings on the vulnerable build → **0 findings** on the hardened build.

## Quick start

```bash
# 1. Set up
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Reproduce the findings against the vulnerable target
python vulnerable_api/app.py &            # starts on http://127.0.0.1:5000
cd security_scripts && python run_all.py  # expect TOTAL FINDINGS: 9
kill %1

# 3. Confirm the fixes against the hardened build
export JWT_SECRET="$(openssl rand -base64 24)"
python hardened_api/app.py &
cd security_scripts && python run_all.py  # expect TOTAL FINDINGS: 0
```

Point any script at a different host with `TARGET_URL=http://host:5000`.

## Deploy the hardened build (cloud-ready)

```bash
export JWT_SECRET="$(openssl rand -base64 24)"
cd deployment && docker compose up --build
```
The container runs as a non-root user via gunicorn; the JWT secret is injected
from the environment and never baked into the image.

## Deliverables mapping (Week 5)

- ✅ Detailed report of BOLA/BFLA/Broken Authentication vulns with steps to
  reproduce → `report/PENTEST_REPORT.md`
- ✅ Proof-of-concept for at least one bypass → token-forgery PoC (BFLA) and
  password-spray PoC (auth), both in `security_scripts/`
- ✅ Custom Python security scripts → `security_scripts/`
- ✅ Hardened, securely configured Flask API with basic cloud infra →
  `hardened_api/` + `deployment/`

---
*JPR Solutions · Internship Project*
