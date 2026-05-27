# config.py (НОВЫЙ ФАЙЛ)
import os

# VK Configuration
VK_CONFIG = {
    "group_token": os.environ.get("VK_GROUP_TOKEN", "vk1.a.anNaJCeOS28-80xGjk3h5AAc85btGUYYzgUZKWXh91G-_EVlxVr5Xa2JBPnxCs0y1X6XJCa8DkocBAtAo3qDPjXZriFPnK-Ys6WSDbog1HjDYPPmPv88e4TCSu2rg1w-cRjZitVb-gSLaibiINf__JndTED8hC8fkPXQ9zcJBPbcDqfFnfnhMK0h0sL_TLZZUVgGQZxheTByXO8W8RQV7Q"),
    "group_id": int(os.environ.get("VK_GROUP_ID", 239120595)),  # ID группы (число)
    "api_version": "5.131"
}

# Bot settings
BOT_SETTINGS = {
    "enabled": True,
    "admin_ids": [],  # ID администраторов в VK
    "welcome_message": """🏊 Привет! Я бот Swim CRM.

Доступные команды:
📝 /apply - Подать заявку на занятия
📊 /status - Проверить статус заявки
👶 /my_children - Мои дети
📅 /schedule - Расписание занятий
❓ /help - Помощь

Для начала работы свяжите свой аккаунт VK с личным кабинетом.""",

    "help_message": """🤖 *Помощь по боту Swim CRM*

*Основные команды:*
📝 `/apply` - Подать новую заявку на занятия
📊 `/status [номер]` - Проверить статус заявки
👶 `/my_children` - Список ваших детей
📅 `/schedule` - Расписание занятий
🔗 `/link [телефон] [пароль]` - Привязать VK к аккаунту
👤 `/profile` - Информация о профиле
❓ `/help` - Эта справка

*Примеры:*
`/status 123` - Проверить заявку #123
`/link +79123456789 password123` - Привязать аккаунт

По всем вопросам обращайтесь к администратору."""
}