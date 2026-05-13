import os
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Notification settings
USE_NOTIFY = os.getenv("USE_NOTIFY", "true").lower() == "true"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Rate limiting
REGISTRY_DELAY = float(os.getenv("REGISTRY_DELAY", "0.5"))

# Workers
WORKERS = int(os.getenv("WORKERS", "3"))

# Database
DB_PATH = BASE_DIR / "hunter.db"

# Manifest patterns file
PATTERNS_FILE = BASE_DIR / "package_patterns.txt"

# Temp directory for downloads
TMP_DIR = BASE_DIR / "tmp_downloads"


# Global lock for thread-safe SQLite access.
# SQLite doesn't support concurrent writes from multiple threads on the same
# connection — all DB operations must be serialized.
_db_lock = threading.Lock()


def get_db():
    """Get SQLite database connection, create tables if needed."""
    db = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("""
        CREATE TABLE IF NOT EXISTS checked_packages (
            name TEXT NOT NULL,
            ecosystem TEXT NOT NULL,
            status TEXT NOT NULL,
            source TEXT,
            found_at TEXT DEFAULT (datetime('now')),
            claimed_at TEXT,
            PRIMARY KEY (name, ecosystem)
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS analyzed_files (
            identifier TEXT PRIMARY KEY,
            analyzed_at TEXT DEFAULT (datetime('now'))
        )
    """)
    db.commit()
    return db


# How long before rechecking a cached result
_CACHE_TTL = {
    "exists":    timedelta(days=7),   # package exists — recheck after 7 days
    "claimable": timedelta(days=1),   # was claimable — recheck daily to confirm
}


def is_already_checked(db, name, ecosystem):
    """Check if a package was already checked and the result is still fresh.

    Returns True (skip) only if the cached result exists AND is within TTL.
    Returns False (recheck) if expired or not found.
    """
    with _db_lock:
        row = db.execute(
            "SELECT status, found_at FROM checked_packages WHERE name = ? AND ecosystem = ?",
            (name, ecosystem)
        ).fetchone()

    if row is None:
        return False

    status, found_at = row
    ttl = _CACHE_TTL.get(status)

    if ttl and found_at:
        try:
            cached_time = datetime.fromisoformat(found_at)
            if datetime.utcnow() - cached_time > ttl:
                return False  # expired — recheck
        except (ValueError, TypeError):
            pass

    return True


def is_already_analyzed(db, identifier):
    """Check if a file/URL was already analyzed."""
    with _db_lock:
        row = db.execute(
            "SELECT 1 FROM analyzed_files WHERE identifier = ?",
            (identifier,)
        ).fetchone()
    return row is not None


def mark_analyzed(db, identifier):
    """Mark a file/URL as analyzed."""
    with _db_lock:
        db.execute(
            "INSERT OR IGNORE INTO analyzed_files (identifier) VALUES (?)",
            (identifier,)
        )
        db.commit()


def save_package(db, name, ecosystem, status, source=""):
    """Save a package check result."""
    with _db_lock:
        db.execute(
            "INSERT OR REPLACE INTO checked_packages (name, ecosystem, status, source) VALUES (?, ?, ?, ?)",
            (name, ecosystem, status, source)
        )
        db.commit()


