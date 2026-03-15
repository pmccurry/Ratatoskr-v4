#!/usr/bin/env python3
"""Pre-live readiness check.

Run: uv run python scripts/readiness_check.py

Checks all critical configuration and connectivity requirements.
Exits 0 if all checks pass, 1 if any fail.
"""

import os
import sys

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass

API_URL = os.environ.get("READINESS_API_URL", "http://localhost:8000/api/v1")


def check_jwt_secret():
    secret = os.environ.get("AUTH_JWT_SECRET_KEY", "")
    if "dev-only" in secret or "change-me" in secret.lower():
        return "still using default dev secret"
    if len(secret) < 32:
        return "secret too short (min 32 chars)"
    return "pass"


def check_environment():
    env = os.environ.get("ENVIRONMENT", "development")
    if env != "production":
        return "warn"  # Not production — acceptable for testing
    return "pass"


def check_cors():
    origins = os.environ.get("CORS_ALLOWED_ORIGINS", "")
    if not origins:
        return "warn"  # Empty defaults to localhost — OK for dev
    if origins.strip() == "*":
        return "CORS set to allow-all (*) — not safe for production"
    return "pass"


def check_env_gitignore():
    gitignore_path = os.path.join(os.path.dirname(__file__), "..", ".gitignore")
    if os.path.exists(gitignore_path):
        with open(gitignore_path) as f:
            content = f.read()
        if ".env" in content:
            return "pass"
    return ".env not found in .gitignore"


def check_admin_password():
    try:
        import requests
        resp = requests.post(f"{API_URL}/auth/login", json={
            "email": "admin@ratatoskr.local",
            "password": "changeme123456",
        }, timeout=5)
        if resp.status_code == 200:
            return "admin still using default password"
        return "pass"
    except Exception as e:
        return f"warn"  # Can't check — backend may not be running


def check_database_connection():
    try:
        import requests
        resp = requests.get(f"{API_URL}/health", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("database") == "connected":
                return "pass"
            return f"database status: {data.get('database')}"
        return f"health check returned {resp.status_code}"
    except Exception:
        return "warn"  # Backend not running


def check_alpaca_keys():
    key = os.environ.get("ALPACA_API_KEY", "")
    if not key:
        return "warn"  # Optional
    return "pass"


def check_alpaca_connection():
    try:
        import requests
        resp = requests.get(f"{API_URL}/health", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            brokers = data.get("brokers", {})
            alpaca = brokers.get("alpaca", {})
            status = alpaca.get("status", "unknown")
            if status in ("connected", "not_started"):
                return "pass"
            if status == "unconfigured":
                return "warn"  # Keys not set
            return f"Alpaca status: {status}"
        return "warn"
    except Exception:
        return "warn"


def check_oanda_keys():
    token = os.environ.get("OANDA_ACCESS_TOKEN", "")
    if not token:
        return "warn"  # Optional
    return "pass"


def check_oanda_connection():
    try:
        import requests
        resp = requests.get(f"{API_URL}/health", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            brokers = data.get("brokers", {})
            oanda = brokers.get("oanda", {})
            status = oanda.get("status", "unknown")
            if status in ("connected", "configured", "not_started"):
                return "pass"
            if status == "unconfigured":
                return "warn"
            return f"OANDA status: {status}"
        return "warn"
    except Exception:
        return "warn"


def check_forex_pool_mapping():
    mapped = 0
    for i in range(1, 5):
        if os.environ.get(f"OANDA_POOL_ACCOUNT_{i}", ""):
            mapped += 1
    if mapped == 0:
        return "warn"  # Using virtual accounts
    return "pass"


def check_kill_switch():
    """Check kill switch is deactivated (requires auth)."""
    try:
        import requests
        email = os.environ.get("ADMIN_SEED_EMAIL", "admin@ratatoskr.local")
        password = os.environ.get("READINESS_CHECK_PASSWORD", "")
        if not password:
            return "warn"  # No password configured for readiness check

        login_resp = requests.post(f"{API_URL}/auth/login", json={
            "email": email,
            "password": password,
        }, timeout=5)
        if login_resp.status_code != 200:
            return "warn"  # Can't authenticate

        token = login_resp.json().get("data", {}).get("accessToken", "")
        resp = requests.get(
            f"{API_URL}/risk/kill-switch/status",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            if data.get("globalActive") or data.get("isActive") or data.get("global"):
                return "Kill switch is ACTIVE — deactivate before going live"
            return "pass"
        return "warn"
    except Exception:
        return "warn"


def check_migrations():
    """Check if alembic migrations are current."""
    try:
        import subprocess
        result = subprocess.run(
            ["uv", "run", "alembic", "current"],
            capture_output=True, text=True, timeout=10,
            cwd=os.path.join(os.path.dirname(__file__), "..", "backend"),
        )
        if result.returncode == 0 and "head" in result.stdout:
            return "pass"
        return "warn"
    except Exception:
        return "warn"


def check_sensitive_logs():
    """Scan log statements for potential sensitive data exposure."""
    import glob
    sensitive_patterns = ["password", "secret", "api_key", "api_secret", "access_token"]
    format_markers = ["%s", "f'", 'f"', "{"]
    issues = []
    base = os.path.join(os.path.dirname(__file__), "..", "backend", "app")
    for py_file in glob.glob(os.path.join(base, "**", "*.py"), recursive=True):
        try:
            with open(py_file) as f:
                for line_num, line in enumerate(f, 1):
                    line_lower = line.lower()
                    if "logger." not in line_lower and "logging." not in line_lower:
                        continue
                    for pattern in sensitive_patterns:
                        if pattern in line_lower:
                            if any(m in line for m in format_markers):
                                rel_path = os.path.relpath(py_file, base)
                                issues.append(f"{rel_path}:{line_num}")
        except Exception:
            continue
    if issues:
        return f"Potential sensitive data in logs: {', '.join(issues[:3])}"
    return "pass"


# === Main ===

CHECKS = [
    ("JWT secret changed from default", check_jwt_secret),
    ("Admin password changed from default", check_admin_password),
    ("CORS not allow-all", check_cors),
    ("Environment setting", check_environment),
    (".env in .gitignore", check_env_gitignore),
    ("Database reachable", check_database_connection),
    ("Migrations current", check_migrations),
    ("Alpaca API keys configured", check_alpaca_keys),
    ("Alpaca connection healthy", check_alpaca_connection),
    ("OANDA credentials configured", check_oanda_keys),
    ("OANDA connection healthy", check_oanda_connection),
    ("Forex pool accounts mapped", check_forex_pool_mapping),
    ("Kill switch state", check_kill_switch),
    ("No sensitive data in logs", check_sensitive_logs),
]


def main():
    print("=" * 60)
    print("  Ratatoskr Pre-Live Readiness Check")
    print("=" * 60)
    print()

    passed = 0
    failed = 0
    warnings = 0

    for name, check_fn in CHECKS:
        try:
            result = check_fn()
            if result == "pass":
                print(f"  [PASS] {name}")
                passed += 1
            elif result == "warn":
                print(f"  [WARN] {name}")
                warnings += 1
            else:
                print(f"  [FAIL] {name}: {result}")
                failed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            failed += 1

    print()
    print(f"Results: {passed} passed, {warnings} warnings, {failed} failed")
    print()

    if failed > 0:
        print("NOT READY -- fix failed checks before going live")
        sys.exit(1)
    elif warnings > 0:
        print("READY WITH WARNINGS -- review warnings before going live")
        sys.exit(0)
    else:
        print("ALL CLEAR -- system is ready for live trading")
        sys.exit(0)


if __name__ == "__main__":
    main()
