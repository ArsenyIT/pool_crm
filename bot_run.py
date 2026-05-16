# bot_run.py
import sys
import logging
import signal
import time
from vk_bot import VKBot, run_bot

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vk_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения"""
    logger.info("Received signal to terminate...")
    logger.info("VK Bot is shutting down...")
    sys.exit(0)


def main():
    """Главная функция запуска бота"""
    logger.info("=" * 50)
    logger.info("Starting VK Bot for Swim CRM")
    logger.info("=" * 50)

    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Запускаем бота
        logger.info("Initializing VK Bot...")
        run_bot()

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")

    except Exception as e:
        logger.error(f"Critical error: {e}")
        logger.exception("Full traceback:")
        sys.exit(1)


def run_bot_with_reconnect():
    """Запуск бота с автоматическим переподключением при ошибках"""
    max_retries = 5
    retry_delay = 10

    for attempt in range(max_retries):
        try:
            logger.info(f"Starting bot (attempt {attempt + 1}/{max_retries})")
            main()

        except Exception as e:
            logger.error(f"Bot crashed: {e}")

            if attempt < max_retries - 1:
                logger.info(f"Restarting in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Экспоненциальная задержка
            else:
                logger.error("Max retries reached. Bot stopped.")
                sys.exit(1)


if __name__ == "__main__":
    run_bot_with_reconnect()