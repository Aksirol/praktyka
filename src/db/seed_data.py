# src/db/seed_data.py
import os
from src.db.db_manager import DatabaseManager


def initialize_database():
    db_path = os.getenv("DB_PATH", "data/library.db")
    schema_path = "src/db/migrations/schema.sql"

    print(f"Ініціалізація бази даних у {db_path}...")
    db = DatabaseManager(db_path=db_path)

    # 1. Застосування схеми
    if os.path.exists(schema_path):
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_script = f.read()

        with db.get_connection() as conn:
            conn.executescript(schema_script)
            conn.commit()
        print("Схему успішно застосовано.")
    else:
        print(f"Помилка: Файл {schema_path} не знайдено.")
        return

    # Фрагмент для заміни у src/db/seed_data.py (Крок 2)
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")

    admin = db.fetch_one("SELECT * FROM USERS WHERE username = ?", (admin_username,))
    if not admin:
        hashed_pw = DatabaseManager.hash_password(admin_password)
        db.execute_query(
            "INSERT INTO USERS (username, password_hash, role) VALUES (?, ?, ?)",
            (admin_username, hashed_pw, "Адміністратор")
        )
        print(f"Створено обліковий запис: {admin_username}")

    # Додавання базових жанрів
    genres = ["Класична література", "Фантастика", "Науково-популярна", "Підручники"]
    for genre in genres:
        db.execute_query("INSERT OR IGNORE INTO GENRES (name) VALUES (?)", (genre,))

    print("Seed-дані успішно додано!")


if __name__ == "__main__":
    initialize_database()