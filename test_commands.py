import os
from dotenv import load_dotenv
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Загрузка переменных окружения
load_dotenv()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    keyboard = [
        [
            InlineKeyboardButton("👤 Профиль", callback_data='profile'),
            InlineKeyboardButton("⚙️ Настройки", callback_data='settings')
        ],
        [
            InlineKeyboardButton("📊 Статистика", callback_data='stats'),
            InlineKeyboardButton("❓ FAQ", callback_data='faq')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Привет! Я бот Random Coffee. Я помогу вам организовать случайные встречи за кофе.",
        reply_markup=reply_markup
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()

    if query.data == 'profile':
        await query.message.reply_text("👤 Ваш профиль:\n\nПока что пустой")
    elif query.data == 'settings':
        await query.message.reply_text("⚙️ Настройки:\n\nПока что пустые")
    elif query.data == 'stats':
        await query.message.reply_text("📊 Статистика:\n\nПока что пустая")
    elif query.data == 'faq':
        await query.message.reply_text("❓ Часто задаваемые вопросы:\n\n1. Как это работает?\n2. Как зарегистрироваться?\n3. Как отменить встречу?")


def main():
    """Запуск бота"""
    # Получаем токен бота
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("Ошибка: Не найден токен бота в файле .env")
        return

    # Создаем приложение
    application = Application.builder().token(token).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Запускаем бота
    print("Бот запускается...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nБот остановлен пользователем")
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")
