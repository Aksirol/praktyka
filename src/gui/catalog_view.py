# src/gui/catalog_view.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QComboBox, QMessageBox, QInputDialog)
from PyQt5.QtCore import Qt
from src.db.db_manager import DatabaseManager
from src.auth.session_manager import SessionManager, require_role
from src.gui.book_form import BookForm
from src.gui.copy_manager import CopyManager
from src.services.reservation_service import ReservationService
import sqlite3


class NumericItem(QTableWidgetItem):
    def __lt__(self, other):
        try:
            return float(self.text()) < float(other.text())
        except ValueError:
            return super().__lt__(other)


class CatalogView(QWidget):
    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.db = db_manager
        self.init_ui()
        self.load_genres()
        self.load_data()

    def init_ui(self):
        self.setWindowTitle("Каталог книг")
        layout = QVBoxLayout()

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Пошук за назвою, автором або ISBN...")
        self.genre_filter = QComboBox()
        self.genre_filter.addItem("Всі жанри", None)
        self.search_btn = QPushButton("Знайти")
        self.search_btn.clicked.connect(self.load_data)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.genre_filter)
        search_layout.addWidget(self.search_btn)
        layout.addLayout(search_layout)

        self.manage_layout = QHBoxLayout()

        self.add_book_btn = QPushButton("Додати книгу")
        self.add_book_btn.clicked.connect(self.open_book_form)

        self.copies_btn = QPushButton("Управління примірниками")
        self.copies_btn.clicked.connect(self.open_copy_manager)

        self.reserve_btn = QPushButton("Забронювати")
        self.reserve_btn.clicked.connect(self.reserve_book)

        self.delete_book_btn = QPushButton("Видалити книгу")
        self.delete_book_btn.clicked.connect(self.delete_book)
        self.delete_book_btn.setStyleSheet("color: white; background-color: #d9534f;")

        self.manage_layout.addWidget(self.add_book_btn)
        self.manage_layout.addWidget(self.copies_btn)
        self.manage_layout.addWidget(self.reserve_btn)
        self.manage_layout.addWidget(self.delete_book_btn)
        self.manage_layout.addStretch()
        layout.addLayout(self.manage_layout)

        user = SessionManager.get_current_user()
        if not user or user['role'] == 'Читач':
            self.add_book_btn.hide()
            self.copies_btn.hide()
            self.reserve_btn.hide()
            self.delete_book_btn.hide()

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Назва", "Автор", "Жанр", "ISBN", "Доступно"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)
        self.setLayout(layout)

    def load_genres(self):
        genres = self.db.fetch_all("SELECT id, name FROM GENRES ORDER BY name")
        for g in genres:
            self.genre_filter.addItem(g['name'], g['id'])

    def load_data(self):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        search_term = f"%{self.search_input.text().strip()}%"
        genre_id = self.genre_filter.currentData()

        query = """
            SELECT b.id, b.title, a.last_name || ' ' || a.first_name as author_name, 
                   g.name as genre_name, b.isbn, 
                   (SELECT COUNT(*) FROM COPIES c WHERE c.book_id = b.id AND c.status = 'available') as available_copies
            FROM BOOKS b
            LEFT JOIN AUTHORS a ON b.author_id = a.id
            LEFT JOIN GENRES g ON b.genre_id = g.id
            WHERE (b.title LIKE ? OR a.last_name LIKE ? OR b.isbn LIKE ?)
        """
        params = [search_term, search_term, search_term]
        if genre_id:
            query += " AND b.genre_id = ?"
            params.append(genre_id)

        books = self.db.fetch_all(query, params)
        self.table.setRowCount(len(books))

        for row_idx, book in enumerate(books):
            self.table.setItem(row_idx, 0, NumericItem(str(book['id'])))
            self.table.setItem(row_idx, 1, QTableWidgetItem(book['title']))
            self.table.setItem(row_idx, 2, QTableWidgetItem(book['author_name'] or "Невідомо"))
            self.table.setItem(row_idx, 3, QTableWidgetItem(book['genre_name'] or "Невідомо"))
            self.table.setItem(row_idx, 4, QTableWidgetItem(book['isbn'] or "-"))
            self.table.setItem(row_idx, 5, NumericItem(str(book['available_copies'])))

        self.table.setSortingEnabled(True)

    def open_book_form(self):
        dialog = BookForm(self.db, self)
        if dialog.exec_():
            self.load_data()

    @require_role(["Адміністратор", "Бібліотекар"])
    def open_copy_manager(self, *args, **kwargs):
        row = self.table.currentRow()
        if row < 0: return QMessageBox.warning(self, "Увага", "Оберіть книгу!")
        book_id = int(self.table.item(row, 0).text())
        dialog = CopyManager(self.db, book_id, self)
        dialog.exec_()
        self.load_data()

    @require_role(["Адміністратор", "Бібліотекар"])
    def reserve_book(self, *args, **kwargs):
        row = self.table.currentRow()
        if row < 0: return QMessageBox.warning(self, "Увага", "Оберіть книгу для бронювання!")

        book_id = int(self.table.item(row, 0).text())
        avail = int(self.table.item(row, 5).text())

        if avail > 0:
            return QMessageBox.warning(self, "Відмовлено", "Бронювання неможливе: у фонді є доступні примірники.")

        reader_id_str, ok = QInputDialog.getText(self, "Бронювання", "Введіть ID читача для резервування:")
        if ok and reader_id_str.strip().isdigit():
            reader_id = int(reader_id_str.strip())
            success, msg = ReservationService(self.db).create_reservation(book_id, reader_id)
            if success:
                QMessageBox.information(self, "Успіх", msg)
            else:
                QMessageBox.critical(self, "Помилка", msg)

    @require_role(["Адміністратор", "Бібліотекар"])
    def delete_book(self, *args, **kwargs):
        # ... твій код видалення залишається без змін ...
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Увага", "Оберіть книгу для видалення!")
            return
        book_id = self.table.item(current_row, 0).text()
        reply = QMessageBox.question(self, 'Підтвердження', 'Ви впевнені?', QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                self.db.execute_query("DELETE FROM COPIES WHERE book_id = ?", (book_id,))
                self.db.execute_query("DELETE FROM BOOKS WHERE id = ?", (book_id,))
                self.load_data()
            except sqlite3.IntegrityError:
                QMessageBox.critical(self, "Помилка", "Неможливо видалити книгу (є в історії видач).")