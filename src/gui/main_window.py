# src/gui/main_window.py
from PyQt5.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget, QAction, QMessageBox
from src.db.db_manager import DatabaseManager
from src.auth.session_manager import SessionManager
from src.gui.catalog_view import CatalogView
from src.gui.reader_view import ReaderRegistrationForm
from src.gui.reports_view import ReportsView
from src.gui.circulation_view import CirculationView
from src.gui.admin_view import AdminView
from src.services.notification_service import NotificationService
from src.services.fine_service import FineService
from src.services.reservation_service import ReservationService


class MainWindow(QMainWindow):
    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.db = db_manager

        self.run_background_tasks()
        self.init_ui()
        self.check_notifications()

    def run_background_tasks(self):
        try:
            ReservationService(self.db).cancel_expired_reservations()
            FineService(self.db).calculate_fines()
        except Exception as e:
            print(f"Помилка фонових задач: {e}")

    def init_ui(self):
        self.setWindowTitle("Система обліку шкільної бібліотеки")
        self.resize(1100, 750)

        self.setup_menu()

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # 1. Каталог
        self.catalog_tab = CatalogView(self.db)
        self.tabs.addTab(self.catalog_tab, "Каталог книг")

        # 2. Обслуговування (Видача/Повернення)
        self.circulation_tab = CirculationView(self.db)
        self.tabs.addTab(self.circulation_tab, "Обслуговування (Видача/Повернення)")

        # 3. Реєстрація читачів
        self.reader_tab = ReaderRegistrationForm(self.db)
        self.tabs.addTab(self.reader_tab, "Реєстрація читачів")

        # 4. Звіти
        self.reports_tab = ReportsView(self.db)
        self.tabs.addTab(self.reports_tab, "Звіти та Налаштування")

        # 5. Адміністрування (Вкладка з'являється лише для адміністратора)
        user = SessionManager.get_current_user()
        if user and user['role'] == 'Адміністратор':
            self.admin_tab = AdminView(self.db)
            self.tabs.addTab(self.admin_tab, "Адміністрування")

    def setup_menu(self):
        menubar = self.menuBar()
        user = SessionManager.get_current_user()
        role = user['role'] if user else "Гість"
        username = user['username'] if user else "Невідомо"

        user_menu = menubar.addMenu(f"Профіль: {username} ({role})")

        logout_action = QAction("Вийти", self)
        logout_action.triggered.connect(self.logout)
        user_menu.addAction(logout_action)

    def check_notifications(self):
        user = SessionManager.get_current_user()
        if user and user['role'] in ['Адміністратор', 'Бібліотекар']:
            service = NotificationService(self.db)
            reminders = service.get_overdue_reminders()

            if reminders:
                msg = f"Увага! Є прострочені видачі ({len(reminders)} читачів).\nПерейдіть до звітів, щоб сформувати список боржників."
                QMessageBox.information(self, "Нагадування", msg)

    def logout(self):
        SessionManager.logout()
        self.close()