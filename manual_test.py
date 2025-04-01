import os
import asyncio
from dotenv import load_dotenv
from telegram import Bot
from database import init_db, User, UserPreferences, WeeklyPoll, PollResponse

# Загрузка переменных окружения
load_dotenv()

# Инициализация базы данных
db = init_db()


async def test_bot():
    """Функция для ручного тестирования бота"""
    # Получаем токен бота
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("Ошибка: Не найден токен бота в файле .env")
        return

    # Создаем экземпляр бота
    bot = Bot(token=token)

    try:
        # Получаем информацию о боте
        bot_info = await bot.get_me()
        print(f"Бот успешно подключен: @{bot_info.username}")

        # Проверяем базу данных
        print("\nПроверка базы данных:")
        users_count = db.query(User).count()
        print(f"Количество пользователей: {users_count}")

        # Проверяем активные опросы
        active_polls = db.query(WeeklyPoll).filter(
            WeeklyPoll.status == 'active').all()
        print(f"Активные опросы: {len(active_polls)}")

        # Проверяем предпочтения пользователей
        preferences_count = db.query(UserPreferences).count()
        print(f"Настроенные предпочтения: {preferences_count}")

        # Отправляем тестовое сообщение
        print("\nОтправка тестового сообщения...")
        await bot.send_message(
            chat_id=os.getenv('GROUP_CHAT_ID'),
            text="🤖 Тестовое сообщение от бота\n\nБот успешно подключен и готов к работе!"
        )
        print("Тестовое сообщение отправлено")

        # Проверяем команды бота
        print("\nПроверка команд бота:")
        commands = await bot.get_my_commands()
        for command in commands:
            print(f"- /{command.command}: {command.description}")

    except Exception as e:
        print(f"Ошибка при тестировании: {e}")
    finally:
        await bot.close()


def main():
    """Запуск тестирования"""
    print("Начинаем тестирование бота...")
    asyncio.run(test_bot())
    print("\nТестирование завершено")


if __name__ == '__main__':
    main()
