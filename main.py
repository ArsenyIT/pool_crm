# main.py

from fastapi import (
    FastAPI, Request, HTTPException, Depends, status,
    Form, UploadFile, File, Coockie)
from typing import Annotated, Optional
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import secrets
from database import db_instance, get_db
from init_db import create_tables, seed_test_data, ensure_tables_exist
from contextlib import asynccontextmanager


# Хранилище активных сессий: {token: {"user_id": int, "user_type": str, "login": str}}
active_sessions = {}

def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управляет жизненным циклом приложения:
    - при запуске проверяет и инициализирует БД
    - при завершении закрывает соединение с БД
    """

    print("Запуск приложения...")

    # Проверяем, существуют ли таблицы       ensure_tables_exist() создаёт таблицы, если их нет
    tables_created = ensure_tables_exist() # и возвращает True, если были созданы

    # Если таблицы были только что созданы, заполняем их тестовыми данными
    if tables_created:
        print("Таблицы созданы, заполняем тестовыми данными...")
        seed_test_data()
    else: # Таблицы уже существуют. Проверка наличия данных
        from database import get_db_cursor
        with get_db_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM trainers")
            count = cursor.fetchone()[0]
            if count == 0:
                print("Данные отсутствуют. Заполнение тестовыми данными...")
                seed_test_data()
            else:
                print("Данные уже существуют. Пропускаем инициализацию.")

    print("Приложение готово к работе")

    yield  # Здесь работает само приложение

    # Завершение работы
    print("Остановка приложения, закрытие соединения с БД...")
    db_instance.close()
    print("Соединение закрыто")


# Инициализация FastAPI
app = FastAPI(
    title="pool_crm",
    description="SRM для бассейна",
    version="1.0.0",
    lifespan=lifespan
)

# Подключение статики и шаблонов
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ========== СТРАНИЦА ВХОДА ==========
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """
    Показывает страницу входа в систему
    """

    return templates.TeemplateResponse(
        request, # В новых версиях обязательно первым параметром указывать request
        "login.html",
        {"request": request, "title": "Вход в систему"}
    )

@app.post("/login")
async def login(
        request: Request,
        username: Annotated[str, Form()],
        password: Annotated[str, Form()],
        db_cursor = Depends(get_db)
):
    """
    Обрабатывает форму входа
    """

    # Ищем тренера в базе данных
    db_cursor.execute("SELECT id, login, password_hash, 'trainer' as type FROM trainers WHERE login = ?", (username,))
    user = db_cursor.fetchone()

    # Если не тренер, ищем родителя по телефону
    if not user:
        db_cursor.execute("SELECT id, phone, password_hash, 'parent' as type FROM parents WHERE phone = ?", (username,))
        user = db_cursor.fetchone()

    # Проверяем пароль (простое сравнение строк)
    if user and user["password_hash"] == password:
        token = secrets.token_urlsafe(32)
        active_sessions[token] = {"user_id": user["id"], "user_type": user["type"]}
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie("session_token", token, httponly=True)
        return response

    return templates.TemplateResponse(
        request,
        "login.html",
        {"request": request, "error": "Неверный логин/пароль"}
    )