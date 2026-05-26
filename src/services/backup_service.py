# src/services/backup_service.py
import os
import shutil
from datetime import datetime
from src.db.db_manager import DatabaseManager
from src.auth.audit_logger import AuditLogger


class BackupService:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.logger = AuditLogger(db)

    def create_backup(self, dest_dir: str) -> tuple[bool, str]:
        """Створює резервну копію БД (A2)."""
        try:
            date_str = datetime.now().strftime("%Y-%m-%d")
            filename = f"library_backup_{date_str}.db"
            dest_path = os.path.join(dest_dir, filename)

            # Копіюємо файл бази даних
            shutil.copy2(self.db.db_path, dest_path)

            self.logger.log_operation(f"Створено резервну копію: {dest_path}")
            return True, f"Копію успішно збережено: {dest_path}"
        except Exception as e:
            return False, f"Помилка створення копії: {str(e)}"

    def restore_backup(self, source_file: str) -> tuple[bool, str]:
        """Відновлює БД з файлу резервної копії (A3)."""
        try:
            # Замінюємо поточний файл бази даних вибраним файлом
            shutil.copy2(source_file, self.db.db_path)

            self.logger.log_operation(f"Відновлено базу даних з копії: {source_file}")
            return True, "Базу даних успішно відновлено. Будь ласка, перезапустіть програму."
        except Exception as e:
            return False, f"Помилка відновлення: {str(e)}"