# src/auth/auth_service.py
from src.db.db_manager import DatabaseManager
from src.auth.session_manager import SessionManager


class AuthService:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def authenticate(self, username: str, password: str) -> bool:
        """Перевіряє облікові дані активного користувача та відкриває сесію."""
        # ВИПРАВЛЕННЯ: Додано умову AND is_active = 1
        query = "SELECT * FROM USERS WHERE username = ? AND is_active = 1"
        user = self.db.fetch_one(query, (username,))

        if user and DatabaseManager.check_password(password, user['password_hash']):
            SessionManager.login(user)
            return True
        return False

    def logout(self):
        SessionManager.logout()