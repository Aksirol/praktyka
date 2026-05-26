# src/gui/catalog_view.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox)
from src.db.db_manager import DatabaseManager
from src.auth.session_manager import SessionManager
from src.gui.book_form import BookForm


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

        # Панель пошуку
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

        # Панель кнопок керування (тільки для бібліотекаря/адміна)
        self.manage_layout = QHBoxLayout()
        self.add_book_btn = QPushButton("Додати книгу")
        self.manage_layout.addWidget(self.add_book_btn)
        self.add_book_btn.clicked.connect(self.open_book_form)
        layout.addLayout(self.manage_layout)

        # Перевірка прав доступу для приховування кнопок керування
        user = SessionManager.get_current_user()
        if not user or user['role'] == 'Читач':
            self.add_book_btn.hide()

        # Таблиця
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Назва", "Автор", "Жанр", "ISBN", "Доступно"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        self.setLayout(layout)

    def load_genres(self):
        genres = self.db.fetch_all("SELECT id, name FROM GENRES ORDER BY name")
        for g in genres:
            self.genre_filter.addItem(g['name'], g['id'])

    def load_data(self):
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
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(book['id'])))
            self.table.setItem(row_idx, 1, QTableWidgetItem(book['title']))
            self.table.setItem(row_idx, 2, QTableWidgetItem(book['author_name'] or "Невідомо"))
            self.table.setItem(row_idx, 3, QTableWidgetItem(book['genre_name'] or "Невідомо"))
            self.table.setItem(row_idx, 4, QTableWidgetItem(book['isbn'] or "-"))
            self.table.setItem(row_idx, 5, QTableWidgetItem(str(book['available_copies'])))

    def open_book_form(self):
        dialog = BookForm(self.db, self)
        # Якщо книгу успішно додано (dialog.exec_() повертає 1), оновлюємо таблицю
        if dialog.exec_():
            self.load_data()