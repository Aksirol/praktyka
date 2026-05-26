# src/gui/book_form.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                             QComboBox, QSpinBox, QPushButton, QMessageBox)
from src.db.db_manager import DatabaseManager
from src.auth.session_manager import require_role


class BookForm(QDialog):
    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.init_ui()
        self.load_dictionaries()

    def init_ui(self):
        self.setWindowTitle("Додати книгу")
        self.setFixedSize(400, 300)

        layout = QVBoxLayout()
        form_layout = QFormLayout()

        self.title_input = QLineEdit()
        self.author_cb = QComboBox()
        self.genre_cb = QComboBox()
        self.isbn_input = QLineEdit()
        self.year_input = QSpinBox()
        self.year_input.setRange(1800, 2100)
        self.year_input.setValue(2023)
        self.copies_input = QSpinBox()
        self.copies_input.setRange(1, 100)

        form_layout.addRow("Назва:", self.title_input)
        form_layout.addRow("Автор:", self.author_cb)
        form_layout.addRow("Жанр:", self.genre_cb)
        form_layout.addRow("ISBN:", self.isbn_input)
        form_layout.addRow("Рік видання:", self.year_input)
        form_layout.addRow("Кількість примірників:", self.copies_input)

        layout.addLayout(form_layout)

        self.save_btn = QPushButton("Зберегти")
        self.save_btn.clicked.connect(self.save_book)
        layout.addWidget(self.save_btn)

        self.setLayout(layout)

    def load_dictionaries(self):
        # Завантаження авторів
        authors = self.db.fetch_all("SELECT id, last_name, first_name FROM AUTHORS ORDER BY last_name")
        for a in authors:
            self.author_cb.addItem(f"{a['last_name']} {a['first_name']}", a['id'])

        # Завантаження жанрів
        genres = self.db.fetch_all("SELECT id, name FROM GENRES ORDER BY name")
        for g in genres:
            self.genre_cb.addItem(g['name'], g['id'])

    @require_role(["Адміністратор", "Бібліотекар"])
    def save_book(self, *args, kwargs):
        title = self.title_input.text().strip()
        author_id = self.author_cb.currentData()
        genre_id = self.genre_cb.currentData()
        isbn = self.isbn_input.text().strip()
        year = self.year_input.value()
        copies = self.copies_input.value()

        if not title:
            QMessageBox.warning(self, "Помилка", "Назва книги обов'язкова!")
            return

        try:
            # Створення книги
            book_id = self.db.execute_query(
                "INSERT INTO BOOKS (title, author_id, genre_id, isbn, year, total_copies) VALUES (?, ?, ?, ?, ?, ?)",
                (title, author_id, genre_id, isbn, year, copies)
            )

            # Автоматична генерація примірників
            for i in range(1, copies + 1):
                inv_number = f"INV-{book_id:04d}-{i:03d}"
                self.db.execute_query(
                    "INSERT INTO COPIES (book_id, inventory_number, status) VALUES (?, ?, 'available')",
                    (book_id, inv_number)
                )

            QMessageBox.information(self, "Успіх", "Книгу та примірники успішно додано!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Помилка БД", f"Не вдалося зберегти книгу: {str(e)}")