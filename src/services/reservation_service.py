# src/services/reservation_service.py
from datetime import datetime, timedelta
from src.db.db_manager import DatabaseManager


class ReservationService:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def create_reservation(self, book_id: int, reader_id: int, days_valid: int = 3) -> tuple[bool, str]:
        """Реєструє бронювання, якщо всі примірники видані."""
        # Перевіряємо наявність доступних примірників
        available = self.db.fetch_one("""
            SELECT COUNT(*) as count FROM COPIES 
            WHERE book_id = ? AND status = 'available'
        """, (book_id,))

        if available['count'] > 0:
            return False, "Бронювання неможливе: у фонді є доступні примірники."

        # Перевіряємо, чи немає вже активного бронювання на цю книгу для цього читача
        existing = self.db.fetch_one("""
            SELECT id FROM RESERVATIONS 
            WHERE book_id = ? AND reader_id = ? AND status = 'active'
        """, (book_id, reader_id))

        if existing:
            return False, "У читача вже є активне бронювання на цю книгу."

        # Резерв діє вказану кількість днів (за замовчуванням 3)
        expires_at = (datetime.now() + timedelta(days=days_valid)).strftime('%Y-%m-%d')

        self.db.execute_query("""
            INSERT INTO RESERVATIONS (book_id, reader_id, expires_at) 
            VALUES (?, ?, ?)
        """, (book_id, reader_id, expires_at))

        return True, f"Книгу успішно заброньовано. Резерв діє до {expires_at}."

    def cancel_expired_reservations(self):
        """Знаходить та скасовує прострочені бронювання."""
        self.db.execute_query("""
            UPDATE RESERVATIONS 
            SET status = 'expired' 
            WHERE status = 'active' AND expires_at < DATE('now')
        """)