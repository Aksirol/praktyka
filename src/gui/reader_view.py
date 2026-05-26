# src/gui/reader_view.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLineEdit, QComboBox, QPushButton, QMessageBox, QTableWidget, QTableWidgetItem)
from src.db.db_manager import DatabaseManager
from src.services.reader_service import ReaderService
from src.auth.session_manager import require_role


class ReaderRegistrationForm(QWidget):
    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.reader_service = ReaderService(db_manager)
        self.db = db_manager
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        form_layout = QFormLayout()

        self.first_name_input = QLineEdit()
        self.last_name_input = QLineEdit()
        self.phone_input = QLineEdit()

        self.type_cb = QComboBox()
        self.type_cb.addItems(["Учень", "Вчитель"])

        self.class_cb = QComboBox()
        self.load_classes()

        form_layout.addRow("Прізвище:", self.last_name_input)
        form_layout.addRow("Ім'я:", self.first_name_input)
        form_layout.addRow("Тип читача:", self.type_cb)
        form_layout.addRow("Клас (для учнів):", self.class_cb)
        form_layout.addRow("Телефон:", self.phone_input)

        layout.addLayout(form_layout)

        self.save_btn = QPushButton("Зареєструвати")
        self.save_btn.clicked.connect(self.register)
        layout.addWidget(self.save_btn)

        self.setLayout(layout)

    def load_classes(self):
        classes = self.db.fetch_all("SELECT id, name FROM CLASSES ORDER BY grade_number, name")
        self.class_cb.addItem("Немає", None)
        for c in classes:
            self.class_cb.addItem(c['name'], c['id'])

    @require_role(["Адміністратор", "Бібліотекар"])
    def register(self):
        first_name = self.first_name_input.text().strip()
        last_name = self.last_name_input.text().strip()
        reader_type = self.type_cb.currentText()
        class_id = self.class_cb.currentData()
        phone = self.phone_input.text().strip()

        if not first_name or not last_name:
            QMessageBox.warning(self, "Помилка", "ПІБ є обов'язковими полями!")
            return

        try:
            self.reader_service.register_reader(first_name, last_name, reader_type, class_id, phone)
            QMessageBox.information(self, "Успіх", "Читача успішно зареєстровано!")
            self.first_name_input.clear()
            self.last_name_input.clear()
            self.phone_input.clear()
        except Exception as e:
            QMessageBox.critical(self, "Помилка", str(e))