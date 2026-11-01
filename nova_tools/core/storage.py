"""SQLite tabanlı kalıcı depolama: notlar, ayarlar ve son kullanılan araçlar."""
from __future__ import annotations

import os
import sqlite3
import sys
import threading
import time
from dataclasses import dataclass
from typing import Optional

from .text import tr_fold

PORTABLE_MARKER = "portable.txt"


def is_portable() -> bool:
    exe_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else sys.argv[0]))
    return os.path.exists(os.path.join(exe_dir, PORTABLE_MARKER))


def default_data_dir() -> str:
    """Veri klasörü: NOVA_DATA_DIR > taşınabilir mod (exe yanında data/) > %APPDATA%\\NovaTools."""
    env = os.environ.get("NOVA_DATA_DIR")
    if env:
        return env
    if getattr(sys, "frozen", False) and is_portable():
        return os.path.join(os.path.dirname(sys.executable), "data")
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "NovaTools")
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "NovaTools")


@dataclass
class Note:
    id: int
    title: str
    content: str
    category: str
    created_at: float
    updated_at: float


SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT 'Genel',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS recent_tools (
    tool TEXT PRIMARY KEY,
    used_at REAL NOT NULL,
    count INTEGER NOT NULL DEFAULT 1
);
"""


class Storage:
    def __init__(self, path: Optional[str] = None):
        if path is None:
            folder = default_data_dir()
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, "nova_tools.db")
        else:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.path = path
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        with self._lock:
            self.conn.close()

    # ---------- Ayarlar ----------
    def get(self, key: str, default: str = "") -> str:
        with self._lock:
            row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set(self, key: str, value: str) -> None:
        with self._lock:
            self.conn.execute(
                "INSERT INTO settings(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, str(value)),
            )
            self.conn.commit()

    # ---------- Notlar ----------
    def add_note(self, title: str = "", content: str = "", category: str = "Genel") -> int:
        now = time.time()
        with self._lock:
            cur = self.conn.execute(
                "INSERT INTO notes(title, content, category, created_at, updated_at) VALUES(?,?,?,?,?)",
                (title, content, category or "Genel", now, now),
            )
            self.conn.commit()
            return int(cur.lastrowid)

    def update_note(self, note_id: int, title: str, content: str, category: str) -> None:
        with self._lock:
            self.conn.execute(
                "UPDATE notes SET title=?, content=?, category=?, updated_at=? WHERE id=?",
                (title, content, category or "Genel", time.time(), note_id),
            )
            self.conn.commit()

    def delete_note(self, note_id: int) -> None:
        with self._lock:
            self.conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
            self.conn.commit()

    def get_note(self, note_id: int) -> Optional[Note]:
        with self._lock:
            row = self.conn.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
        return Note(**dict(row)) if row else None

    def list_notes(self, query: str = "", category: Optional[str] = None) -> list[Note]:
        sql = "SELECT * FROM notes"
        params: list = []
        if category:
            sql += " WHERE category = ?"
            params.append(category)
        sql += " ORDER BY updated_at DESC"
        with self._lock:
            rows = self.conn.execute(sql, params).fetchall()
        notes = [Note(**dict(r)) for r in rows]
        # SQLite LIKE Türkçe harfleri (İ/ı, Ş/ş…) eşlemediği için arama Python'da yapılır.
        q = tr_fold(query.strip())
        if q:
            notes = [n for n in notes if q in tr_fold(n.title + "\n" + n.content)]
        return notes

    def categories(self) -> list[str]:
        with self._lock:
            rows = self.conn.execute("SELECT DISTINCT category FROM notes ORDER BY category").fetchall()
        return [r["category"] for r in rows]

    def note_count(self) -> int:
        with self._lock:
            return int(self.conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0])

    # ---------- Son kullanılan araçlar ----------
    def touch_tool(self, tool: str) -> None:
        with self._lock:
            self.conn.execute(
                "INSERT INTO recent_tools(tool, used_at, count) VALUES(?, ?, 1) "
                "ON CONFLICT(tool) DO UPDATE SET used_at=excluded.used_at, count=count+1",
                (tool, time.time()),
            )
            self.conn.commit()

    def recent_tools(self, limit: int = 6) -> list[tuple[str, float, int]]:
        with self._lock:
            rows = self.conn.execute(
                "SELECT tool, used_at, count FROM recent_tools ORDER BY used_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [(r["tool"], r["used_at"], r["count"]) for r in rows]

    # ---------- Yedekleme ----------
    def backup_to(self, target: str) -> None:
        """Tutarlı bir kopya oluşturur (SQLite online backup API)."""
        if os.path.abspath(target) == os.path.abspath(self.path):
            raise ValueError("Yedek, kullanılan veritabanının üzerine yazılamaz.")
        dest = sqlite3.connect(target)
        try:
            with self._lock:
                self.conn.backup(dest)
        finally:
            dest.close()

    @staticmethod
    def validate_backup(source: str) -> int:
        """Yedek dosyasının geçerli olduğunu doğrular, not sayısını döndürür."""
        try:
            src = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
        except sqlite3.Error as e:
            raise ValueError(f"Dosya açılamadı: {e}") from e
        try:
            tables = {r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {"notes", "settings"}.issubset(tables):
                raise ValueError("Bu dosya bir Nova Tools yedeği değil.")
            return int(src.execute("SELECT COUNT(*) FROM notes").fetchone()[0])
        except sqlite3.DatabaseError as e:
            raise ValueError("Dosya geçerli bir SQLite veritabanı değil.") from e
        finally:
            src.close()

    def restore_from(self, source: str) -> None:
        self.validate_backup(source)
        src = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
        try:
            with self._lock:
                src.backup(self.conn)
                self.conn.executescript(SCHEMA)
                self.conn.commit()
        finally:
            src.close()
