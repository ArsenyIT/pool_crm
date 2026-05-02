# database.py
import sqlite3
from contextlib import contextmanager
from fastapi import FastAPI, Depends, HTTPException

DATABASE_PATH = "swim_crm.db"  # файл базы данных


class Database:
    """Класс для управления подключением к SQLite"""

    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._connection = None

    def get_connection(self): # Создаёт соединение с SQLite при первом запросе
        """Получить соединение с БД (создаёт новое при необходимости)"""
        if self._connection is None:
            self._connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,  # Разрешаем использование в разных потоках
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
            )
            # Включаем поддержку внешних ключей (очень важно!)
            self._connection.execute("PRAGMA foreign_keys = ON")
            # Возвращаем строки как словари для удобства
            self._connection.row_factory = sqlite3.Row
        return self._connection

    def close(self):
        """Закрыть соединение с БД"""
        if self._connection is not None:
            self._connection.close()
            self._connection = None


# Глобальный экземпляр БД
db_instance = Database()


@contextmanager
def get_db_cursor():
    """
    Контекстный менеджер для работы с курсором.
    Автоматически управляет транзакциями.

    Использование:
    with get_db_cursor() as cursor:
        cursor.execute("SELECT * FROM users")
        results = cursor.fetchall()
    """
    conn = db_instance.get_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()  # Автоматический коммит при успехе
    except Exception as e:
        conn.rollback()  # Откат при ошибке
        raise e
    finally:
        cursor.close()


def get_db():
    """
    Dependency для FastAPI.
    Используется в эндпоинтах для получения курсора.
    """
    with get_db_cursor() as cursor:
        yield cursor


# Функция для инициализации БД (будет вызвана при старте)
def init_database(app: FastAPI):
    """Инициализация БД при запуске приложения"""
    from init_db import create_tables, seed_test_data

    @app.on_event("startup")
    async def startup():
        create_tables()
        seed_test_data()
        print("✅ Database initialized successfully")

    @app.on_event("shutdown")
    async def shutdown():
        db_instance.close()
        print("👋 Database connection closed")