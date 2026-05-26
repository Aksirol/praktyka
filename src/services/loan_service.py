# src/services/loan_service.py
from datetime import datetime, timedelta
from src.db.db_manager import DatabaseManager
from src.auth.session_manager import SessionManager


class LoanService:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def check_overdue_loans(self, reader_id: int) -> bool:
        """Перевіряє, чи є у читача прострочені видачі."""
        query = """
            SELECT COUNT(*) as overdue FROM LOANS 
            WHERE reader_id = ? AND return_date IS NULL AND due_date < DATE('now')
        """
        result = self.db.fetch_one(query, (reader_id,))
        return result['overdue'] > 0

    def issue_loan(self, copy_id: int, reader_id: int, book_id: int) -> tuple[bool, str]:
        """Оформлює видачу примірника читачу."""
        if self.check_overdue_loans(reader_id):
            return False, "У читача є прострочені видачі! Видача нових книг заборонена."

        # Якщо є активне бронювання на цю книгу, автоматично закриваємо його
        self.db.execute_query("""
            UPDATE RESERVATIONS SET status = 'closed' 
            WHERE book_id = ? AND reader_id = ? AND status = 'active'
        """, (book_id, reader_id))

        user = SessionManager.get_current_user()
        issued_by = user['id'] if user else None

        # Автоматичний розрахунок дати повернення (14 днів)
        due_date = (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')

        try:
            # Створення запису про видачу та зміна статусу примірника
            self.db.execute_query("""
                INSERT INTO LOANS (copy_id, reader_id, issued_by, due_date) 
                VALUES (?, ?, ?, ?)
            """, (copy_id, reader_id, issued_by, due_date))

            self.db.execute_query("UPDATE COPIES SET status = 'issued' WHERE id = ?", (copy_id,))
            return True, f"Книгу успішно видано. Дата повернення: {due_date}"
        except Exception as e:
            return False, f"Помилка БД: {str(e)}"

    def return_loan(self, loan_id: int, copy_id: int) -> bool:
        """Фіксує повернення книги."""
        self.db.execute_query(
            "UPDATE LOANS SET return_date = DATE('now'), status = 'returned' WHERE id = ?",
            (loan_id,)
        )
        self.db.execute_query(
            "UPDATE COPIES SET status = 'available' WHERE id = ?",
            (copy_id,)
        )
        return True