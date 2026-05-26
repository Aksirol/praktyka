# src/main.py
import sys
import os
from PyQt5.QtWidgets import QApplication
from src.db.db_manager import DatabaseManager
from src.gui.login_window import LoginWindow
from src.gui.main_window import MainWindow


class LibraryApp:
    def __init__(self):
        self.app = QApplication(sys.argv)

        # Ініціалізація бази даних
        db_path = os.getenv("DB_PATH", "data/library.db")
        self.db = DatabaseManager(db_path)

        self.login_window = None
        self.main_window = None

    def start(self):
        self.show_login()
        sys.exit(self.app.exec_())

    def show_login(self):
        self.login_window = LoginWindow(self.db, self.show_main)
        self.login_window.show()

    def show_main(self):
        self.main_window = MainWindow(self.db)
        # Перевизначаємо метод closeEvent головного вікна, щоб при виході з акаунту показувати логін
        original_close = self.main_window.closeEvent

        def custom_close(event):
            original_close(event)
            from src.auth.session_manager import SessionManager
            if SessionManager.get_current_user() is None:
                self.show_login()

        self.main_window.closeEvent = custom_close
        self.main_window.show()


if __name__ == "__main__":
    app = LibraryApp()
    app.start()