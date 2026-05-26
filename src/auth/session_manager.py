# src/auth/session_manager.py
from functools import wraps


class SessionManager:
    _current_user = None

    @classmethod
    def login(cls, user_data: dict):
        """Зберігає дані користувача після успішного входу."""
        cls._current_user = user_data

    @classmethod
    def logout(cls):
        """Очищає сесію."""
        cls._current_user = None

    @classmethod
    def get_current_user(cls) -> dict:
        """Повертає дані поточного користувача."""
        return cls._current_user


def require_role(allowed_roles: list):
    """Декоратор для перевірки прав доступу до методу."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = SessionManager.get_current_user()
            if not user:
                raise PermissionError("Користувач не авторизований. Будь ласка, увійдіть у систему.")

            if user['role'] not in allowed_roles:
                raise PermissionError(f"Недостатньо прав. Необхідні ролі: {', '.join(allowed_roles)}")

            return func(*args, **kwargs)

        return wrapper

    return decorator