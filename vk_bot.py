# vk_bot.py
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.exceptions import ApiError
import logging
import re
from datetime import datetime
from database import get_db_cursor
from vk_config import (
    VK_GROUP_ID,
    VK_ACCESS_TOKEN,
    VK_API_VERSION,
    VK_LONGPOLL_WAIT,
    check_vk_config
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VKBot:
    def __init__(self):
        """Инициализация VK бота"""
        # Проверяем конфигурацию
        errors = check_vk_config()
        if errors:
            error_msg = "Ошибки конфигурации VK:\n" + "\n".join(errors)
            logger.error(error_msg)
            raise ValueError(error_msg)

        try:
            # Пробуем создать сессию VK
            self.vk_session = vk_api.VkApi(token=VK_ACCESS_TOKEN, api_version=VK_API_VERSION)
            self.vk = self.vk_session.get_api()

            # Проверяем токен, пытаясь получить информацию о группе
            try:
                group_info = self.vk.groups.getById(group_id=VK_GROUP_ID)
                logger.info(f"✅ Успешное подключение к группе: {group_info[0]['name']}")
            except ApiError as e:
                if e.code == 15:
                    logger.error("❌ Ошибка доступа: Неверный токен или недостаточно прав")
                    logger.error("Проверьте:")
                    logger.error("1. Токен должен быть ключом доступа сообщества")
                    logger.error("2. У токена должны быть права на 'Управление сообществом' и 'Сообщения сообщества'")
                    logger.error("3. В настройках сообщества должен быть включен Long Poll API")
                raise

            # Инициализируем Long Poll
            self.longpoll = VkBotLongPoll(self.vk_session, VK_GROUP_ID, wait=VK_LONGPOLL_WAIT)

        except ApiError as e:
            logger.error(f"Ошибка VK API: {e} (код: {e.code})")
            if e.code == 15:
                logger.error("""
                🔧 Как исправить ошибку доступа:

                1. Получите новый токен сообщества:
                   - Перейдите в управление сообществом
                   - Раздел "Работа с API"
                   - Создайте новый ключ доступа
                   - Включите права: "Управление сообществом" и "Сообщения сообщества"

                2. Настройте Long Poll API:
                   - В настройках сообщества → "Сообщения"
                   - Включите "Long Poll API"
                   - Включите "Получение событий"

                3. Обновите .env файл:
                   VK_GROUP_ID=123456789  (числовой ID группы)
                   VK_ACCESS_TOKEN=ваш_новый_токен
                """)
            raise

        # Состояния диалога с пользователями
        self.user_states = {}  # user_id -> state
        self.user_data = {}  # временные данные для регистрации

        # Состояния
        self.STATE_NONE = 0
        self.STATE_WAITING_NAME = 1
        self.STATE_WAITING_PHONE = 2
        self.STATE_WAITING_EMAIL = 3
        self.STATE_WAITING_CHILD_NAME = 4
        self.STATE_WAITING_CHILD_AGE = 5
        self.STATE_WAITING_SCHOOL = 6
        self.STATE_WAITING_SHIFT = 7
        self.STATE_WAITING_LESSONS = 8
        self.STATE_WAITING_CONFIRM = 9

    def send_message(self, user_id, message, keyboard=None):
        """Отправка сообщения пользователю"""
        try:
            params = {
                "user_id": user_id,
                "message": message,
                "random_id": 0
            }
            if keyboard:
                params["keyboard"] = keyboard.get_keyboard()

            self.vk.messages.send(**params)
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения: {e}")

    def get_main_keyboard(self):
        """Главное меню бота"""
        keyboard = VkKeyboard(one_time=False)
        keyboard.add_button("📝 Подать заявку", color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button("ℹ️ О школе", color=VkKeyboardColor.SECONDARY)
        keyboard.add_button("📞 Контакты", color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button("✅ Статус заявки", color=VkKeyboardColor.PRIMARY)
        return keyboard

    def get_shift_keyboard(self):
        """Клавиатура выбора смены"""
        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button("🌅 Дневная", color=VkKeyboardColor.PRIMARY)
        keyboard.add_button("🌙 Вечерняя", color=VkKeyboardColor.PRIMARY)
        return keyboard

    def get_lessons_keyboard(self):
        """Клавиатура выбора количества занятий"""
        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button("1 раз в неделю", color=VkKeyboardColor.SECONDARY)
        keyboard.add_button("2 раза в неделю", color=VkKeyboardColor.PRIMARY)
        keyboard.add_button("3 раза в неделю", color=VkKeyboardColor.SECONDARY)
        return keyboard

    def get_confirm_keyboard(self):
        """Клавиатура подтверждения"""
        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button("✅ Да", color=VkKeyboardColor.POSITIVE)
        keyboard.add_button("❌ Нет", color=VkKeyboardColor.NEGATIVE)
        return keyboard

    def handle_start(self, user_id):
        """Обработка команды /start или Начать"""
        welcome_text = (
            "🏊‍♂️ *Добро пожаловать в Школу плавания!* 🏊‍♀️\n\n"
            "Я помогу вам записать ребёнка в нашу школу.\n\n"
            "📌 *Что я умею:*\n"
            "• Подать заявку на обучение\n"
            "• Рассказать о школе\n"
            "• Показать контакты\n"
            "• Проверить статус заявки\n\n"
            "Выберите действие в меню ниже 👇"
        )
        keyboard = self.get_main_keyboard()
        self.send_message(user_id, welcome_text, keyboard)

    def handle_about(self, user_id):
        """Информация о школе"""
        about_text = (
            "🏊 *О нашей школе плавания*\n\n"
            "Мы обучаем детей плаванию с 2010 года. "
            "Наши тренеры - профессионалы с многолетним опытом.\n\n"
            "✨ *Преимущества:*\n"
            "• Современный бассейн с 4 дорожками\n"
            "• Индивидуальный подход к каждому ребёнку\n"
            "• Гибкое расписание (дневные и вечерние группы)\n"
            "• Доступные цены\n"
            "• Спортивные мероприятия и соревнования\n\n"
            "📚 *Группы:*\n"
            "• Дельфинчики (3-5 лет) - начальная подготовка\n"
            "• Рыбки (6-8 лет) - обучение плаванию\n"
            "• Спортивная (9-12 лет) - совершенствование техники\n"
            "• Продвинутая (13-17 лет) - спортивное плавание\n\n"
            "Чтобы подать заявку, нажмите кнопку '📝 Подать заявку'"
        )
        keyboard = self.get_main_keyboard()
        self.send_message(user_id, about_text, keyboard)

    def handle_contacts(self, user_id):
        """Контакты школы"""
        contacts_text = (
            "📞 *Наши контакты*\n\n"
            "🏢 *Адрес:* г. Москва, ул. Спортивная, д. 10\n"
            "📱 *Телефон:* +7 (495) 123-45-67\n"
            "✉️ *Email:* swim@school.ru\n"
            "🌐 *Сайт:* swim-school.ru\n\n"
            "⏰ *Часы работы:*\n"
            "Пн-Пт: 9:00 - 21:00\n"
            "Сб-Вс: 10:00 - 18:00\n\n"
            "Администратор ответит на все ваши вопросы!"
        )
        keyboard = self.get_main_keyboard()
        self.send_message(user_id, contacts_text, keyboard)

    def start_application(self, user_id):
        """Начало процесса подачи заявки"""
        self.user_states[user_id] = self.STATE_WAITING_NAME
        self.user_data[user_id] = {}

        msg = (
            "📝 *Подача заявки на обучение*\n\n"
            "Для записи ребёнка в школу плавания, пожалуйста, "
            "ответьте на несколько вопросов.\n\n"
            "✏️ *Введите ваше полное имя:*\n"
            "(Фамилия Имя Отчество)"
        )
        self.send_message(user_id, msg)

    def validate_name(self, name):
        """Валидация имени"""
        return len(name.strip()) >= 3 and re.match(r'^[А-Яа-я\s-]+$', name) is not None

    def validate_phone(self, phone):
        """Валидация телефона"""
        phone_clean = re.sub(r'[\s\-\(\)]', '', phone)
        return len(phone_clean) >= 10 and phone_clean.isdigit()

    def validate_email(self, email):
        """Валидация email"""
        if not email or email.lower() in ['нет', '-', 'skip']:
            return True
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def validate_age(self, age):
        """Валидация возраста"""
        try:
            age_int = int(age)
            return 3 <= age_int <= 17
        except ValueError:
            return False

    def process_application(self, user_id, db_cursor):
        """Обработка и сохранение заявки в БД"""
        data = self.user_data[user_id]

        try:
            # Сохраняем заявку в базу данных
            db_cursor.execute(
                """
                INSERT INTO applications 
                (parent_full_name, parent_phone, parent_email, child_full_name, 
                 child_age, school_name, shift, desired_lessons_per_week, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new')
                """,
                (
                    data['parent_name'],
                    data['parent_phone'],
                    data.get('parent_email'),
                    data['child_name'],
                    data['child_age'],
                    data.get('school', 'Не указана'),
                    data['shift'],
                    data['lessons']
                )
            )
            db_cursor.connection.commit()

            # Отправляем подтверждение
            confirm_text = (
                "✅ *Заявка успешно отправлена!*\n\n"
                f"📌 *Данные заявки:*\n"
                f"Родитель: {data['parent_name']}\n"
                f"Телефон: {data['parent_phone']}\n"
                f"Email: {data.get('parent_email', 'Не указан')}\n"
                f"Ребёнок: {data['child_name']}\n"
                f"Возраст: {data['child_age']} лет\n"
                f"Смена: {'Дневная' if data['shift'] == 'day' else 'Вечерняя'}\n"
                f"Занятий в неделю: {data['lessons']}\n\n"
                "Наш администратор свяжется с вами в ближайшее время!\n"
                "Спасибо, что выбрали нашу школу! 🏊‍♂️"
            )
            keyboard = self.get_main_keyboard()
            self.send_message(user_id, confirm_text, keyboard)

            # Очищаем состояние
            del self.user_states[user_id]
            del self.user_data[user_id]

            return True

        except Exception as e:
            logger.error(f"Ошибка сохранения заявки: {e}")
            error_text = (
                "❌ *Произошла ошибка при отправке заявки*\n\n"
                "Пожалуйста, попробуйте позже или свяжитесь с нами по телефону."
            )
            self.send_message(user_id, error_text)
            return False

    def check_application_status(self, user_id, db_cursor):
        """Проверка статуса заявки по телефону"""
        self.user_states[user_id] = self.STATE_WAITING_PHONE
        msg = (
            "🔍 *Проверка статуса заявки*\n\n"
            "Пожалуйста, введите номер телефона, который вы указали при подаче заявки:\n"
            "(в формате 79123456789)"
        )
        self.send_message(user_id, msg)

    def show_application_status(self, user_id, phone, db_cursor):
        """Показать статус заявки"""
        try:
            db_cursor.execute(
                """
                SELECT parent_full_name, child_full_name, child_age, status, 
                       created_at, processed_at, rejection_reason
                FROM applications
                WHERE parent_phone = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (phone,)
            )
            app = db_cursor.fetchone()

            if app:
                status_emoji = {
                    'new': '🟡',
                    'processing': '🟠',
                    'approved': '🟢',
                    'rejected': '🔴'
                }

                status_text = {
                    'new': 'Новая (ожидает обработки)',
                    'processing': 'В обработке',
                    'approved': 'Одобрена ✅',
                    'rejected': 'Отклонена ❌'
                }

                msg = (
                    f"📋 *Статус вашей заявки*\n\n"
                    f"{status_emoji.get(app['status'], '⚪')} *Статус:* {status_text.get(app['status'], app['status'])}\n"
                    f"👤 *Родитель:* {app['parent_full_name']}\n"
                    f"👶 *Ребёнок:* {app['child_full_name']} ({app['child_age']} лет)\n"
                    f"📅 *Дата подачи:* {app['created_at'][:10]}\n"
                )

                if app['processed_at']:
                    msg += f"🕐 *Дата обработки:* {app['processed_at'][:10]}\n"

                if app['rejection_reason'] and app['status'] == 'rejected':
                    msg += f"\n❌ *Причина отказа:* {app['rejection_reason']}\n"

                if app['status'] == 'approved':
                    msg += (
                        "\n✅ *Ваша заявка одобрена!*\n"
                        "Наш администратор свяжется с вами для уточнения деталей."
                    )

                self.send_message(user_id, msg, self.get_main_keyboard())
            else:
                msg = (
                    "❌ *Заявка не найдена*\n\n"
                    "Заявка с таким номером телефона не найдена.\n"
                    "Возможно, вы ещё не подавали заявку или указали другой номер.\n\n"
                    "Чтобы подать заявку, нажмите кнопку '📝 Подать заявку'"
                )
                self.send_message(user_id, msg, self.get_main_keyboard())

            # Очищаем состояние
            if user_id in self.user_states:
                del self.user_states[user_id]

        except Exception as e:
            logger.error(f"Ошибка проверки статуса: {e}")
            self.send_message(user_id, "❌ Произошла ошибка. Попробуйте позже.")

    def run(self):
        """Запуск бота"""
        logger.info("🚀 VK Bot started successfully!")
        logger.info(f"Group ID: {VK_GROUP_ID}")

        for event in self.longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                user_id = event.object.message['from_id']
                message_text = event.object.message['text'].lower().strip()

                logger.info(f"New message from {user_id}: {message_text[:50]}")

                # Обработка с использованием контекстного менеджера БД
                with get_db_cursor() as db_cursor:
                    # Проверяем состояние пользователя
                    state = self.user_states.get(user_id, self.STATE_NONE)

                    # Команды
                    if message_text in ['/start', 'начать', 'старт', 'меню', 'привет']:
                        self.handle_start(user_id)
                        continue

                    if message_text in ['ℹ️ о школе', 'о школе', 'инфо', 'информация']:
                        self.handle_about(user_id)
                        continue

                    if message_text in ['📞 контакты', 'контакты', 'телефон', 'связь']:
                        self.handle_contacts(user_id)
                        continue

                    if message_text in ['📝 подать заявку', 'подать заявку', 'заявка', 'запись', 'записаться']:
                        self.start_application(user_id)
                        continue

                    if message_text in ['✅ статус заявки', 'статус заявки', 'статус', 'проверить']:
                        self.check_application_status(user_id, db_cursor)
                        continue

                    # Обработка диалога подачи заявки
                    if state != self.STATE_NONE:
                        if state == self.STATE_WAITING_NAME:
                            if self.validate_name(message_text):
                                self.user_data[user_id]['parent_name'] = message_text.strip()
                                self.user_states[user_id] = self.STATE_WAITING_PHONE
                                msg = "📱 *Введите ваш номер телефона:*\n(например: 79123456789)"
                                self.send_message(user_id, msg)
                            else:
                                msg = "❌ *Некорректное имя*\n\nПожалуйста, введите полное имя (Фамилия Имя Отчество) кириллицей:"
                                self.send_message(user_id, msg)

                        elif state == self.STATE_WAITING_PHONE:
                            phone_clean = re.sub(r'[\s\-\(\)]', '', message_text)
                            if self.validate_phone(phone_clean):
                                self.user_data[user_id]['parent_phone'] = phone_clean
                                self.user_states[user_id] = self.STATE_WAITING_EMAIL
                                msg = "✉️ *Введите email:*\n(или напишите 'нет', если не хотите указывать)"
                                self.send_message(user_id, msg)
                            else:
                                msg = "❌ *Некорректный номер телефона*\n\nПожалуйста, введите номер в формате: 79123456789"
                                self.send_message(user_id, msg)

                        elif state == self.STATE_WAITING_EMAIL:
                            if message_text.lower() in ['нет', '-', 'skip']:
                                self.user_data[user_id]['parent_email'] = None
                                self.user_states[user_id] = self.STATE_WAITING_CHILD_NAME
                                msg = "👶 *Введите полное имя ребёнка:*"
                                self.send_message(user_id, msg)
                            elif self.validate_email(message_text):
                                self.user_data[user_id]['parent_email'] = message_text
                                self.user_states[user_id] = self.STATE_WAITING_CHILD_NAME
                                msg = "👶 *Введите полное имя ребёнка:*"
                                self.send_message(user_id, msg)
                            else:
                                msg = "❌ *Некорректный email*\n\nПожалуйста, введите корректный email или напишите 'нет':"
                                self.send_message(user_id, msg)

                        elif state == self.STATE_WAITING_CHILD_NAME:
                            if len(message_text.strip()) >= 2:
                                self.user_data[user_id]['child_name'] = message_text.strip()
                                self.user_states[user_id] = self.STATE_WAITING_CHILD_AGE
                                msg = "🎂 *Введите возраст ребёнка (от 3 до 17 лет):*"
                                self.send_message(user_id, msg)
                            else:
                                msg = "❌ *Некорректное имя*\n\nПожалуйста, введите полное имя ребёнка:"
                                self.send_message(user_id, msg)

                        elif state == self.STATE_WAITING_CHILD_AGE:
                            if self.validate_age(message_text):
                                self.user_data[user_id]['child_age'] = int(message_text)
                                self.user_states[user_id] = self.STATE_WAITING_SCHOOL
                                msg = "🏫 *Введите название школы или детского сада:*\n(или напишите 'нет')"
                                self.send_message(user_id, msg)
                            else:
                                msg = "❌ *Некорректный возраст*\n\nВозраст должен быть от 3 до 17 лет. Повторите ввод:"
                                self.send_message(user_id, msg)

                        elif state == self.STATE_WAITING_SCHOOL:
                            school = message_text if message_text.lower() != 'нет' else 'Не указана'
                            self.user_data[user_id]['school'] = school
                            self.user_states[user_id] = self.STATE_WAITING_SHIFT
                            msg = "⏰ *Выберите предпочтительную смену занятий:*"
                            keyboard = self.get_shift_keyboard()
                            self.send_message(user_id, msg, keyboard)

                        elif state == self.STATE_WAITING_SHIFT:
                            shift_map = {
                                '🌅 дневная': 'day',
                                'дневная': 'day',
                                '🌙 вечерняя': 'evening',
                                'вечерняя': 'evening'
                            }

                            shift = shift_map.get(message_text)
                            if shift:
                                self.user_data[user_id]['shift'] = shift
                                self.user_states[user_id] = self.STATE_WAITING_LESSONS
                                msg = "📅 *Выберите желаемое количество занятий в неделю:*"
                                keyboard = self.get_lessons_keyboard()
                                self.send_message(user_id, msg, keyboard)
                            else:
                                msg = "❌ Пожалуйста, выберите смену из предложенных вариантов:"
                                keyboard = self.get_shift_keyboard()
                                self.send_message(user_id, msg, keyboard)

                        elif state == self.STATE_WAITING_LESSONS:
                            lessons_map = {
                                '1 раз в неделю': 1,
                                '1': 1,
                                '2 раза в неделю': 2,
                                '2': 2,
                                '3 раза в неделю': 3,
                                '3': 3
                            }

                            lessons = lessons_map.get(message_text)
                            if lessons:
                                self.user_data[user_id]['lessons'] = lessons
                                self.user_states[user_id] = self.STATE_WAITING_CONFIRM

                                # Показываем данные для подтверждения
                                data = self.user_data[user_id]
                                confirm_text = (
                                    "📋 *Проверьте данные заявки:*\n\n"
                                    f"👤 Родитель: {data['parent_name']}\n"
                                    f"📱 Телефон: {data['parent_phone']}\n"
                                    f"✉️ Email: {data.get('parent_email', 'Не указан')}\n"
                                    f"👶 Ребёнок: {data['child_name']}\n"
                                    f"🎂 Возраст: {data['child_age']} лет\n"
                                    f"🏫 Школа: {data['school']}\n"
                                    f"⏰ Смена: {'Дневная' if data['shift'] == 'day' else 'Вечерняя'}\n"
                                    f"📅 Занятий в неделю: {data['lessons']}\n\n"
                                    "✅ *Всё верно?*\n"
                                    "Нажмите 'Да' для подтверждения или 'Нет' для отмены."
                                )
                                keyboard = self.get_confirm_keyboard()
                                self.send_message(user_id, confirm_text, keyboard)
                            else:
                                msg = "❌ Пожалуйста, выберите количество занятий из предложенных вариантов:"
                                keyboard = self.get_lessons_keyboard()
                                self.send_message(user_id, msg, keyboard)

                        elif state == self.STATE_WAITING_CONFIRM:
                            if message_text in ['✅ да', 'да', 'yes', 'да, всё верно', '+']:
                                self.process_application(user_id, db_cursor)
                            elif message_text in ['❌ нет', 'нет', 'no', '-']:
                                self.user_states[user_id] = self.STATE_NONE
                                self.user_data[user_id] = {}
                                msg = "❌ *Заявка отменена*\n\nВы можете начать заново, нажав кнопку '📝 Подать заявку'"
                                self.send_message(user_id, msg, self.get_main_keyboard())
                            else:
                                msg = "Пожалуйста, подтвердите или отмените заявку (Да/Нет):"
                                keyboard = self.get_confirm_keyboard()
                                self.send_message(user_id, msg, keyboard)
                    else:
                        # Если сообщение не распознано
                        msg = (
                            "🤔 *Не понял вас*\n\n"
                            "Пожалуйста, используйте кнопки меню для навигации:\n"
                            "• 📝 Подать заявку\n"
                            "• ℹ️ О школе\n"
                            "• 📞 Контакты\n"
                            "• ✅ Статус заявки\n\n"
                            "Или напишите /start для показа меню"
                        )
                        self.send_message(user_id, msg, self.get_main_keyboard())


def run_bot():
    """Запуск VK бота"""
    try:
        bot = VKBot()
        bot.run()
    except ApiError as e:
        logger.error(f"VK API Error: {e}")
        logger.error("Проверьте настройки токена и прав доступа!")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise


if __name__ == "__main__":
    run_bot()