# src/auth/audit_logger.py
from src.db.db_manager import DatabaseManager
from src.auth.session_manager import SessionManager


class AuditLogger:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def log_operation(self, operation_details: str, status: str = "SUCCESS"):
        """Записує критичну дію у базу даних."""
        user = SessionManager.get_current_user()
        user_id = user['id'] if user else None

        query = """
            INSERT INTO BACKUP_LOG (file_path, created_by, status)
            VALUES (?, ?, ?)
        """
        # Зберігаємо опис операції у поле file_path (або шлях до файлу, якщо це бекап)
        self.db.execute_query(query, (operation_details, user_id, status))