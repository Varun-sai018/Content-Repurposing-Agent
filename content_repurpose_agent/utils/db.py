"""SQLite helper functions for storing generated posts."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


DB_FILENAME = "repurpose_agent.db"
DB_PATH = Path(__file__).resolve().parent.parent / DB_FILENAME


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    return sqlite3.connect(db_path)


def init_db(db_path: Path = DB_PATH) -> None:
    connection = get_connection(db_path)
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                tone TEXT NOT NULL,
                platform TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
            """
        )
        connection.commit()
    finally:
        connection.close()


def save_to_db(
    title: str,
    tone: str,
    platform_outputs: Dict[str, str],
    db_path: Path = DB_PATH,
) -> None:
    timestamp = datetime.utcnow().isoformat()
    records = [
        (title.strip(), tone.strip(), platform, content.strip(), timestamp)
        for platform, content in platform_outputs.items()
        if content.strip()
    ]

    if not records:
        return

    connection = get_connection(db_path)
    try:
        connection.executemany(
            "INSERT INTO posts (title, tone, platform, content, timestamp) VALUES (?, ?, ?, ?, ?)",
            records,
        )
        connection.commit()
    finally:
        connection.close()


def view_saved_posts(limit: int = 50, db_path: Path = DB_PATH) -> List[Tuple[int, str, str, str, str]]:
    connection = get_connection(db_path)
    try:
        cursor = connection.execute(
            "SELECT id, title, tone, platform, timestamp FROM posts ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return list(cursor.fetchall())
    finally:
        connection.close()


__all__ = ["init_db", "save_to_db", "view_saved_posts", "DB_PATH", "DB_FILENAME"]

