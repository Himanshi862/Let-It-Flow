"""
Let It Flow - configuration.

Secrets (database password, secret key) are read from environment variables or
from a local file called  .env  that you create yourself.  NEVER put real
passwords in source code or commit .env to GitHub.
"""
import os
import secrets

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_dotenv(path):
    """Tiny .env reader (so we don't need an extra package)."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(os.path.join(BASE_DIR, ".env"))


def _secret_key():
    """Use SECRET_KEY from the environment, otherwise create one once and keep it."""
    if os.environ.get("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    key_file = os.path.join(BASE_DIR, "instance", "secret_key.txt")
    os.makedirs(os.path.dirname(key_file), exist_ok=True)
    if not os.path.exists(key_file):
        with open(key_file, "w") as f:
            f.write(secrets.token_hex(32))
    with open(key_file) as f:
        return f.read().strip()


class Config:
    SECRET_KEY = _secret_key()

    # "mysql" (the project database) or "sqlite" (zero-setup, handy for quick tests)
    DB_BACKEND = os.environ.get("DB_BACKEND", "mysql").lower()

    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "let_it_flow")

    SQLITE_PATH = os.environ.get("SQLITE_PATH", os.path.join(BASE_DIR, "instance", "let_it_flow.db"))

    # Secure session cookies
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"  # set 1 behind HTTPS
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8   # 8 hours
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024
