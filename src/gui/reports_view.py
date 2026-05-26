# src/gui/reports_view.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QMessageBox, QFileDialog, QGroupBox
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

        self.btn_overdue = QPushButton("Звіт по боржниках")
        self.btn_overdue.clicked.connect(self.create_overdue_report)

        self.btn_popular = QPushButton("Топ популярних книг")
        self.btn_popular.clicked.connect(self.create_popular_report)

        reports_layout.addWidget(self.btn_overdue)
        reports_layout.addWidget(self.btn_popular)
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

        self.setLayout(layout)

    @require_role(["Адміністратор", "Бібліотекар"])
    def create_overdue_report(self, *args, **kwargs):
        success, msg = self.report_service.generate_overdue_report()
        QMessageBox.information(self, "Результат", msg)

    @require_role(["Адміністратор", "Бібліотекар"])
    def create_popular_report(self, *args, **kwargs):
        success, msg = self.report_service.generate_popular_books_report()
        QMessageBox.information(self, "Результат", msg)

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