# src/gui/circulation_view.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QGroupBox)
from src.db.db_manager import DatabaseManager
from src.services.loan_service import LoanService
from src.services.fine_service import FineService
from src.auth.session_manager import require_role


class CirculationView(QWidget):
    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.db = db_manager
        self.loan_service = LoanService(self.db)
        self.fine_service = FineService(self.db)
        self.current_reader_id = None
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout()

        # === ЛІВА ПАНЕЛЬ: Пошук читача ===
        left_panel = QVBoxLayout()
        reader_group = QGroupBox("1. Пошук читача")
        rg_layout = QVBoxLayout()

        search_layout = QHBoxLayout()
        self.reader_search_input = QLineEdit()
        self.reader_search_input.setPlaceholderText("Прізвище, ім'я або телефон...")
        self.reader_search_btn = QPushButton("Знайти")
        self.reader_search_btn.clicked.connect(self.search_readers)
        search_layout.addWidget(self.reader_search_input)
        search_layout.addWidget(self.reader_search_btn)
        rg_layout.addLayout(search_layout)

        self.readers_table = QTableWidget()
        self.readers_table.setColumnCount(4)
        self.readers_table.setHorizontalHeaderLabels(["ID", "Прізвище", "Ім'я", "Телефон"])
        self.readers_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.readers_table.itemSelectionChanged.connect(self.on_reader_selected)
        rg_layout.addWidget(self.readers_table)

        reader_group.setLayout(rg_layout)
        left_panel.addWidget(reader_group)

        # === ПРАВА ПАНЕЛЬ: Операції ===
        right_panel = QVBoxLayout()

        # Видача
        issue_group = QGroupBox("2. Видача книги")
        ig_layout = QHBoxLayout()
        self.inv_input = QLineEdit()
        self.inv_input.setPlaceholderText("Інвентарний номер (напр., INV-0001-001)")
        self.issue_btn = QPushButton("Видати")
        self.issue_btn.clicked.connect(self.issue_book)
        ig_layout.addWidget(self.inv_input)
        ig_layout.addWidget(self.issue_btn)
        issue_group.setLayout(ig_layout)
        right_panel.addWidget(issue_group)

        # Повернення
        loans_group = QGroupBox("3. Активні видачі (Повернення)")
        lg_layout = QVBoxLayout()
        self.loans_table = QTableWidget()
        self.loans_table.setColumnCount(5)
        self.loans_table.setHorizontalHeaderLabels(["ID", "Copy ID", "Назва", "Інв. №", "Повернути до"])
        self.loans_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.return_btn = QPushButton("Повернути обрану книгу")
        self.return_btn.clicked.connect(self.return_book)
        lg_layout.addWidget(self.loans_table)
        lg_layout.addWidget(self.return_btn)
        loans_group.setLayout(lg_layout)
        right_panel.addWidget(loans_group)

        # Штрафи
        fines_group = QGroupBox("4. Штрафи читача")
        fg_layout = QVBoxLayout()
        self.fines_table = QTableWidget()
        self.fines_table.setColumnCount(4)
        self.fines_table.setHorizontalHeaderLabels(["ID", "Книга", "Днів", "Сума (грн)"])
        self.fines_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.pay_btn = QPushButton("Оплатити обраний штраф")
        self.pay_btn.clicked.connect(self.pay_fine)
        fg_layout.addWidget(self.fines_table)
        fg_layout.addWidget(self.pay_btn)
        fines_group.setLayout(fg_layout)
        right_panel.addWidget(fines_group)

        main_layout.addLayout(left_panel, 40)
        main_layout.addLayout(right_panel, 60)
        self.setLayout(main_layout)

        self.issue_btn.setEnabled(False)
        self.return_btn.setEnabled(False)
        self.pay_btn.setEnabled(False)

    def search_readers(self):
        term = f"%{self.reader_search_input.text().strip()}%"
        readers = self.db.fetch_all(
            "SELECT id, last_name, first_name, phone FROM READERS WHERE last_name LIKE ? OR first_name LIKE ? OR phone LIKE ?",
            (term, term, term)
        )
        self.readers_table.setRowCount(len(readers))
        for row, r in enumerate(readers):
            self.readers_table.setItem(row, 0, QTableWidgetItem(str(r['id'])))
            self.readers_table.setItem(row, 1, QTableWidgetItem(r['last_name']))
            self.readers_table.setItem(row, 2, QTableWidgetItem(r['first_name']))
            self.readers_table.setItem(row, 3, QTableWidgetItem(r['phone'] or ""))

    def on_reader_selected(self):
        row = self.readers_table.currentRow()
        if row >= 0:
            self.current_reader_id = int(self.readers_table.item(row, 0).text())
            self.issue_btn.setEnabled(True)
            self.return_btn.setEnabled(True)
            self.pay_btn.setEnabled(True)
            self.load_reader_details()

    def load_reader_details(self):
        if not self.current_reader_id: return

        loans = self.db.fetch_all("""
            SELECT l.id as loan_id, c.id as copy_id, b.title, c.inventory_number, l.due_date 
            FROM LOANS l JOIN COPIES c ON l.copy_id = c.id JOIN BOOKS b ON c.book_id = b.id
            WHERE l.reader_id = ? AND l.return_date IS NULL
        """, (self.current_reader_id,))
        self.loans_table.setRowCount(len(loans))
        for i, loan in enumerate(loans):
            self.loans_table.setItem(i, 0, QTableWidgetItem(str(loan['loan_id'])))
            self.loans_table.setItem(i, 1, QTableWidgetItem(str(loan['copy_id'])))
            self.loans_table.setItem(i, 2, QTableWidgetItem(loan['title']))
            self.loans_table.setItem(i, 3, QTableWidgetItem(loan['inventory_number']))
            self.loans_table.setItem(i, 4, QTableWidgetItem(loan['due_date']))

        fines = self.db.fetch_all("""
            SELECT f.id, b.title, f.days_overdue, f.amount
            FROM FINES f JOIN LOANS l ON f.loan_id = l.id JOIN COPIES c ON l.copy_id = c.id JOIN BOOKS b ON c.book_id = b.id
            WHERE f.reader_id = ? AND f.is_paid = 0
        """, (self.current_reader_id,))
        self.fines_table.setRowCount(len(fines))
        for i, fine in enumerate(fines):
            self.fines_table.setItem(i, 0, QTableWidgetItem(str(fine['id'])))
            self.fines_table.setItem(i, 1, QTableWidgetItem(fine['title']))
            self.fines_table.setItem(i, 2, QTableWidgetItem(str(fine['days_overdue'])))
            self.fines_table.setItem(i, 3, QTableWidgetItem(f"{fine['amount']:.2f}"))

    @require_role(["Адміністратор", "Бібліотекар"])
    def issue_book(self, *args, **kwargs):
        inv_number = self.inv_input.text().strip()
        copy = self.db.fetch_one("SELECT id, book_id FROM COPIES WHERE inventory_number = ?", (inv_number,))
        if not copy:
            QMessageBox.warning(self, "Помилка", "Примірник з таким номером не знайдено.")
            return

        success, msg = self.loan_service.issue_loan(copy['id'], self.current_reader_id, copy['book_id'])
        if success:
            QMessageBox.information(self, "Успіх", msg)
            self.inv_input.clear()
            self.load_reader_details()
        else:
            QMessageBox.critical(self, "Відмовлено", msg)

    @require_role(["Адміністратор", "Бібліотекар"])
    def return_book(self, *args, **kwargs):
        row = self.loans_table.currentRow()
        if row < 0: return QMessageBox.warning(self, "Увага", "Оберіть видачу для повернення.")
        self.loan_service.return_loan(int(self.loans_table.item(row, 0).text()),
                                      int(self.loans_table.item(row, 1).text()))
        QMessageBox.information(self, "Успіх", "Книгу успішно повернуто.")
        self.load_reader_details()

    @require_role(["Адміністратор", "Бібліотекар"])
    def pay_fine(self, *args, **kwargs):
        row = self.fines_table.currentRow()
        if row < 0: return QMessageBox.warning(self, "Увага", "Оберіть штраф для оплати.")
        self.fine_service.pay_fine(int(self.fines_table.item(row, 0).text()))
        QMessageBox.information(self, "Успіх", "Штраф позначено як оплачений.")
        self.load_reader_details()