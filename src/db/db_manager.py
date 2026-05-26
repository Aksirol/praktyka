# src/db/db_manager.py
import sqlite3
import bcrypt
import os

class DatabaseManager:
    def __init__(self, db_path="data/library.db"):
        self.db_path = db_path
        # Переконуємось, що папка для БД існує
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def get_connection(self):
        """Створює та повертає підключення до БД з підтримкою зовнішніх ключів."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Дозволяє звертатися до колонок за іменами
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def execute_query(self, query, params=(), commit=True):
        """Виконує запит (INSERT, UPDATE, DELETE) з підтримкою транзакцій."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if commit:
                conn.commit()
            return cursor.lastrowid

    def fetch_all(self, query, params=()):
        """Повертає всі результати запиту."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def fetch_one(self, query, params=()):
        """Повертає один результат запиту."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def hash_password(password: str) -> str:
        """Хешує пароль алгоритмом bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    @staticmethod
    def check_password(password: str, hashed: str) -> bool:
        """Перевіряє, чи відповідає пароль хешу."""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))