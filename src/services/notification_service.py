# src/services/notification_service.py
from src.db.db_manager import DatabaseManager

class NotificationService:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def get_overdue_reminders(self) -> list[dict]:
        """Повертає список читачів із простроченими видачами для нагадування при запуску програми."""
        return self.db.fetch_all("""
            SELECT r.id, r.first_name, r.last_name, r.phone, COUNT(l.id) as overdue_count
            FROM READERS r
            JOIN LOANS l ON r.id = l.reader_id
            WHERE l.return_date IS NULL AND l.due_date < DATE('now')
            GROUP BY r.id
        """)