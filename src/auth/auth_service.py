# src/auth/auth_service.py
from src.db.db_manager import DatabaseManager
from src.auth.session_manager import SessionManager


class AuthService:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def authenticate(self, username: str, password: str) -> bool:
        """Перевіряє облікові дані та відкриває сесію у разі успіху."""
        user = self.db.fetch_one("SELECT * FROM USERS WHERE username = ?", (username,))

        if user and DatabaseManager.check_password(password, user['password_hash']):
            SessionManager.login(user)
            return True
        return False

    def logout(self):
        SessionManager.logout()