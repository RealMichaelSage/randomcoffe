import os
from dotenv import load_dotenv
from telegram import Bot
import asyncio

# Загрузка переменных окружения
load_dotenv()


async def test_bot():
    # Получаем токен бота
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("Ошибка: Не найден токен бота в файле .env")
        return

    try:
        # Создаем экземпляр бота
        bot = Bot(token=token)

        # Получаем информацию о боте
        bot_info = await bot.get_me()
        print(f"Бот успешно подключен: @{bot_info.username}")

        # Отправляем тестовое сообщение
        await bot.send_message(
            chat_id=os.getenv('GROUP_CHAT_ID'),
            text="🤖 Тестовое сообщение от бота\n\nБот успешно подключен!"
        )
        print("Тестовое сообщение отправлено")

        # Проверяем обновления
        updates = await bot.get_updates()
        print(f"Получено обновлений: {len(updates)}")

    except Exception as e:
        print(f"Ошибка при тестировании: {e}")
    finally:
        await bot.close()

if __name__ == '__main__':
    asyncio.run(test_bot())
