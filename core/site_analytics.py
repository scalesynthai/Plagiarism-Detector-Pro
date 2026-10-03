"""Small, privacy-conscious site analytics store.

Page views contain only a timestamp and route. Email addresses are collected in
a separate opt-in table and are never joined to browsing activity.
"""

from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path


EMAIL_RE = re.compile(r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+$", re.IGNORECASE)


class SiteAnalytics:
    def __init__(self, database_path: str):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=10000")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS page_views (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    viewed_at TEXT NOT NULL,
                    path TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_page_views_viewed_at
                    ON page_views(viewed_at);
                CREATE TABLE IF NOT EXISTS email_subscribers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    consented_at TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'site_footer'
                );
                """
            )

    @staticmethod
    def normalize_email(value: object) -> str:
        email = str(value or "").strip().lower()
        if len(email) > 254 or not EMAIL_RE.fullmatch(email):
            raise ValueError("Enter a valid email address.")
        return email

    def record_page_view(self, path: str = "/") -> None:
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as connection:
            connection.execute(
                "INSERT INTO page_views (viewed_at, path) VALUES (?, ?)",
                (now, path[:200]),
            )
            connection.commit()

    def summary(self, days: int = 30) -> dict:
        days = max(1, min(int(days), 365))
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with closing(self._connect()) as connection:
            recent = connection.execute(
                "SELECT COUNT(*) FROM page_views WHERE viewed_at >= ?", (cutoff,)
            ).fetchone()[0]
            total = connection.execute("SELECT COUNT(*) FROM page_views").fetchone()[0]
        return {"page_views": recent, "all_time_page_views": total, "days": days}

    def subscribe(self, value: object, source: str = "site_footer") -> bool:
        email = self.normalize_email(value)
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as connection:
            cursor = connection.execute(
                "INSERT OR IGNORE INTO email_subscribers (email, consented_at, source) VALUES (?, ?, ?)",
                (email, now, source[:80]),
            )
            connection.commit()
            return cursor.rowcount == 1

    def subscribers(self) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT email, consented_at, source FROM email_subscribers ORDER BY consented_at DESC"
            ).fetchall()
        return [
            {"email": email, "consented_at": consented_at, "source": source}
            for email, consented_at, source in rows
        ]
