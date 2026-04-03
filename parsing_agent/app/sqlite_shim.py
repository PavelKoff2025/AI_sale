"""Подмена stdlib sqlite3 на встроенный SQLite ≥ 3.35 (требование ChromaDB)."""
import sys


def _apply() -> None:
    try:
        import sqlite3

        if sqlite3.sqlite_version_info >= (3, 35, 0):
            return
    except Exception:
        return
    try:
        import pysqlite3

        sys.modules["sqlite3"] = pysqlite3
    except ImportError:
        pass


_apply()
