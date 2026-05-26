# tests/test_catalog.py
import pytest
import os
from src.db.db_manager import DatabaseManager


# Фікстура для створення чистої БД перед кожним тестом
@pytest.fixture
def db(tmp_path):
    db_file = tmp_path / "test_catalog.db"
    db_manager = DatabaseManager(str(db_file))
    schema_path = os.path.join(os.path.dirname(__file__), '../src/db/migrations/schema.sql')

    with open(schema_path, "r", encoding="utf-8") as f:
        db_manager.get_connection().executescript(f.read())

    return db_manager


# Фікстура для наповнення довідників (автори та жанри)
@pytest.fixture
def seed_data(db):
    author_id = db.execute_query(
        "INSERT INTO AUTHORS (first_name, last_name, country) VALUES (?, ?, ?)",
        ("Тарас", "Шевченко", "Україна")
    )
    genre_id = db.execute_query(
        "INSERT INTO GENRES (name) VALUES (?)",
        ("Поезія",)
    )
    return {"author_id": author_id, "genre_id": genre_id}


def test_add_book_with_copies(db, seed_data):
    """Тестування логіки додавання книги та генерації примірників (Use Case B1)."""
    title = "Кобзар"
    isbn = "978-966-123-456-7"
    year = 2023
    copies_count = 3

    # Симуляція коду з BookForm.save_book()
    book_id = db.execute_query(
        "INSERT INTO BOOKS (title, author_id, genre_id, isbn, year, total_copies) VALUES (?, ?, ?, ?, ?, ?)",
        (title, seed_data["author_id"], seed_data["genre_id"], isbn, year, copies_count)
    )

    assert book_id == 1

    # Симуляція генерації примірників
    for i in range(1, copies_count + 1):
        inv_number = f"INV-{book_id:04d}-{i:03d}"
        db.execute_query(
            "INSERT INTO COPIES (book_id, inventory_number, status) VALUES (?, ?, 'available')",
            (book_id, inv_number)
        )

    # Перевірка результату в БД
    saved_copies = db.fetch_all("SELECT * FROM COPIES WHERE book_id = ?", (book_id,))

    assert len(saved_copies) == 3
    assert saved_copies[0]["inventory_number"] == "INV-0001-001"
    assert saved_copies[0]["status"] == "available"
    assert saved_copies[2]["inventory_number"] == "INV-0001-003"


def test_catalog_search_query(db, seed_data):
    """Тестування SQL-запиту для пошуку книг у каталозі (Use Case C1)."""
    # Додаємо книгу 1
    db.execute_query(
        "INSERT INTO BOOKS (title, author_id, genre_id, isbn, total_copies) VALUES (?, ?, ?, ?, ?)",
        ("Кобзар", seed_data["author_id"], seed_data["genre_id"], "111-222", 2)
    )

    # Додаємо книгу 2 з іншим жанром
    genre2_id = db.execute_query("INSERT INTO GENRES (name) VALUES (?)", ("Фантастика",))
    db.execute_query(
        "INSERT INTO BOOKS (title, author_id, genre_id, isbn, total_copies) VALUES (?, ?, ?, ?, ?)",
        ("Дюна", seed_data["author_id"], genre2_id, "333-444", 0)
    )

    # Симуляція пошуку з CatalogView.load_data() за назвою "Кобзар"
    search_term = "%Кобзар%"
    query = """
        SELECT b.title, a.last_name as author_name, g.name as genre_name
        FROM BOOKS b
        LEFT JOIN AUTHORS a ON b.author_id = a.id
        LEFT JOIN GENRES g ON b.genre_id = g.id
        WHERE (b.title LIKE ? OR a.last_name LIKE ? OR b.isbn LIKE ?)
    """
    results = db.fetch_all(query, [search_term, search_term, search_term])

    assert len(results) == 1
    assert results[0]["title"] == "Кобзар"
    assert results[0]["genre_name"] == "Поезія"
    assert results[0]["author_name"] == "Шевченко"


def test_write_off_copy(db, seed_data):
    """Тестування логіки списання примірника (Use Case B2)."""
    # Створюємо книгу та примірник
    book_id = db.execute_query(
        "INSERT INTO BOOKS (title, author_id, genre_id, total_copies) VALUES (?, ?, ?, ?)",
        ("Тіні забутих предків", seed_data["author_id"], seed_data["genre_id"], 1)
    )
    copy_id = db.execute_query(
        "INSERT INTO COPIES (book_id, inventory_number, status) VALUES (?, ?, 'available')",
        (book_id, "INV-TEST-001")
    )

    # Симуляція методу CopyManager.write_off_copy()
    db.execute_query("UPDATE COPIES SET status = 'written_off' WHERE id = ?", (copy_id,))

    # Перевірка зміни статусу
    updated_copy = db.fetch_one("SELECT status FROM COPIES WHERE id = ?", (copy_id,))
    assert updated_copy["status"] == "written_off"