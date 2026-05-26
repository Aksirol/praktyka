# tests/test_reservations_fines.py
import pytest
import os
from src.db.db_manager import DatabaseManager
from src.services.reservation_service import ReservationService
from src.services.fine_service import FineService
from src.services.notification_service import NotificationService


@pytest.fixture
def db(tmp_path):
    """Фікстура бази даних."""
    db_file = tmp_path / "test_advanced.db"
    db_manager = DatabaseManager(str(db_file))
    schema_path = os.path.join(os.path.dirname(__file__), '../src/db/migrations/schema.sql')

    with open(schema_path, "r", encoding="utf-8") as f:
        db_manager.get_connection().executescript(f.read())

    return db_manager


@pytest.fixture
def setup_data(db):
    """Створення базових сутностей: книга, примірники, читач."""
    book_id = db.execute_query("INSERT INTO BOOKS (title, total_copies) VALUES (?, ?)", ("Маруся Чурай", 2))

    # Два примірники: один виданий, один доступний
    copy1 = db.execute_query("INSERT INTO COPIES (book_id, inventory_number, status) VALUES (?, ?, 'issued')",
                             (book_id, "INV-1"))
    copy2 = db.execute_query("INSERT INTO COPIES (book_id, inventory_number, status) VALUES (?, ?, 'available')",
                             (book_id, "INV-2"))

    reader1 = db.execute_query("INSERT INTO READERS (first_name, last_name, reader_type) VALUES (?, ?, ?)",
                               ("Олена", "Теліга", "Вчитель"))
    reader2 = db.execute_query("INSERT INTO READERS (first_name, last_name, reader_type) VALUES (?, ?, ?)",
                               ("Василь", "Стус", "Учень"))

    return {"book_id": book_id, "copy1": copy1, "copy2": copy2, "reader1": reader1, "reader2": reader2}


def test_create_reservation_when_copies_available(db, setup_data):
    """Бронювання неможливе, якщо є хоча б один доступний примірник."""
    service = ReservationService(db)
    success, msg = service.create_reservation(setup_data["book_id"], setup_data["reader1"])

    assert success is False
    assert "у фонді є доступні примірники" in msg


def test_create_reservation_success(db, setup_data):
    """Успішне бронювання, коли всі примірники видані."""
    # Змінюємо статус другого примірника на 'issued'
    db.execute_query("UPDATE COPIES SET status = 'issued' WHERE id = ?", (setup_data["copy2"],))

    service = ReservationService(db)
    success, msg = service.create_reservation(setup_data["book_id"], setup_data["reader1"])

    assert success is True

    res = db.fetch_one("SELECT status FROM RESERVATIONS WHERE reader_id = ?", (setup_data["reader1"],))
    assert res["status"] == "active"


def test_cancel_expired_reservations(db, setup_data):
    """Перевірка автоматичного скасування прострочених бронювань."""
    # Створюємо резерв, що "згорів" 2 дні тому
    db.execute_query("""
        INSERT INTO RESERVATIONS (book_id, reader_id, expires_at, status) 
        VALUES (?, ?, DATE('now', '-2 days'), 'active')
    """, (setup_data["book_id"], setup_data["reader1"]))

    service = ReservationService(db)
    service.cancel_expired_reservations()

    res = db.fetch_one("SELECT status FROM RESERVATIONS WHERE reader_id = ?", (setup_data["reader1"],))
    assert res["status"] == "expired"


def test_calculate_fines(db, setup_data):
    """Тестування нарахування штрафів за прострочені видачі."""
    # Створюємо видачу, прострочену на 5 днів
    loan_id = db.execute_query("""
        INSERT INTO LOANS (copy_id, reader_id, issue_date, due_date) 
        VALUES (?, ?, DATE('now', '-19 days'), DATE('now', '-5 days'))
    """, (setup_data["copy1"], setup_data["reader1"]))

    service = FineService(db)
    service.calculate_fines()

    fine = db.fetch_one("SELECT * FROM FINES WHERE loan_id = ?", (loan_id,))
    assert fine is not None
    assert fine["days_overdue"] == 5
    assert fine["amount"] == 5 * FineService.FINE_PER_DAY
    assert fine["is_paid"] == 0


def test_pay_fine(db, setup_data):
    """Тестування оплати штрафу."""
    # 1. Створюємо видачу, щоб не порушувати зовнішній ключ (FOREIGN KEY)
    loan_id = db.execute_query("""
        INSERT INTO LOANS (copy_id, reader_id, due_date) 
        VALUES (?, ?, DATE('now', '-5 days'))
    """, (setup_data["copy1"], setup_data["reader1"]))

    # 2. Додаємо неоплачений штраф з існуючим loan_id
    fine_id = db.execute_query("""
        INSERT INTO FINES (loan_id, reader_id, days_overdue, amount, is_paid) 
        VALUES (?, ?, 3, 15.0, 0)
    """, (loan_id, setup_data["reader1"]))

    # 3. Виконуємо оплату
    service = FineService(db)
    service.pay_fine(fine_id)

    # 4. Перевіряємо результат
    fine = db.fetch_one("SELECT is_paid, paid_at FROM FINES WHERE id = ?", (fine_id,))
    assert fine["is_paid"] == 1
    assert fine["paid_at"] is not None


def test_notification_service(db, setup_data):
    """Тестування сповіщень про боржників."""
    # Читач 1 має прострочену видачу
    db.execute_query("""
        INSERT INTO LOANS (copy_id, reader_id, due_date) 
        VALUES (?, ?, DATE('now', '-2 days'))
    """, (setup_data["copy1"], setup_data["reader1"]))

    # Читач 2 має активну, але НЕ прострочену видачу
    db.execute_query("""
        INSERT INTO LOANS (copy_id, reader_id, due_date) 
        VALUES (?, ?, DATE('now', '+5 days'))
    """, (setup_data["copy2"], setup_data["reader2"]))

    service = NotificationService(db)
    reminders = service.get_overdue_reminders()

    assert len(reminders) == 1
    assert reminders[0]["first_name"] == "Олена"
    assert reminders[0]["overdue_count"] == 1