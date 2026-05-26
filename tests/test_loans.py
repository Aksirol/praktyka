# tests/test_loans.py
import pytest
import os
from datetime import datetime, timedelta
from src.db.db_manager import DatabaseManager
from src.services.reader_service import ReaderService
from src.services.loan_service import LoanService
from src.auth.session_manager import SessionManager


@pytest.fixture
def db(tmp_path):
    """Фікстура для ініціалізації тимчасової БД."""
    db_file = tmp_path / "test_loans.db"
    db_manager = DatabaseManager(str(db_file))
    schema_path = os.path.join(os.path.dirname(__file__), '../src/db/migrations/schema.sql')

    with open(schema_path, "r", encoding="utf-8") as f:
        db_manager.get_connection().executescript(f.read())

    return db_manager


@pytest.fixture
def setup_data(db):
    """Фікстура для створення базових даних (користувач, книга, примірник, читач)."""
    # Імітація авторизації
    hashed = DatabaseManager.hash_password("admin_pass")
    user_id = db.execute_query(
        "INSERT INTO USERS (username, password_hash, role) VALUES (?, ?, ?)",
        ("admin", hashed, "Адміністратор")
    )
    SessionManager.login({"id": user_id, "username": "admin", "role": "Адміністратор"})

    # Додавання книги та примірника
    book_id = db.execute_query("INSERT INTO BOOKS (title, total_copies) VALUES (?, ?)", ("1984", 1))
    copy_id = db.execute_query(
        "INSERT INTO COPIES (book_id, inventory_number, status) VALUES (?, ?, 'available')",
        (book_id, "INV-1984-001")
    )

    # Додавання читача
    reader_id = db.execute_query(
        "INSERT INTO READERS (first_name, last_name, reader_type) VALUES (?, ?, ?)",
        ("Іван", "Франко", "Вчитель")
    )

    return {"book_id": book_id, "copy_id": copy_id, "reader_id": reader_id}


@pytest.fixture(autouse=True)
def clear_session():
    """Очищення сесії після кожного тесту."""
    yield
    SessionManager.logout()


def test_register_reader(db):
    """Тестування реєстрації нового читача."""
    service = ReaderService(db)
    service.register_reader("Леся", "Українка", "Вчитель", None, "+380991234567")

    reader = db.fetch_one("SELECT * FROM READERS WHERE first_name = 'Леся'")
    assert reader is not None
    assert reader["last_name"] == "Українка"
    assert reader["is_active"] == 1


def test_issue_loan_success(db, setup_data):
    """Тестування успішної видачі книги та автоматичного розрахунку дати (B4)."""
    service = LoanService(db)
    success, msg = service.issue_loan(setup_data["copy_id"], setup_data["reader_id"], setup_data["book_id"])

    assert success is True
    assert "успішно" in msg

    # Перевірка запису в таблиці LOANS
    loan = db.fetch_one("SELECT * FROM LOANS WHERE reader_id = ?", (setup_data["reader_id"],))
    assert loan is not None

    # Перевірка зміни статусу примірника
    copy = db.fetch_one("SELECT status FROM COPIES WHERE id = ?", (setup_data["copy_id"],))
    assert copy["status"] == "issued"

    # Перевірка правильності розрахунку дати (+14 днів)
    expected_due_date = (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')
    assert loan["due_date"] == expected_due_date


def test_issue_loan_with_overdue(db, setup_data):
    """Тестування блокування видачі при наявності простроченої книги."""
    # Штучно створюємо прострочену видачу
    past_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
    db.execute_query(
        "INSERT INTO LOANS (copy_id, reader_id, due_date) VALUES (?, ?, ?)",
        (setup_data["copy_id"], setup_data["reader_id"], past_date)
    )

    service = LoanService(db)
    # Намагаємось видати нову книгу
    success, msg = service.issue_loan(999, setup_data["reader_id"], setup_data["book_id"])

    assert success is False
    assert "прострочені видачі" in msg


def test_return_loan(db, setup_data):
    """Тестування повернення книги (B5)."""
    service = LoanService(db)
    # Спочатку видаємо книгу
    service.issue_loan(setup_data["copy_id"], setup_data["reader_id"], setup_data["book_id"])
    loan = db.fetch_one("SELECT id FROM LOANS WHERE reader_id = ?", (setup_data["reader_id"],))

    # Повертаємо книгу
    assert service.return_loan(loan["id"], setup_data["copy_id"]) is True

    # Перевіряємо таблицю LOANS (дата повернення не None)
    updated_loan = db.fetch_one("SELECT * FROM LOANS WHERE id = ?", (loan["id"],))
    assert updated_loan["return_date"] is not None
    assert updated_loan["status"] == "returned"

    # Перевіряємо статус примірника (знову доступний)
    copy = db.fetch_one("SELECT status FROM COPIES WHERE id = ?", (setup_data["copy_id"],))
    assert copy["status"] == "available"


def test_issue_loan_closes_reservation(db, setup_data):
    """Тестування автоматичного закриття бронювання при видачі."""
    # Створюємо активне бронювання
    future_date = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
    db.execute_query(
        "INSERT INTO RESERVATIONS (book_id, reader_id, expires_at, status) VALUES (?, ?, ?, 'active')",
        (setup_data["book_id"], setup_data["reader_id"], future_date)
    )

    service = LoanService(db)
    # Видаємо книгу (має закрити бронювання)
    service.issue_loan(setup_data["copy_id"], setup_data["reader_id"], setup_data["book_id"])

    reservation = db.fetch_one("SELECT status FROM RESERVATIONS WHERE book_id = ? AND reader_id = ?",
                               (setup_data["book_id"], setup_data["reader_id"]))
    assert reservation["status"] == "closed"