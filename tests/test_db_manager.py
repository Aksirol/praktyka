# tests/test_db_manager.py
import pytest
import sqlite3
import os
from src.db.db_manager import DatabaseManager


# Фікстура для ініціалізації тимчасової БД перед кожним тестом
@pytest.fixture
def db(tmp_path):
    # Створюємо тимчасовий файл БД
    db_file = tmp_path / "test_library.db"
    db_manager = DatabaseManager(str(db_file))

    # Шлях до файлу schema.sql
    schema_path = os.path.join(
        os.path.dirname(__file__),
        '../src/db/migrations/schema.sql'
    )

    # Застосовуємо схему
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_script = f.read()
        with db_manager.get_connection() as conn:
            conn.executescript(schema_script)

    return db_manager


def test_password_hashing():
    """Тестування хешування та перевірки паролів."""
    password = "secure_password_123"
    hashed = DatabaseManager.hash_password(password)

    assert hashed != password
    assert DatabaseManager.check_password(password, hashed) is True
    assert DatabaseManager.check_password("wrong_password", hashed) is False


def test_insert_and_fetch_one(db):
    """Тестування додавання запису та його отримання."""
    genre_name = "Фентезі"

    # Insert
    genre_id = db.execute_query(
        "INSERT INTO GENRES (name) VALUES (?)",
        (genre_name,)
    )
    assert genre_id == 1

    # Fetch
    genre = db.fetch_one("SELECT * FROM GENRES WHERE id = ?", (genre_id,))
    assert genre is not None
    assert genre['name'] == genre_name


def test_fetch_all(db):
    """Тестування отримання списку записів."""
    genres = ["Детектив", "Роман", "Поезія"]
    for genre in genres:
        db.execute_query("INSERT INTO GENRES (name) VALUES (?)", (genre,))

    results = db.fetch_all("SELECT * FROM GENRES ORDER BY id")
    assert len(results) == 3
    assert results[0]['name'] == "Детектив"
    assert results[2]['name'] == "Поезія"


def test_foreign_key_constraint(db):
    """Тестування підтримки зовнішніх ключів (PRAGMA foreign_keys = ON)."""
    # Спроба додати книгу з неіснуючим author_id
    with pytest.raises(sqlite3.IntegrityError) as excinfo:
        db.execute_query(
            "INSERT INTO BOOKS (title, author_id) VALUES (?, ?)",
            ("Тестова книга", 999)  # 999 - неіснуючий автор
        )

    assert "FOREIGN KEY constraint failed" in str(excinfo.value)


def test_unique_constraint(db):
    """Тестування обмеження UNIQUE."""
    db.execute_query("INSERT INTO GENRES (name) VALUES (?)", ("Історія",))

    with pytest.raises(sqlite3.IntegrityError):
        # Спроба додати жанр з таким самим ім'ям
        db.execute_query("INSERT INTO GENRES (name) VALUES (?)", ("Історія",))