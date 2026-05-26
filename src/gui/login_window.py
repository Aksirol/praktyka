# src/gui/login_window.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox
from PyQt5.QtCore import Qt
from src.auth.auth_service import AuthService
from src.db.db_manager import DatabaseManager


class LoginWindow(QWidget):
    def __init__(self, db_manager: DatabaseManager, on_success_callback):
        super().__init__()
        self.auth_service = AuthService(db_manager)
        self.on_success_callback = on_success_callback
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Система обліку бібліотеки - Вхід")
        self.setFixedSize(300, 200)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        # Заголовок
        title = QLabel("Авторизація")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        # Поле логіну
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Логін")
        layout.addWidget(self.username_input)

        # Поле паролю
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Пароль")
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)

        # Кнопка входу
        self.login_btn = QPushButton("Увійти")
        self.login_btn.clicked.connect(self.handle_login)
        self.login_btn.setStyleSheet("padding: 5px; margin-top: 10px;")
        layout.addWidget(self.login_btn)

        self.setLayout(layout)

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Увага", "Будь ласка, заповніть всі поля.")
            return

        if self.auth_service.authenticate(username, password):
            self.close()
            self.on_success_callback()  # Виклик головного вікна
        else:
            QMessageBox.critical(self, "Помилка", "Невірний логін або пароль!")
            self.password_input.clear()