# src/gui/loan_form.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QMessageBox
from src.db.db_manager import DatabaseManager
from src.services.loan_service import LoanService


class LoanForm(QDialog):
    def __init__(self, db_manager: DatabaseManager, copy_id: int, book_id: int, parent=None):
        super().__init__(parent)
        self.loan_service = LoanService(db_manager)
        self.copy_id = copy_id
        self.book_id = book_id
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Оформлення видачі")
        self.setFixedSize(300, 150)

        layout = QVBoxLayout()
        form_layout = QFormLayout()

        self.reader_id_input = QLineEdit()
        self.reader_id_input.setPlaceholderText("Введіть ID читача")
        form_layout.addRow("ID Читача:", self.reader_id_input)

        layout.addLayout(form_layout)

        self.issue_btn = QPushButton("Видати книгу")
        self.issue_btn.clicked.connect(self.process_loan)
        layout.addWidget(self.issue_btn)

        self.setLayout(layout)

    def process_loan(self):
        reader_id_str = self.reader_id_input.text().strip()
        if not reader_id_str.isdigit():
            QMessageBox.warning(self, "Помилка", "ID читача має бути числом!")
            return

        reader_id = int(reader_id_str)

        success, message = self.loan_service.issue_loan(self.copy_id, reader_id, self.book_id)

        if success:
            QMessageBox.information(self, "Успіх", message)
            self.accept()
        else:
            QMessageBox.critical(self, "Відмовлено", message)