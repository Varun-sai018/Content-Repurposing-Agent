"""SQLite helper functions for storing generated posts."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


DB_FILENAME = "repurpose_agent.db"
DB_PATH = Path(__file__).resolve().parent.parent / DB_FILENAME


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(db_path: Path = DB_PATH) -> None:
    connection = get_connection(db_path)
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT NOT NULL,
                tone TEXT NOT NULL,
                platform TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )

        # Ensure legacy databases have the user_id column
        columns = connection.execute("PRAGMA table_info(posts)").fetchall()
        column_names = {column[1] for column in columns}
        if "user_id" not in column_names:
            connection.execute("ALTER TABLE posts ADD COLUMN user_id INTEGER")

        connection.commit()
    finally:
        connection.close()


def save_to_db(
    title: str,
    tone: str,
    platform_outputs: Dict[str, str],
    user_id: Optional[int] = None,
    db_path: Path = DB_PATH,
) -> None:
    timestamp = datetime.utcnow().isoformat()
    records = [
        (title.strip(), tone.strip(), platform, content.strip(), timestamp, user_id)
        for platform, content in platform_outputs.items()
        if content.strip()
    ]

    if not records:
        return

    connection = get_connection(db_path)
    try:
        connection.executemany(
            """
            INSERT INTO posts (title, tone, platform, content, timestamp, user_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            records,
        )
        connection.commit()
    finally:
        connection.close()


def view_saved_posts(
    limit: int = 50,
    user_id: Optional[int] = None,
    include_content: bool = False,
    db_path: Path = DB_PATH,
) -> List[sqlite3.Row]:
    connection = get_connection(db_path)
    try:
        fields = "id, title, tone, platform, timestamp"
        if include_content:
            fields += ", content"

        if user_id is None:
            cursor = connection.execute(
                f"SELECT {fields} FROM posts ORDER BY id DESC LIMIT ?",
                (limit,),
            )
        else:
            cursor = connection.execute(
                f"SELECT {fields} FROM posts WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit),
            )
        return list(cursor.fetchall())
    finally:
        connection.close()


def fetch_all_posts(
    limit: Optional[int] = None,
    include_content: bool = True,
    db_path: Path = DB_PATH,
) -> List[sqlite3.Row]:
    connection = get_connection(db_path)
    try:
        fields = "id, title, tone, platform, timestamp"
        if include_content:
            fields += ", content"
        query = f"SELECT {fields} FROM posts ORDER BY timestamp DESC"
        params: Tuple = ()
        if limit is not None:
            query += " LIMIT ?"
            params = (limit,)
        cursor = connection.execute(query, params)
        return list(cursor.fetchall())
    finally:
        connection.close()


def get_user_by_email(email: str, db_path: Path = DB_PATH) -> Optional[sqlite3.Row]:
    connection = get_connection(db_path)
    try:
        cursor = connection.execute("SELECT * FROM users WHERE email = ?", (email.strip(),))
        return cursor.fetchone()
    finally:
        connection.close()


def get_user_by_id(user_id: int, db_path: Path = DB_PATH) -> Optional[sqlite3.Row]:
    connection = get_connection(db_path)
    try:
        cursor = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        return cursor.fetchone()
    finally:
        connection.close()


def insert_user(
    name: str,
    email: str,
    password_hash: str,
    db_path: Path = DB_PATH,
) -> int:
    connection = get_connection(db_path)
    try:
        cursor = connection.execute(
            "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (name.strip(), email.strip().lower(), password_hash, datetime.utcnow().isoformat()),
        )
        connection.commit()
        return int(cursor.lastrowid)
    finally:
        connection.close()


__all__ = [
    "init_db",
    "save_to_db",
    "view_saved_posts",
    "get_user_by_email",
    "get_user_by_id",
    "insert_user",
    "fetch_all_posts",
    "DB_PATH",
    "DB_FILENAME",
]


__all__ = ["init_db", "save_to_db", "view_saved_posts", "DB_PATH", "DB_FILENAME"]

