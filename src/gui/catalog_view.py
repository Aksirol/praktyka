# src/gui/catalog_view.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QComboBox, QMessageBox)
from PyQt5.QtCore import Qt
from src.db.db_manager import DatabaseManager
from src.auth.session_manager import SessionManager, require_role
from src.gui.book_form import BookForm
import sqlite3


class NumericItem(QTableWidgetItem):
    """Спеціальний клас для коректного числового сортування стовпців таблиці."""

    def __lt__(self, other):
        try:
            # Спроба порівняти як числа
            return float(self.text()) < float(other.text())
        except ValueError:
            # Якщо це не числа (наприклад, порожній рядок або текст), порівнюємо як текст
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
        self.add_book_btn.clicked.connect(self.open_book_form)

        self.delete_book_btn = QPushButton("Видалити книгу")
        self.delete_book_btn.clicked.connect(self.delete_book)
        self.delete_book_btn.setStyleSheet("color: white; background-color: #d9534f;")  # Робимо кнопку червоною

        self.manage_layout.addWidget(self.add_book_btn)
        self.manage_layout.addWidget(self.delete_book_btn)
        self.manage_layout.addStretch()  # Відкидає кнопки вліво
        layout.addLayout(self.manage_layout)

        # Перевірка прав доступу для приховування кнопок керування
        user = SessionManager.get_current_user()
        if not user or user['role'] == 'Читач':
            self.add_book_btn.hide()
            self.delete_book_btn.hide()

        # Таблиця
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Назва", "Автор", "Жанр", "ISBN", "Доступно"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Дозволяємо сортування по кліку на заголовок
        self.table.setSortingEnabled(True)

        layout.addWidget(self.table)
        self.setLayout(layout)

    def load_genres(self):
        genres = self.db.fetch_all("SELECT id, name FROM GENRES ORDER BY name")
        for g in genres:
            self.genre_filter.addItem(g['name'], g['id'])

    def load_data(self):
        # Обов'язково вимикаємо сортування під час заповнення таблиці, щоб рядки не перемішалися
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)  # Очищення таблиці перед новим пошуком

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
            # Використовуємо NumericItem для колонок з числами (ID та Доступно)
            id_item = NumericItem(str(book['id']))
            copies_item = NumericItem(str(book['available_copies']))

            # Стандартні текстові елементи
            title_item = QTableWidgetItem(book['title'])
            author_item = QTableWidgetItem(book['author_name'] or "Невідомо")
            genre_item = QTableWidgetItem(book['genre_name'] or "Невідомо")
            isbn_item = QTableWidgetItem(book['isbn'] or "-")

            self.table.setItem(row_idx, 0, id_item)
            self.table.setItem(row_idx, 1, title_item)
            self.table.setItem(row_idx, 2, author_item)
            self.table.setItem(row_idx, 3, genre_item)
            self.table.setItem(row_idx, 4, isbn_item)
            self.table.setItem(row_idx, 5, copies_item)

        # Вмикаємо сортування назад після того, як таблиця заповнена
        self.table.setSortingEnabled(True)

    def open_book_form(self):
        dialog = BookForm(self.db, self)
        if dialog.exec_():
            self.load_data()

    @require_role(["Адміністратор", "Бібліотекар"])
    def delete_book(self, *args, **kwargs):
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Увага", "Оберіть книгу для видалення, натиснувши на рядок у таблиці!")
            return

        book_id = self.table.item(current_row, 0).text()
        title = self.table.item(current_row, 1).text()

        # Запитуємо підтвердження
        reply = QMessageBox.question(self, 'Підтвердження',
                                     f'Ви впевнені, що хочете видалити книгу "{title}" та всі її примірники?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                # Видаляємо всі примірники цієї книги
                self.db.execute_query("DELETE FROM COPIES WHERE book_id = ?", (book_id,))
                # Видаляємо саму книгу
                self.db.execute_query("DELETE FROM BOOKS WHERE id = ?", (book_id,))

                QMessageBox.information(self, "Успіх", "Книгу успішно видалено.")
                self.load_data()  # Оновлюємо таблицю

            except sqlite3.IntegrityError:
                # Перехоплюємо помилку зовнішніх ключів
                QMessageBox.critical(self, "Помилка видалення",
                                     "Неможливо видалити цю книгу, оскільки вона знаходиться в історії видач читачів.\n"
                                     "Рекомендуємо змінити статуси її примірників на 'Списано' через меню управління примірниками.")
            except Exception as e:
                QMessageBox.critical(self, "Помилка БД", f"Не вдалося видалити книгу: {str(e)}")