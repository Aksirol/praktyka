from src.db.db_manager import DatabaseManager
from src.auth.session_manager import SessionManager


class AuditLogger:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def log_operation(self, operation: str, status: str = "SUCCESS"):
        """Записує дію у Журнал аудиту (AUDIT_LOG)."""
        user = SessionManager.get_current_user()
        user_id = user['id'] if user else None

        self.db.execute_query(
            "INSERT INTO AUDIT_LOG (operation, user_id) VALUES (?, ?)",
            (operation, user_id)
        )