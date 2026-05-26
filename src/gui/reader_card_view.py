# src/gui/reader_card_view.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QMessageBox, QGroupBox, QTabWidget, QLabel)
from src.db.db_manager import DatabaseManager
from src.services.reader_service import ReaderService
from src.auth.session_manager import require_role


class ReaderCardView(QWidget):
    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.db = db_manager
        self.reader_service = ReaderService(self.db)
        self.current_reader_id = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Пошук читача
        search_group = QGroupBox("Пошук читача")
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Прізвище, ім'я або телефон...")
        self.search_btn = QPushButton("Знайти")
        self.search_btn.clicked.connect(self.search_readers)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)

        # Таблиця пошуку
        self.readers_table = QTableWidget()
        self.readers_table.setColumnCount(4)
        self.readers_table.setHorizontalHeaderLabels(["ID", "Прізвище", "Ім'я", "Телефон"])
        self.readers_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.readers_table.setFixedHeight(120)
        self.readers_table.itemSelectionChanged.connect(self.on_reader_selected)
        layout.addWidget(self.readers_table)

        # Інфо панель
        self.info_label = QLabel("Оберіть читача для перегляду інформації")
        self.info_label.setStyleSheet("font-weight: bold; font-size: 14px; margin: 10px 0; color: #2c3e50;")
        layout.addWidget(self.info_label)

        # Вкладки картки
        self.tabs = QTabWidget()

        self.active_table = QTableWidget()
        self.active_table.setColumnCount(4)
        self.active_table.setHorizontalHeaderLabels(["Книга", "Інв. №", "Дата видачі", "Термін"])
        self.active_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabs.addTab(self.active_table, "Активні видачі")

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(3)
        self.history_table.setHorizontalHeaderLabels(["Книга", "Дата видачі", "Дата повернення"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabs.addTab(self.history_table, "Історія видач")

        # Вкладка Бронювань
        res_tab = QWidget()
        res_layout = QVBoxLayout()
        self.res_table = QTableWidget()
        self.res_table.setColumnCount(4)
        self.res_table.setHorizontalHeaderLabels(["ID", "Книга", "Дата бронювання", "Діє до"])
        self.res_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.cancel_res_btn = QPushButton("Скасувати обране бронювання")
        self.cancel_res_btn.clicked.connect(self.cancel_reservation)

        res_layout.addWidget(self.res_table)
        res_layout.addWidget(self.cancel_res_btn)
        res_tab.setLayout(res_layout)
        self.tabs.addTab(res_tab, "Активні бронювання")

        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def search_readers(self):
        term = f"%{self.search_input.text().strip()}%"
        readers = self.db.fetch_all(
            "SELECT id, last_name, first_name, phone FROM READERS WHERE last_name LIKE ? OR first_name LIKE ? OR phone LIKE ?",
            (term, term, term)
        )
        self.readers_table.setRowCount(len(readers))
        for row, r in enumerate(readers):
            self.readers_table.setItem(row, 0, QTableWidgetItem(str(r['id'])))
            self.readers_table.setItem(row, 1, QTableWidgetItem(r['last_name']))
            self.readers_table.setItem(row, 2, QTableWidgetItem(r['first_name']))
            self.readers_table.setItem(row, 3, QTableWidgetItem(r['phone'] or ""))

    def on_reader_selected(self):
        row = self.readers_table.currentRow()
        if row >= 0:
            self.current_reader_id = int(self.readers_table.item(row, 0).text())
            self.load_reader_card()

    def load_reader_card(self):
        if not self.current_reader_id: return
        summary = self.reader_service.get_reader_summary(self.current_reader_id)
        profile = summary['profile']

        self.info_label.setText(
            f"Картка: {profile['last_name']} {profile['first_name']} | {profile['reader_type']} | Тел: {profile['phone'] or '-'}")

        self.active_table.setRowCount(len(summary['active_loans']))
        for i, l in enumerate(summary['active_loans']):
            self.active_table.setItem(i, 0, QTableWidgetItem(l['title']))
            self.active_table.setItem(i, 1, QTableWidgetItem(l['inventory_number']))
            self.active_table.setItem(i, 2, QTableWidgetItem(l['issue_date']))
            self.active_table.setItem(i, 3, QTableWidgetItem(l['due_date']))

        self.history_table.setRowCount(len(summary['history']))
        for i, h in enumerate(summary['history']):
            self.history_table.setItem(i, 0, QTableWidgetItem(h['title']))
            self.history_table.setItem(i, 1, QTableWidgetItem(h['issue_date']))
            self.history_table.setItem(i, 2, QTableWidgetItem(h['return_date']))

        self.res_table.setRowCount(len(summary['reservations']))
        for i, r in enumerate(summary['reservations']):
            self.res_table.setItem(i, 0, QTableWidgetItem(str(r['id'])))
            self.res_table.setItem(i, 1, QTableWidgetItem(r['title']))
            self.res_table.setItem(i, 2, QTableWidgetItem(r['reserved_at'] or "-"))
            self.res_table.setItem(i, 3, QTableWidgetItem(r['expires_at']))

    @require_role(["Адміністратор", "Бібліотекар"])
    def cancel_reservation(self, *args, **kwargs):
        row = self.res_table.currentRow()
        if row < 0: return QMessageBox.warning(self, "Увага", "Оберіть бронювання для скасування!")

        res_id = int(self.res_table.item(row, 0).text())
        reply = QMessageBox.question(self, "Підтвердження", "Скасувати це бронювання?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.db.execute_query("UPDATE RESERVATIONS SET status = 'cancelled' WHERE id = ?", (res_id,))
            QMessageBox.information(self, "Успіх", "Бронювання скасовано.")
            self.load_reader_card()