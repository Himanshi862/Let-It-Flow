"""
Let It Flow - database helper.

* Works with MySQL (the project database) and, for quick tests, SQLite.
* EVERY query uses placeholders (%s) with a separate parameter list - never
  string-formatting user input into SQL.  That is what prevents SQL injection.
* Each web request gets its own connection (flask.g) and closes it afterwards.
"""
import os
import re
import sqlite3
from datetime import date, datetime

from flask import current_app, g

try:                                    # PyMySQL is only needed for the MySQL backend
    import pymysql
    import pymysql.cursors
except ImportError:                     # pragma: no cover
    pymysql = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---- SQLite: turn DATE / DATETIME columns into Python date / datetime ------
sqlite3.register_converter("DATE", lambda b: date.fromisoformat(b.decode()))
sqlite3.register_converter(
    "DATETIME", lambda b: datetime.fromisoformat(b.decode().replace(" ", "T")))
sqlite3.register_adapter(date, lambda d: d.isoformat())
sqlite3.register_adapter(datetime, lambda d: d.isoformat(sep=" "))


def _backend():
    return current_app.config["DB_BACKEND"]


def _connect():
    cfg = current_app.config
    if _backend() == "sqlite":
        conn = sqlite3.connect(cfg["SQLITE_PATH"], detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    if pymysql is None:
        raise RuntimeError("PyMySQL is not installed. Run: pip install -r requirements.txt")
    return pymysql.connect(
        host=cfg["MYSQL_HOST"], port=cfg["MYSQL_PORT"], user=cfg["MYSQL_USER"],
        password=cfg["MYSQL_PASSWORD"], database=cfg["MYSQL_DATABASE"], charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor, autocommit=False)


def get_db():
    if "db" not in g:
        g.db = _connect()
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _sql(sql):
    """Write SQL once with %s placeholders; SQLite wants ? instead."""
    return sql.replace("%s", "?") if _backend() == "sqlite" else sql


def _rows(cur):
    return [dict(r) for r in cur.fetchall()]


def query_all(sql, params=()):
    cur = get_db().cursor()
    cur.execute(_sql(sql), params)
    return _rows(cur)


def query_one(sql, params=()):
    rows = query_all(sql, params)
    return rows[0] if rows else None


def execute(sql, params=()):
    """INSERT / UPDATE / DELETE.  Commits, returns the new row id (for inserts)."""
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute(_sql(sql), params)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return cur.lastrowid


def upsert(table, key_cols, data):
    """
    Insert a row, or update it when a row with the same key already exists.
    Done in plain Python so the same code works for MySQL and SQLite.
    table / column names come from OUR code (never from users); values are parameters.
    """
    where = " AND ".join(f"{c} = %s" for c in key_cols)
    existing = query_one(f"SELECT 1 AS x FROM {table} WHERE {where}", [data[c] for c in key_cols])
    if existing:
        set_cols = [c for c in data if c not in key_cols]
        if set_cols:
            sets = ", ".join(f"{c} = %s" for c in set_cols)
            execute(f"UPDATE {table} SET {sets} WHERE {where}",
                    [data[c] for c in set_cols] + [data[c] for c in key_cols])
    else:
        cols = ", ".join(data)
        marks = ", ".join(["%s"] * len(data))
        execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", list(data.values()))


def is_integrity_error(exc):
    if isinstance(exc, sqlite3.IntegrityError):
        return True
    return pymysql is not None and isinstance(exc, pymysql.err.IntegrityError)


# ---------------------------------------------------------------------------
def init_db(app):
    """Create the database (MySQL) and all tables.  Safe to run many times."""
    cfg = app.config
    if cfg["DB_BACKEND"] == "sqlite":
        os.makedirs(os.path.dirname(cfg["SQLITE_PATH"]), exist_ok=True)
        conn = sqlite3.connect(cfg["SQLITE_PATH"])
        with open(os.path.join(BASE_DIR, "schema_sqlite.sql"), encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.close()
        return
    if pymysql is None:
        raise RuntimeError("PyMySQL is not installed. Run: pip install -r requirements.txt")
    conn = pymysql.connect(host=cfg["MYSQL_HOST"], port=cfg["MYSQL_PORT"], user=cfg["MYSQL_USER"],
                           password=cfg["MYSQL_PASSWORD"], charset="utf8mb4")
    with open(os.path.join(BASE_DIR, "schema.sql"), encoding="utf-8") as f:
        script = f.read()
    # use the database name from .env instead of the hard-coded one in schema.sql
    script = script.replace("let_it_flow", cfg["MYSQL_DATABASE"])
    script = re.sub(r"--.*", "", script)                 # drop SQL comments
    with conn.cursor() as cur:
        for statement in script.split(";"):
            if statement.strip():
                cur.execute(statement)
    conn.commit()
    conn.close()
