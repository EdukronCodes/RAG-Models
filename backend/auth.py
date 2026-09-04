import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import g, jsonify, session
from werkzeug.security import check_password_hash, generate_password_hash

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_PATH = os.environ.get("DATABASE_PATH", os.path.join(ROOT_DIR, "instance", "app.db"))
SESSION_TTL_DAYS = 7


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class AuthStore:
    def __init__(self, database_path=DATABASE_PATH):
        self.database_path = database_path
        os.makedirs(os.path.dirname(database_path), exist_ok=True)
        self._initialize()

    def connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self):
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS login_sessions (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    title TEXT NOT NULL DEFAULT 'New support session',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_session_id INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_login_sessions_user ON login_sessions(user_id);
                CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id);
                CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages(chat_session_id);
                """
            )

    def create_user(self, username, password):
        username = username.strip()
        if len(username) < 3 or len(username) > 80:
            raise ValueError("Username must be between 3 and 80 characters.")
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters.")
        try:
            with self.connect() as connection:
                cursor = connection.execute(
                    "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                    (username, generate_password_hash(password), utc_now()),
                )
                return self._user(connection, cursor.lastrowid)
        except sqlite3.IntegrityError as error:
            raise ValueError("That username is already registered.") from error

    def authenticate(self, username, password):
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM users WHERE username = ?", (username.strip(),)).fetchone()
            if row and check_password_hash(row["password_hash"], password):
                return dict(row)
        return None

    def _user(self, connection, user_id):
        row = connection.execute("SELECT id, username, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row)

    def create_login_session(self, user_id):
        now = datetime.now(timezone.utc)
        token = secrets.token_urlsafe(32)
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO login_sessions VALUES (?, ?, ?, ?, ?)",
                (token, user_id, now.isoformat(), now.isoformat(), (now + timedelta(days=SESSION_TTL_DAYS)).isoformat()),
            )
        return token

    def get_user_for_session(self, token):
        if not token:
            return None
        now = utc_now()
        with self.connect() as connection:
            row = connection.execute(
                "SELECT u.id, u.username, u.created_at FROM login_sessions s JOIN users u ON u.id = s.user_id WHERE s.id = ? AND s.expires_at > ?",
                (token, now),
            ).fetchone()
            if row:
                connection.execute("UPDATE login_sessions SET last_seen_at = ? WHERE id = ?", (now, token))
                return dict(row)
        return None

    def delete_login_session(self, token):
        with self.connect() as connection:
            connection.execute("DELETE FROM login_sessions WHERE id = ?", (token,))

    def create_chat_session(self, user_id, title="New support session"):
        now = utc_now()
        with self.connect() as connection:
            cursor = connection.execute(
                "INSERT INTO chat_sessions (user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (user_id, title[:120], now, now),
            )
            return self.get_chat_session(user_id, cursor.lastrowid, connection)

    def list_chat_sessions(self, user_id):
        with self.connect() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM chat_sessions WHERE user_id = ? ORDER BY updated_at DESC", (user_id,))]

    def get_chat_session(self, user_id, chat_id, connection=None):
        owns_connection = connection is None
        connection = connection or self.connect()
        try:
            row = connection.execute("SELECT * FROM chat_sessions WHERE id = ? AND user_id = ?", (chat_id, user_id)).fetchone()
            return dict(row) if row else None
        finally:
            if owns_connection:
                connection.close()

    def add_message(self, user_id, chat_id, role, content, metadata=None):
        now = utc_now()
        with self.connect() as connection:
            chat = self.get_chat_session(user_id, chat_id, connection)
            if not chat:
                return False
            connection.execute(
                "INSERT INTO messages (chat_session_id, role, content, metadata, created_at) VALUES (?, ?, ?, ?, ?)",
                (chat_id, role, content, metadata, now),
            )
            connection.execute("UPDATE chat_sessions SET updated_at = ? WHERE id = ?", (now, chat_id))
        return True

    def get_messages(self, user_id, chat_id):
        with self.connect() as connection:
            if not self.get_chat_session(user_id, chat_id, connection):
                return None
            return [dict(row) for row in connection.execute("SELECT role, content, metadata, created_at FROM messages WHERE chat_session_id = ? ORDER BY id", (chat_id,))]

    def delete_chat_session(self, user_id, chat_id):
        with self.connect() as connection:
            cursor = connection.execute("DELETE FROM chat_sessions WHERE id = ? AND user_id = ?", (chat_id, user_id))
            return cursor.rowcount > 0


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not getattr(g, "user", None):
            return jsonify({"error": "Authentication required."}), 401
        return view(*args, **kwargs)
    return wrapped


def load_user(store):
    g.user = store.get_user_for_session(session.get("login_session"))
