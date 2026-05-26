# src/gui/copy_manager.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QMessageBox
from src.db.db_manager import DatabaseManager
from src.auth.session_manager import require_role


class CopyManager(QDialog):
    def __init__(self, db_manager: DatabaseManager, book_id: int, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.book_id = book_id
        self.init_ui()
        self.load_copies()

    def init_ui(self):
        self.setWindowTitle("Управління примірниками")
        self.setFixedSize(500, 300)
        layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Інвентарний номер", "Статус"])
        layout.addWidget(self.table)

        self.write_off_btn = QPushButton("Списати обраний примірник")
        self.write_off_btn.clicked.connect(self.write_off_copy)
        layout.addWidget(self.write_off_btn)

        self.setLayout(layout)

    def load_copies(self):
        copies = self.db.fetch_all("SELECT id, inventory_number, status FROM COPIES WHERE book_id = ?", (self.book_id,))
        self.table.setRowCount(len(copies))

        for row_idx, copy in enumerate(copies):
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(copy['id'])))
            self.table.setItem(row_idx, 1, QTableWidgetItem(copy['inventory_number']))
            self.table.setItem(row_idx, 2, QTableWidgetItem(copy['status']))

    @require_role(["Адміністратор", "Бібліотекар"])
    def write_off_copy(self, *args, **kwargs):
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Увага", "Оберіть примірник для списання!")
            return

        copy_id = self.table.item(current_row, 0).text()
        status = self.table.item(current_row, 2).text()

        if status == 'written_off':
            QMessageBox.information(self, "Увага", "Цей примірник вже списано.")
            return

        reply = QMessageBox.question(self, 'Підтвердження', 'Ви впевнені, що хочете списати цей примірник?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.db.execute_query("UPDATE COPIES SET status = 'written_off' WHERE id = ?", (copy_id,))
            QMessageBox.information(self, "Успіх", "Примірник успішно списано.")
            self.load_copies()