# vk_config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Настройки VK
VK_GROUP_ID = os.getenv("VK_GROUP_ID")  # ID сообщества
VK_ACCESS_TOKEN = os.getenv("VK_ACCESS_TOKEN")  # Токен сообщества
VK_API_VERSION = "5.199"
VK_LONGPOLL_WAIT = 25
VK_LONGPOLL_MODE = 2  # 2 - получать сообщения
VK_CONFIRMATION_CODE = os.getenv("VK_CONFIRMATION_CODE")  # Код подтверждения для Callback API
VK_SECRET_KEY = os.getenv("VK_SECRET_KEY")  # Секретный ключ (опционально)


# Проверка наличия необходимых переменных
def check_vk_config():
    """Проверяет наличие необходимых настроек VK"""
    errors = []
    if not VK_GROUP_ID:
        errors.append("VK_GROUP_ID не установлен в .env файле")
    if not VK_ACCESS_TOKEN:
        errors.append("VK_ACCESS_TOKEN не установлен в .env файле")

    if errors:
        print("\n⚠️ Ошибки конфигурации VK:")
        for error in errors:
            print(f"  - {error}")
        print("\n📝 Инструкция по настройке:")
        print("1. Создайте файл .env в корне проекта")
        print("2. Добавьте в него:")
        print("   VK_GROUP_ID=123456789  (ID вашей группы VK)")
        print("   VK_ACCESS_TOKEN=vk1.a.ваш_токен")
        print("3. Получите токен в настройках сообщества VK -> Работа с API")
        print("4. Включите Long Poll API в настройках сообщества\n")

    return errors


# Для обратной совместимости
def get_vk_config():
    """Возвращает конфигурацию VK"""
    return {
        'group_id': VK_GROUP_ID,
        'access_token': VK_ACCESS_TOKEN,
        'api_version': VK_API_VERSION,
        'longpoll_wait': VK_LONGPOLL_WAIT,
        'confirmation_code': VK_CONFIRMATION_CODE,
        'secret_key': VK_SECRET_KEY
    }