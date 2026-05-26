# tests/test_auth.py
import pytest
import os
from src.db.db_manager import DatabaseManager
from src.auth.session_manager import SessionManager, require_role
from src.auth.auth_service import AuthService
from src.auth.audit_logger import AuditLogger


# Фікстура бази даних (подібна до тієї, що в test_db_manager)
@pytest.fixture
def db(tmp_path):
    db_file = tmp_path / "test_auth.db"
    db_manager = DatabaseManager(str(db_file))
    schema_path = os.path.join(os.path.dirname(__file__), '../src/db/migrations/schema.sql')
    with open(schema_path, "r", encoding="utf-8") as f:
        db_manager.get_connection().executescript(f.read())
    return db_manager


# Фікстура для створення тестових користувачів
@pytest.fixture
def setup_users(db):
    hashed_admin = DatabaseManager.hash_password("admin_pass")
    db.execute_query(
        "INSERT INTO USERS (username, password_hash, role) VALUES (?, ?, ?)",
        ("admin", hashed_admin, "Адміністратор")
    )

    hashed_lib = DatabaseManager.hash_password("lib_pass")
    db.execute_query(
        "INSERT INTO USERS (username, password_hash, role) VALUES (?, ?, ?)",
        ("librarian", hashed_lib, "Бібліотекар")
    )


# Фікстура для автоматичного очищення сесії до і після кожного тесту
@pytest.fixture(autouse=True)
def clear_session():
    SessionManager.logout()
    yield
    SessionManager.logout()


def test_session_manager():
    """Тестування базових операцій збереження та очищення сесії."""
    user_data = {"id": 1, "username": "admin", "role": "Адміністратор"}

    SessionManager.login(user_data)
    assert SessionManager.get_current_user() == user_data

    SessionManager.logout()
    assert SessionManager.get_current_user() is None


def test_require_role_decorator():
    """Тестування захисту функцій за допомогою декоратора."""

    @require_role(["Адміністратор"])
    def restricted_action():
        return "Успіх"

    # Випадок 1: Користувач не увійшов
    with pytest.raises(PermissionError, match="не авторизований"):
        restricted_action()

    # Випадок 2: Користувач увійшов, але не має прав
    SessionManager.login({"id": 2, "username": "librarian", "role": "Бібліотекар"})
    with pytest.raises(PermissionError, match="Недостатньо прав"):
        restricted_action()

    # Випадок 3: Користувач має необхідні права
    SessionManager.login({"id": 1, "username": "admin", "role": "Адміністратор"})
    assert restricted_action() == "Успіх"


def test_auth_service(db, setup_users):
    """Тестування логіки перевірки облікових даних."""
    auth_service = AuthService(db)

    # Успішний вхід
    assert auth_service.authenticate("admin", "admin_pass") is True
    assert SessionManager.get_current_user()["username"] == "admin"
    assert SessionManager.get_current_user()["role"] == "Адміністратор"

    SessionManager.logout()

    # Помилка: неправильний пароль
    assert auth_service.authenticate("admin", "wrong_pass") is False
    assert SessionManager.get_current_user() is None

    # Помилка: неіснуючий користувач
    assert auth_service.authenticate("unknown_user", "admin_pass") is False


def test_audit_logger(db, setup_users):
    """Тестування журналу критичних операцій."""
    logger = AuditLogger(db)

    # Запис події без активної сесії (наприклад, системний збій)
    logger.log_operation("Автоматичне резервне копіювання")

    # Запис події від імені користувача
    SessionManager.login({"id": 1, "username": "admin", "role": "Адміністратор"})
    logger.log_operation("Видалення користувача ID 5")

    # Перевірка бази даних
    logs = db.fetch_all("SELECT * FROM BACKUP_LOG ORDER BY id")
    assert len(logs) == 2

    assert logs[0]["file_path"] == "Автоматичне резервне копіювання"
    assert logs[0]["created_by"] is None

    assert logs[1]["file_path"] == "Видалення користувача ID 5"
    assert logs[1]["created_by"] == 1