# src/services/fine_service.py
from src.db.db_manager import DatabaseManager


class FineService:
    FINE_PER_DAY = 5.00  # Сума штрафу за один день прострочення (можна винести у налаштування)

    def __init__(self, db: DatabaseManager):
        self.db = db

    def calculate_fines(self):
        """Розраховує та оновлює штрафи для всіх прострочених видач."""
        # julianday() в SQLite повертає кількість днів, що дозволяє легко знайти різницю
        overdue_loans = self.db.fetch_all("""
            SELECT id, reader_id, due_date, 
                   CAST(julianday('now') - julianday(due_date) AS INTEGER) as days_overdue
            FROM LOANS
            WHERE return_date IS NULL AND due_date < DATE('now')
        """)

        for loan in overdue_loans:
            days = loan['days_overdue']
            amount = days * self.FINE_PER_DAY

            # Перевіряємо, чи вже створено запис про штраф для цієї видачі
            existing_fine = self.db.fetch_one("SELECT id FROM FINES WHERE loan_id = ?", (loan['id'],))

            if existing_fine:
                # Оновлюємо суму та кількість днів, якщо штраф ще не сплачено
                self.db.execute_query("""
                    UPDATE FINES 
                    SET days_overdue = ?, amount = ? 
                    WHERE id = ? AND is_paid = 0
                """, (days, amount, existing_fine['id']))
            else:
                # Створюємо новий запис про штраф
                self.db.execute_query("""
                    INSERT INTO FINES (loan_id, reader_id, days_overdue, amount) 
                    VALUES (?, ?, ?, ?)
                """, (loan['id'], loan['reader_id'], days, amount))

    def pay_fine(self, fine_id: int):
        """Позначає штраф як оплачений."""
        self.db.execute_query("""
            UPDATE FINES 
            SET is_paid = 1, paid_at = DATE('now') 
            WHERE id = ?
        """, (fine_id,))