from datetime import datetime, timedelta
from src.db.db_manager import DatabaseManager
from src.auth.session_manager import SessionManager
from src.auth.audit_logger import AuditLogger


class LoanService:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.logger = AuditLogger(db)

    def check_overdue_loans(self, reader_id: int) -> bool:
        query = """
            SELECT COUNT(*) as overdue FROM LOANS 
            WHERE reader_id = ? AND return_date IS NULL AND due_date < DATE('now')
        """
        result = self.db.fetch_one(query, (reader_id,))
        return result['overdue'] > 0

    def issue_loan(self, copy_id: int, reader_id: int, book_id: int) -> tuple[bool, str]:
        # Виправлення БАГУ: Перевірка статусу примірника
        copy = self.db.fetch_one("SELECT status, inventory_number FROM COPIES WHERE id = ?", (copy_id,))
        if not copy or copy['status'] != 'available':
            return False, "Примірник недоступний для видачі (можливо, вже виданий або списаний)."

        if self.check_overdue_loans(reader_id):
            return False, "У читача є прострочені видачі! Видача нових книг заборонена."

        self.db.execute_query("""
            UPDATE RESERVATIONS SET status = 'closed' 
            WHERE book_id = ? AND reader_id = ? AND status = 'active'
        """, (book_id, reader_id))

        user = SessionManager.get_current_user()
        issued_by = user['id'] if user else None
        due_date = (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')

        try:
            self.db.execute_query("""
                INSERT INTO LOANS (copy_id, reader_id, issued_by, due_date) 
                VALUES (?, ?, ?, ?)
            """, (copy_id, reader_id, issued_by, due_date))

            self.db.execute_query("UPDATE COPIES SET status = 'issued' WHERE id = ?", (copy_id,))

            self.logger.log_operation(f"Видача примірника {copy['inventory_number']} читачу ID {reader_id}")
            return True, f"Книгу успішно видано. Дата повернення: {due_date}"
        except Exception as e:
            return False, f"Помилка БД: {str(e)}"

    def return_loan(self, loan_id: int, copy_id: int) -> bool:
        self.db.execute_query(
            "UPDATE LOANS SET return_date = DATE('now'), status = 'returned' WHERE id = ?", (loan_id,)
        )
        self.db.execute_query(
            "UPDATE COPIES SET status = 'available' WHERE id = ?", (copy_id,)
        )
        self.logger.log_operation(f"Повернення примірника ID {copy_id} (Видача ID {loan_id})")
        return True