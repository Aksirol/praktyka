# src/gui/admin_view.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QComboBox, QMessageBox, QGroupBox, QFormLayout)
from src.db.db_manager import DatabaseManager
from src.auth.session_manager import require_role


class AdminView(QWidget):
    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.db = db_manager
        self.init_ui()
        self.load_users()

    def init_ui(self):
        layout = QHBoxLayout()

        # Ліва частина - Список користувачів
        list_group = QGroupBox("Користувачі системи")
        list_layout = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(5)  # Збільшено до 5 стовпців для статусу
        self.table.setHorizontalHeaderLabels(["ID", "Логін", "Роль", "Статус", "Створено"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        list_layout.addWidget(self.table)

        self.delete_btn = QPushButton("Деактивувати обраного користувача")
        self.delete_btn.setStyleSheet("color: white; background-color: #d9534f;")
        self.delete_btn.clicked.connect(self.delete_user)
        list_layout.addWidget(self.delete_btn)
        list_group.setLayout(list_layout)

        # Права частина - Додавання нового
        add_group = QGroupBox("Додати бібліотекаря")
        add_layout = QFormLayout()
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.role_cb = QComboBox()
        self.role_cb.addItems(["Бібліотекар", "Адміністратор"])

        add_layout.addRow("Логін:", self.username_input)
        add_layout.addRow("Пароль:", self.password_input)
        add_layout.addRow("Роль:", self.role_cb)

        self.add_btn = QPushButton("Створити користувача")
        self.add_btn.clicked.connect(self.add_user)
        add_layout.addWidget(self.add_btn)

        add_group.setLayout(add_layout)

        layout.addWidget(list_group, 65)
        layout.addWidget(add_group, 35)
        self.setLayout(layout)

    def load_users(self):
        users = self.db.fetch_all("SELECT id, username, role, is_active, created_at FROM USERS ORDER BY id")
        self.table.setRowCount(len(users))
        for i, u in enumerate(users):
            status_text = "Активний" if u['is_active'] == 1 else "Заблокований"
            self.table.setItem(i, 0, QTableWidgetItem(str(u['id'])))
            self.table.setItem(i, 1, QTableWidgetItem(u['username']))
            self.table.setItem(i, 2, QTableWidgetItem(u['role']))
            self.table.setItem(i, 3, QTableWidgetItem(status_text))
            self.table.setItem(i, 4, QTableWidgetItem(str(u['created_at'])))

    @require_role(["Адміністратор"])
    def add_user(self, *args, **kwargs):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        role = self.role_cb.currentText()

        if not username or not password:
            return QMessageBox.warning(self, "Помилка", "Заповніть всі поля!")

        hashed = DatabaseManager.hash_password(password)
        try:
            self.db.execute_query(
                "INSERT INTO USERS (username, password_hash, role, is_active) VALUES (?, ?, ?, 1)",
                (username, hashed, role)
            )
            QMessageBox.information(self, "Успіх", "Користувача успішно додано!")
            self.username_input.clear()
            self.password_input.clear()
            self.load_users()
        except Exception:
            QMessageBox.critical(self, "Помилка", "Користувач з таким логіном вже існує.")

    @require_role(["Адміністратор"])
    def delete_user(self, *args, **kwargs):
        row = self.table.currentRow()
        if row < 0:
            return QMessageBox.warning(self, "Помилка", "Оберіть користувача у таблиці!")

        user_id = int(self.table.item(row, 0).text())
        from src.auth.session_manager import SessionManager
        curr_user = SessionManager.get_current_user()

        if user_id == curr_user['id']:
            return QMessageBox.critical(self, "Відмовлено", "Ви не можете деактивувати власний обліковий запис!")

        reply = QMessageBox.question(self, "Підтвердження",
                                     "Ви впевнені, що хочете деактивувати цього користувача? Він втратить доступ до системи.",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            # ВИПРАВЛЕННЯ: М'яка деактивація замість жорсткого DELETE
            self.db.execute_query("UPDATE USERS SET is_active = 0 WHERE id = ?", (user_id,))
            self.load_users()
            QMessageBox.information(self, "Успіх", "Користувача успішно деактивовано.")