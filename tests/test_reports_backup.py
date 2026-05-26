# tests/test_reports_backup.py
import pytest
import os
from src.db.db_manager import DatabaseManager
from src.services.backup_service import BackupService
from src.services.report_service import ReportService
from src.auth.session_manager import SessionManager


@pytest.fixture
def db(tmp_path):
    """Фікстура для створення тимчасової бази даних."""
    db_file = tmp_path / "test_reports.db"
    db_manager = DatabaseManager(str(db_file))
    schema_path = os.path.join(os.path.dirname(__file__), '../src/db/migrations/schema.sql')

    with open(schema_path, "r", encoding="utf-8") as f:
        db_manager.get_connection().executescript(f.read())

    return db_manager


@pytest.fixture
def setup_data(db):
    """Наповнення бази даних для тестів звітів."""
    # Авторизація адміністратора (для логування бекапів)
    user_id = db.execute_query(
        "INSERT INTO USERS (username, password_hash, role) VALUES ('admin', 'hash', 'Адміністратор')"
    )
    SessionManager.login({"id": user_id, "username": "admin", "role": "Адміністратор"})

    # Додавання книги, примірника та читача
    book_id = db.execute_query("INSERT INTO BOOKS (title, total_copies) VALUES ('Тіні забутих предків', 1)")
    copy_id = db.execute_query(
        "INSERT INTO COPIES (book_id, inventory_number, status) VALUES (?, 'INV-100', 'issued')",
        (book_id,)
    )
    reader_id = db.execute_query(
        "INSERT INTO READERS (first_name, last_name, reader_type, phone) VALUES ('Михайло', 'Коцюбинський', 'Вчитель', '+380000000000')"
    )

    # Створення простроченої видачі (для звіту по боржниках)
    db.execute_query("""
        INSERT INTO LOANS (copy_id, reader_id, issue_date, due_date) 
        VALUES (?, ?, DATE('now', '-30 days'), DATE('now', '-16 days'))
    """, (copy_id, reader_id))

    return {"db_path": db.db_path}


@pytest.fixture(autouse=True)
def clear_session():
    """Очищення сесії після кожного тесту."""
    yield
    SessionManager.logout()


def test_backup_creation(db, setup_data, tmp_path):
    """Тестування створення резервної копії та логування."""
    dest_dir = tmp_path / "backups"
    dest_dir.mkdir()

    service = BackupService(db)
    success, msg = service.create_backup(str(dest_dir))

    assert success is True

    # Перевіряємо, чи з'явився файл у цільовій папці
    files = list(dest_dir.glob("library_backup_*.db"))
    assert len(files) == 1

    # Перевіряємо журнал транзакцій
    log = db.fetch_one("SELECT * FROM BACKUP_LOG ORDER BY id DESC LIMIT 1")
    assert log is not None
    assert "Створено резервну копію" in log["file_path"]


def test_backup_restoration(db, setup_data, tmp_path):
    """Тестування відновлення бази даних з копії."""
    import shutil
    import sqlite3

    # Створюємо валідну резервну копію з поточної тестової бази
    fake_backup = tmp_path / "fake_backup.db"
    shutil.copy2(db.db_path, str(fake_backup))

    # Модифікуємо резервну копію, щоб перевірити, чи вона дійсно відновиться
    conn = sqlite3.connect(str(fake_backup))
    conn.execute("INSERT INTO GENRES (name) VALUES ('Секретний жанр з бекапу')")
    conn.commit()
    conn.close()

    service = BackupService(db)
    success, msg = service.restore_backup(str(fake_backup))

    assert success is True

    # Перевіряємо, чи з'явилися дані з резервної копії в основній базі
    genre = db.fetch_one("SELECT name FROM GENRES WHERE name = 'Секретний жанр з бекапу'")
    assert genre is not None


def test_generate_overdue_report(db, setup_data):
    """Тестування генерації звіту про боржників у форматі PDF."""
    service = ReportService(db)
    success, msg = service.generate_overdue_report()

    assert success is True
    assert ".pdf" in msg

    # Витягуємо шлях до файлу з повідомлення та перевіряємо його існування
    filepath = msg.split(": ")[1]
    assert os.path.exists(filepath)

    # Прибираємо згенерований файл після тесту, щоб не смітити у проекті
    os.remove(filepath)


def test_generate_popular_books_report(db, setup_data):
    """Тестування генерації звіту про популярні книги у форматі PDF."""
    service = ReportService(db)
    success, msg = service.generate_popular_books_report()

    assert success is True
    assert ".pdf" in msg

    filepath = msg.split(": ")[1]
    assert os.path.exists(filepath)
    os.remove(filepath)