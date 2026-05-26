# src/services/reader_service.py
from src.db.db_manager import DatabaseManager


class ReaderService:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def register_reader(self, first_name: str, last_name: str, reader_type: str, class_id: int, phone: str):
        """Реєструє нового читача в системі."""
        query = """
            INSERT INTO READERS (first_name, last_name, reader_type, class_id, phone) 
            VALUES (?, ?, ?, ?, ?)
        """
        return self.db.execute_query(query, (first_name, last_name, reader_type, class_id, phone))

    def get_reader_summary(self, reader_id: int) -> dict:
        """Повертає всю інформацію для картки читача: профіль, активні видачі, історію та бронювання."""
        profile = self.db.fetch_one("SELECT * FROM READERS WHERE id = ?", (reader_id,))

        active_loans = self.db.fetch_all("""
            SELECT l.id, b.title, c.inventory_number, l.issue_date, l.due_date 
            FROM LOANS l
            JOIN COPIES c ON l.copy_id = c.id
            JOIN BOOKS b ON c.book_id = b.id
            WHERE l.reader_id = ? AND l.return_date IS NULL
        """, (reader_id,))

        history = self.db.fetch_all("""
            SELECT b.title, l.issue_date, l.return_date 
            FROM LOANS l
            JOIN COPIES c ON l.copy_id = c.id
            JOIN BOOKS b ON c.book_id = b.id
            WHERE l.reader_id = ? AND l.return_date IS NOT NULL
        """, (reader_id,))

        return {
            "profile": profile,
            "active_loans": active_loans,
            "history": history
        }