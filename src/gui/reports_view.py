# src/gui/reports_view.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QMessageBox,
                             QFileDialog, QGroupBox, QDateEdit, QHBoxLayout, QLabel)
from PyQt5.QtCore import QDate
from src.db.db_manager import DatabaseManager
from src.services.report_service import ReportService
from src.services.backup_service import BackupService
from src.auth.session_manager import require_role


class ReportsView(QWidget):
    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.report_service = ReportService(db_manager)
        self.backup_service = BackupService(db_manager)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Секція звітів
        reports_group = QGroupBox("Генерація звітів (PDF)")
        reports_layout = QVBoxLayout()

        # --- Фільтр за датою ---
        date_layout = QHBoxLayout()
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addDays(-30))  # За останній місяць

        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())

        date_layout.addWidget(QLabel("Від:"))
        date_layout.addWidget(self.start_date)
        date_layout.addWidget(QLabel("До:"))
        date_layout.addWidget(self.end_date)
        date_layout.addStretch()
        reports_layout.addLayout(date_layout)
        # -----------------------

        self.btn_overdue = QPushButton("Звіт по боржниках")
        self.btn_overdue.clicked.connect(self.create_overdue_report)

        self.btn_popular = QPushButton("Топ популярних книг")
        self.btn_popular.clicked.connect(self.create_popular_report)

        self.btn_movement = QPushButton("Рух фонду (за обраний період)")
        self.btn_movement.clicked.connect(self.create_movement_report)

        reports_layout.addWidget(self.btn_overdue)
        reports_layout.addWidget(self.btn_popular)
        reports_layout.addWidget(self.btn_movement)
        reports_group.setLayout(reports_layout)
        layout.addWidget(reports_group)

        # Секція резервного копіювання (тільки для адміністратора)
        self.backup_group = QGroupBox("Управління базою даних")
        backup_layout = QVBoxLayout()

        self.btn_backup = QPushButton("Створити резервну копію")
        self.btn_backup.clicked.connect(self.do_backup)

        self.btn_restore = QPushButton("Відновити БД з копії")
        self.btn_restore.clicked.connect(self.do_restore)

        backup_layout.addWidget(self.btn_backup)
        backup_layout.addWidget(self.btn_restore)
        self.backup_group.setLayout(backup_layout)
        layout.addWidget(self.backup_group)

        layout.addStretch()
        self.setLayout(layout)

    @require_role(["Адміністратор", "Бібліотекар"])
    def create_overdue_report(self, *args, **kwargs):
        success, msg = self.report_service.generate_overdue_report()
        QMessageBox.information(self, "Результат", msg)

    @require_role(["Адміністратор", "Бібліотекар"])
    def create_popular_report(self, *args, **kwargs):
        success, msg = self.report_service.generate_popular_books_report()
        QMessageBox.information(self, "Результат", msg)

    @require_role(["Адміністратор", "Бібліотекар"])
    def create_movement_report(self, *args, **kwargs):
        start = self.start_date.date().toString("yyyy-MM-dd")
        end = self.end_date.date().toString("yyyy-MM-dd")
        success, msg = self.report_service.generate_movement_report(start, end)
        if success:
            QMessageBox.information(self, "Успіх", msg)
        else:
            QMessageBox.critical(self, "Помилка", msg)

    @require_role(["Адміністратор"])
    def do_backup(self, *args, **kwargs):
        dest_dir = QFileDialog.getExistingDirectory(self, "Оберіть папку для збереження копії")
        if dest_dir:
            success, msg = self.backup_service.create_backup(dest_dir)
            if success:
                QMessageBox.information(self, "Успіх", msg)
            else:
                QMessageBox.critical(self, "Помилка", msg)

    @require_role(["Адміністратор"])
    def do_restore(self, *args, **kwargs):
        source_file, _ = QFileDialog.getOpenFileName(self, "Оберіть файл резервної копії", "", "SQLite Database (*.db)")
        if source_file:
            reply = QMessageBox.question(self, 'Підтвердження',
                                         'Поточна база даних буде замінена. Ви впевнені?',
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                success, msg = self.backup_service.restore_backup(source_file)
                if success:
                    QMessageBox.information(self, "Успіх", msg)
                else:
                    QMessageBox.critical(self, "Помилка", msg)