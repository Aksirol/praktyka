# src/gui/book_form.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                             QComboBox, QSpinBox, QPushButton, QMessageBox,
                             QHBoxLayout, QInputDialog)
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
        self.setFixedSize(450, 300)

        layout = QVBoxLayout()
        form_layout = QFormLayout()

        self.title_input = QLineEdit()
        self.isbn_input = QLineEdit()

        self.year_input = QSpinBox()
        self.year_input.setRange(1800, 2100)
        self.year_input.setValue(2023)

        self.copies_input = QSpinBox()
        self.copies_input.setRange(1, 100)

        # Рядок Автора з кнопкою "+"
        author_layout = QHBoxLayout()
        self.author_cb = QComboBox()
        self.add_author_btn = QPushButton("+")
        self.add_author_btn.setFixedWidth(30)
        self.add_author_btn.clicked.connect(self.add_new_author)
        author_layout.addWidget(self.author_cb)
        author_layout.addWidget(self.add_author_btn)

        # Рядок Жанру з кнопкою "+"
        genre_layout = QHBoxLayout()
        self.genre_cb = QComboBox()
        self.add_genre_btn = QPushButton("+")
        self.add_genre_btn.setFixedWidth(30)
        self.add_genre_btn.clicked.connect(self.add_new_genre)
        genre_layout.addWidget(self.genre_cb)
        genre_layout.addWidget(self.add_genre_btn)

        form_layout.addRow("Назва:", self.title_input)
        form_layout.addRow("Автор:", author_layout)
        form_layout.addRow("Жанр:", genre_layout)
        form_layout.addRow("ISBN:", self.isbn_input)
        form_layout.addRow("Рік видання:", self.year_input)
        form_layout.addRow("Кількість примірників:", self.copies_input)

        layout.addLayout(form_layout)

        self.save_btn = QPushButton("Зберегти")
        self.save_btn.clicked.connect(self.save_book)
        layout.addWidget(self.save_btn)

        self.setLayout(layout)

    def load_dictionaries(self):
        self.author_cb.clear()
        authors = self.db.fetch_all("SELECT id, last_name, first_name FROM AUTHORS ORDER BY last_name")
        for a in authors:
            self.author_cb.addItem(f"{a['last_name']} {a['first_name']}", a['id'])

        self.genre_cb.clear()
        genres = self.db.fetch_all("SELECT id, name FROM GENRES ORDER BY name")
        for g in genres:
            self.genre_cb.addItem(g['name'], g['id'])

    @require_role(["Адміністратор", "Бібліотекар"])
    def add_new_author(self, *args, **kwargs):
        last_name, ok1 = QInputDialog.getText(self, "Новий автор", "Введіть прізвище:")
        if ok1 and last_name.strip():
            first_name, ok2 = QInputDialog.getText(self, "Новий автор", "Введіть ім'я:")
            if ok2 and first_name.strip():
                try:
                    author_id = self.db.execute_query(
                        "INSERT INTO AUTHORS (first_name, last_name) VALUES (?, ?)",
                        (first_name.strip(), last_name.strip())
                    )
                    # Додаємо у список і відразу обираємо
                    self.author_cb.addItem(f"{last_name.strip()} {first_name.strip()}", author_id)
                    self.author_cb.setCurrentIndex(self.author_cb.count() - 1)
                except Exception as e:
                    QMessageBox.warning(self, "Помилка", f"Не вдалося додати автора: {str(e)}")

    @require_role(["Адміністратор", "Бібліотекар"])
    def add_new_genre(self, *args, **kwargs):
        name, ok = QInputDialog.getText(self, "Новий жанр", "Введіть назву жанру:")
        if ok and name.strip():
            try:
                genre_id = self.db.execute_query(
                    "INSERT INTO GENRES (name) VALUES (?)",
                    (name.strip(),)
                )
                self.genre_cb.addItem(name.strip(), genre_id)
                self.genre_cb.setCurrentIndex(self.genre_cb.count() - 1)
            except Exception as e:
                QMessageBox.warning(self, "Помилка", "Жанр з такою назвою, ймовірно, вже існує!")

    @require_role(["Адміністратор", "Бібліотекар"])
    def save_book(self, *args, **kwargs):
        title = self.title_input.text().strip()
        author_id = self.author_cb.currentData()
        genre_id = self.genre_cb.currentData()
        isbn = self.isbn_input.text().strip()
        year = self.year_input.value()
        copies = self.copies_input.value()

        if not title:
            QMessageBox.warning(self, "Помилка", "Назва книги обов'язкова!")
            return

        if not author_id or not genre_id:
            QMessageBox.warning(self, "Помилка", "Будь ласка, оберіть або створіть автора та жанр!")
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