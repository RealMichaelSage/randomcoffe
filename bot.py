import os
import logging
import random
import fcntl
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Poll, Bot, ReplyKeyboardMarkup, KeyboardButton, ChatMemberUpdated, Chat
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler, ChatMemberHandler, PollAnswerHandler
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from database import Base, User, UserPreferences, Meeting, Rating, WeeklyPoll, PollResponse, Chat, BotInstance
import uuid
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

# Загружаем переменные окружения из файла .env, если он существует
load_dotenv(override=True)

# Получаем переменные окружения
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")

# Настройка базы данных
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///random_coffee.db')

# Создаем движок базы данных
engine = create_engine(DATABASE_URL)

# Создаем все таблицы
Base.metadata.create_all(engine)

# Создаем фабрику сессий
Session = sessionmaker(bind=engine)


def get_session():
    """Создает и возвращает новую сессию базы данных"""
    session = Session()
    try:
        yield session
    finally:
        session.close()


# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot restart - 2024-04-01 - Fix database initialization and user handling

# Состояния регистрации
(
    ENTER_NAME,
    ENTER_CITY,
    ENTER_SOCIAL_LINK,
    ENTER_ABOUT,
    ENTER_JOB,
    ENTER_BIRTH_DATE,
    ENTER_AVATAR,
    ENTER_HOBBIES,
    # Состояния настроек
    SETTINGS_CITY,
    SETTINGS_SOCIAL_LINK,
    SETTINGS_ABOUT,
    SETTINGS_JOB,
    SETTINGS_BIRTH_DATE,
    SETTINGS_AVATAR,
    SETTINGS_HOBBIES,
    SETTINGS_VISIBILITY
) = range(16)

# Словарь для хранения состояний пользователей
user_states = {}

# Словарь для хранения активных встреч
active_meetings = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start"""
    chat = update.effective_chat
    session = next(get_session())

    try:
        # Проверяем, есть ли чат в базе данных
        db_chat = session.query(Chat).filter_by(chat_id=chat.id).first()
        if not db_chat:
            # Создаем новую запись о чате
            db_chat = Chat(
                chat_id=chat.id,
                title=chat.title or str(chat.id),
                is_active=True,
                joined_at=datetime.utcnow()
            )
            session.add(db_chat)
            session.commit()

            keyboard = [
                [
                    InlineKeyboardButton(
                        "👤 Регистрация", callback_data='register'),
                    InlineKeyboardButton(
                        "⚙️ Настройки", callback_data='settings')
                ],
                [
                    InlineKeyboardButton(
                        "📊 Статистика", callback_data='stats'),
                    InlineKeyboardButton("❓ FAQ", callback_data='faq')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "Привет! Я бот для случайных кофе-встреч. "
                "Я помогу организовать неформальные встречи между участниками чата. "
                "Каждую неделю я буду отправлять опрос, чтобы узнать, кто хочет участвовать "
                "во встречах на следующей неделе.\n\n"
                "Основные команды:\n"
                "/help - показать справку\n"
                "/stats - показать статистику\n"
                "/settings - настроить предпочтения",
                reply_markup=reply_markup
            )
        else:
            keyboard = [
                [
                    InlineKeyboardButton("👤 Профиль", callback_data='profile'),
                    InlineKeyboardButton(
                        "⚙️ Настройки", callback_data='settings')
                ],
                [
                    InlineKeyboardButton(
                        "📊 Статистика", callback_data='stats'),
                    InlineKeyboardButton("❓ FAQ", callback_data='faq')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "Я уже работаю в этом чате! Используйте кнопки ниже для навигации:",
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text("Произошла ошибка при регистрации чата.")
    finally:
        session.close()


async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало регистрации"""
    query = update.callback_query
    await query.answer()

    session = next(get_session())
    try:
        # Проверяем, не зарегистрирован ли уже пользователь
        existing_user = session.query(User).filter(
            User.telegram_id == query.from_user.id).first()

        if existing_user:
            keyboard = [
                [
                    InlineKeyboardButton("👤 Профиль", callback_data='profile'),
                    InlineKeyboardButton(
                        "⚙️ Настройки", callback_data='settings')
                ],
                [
                    InlineKeyboardButton(
                        "📊 Статистика", callback_data='stats'),
                    InlineKeyboardButton("❓ FAQ", callback_data='faq')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.message.reply_text(
                "Вы уже зарегистрированы! Используйте кнопки ниже для управления профилем:",
                reply_markup=reply_markup
            )
            return ConversationHandler.END

        await query.message.reply_text(
            "Давайте начнем регистрацию!\n"
            "Как вас зовут? (Введите ваше имя)"
        )
        return ENTER_NAME
    except Exception as e:
        logger.error(f"Error in register: {e}")
        await query.message.reply_text("Произошла ошибка при начале регистрации.")
        return ConversationHandler.END
    finally:
        session.close()


async def enter_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода имени"""
    try:
        # Сохраняем имя в контексте пользователя
        context.user_data['name'] = update.message.text

        # Отправляем сообщение с запросом города
        await update.message.reply_text(
            "Отлично! В каком городе вы живете?"
        )
        return ENTER_CITY
    except Exception as e:
        logger.error(f"Error in enter_name: {e}")
        await update.message.reply_text(
            "Произошла ошибка при обработке имени. Пожалуйста, попробуйте еще раз."
        )
        return ENTER_NAME


async def enter_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода города"""
    try:
        # Сохраняем город в контексте пользователя
        context.user_data['city'] = update.message.text

        # Отправляем сообщение с запросом социальной сети
        await update.message.reply_text(
            "Укажите ссылку на вашу социальную сеть (например, VK, Instagram, LinkedIn):"
        )
        return ENTER_SOCIAL_LINK
    except Exception as e:
        logger.error(f"Error in enter_city: {e}")
        await update.message.reply_text(
            "Произошла ошибка при обработке города. Пожалуйста, попробуйте еще раз."
        )
        return ENTER_CITY


async def enter_social_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода ссылки на соц.сеть"""
    try:
        # Сохраняем ссылку в контексте пользователя
        context.user_data['social_link'] = update.message.text

        # Отправляем сообщение с запросом информации о себе
        await update.message.reply_text(
            "Расскажите немного о себе:"
        )
        return ENTER_ABOUT
    except Exception as e:
        logger.error(f"Error in enter_social_link: {e}")
        await update.message.reply_text(
            "Произошла ошибка при обработке ссылки. Пожалуйста, попробуйте еще раз."
        )
        return ENTER_SOCIAL_LINK


async def enter_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода информации о себе"""
    try:
        # Сохраняем информацию о себе в контексте пользователя
        context.user_data['about'] = update.message.text

        # Отправляем сообщение с запросом места работы
        await update.message.reply_text(
            "Кем вы работаете?"
        )
        return ENTER_JOB
    except Exception as e:
        logger.error(f"Error in enter_about: {e}")
        await update.message.reply_text(
            "Произошла ошибка при обработке информации. Пожалуйста, попробуйте еще раз."
        )
        return ENTER_ABOUT


async def enter_job(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода профессии"""
    try:
        # Сохраняем профессию в контексте пользователя
        context.user_data['job'] = update.message.text

        # Отправляем сообщение с запросом даты рождения
        await update.message.reply_text(
            "Укажите вашу дату рождения (в формате ДД.ММ.ГГГГ):"
        )
        return ENTER_BIRTH_DATE
    except Exception as e:
        logger.error(f"Error in enter_job: {e}")
        await update.message.reply_text(
            "Произошла ошибка при обработке профессии. Пожалуйста, попробуйте еще раз."
        )
        return ENTER_JOB


async def enter_birth_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода даты рождения"""
    try:
        # Парсим дату рождения
        birth_date = datetime.strptime(update.message.text, "%d.%m.%Y")

        # Сохраняем дату рождения в контексте пользователя
        context.user_data['birth_date'] = birth_date

        # Отправляем сообщение с запросом аватара
        await update.message.reply_text(
            "Отправьте ваше фото для аватара:"
        )
        return ENTER_AVATAR
    except ValueError:
        await update.message.reply_text(
            "Пожалуйста, введите дату в правильном формате (ДД.ММ.ГГГГ):"
        )
        return ENTER_BIRTH_DATE
    except Exception as e:
        logger.error(f"Error in enter_birth_date: {e}")
        await update.message.reply_text(
            "Произошла ошибка при обработке даты рождения. Пожалуйста, попробуйте еще раз."
        )
        return ENTER_BIRTH_DATE


async def enter_avatar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка загрузки аватара"""
    try:
        if update.message.photo:
            # Берем последнее (самое качественное) фото
            photo = update.message.photo[-1]

            # Сохраняем ID фото в контексте пользователя
            context.user_data['avatar'] = photo.file_id

            # Отправляем сообщение с запросом хобби
            await update.message.reply_text(
                "Отлично! Теперь расскажите о ваших хобби и интересах:"
            )
            return ENTER_HOBBIES
        else:
            await update.message.reply_text(
                "Пожалуйста, отправьте фотографию:"
            )
            return ENTER_AVATAR
    except Exception as e:
        logger.error(f"Error in enter_avatar: {e}")
        await update.message.reply_text(
            "Произошла ошибка при обработке фото. Пожалуйста, попробуйте еще раз."
        )
        return ENTER_AVATAR


async def enter_hobbies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершение регистрации"""
    try:
        # Сохраняем хобби в контексте пользователя
        context.user_data['hobbies'] = update.message.text

        # Создаем нового пользователя
        user = User(
            telegram_id=update.effective_user.id,
            username=update.effective_user.username,
            nickname=context.user_data['name'],
            city=context.user_data['city'],
            social_link=context.user_data['social_link'],
            about=context.user_data['about'],
            job=context.user_data['job'],
            birth_date=context.user_data['birth_date'],
            avatar=context.user_data['avatar'],
            hobbies=context.user_data['hobbies'],
            created_at=datetime.utcnow()
        )

        # Сохраняем пользователя в базу данных
        session = next(get_session())
        try:
            session.add(user)
            session.commit()
        finally:
            session.close()

        # Формируем текст профиля
        profile_text = (
            "✅ Регистрация завершена! Ваш профиль:\n\n"
            f"👤 Имя: {context.user_data['name']}\n"
            f"🏙 Город: {context.user_data['city']}\n"
            f"🔗 Соц.сеть: {context.user_data['social_link']}\n"
            f"ℹ️ О себе: {context.user_data['about']}\n"
            f"💼 Работа: {context.user_data['job']}\n"
            f"📅 Дата рождения: {context.user_data['birth_date'].strftime('%d.%m.%Y')}\n"
            f"🎯 Хобби: {context.user_data['hobbies']}"
        )

        # Создаем клавиатуру
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

        # Отправляем аватар с профилем
        if context.user_data.get('avatar'):
            await update.message.reply_photo(
                photo=context.user_data['avatar'],
                caption=profile_text,
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(profile_text, reply_markup=reply_markup)

        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in enter_hobbies: {e}")
        await update.message.reply_text(
            "Произошла ошибка при сохранении профиля. Пожалуйста, попробуйте еще раз."
        )
        return ENTER_HOBBIES


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    session = next(get_session())

    try:
        if query.data == 'register':
            await register(update, context)
        elif query.data == 'profile':
            # Получаем профиль из базы данных
            user = session.query(User).filter(
                User.telegram_id == query.from_user.id).first()
            if user:
                profile_text = (
                    "👤 Ваш профиль:\n\n"
                    f"👤 Имя: {user.nickname}\n"
                    f"🏙 Город: {user.city or 'Не указан'}\n"
                    f"🔗 Соц.сеть: {user.social_link or 'Не указана'}\n"
                    f"ℹ️ О себе: {user.about or 'Не указано'}\n"
                    f"💼 Работа: {user.job or 'Не указана'}\n"
                    f"📅 Дата рождения: {user.birth_date.strftime('%d.%m.%Y') if user.birth_date else 'Не указана'}\n"
                    f"🎯 Хобби: {user.hobbies or 'Не указаны'}\n"
                    f"👁 Видимость: {'Публичный' if user.is_visible else 'Приватный'}\n"
                    f"📆 Дата регистрации: {user.created_at.strftime('%d.%m.%Y')}"
                )
            else:
                profile_text = "👤 Ваш профиль:\n\nПрофиль не найден. Пожалуйста, зарегистрируйтесь."

            await query.message.reply_text(profile_text)
        elif query.data == 'settings':
            await settings(update, context)
        elif query.data.startswith('set_'):
            # получаем тип настройки (gender, age, language и т.д.)
            setting_type = query.data[4:]
            await handle_settings(update, context, setting_type)
        elif query.data == 'reset_settings':
            await reset_settings(update, context)
        elif query.data == 'stats':
            await stats(update, context)
    except Exception as e:
        logger.error(f"Error in button_handler: {e}")
        await query.message.reply_text("Произошла ошибка при обработке запроса.")


async def create_weekly_poll(context: ContextTypes.DEFAULT_TYPE):
    """Создает еженедельный опрос"""
    session = next(get_session())
    try:
        # Получаем все активные чаты
        active_chats = session.query(Chat).filter_by(is_active=True).all()

        for chat in active_chats:
            # Создаем новый опрос для этого чата
            week_start = datetime.utcnow()
            week_end = week_start + timedelta(days=7)

            poll = WeeklyPoll(
                chat_id=chat.id,
                week_start=week_start,
                week_end=week_end,
                status='active',
                created_at=datetime.utcnow()
            )
            session.add(poll)
            session.commit()

            # Отправляем опрос в чат
            message = await context.bot.send_poll(
                chat_id=chat.chat_id,
                question="Привет! Будете участвовать во встречах Random Coffee на следующей неделе? ☕️",
                options=["Да", "Нет"],
                is_anonymous=False
            )

            # Сохраняем ID сообщения
            poll.message_id = message.message_id
            session.commit()
    except Exception as e:
        logger.error(f"Error sending poll to chat: {e}")


async def distribute_pairs(context: ContextTypes.DEFAULT_TYPE):
    """Распределяет пары для встреч"""
    session = next(get_session())
    try:
        # Получаем все активные чаты
        active_chats = session.query(Chat).filter_by(is_active=True).all()

        for chat in active_chats:
            # Получаем последний опрос для этого чата
            latest_poll = session.query(WeeklyPoll)\
                .filter_by(chat_id=chat.id)\
                .order_by(WeeklyPoll.created_at.desc())\
                .first()

            if not latest_poll:
                continue

            # Получаем положительные ответы
            positive_responses = session.query(PollResponse)\
                .filter_by(poll_id=latest_poll.id, response=True)\
                .all()

            # Получаем ID пользователей, готовых к встрече
            user_ids = [response.user_id for response in positive_responses]

            if len(user_ids) < 2:
                await context.bot.send_message(
                    chat_id=chat.chat_id,
                    text="Недостаточно участников для создания пар на этой неделе."
                )
                continue

            # Получаем историю встреч
            past_meetings = session.query(Meeting)\
                .filter(Meeting.user1_id.in_(user_ids))\
                .filter(Meeting.user2_id.in_(user_ids))\
                .all()

            # Создаем словарь прошлых встреч
            meeting_history = {}
            for meeting in past_meetings:
                for user_id in [meeting.user1_id, meeting.user2_id]:
                    if user_id not in meeting_history:
                        meeting_history[user_id] = set()
                    meeting_history[user_id].add(
                        meeting.user2_id if user_id == meeting.user1_id else meeting.user1_id)

            # Создаем пары
            pairs = create_pairs(user_ids, meeting_history)

            # Сохраняем пары и формируем сообщение
            message = await save_pairs_and_create_message(session, pairs, chat.chat_id)
            await context.bot.send_message(chat_id=chat.chat_id, text=message, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error creating pairs for chat: {e}")
    finally:
        session.close()


def create_pairs(user_ids, meeting_history):
    """Создает пары пользователей с учетом истории встреч"""
    random.shuffle(user_ids)
    pairs = []
    unpaired = []
    used = set()

    for user1 in user_ids:
        if user1 in used:
            continue

        # Ищем подходящего партнера
        best_partner = None
        min_meetings = float('inf')

        for user2 in user_ids:
            if user2 == user1 or user2 in used:
                continue

            meetings_count = len(meeting_history.get(
                user1, set()).intersection({user2}))
            if meetings_count < min_meetings:
                min_meetings = meetings_count
                best_partner = user2
            if meetings_count == 0:
                break

        if best_partner:
            pairs.append((user1, best_partner))
            used.add(user1)
            used.add(best_partner)
        else:
            unpaired.append(user1)

    # Обрабатываем непарных пользователей
    if unpaired:
        if pairs:
            last_pair = list(pairs[-1])
            last_pair.extend(unpaired)
            pairs[-1] = tuple(last_pair)
        else:
            pairs.append(tuple(unpaired))

    return pairs


async def save_pairs_and_create_message(session, pairs, chat_id):
    """Сохраняет пары в базу данных и создает сообщение"""
    message = "🎉 Пары для встреч на следующую неделю:\n\n"

    for pair in pairs:
        # Получаем информацию о пользователях
        users = []
        for user_id in pair:
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                users.append(
                    f"@{user.username}" if user.username else f"[Пользователь](tg://user?id={user.telegram_id})")

        # Добавляем пару в сообщение
        message += "👥 " + " и ".join(users) + "\n"

        # Сохраняем встречи в базу данных
        if len(pair) == 2:
            user1, user2 = pair
            session.add(Meeting(
                user1_id=user1,
                user2_id=user2,
                scheduled_time=datetime.utcnow(),
                status='scheduled',
                created_at=datetime.utcnow()
            ))
        elif len(pair) >= 3:
            for i in range(len(pair)):
                for j in range(i + 1, len(pair)):
                    session.add(Meeting(
                        user1_id=pair[i],
                        user2_id=pair[j],
                        scheduled_time=datetime.utcnow(),
                        status='scheduled',
                        created_at=datetime.utcnow()
                    ))

    message += "\nПожалуйста, договоритесь о времени и формате встречи в личных сообщениях 😊"
    session.commit()
    return message


async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка входа в меню настроек"""
    query = update.callback_query
    await query.answer()

    session = next(get_session())
    try:
        # Проверяем, зарегистрирован ли пользователь
        user = session.query(User).filter(
            User.telegram_id == query.from_user.id).first()
        if not user:
            await query.message.reply_text("⚠️ Сначала нужно зарегистрироваться!")
            return ConversationHandler.END

        keyboard = [
            [
                InlineKeyboardButton("🏙 Город", callback_data='settings_city'),
                InlineKeyboardButton(
                    "🔗 Соц.сеть", callback_data='settings_social_link')
            ],
            [
                InlineKeyboardButton(
                    "ℹ️ О себе", callback_data='settings_about'),
                InlineKeyboardButton("💼 Работа", callback_data='settings_job')
            ],
            [
                InlineKeyboardButton(
                    "📅 Дата рождения", callback_data='settings_birth_date'),
                InlineKeyboardButton(
                    "🖼 Аватар", callback_data='settings_avatar')
            ],
            [
                InlineKeyboardButton(
                    "🎯 Хобби", callback_data='settings_hobbies'),
                InlineKeyboardButton(
                    "👁 Видимость", callback_data='settings_visibility')
            ],
            [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        settings_text = (
            "⚙️ Настройки профиля:\n\n"
            f"🏙 Город: {user.city or 'Не указан'}\n"
            f"🔗 Соц.сеть: {user.social_link or 'Не указана'}\n"
            f"ℹ️ О себе: {user.about or 'Не указано'}\n"
            f"💼 Работа: {user.job or 'Не указана'}\n"
            f"📅 Дата рождения: {user.birth_date.strftime('%d.%m.%Y') if user.birth_date else 'Не указана'}\n"
            f"🎯 Хобби: {user.hobbies or 'Не указаны'}\n"
            f"👁 Видимость: {'Публичный' if user.is_visible else 'Приватный'}"
        )

        await query.message.reply_text(settings_text, reply_markup=reply_markup)
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in settings: {e}")
        await query.message.reply_text("Произошла ошибка при открытии настроек.")
        return ConversationHandler.END
    finally:
        session.close()


async def update_visibility(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обновление видимости профиля"""
    query = update.callback_query
    await query.answer()

    session = next(get_session())
    try:
        user = session.query(User).filter(
            User.telegram_id == query.from_user.id).first()
        if not user:
            await query.message.reply_text("Произошла ошибка при получении данных пользователя.")
            return ConversationHandler.END

        visibility = query.data.split('_')[1]  # 'public' или 'private'
        user.is_visible = (visibility == 'public')
        session.commit()

        keyboard = [[InlineKeyboardButton(
            "◀️ Назад", callback_data='settings')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        visibility_text = "Публичный" if user.is_visible else "Приватный"
        await query.message.reply_text(
            f"✅ Видимость профиля изменена на: {visibility_text}",
            reply_markup=reply_markup
        )
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in update_visibility: {e}")
        await query.message.reply_text("Произошла ошибка при обновлении видимости профиля.")
        return ConversationHandler.END
    finally:
        session.close()


async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка ответов на опросы"""
    answer = update.poll_answer
    session = next(get_session())
    try:
        logger.info(
            f"Received poll answer from user {answer.user.id} for poll {answer.poll_id}")

        # Получаем пользователя и опрос
        user = session.query(User).filter(
            User.telegram_id == answer.user.id).first()
        poll = session.query(WeeklyPoll).filter(
            WeeklyPoll.message_id == answer.poll_id).first()

        if not poll:
            logger.warning(f"Poll not found: poll_id={answer.poll_id}")
            return

        # Получаем выбранный вариант ответа
        selected_option = answer.option_ids[0] if answer.option_ids else None
        if selected_option is None:
            logger.warning(
                f"No option selected in poll: poll_id={answer.poll_id}")
            return

        # Определяем ответ (Да/Нет)
        response = (selected_option == 0)  # True для "Да", False для "Нет"
        logger.info(
            f"User {answer.user.id} answered {'Yes' if response else 'No'}")

        # Если пользователь не найден, создаем запись о его ответе
        if not user:
            logger.info(
                f"Creating new user record for user_id={answer.user.id}")
            user = User(
                telegram_id=answer.user.id,
                username=answer.user.username,
                created_at=datetime.utcnow()
            )
            session.add(user)
            session.commit()
            logger.info(
                f"Created new user record for user_id={answer.user.id}")

        # Обновляем или создаем ответ
        existing_response = session.query(PollResponse).filter(
            PollResponse.poll_id == poll.id,
            PollResponse.user_id == user.id
        ).first()

        if existing_response:
            existing_response.response = response
            existing_response.created_at = datetime.utcnow()
            logger.info(
                f"Updated existing response for user {user.id} and poll {poll.id}")
        else:
            new_response = PollResponse(
                poll_id=poll.id,
                user_id=user.id,
                response=response,
                created_at=datetime.utcnow()
            )
            session.add(new_response)
            logger.info(
                f"Created new response for user {user.id} and poll {poll.id}")

        session.commit()

        # Если пользователь ответил "Да" и не зарегистрирован, предлагаем регистрацию
        if response and not user.nickname:
            logger.info(
                f"User {user.id} answered Yes but is not registered. Sending registration offer.")
            keyboard = [[InlineKeyboardButton(
                "👤 Регистрация", callback_data='register')]]
            try:
                await context.bot.send_message(
                    chat_id=answer.user.id,
                    text="Отлично! Для участия в Random Coffee нужно зарегистрироваться. "
                         "Нажмите кнопку ниже, чтобы начать регистрацию:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                logger.info(
                    f"Successfully sent registration offer to user {answer.user.id}")
            except Exception as e:
                logger.error(
                    f"Failed to send registration offer to user {answer.user.id}: {e}")

    except Exception as e:
        logger.error(f"Error in handle_poll_answer: {e}", exc_info=True)
    finally:
        session.close()


def get_next_monday(hour=10, minute=0):
    """Возвращает дату следующего понедельника"""
    now = datetime.now()
    days_ahead = 7 - now.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    next_monday = now + timedelta(days=days_ahead)
    return next_monday.replace(hour=hour, minute=minute, second=0, microsecond=0)


async def send_weekly_poll(context: ContextTypes.DEFAULT_TYPE):
    """Отправляет еженедельный опрос"""
    session = next(get_session())
    try:
        # Получаем все активные чаты
        active_chats = session.query(Chat).filter_by(is_active=True).all()

        for chat in active_chats:
            # Получаем последний опрос для этого чата
            latest_poll = session.query(WeeklyPoll)\
                .filter_by(chat_id=chat.id)\
                .order_by(WeeklyPoll.created_at.desc())\
                .first()

            if not latest_poll:
                continue

            # Получаем пользователей, которые ответили "Да"
            positive_responses = session.query(PollResponse)\
                .filter_by(poll_id=latest_poll.id, response=True)\
                .all()

            # Получаем ID пользователей, готовых к встрече
            user_ids = [response.user_id for response in positive_responses]

            if len(user_ids) < 2:
                await context.bot.send_message(
                    chat_id=chat.chat_id,
                    text="Недостаточно участников для создания пар на этой неделе."
                )
                continue

            # Получаем историю встреч
            past_meetings = session.query(Meeting)\
                .filter(Meeting.user1_id.in_(user_ids))\
                .filter(Meeting.user2_id.in_(user_ids))\
                .all()

            # Создаем словарь прошлых встреч
            meeting_history = {}
            for meeting in past_meetings:
                if meeting.user1_id not in meeting_history:
                    meeting_history[meeting.user1_id] = set()
                if meeting.user2_id not in meeting_history:
                    meeting_history[meeting.user2_id] = set()
                meeting_history[meeting.user1_id].add(meeting.user2_id)
                meeting_history[meeting.user2_id].add(meeting.user1_id)

            # Перемешиваем список пользователей
            random.shuffle(user_ids)

            # Создаем пары с учетом истории встреч
            pairs = []
            unpaired = []
            used = set()

            for user1 in user_ids:
                if user1 in used:
                    continue

                # Ищем подходящего партнера
                best_partner = None
                min_meetings = float('inf')

                for user2 in user_ids:
                    if user2 == user1 or user2 in used:
                        continue

                    # Проверяем историю встреч
                    meetings_count = len(meeting_history.get(
                        user1, set()).intersection({user2}))

                    if meetings_count < min_meetings:
                        min_meetings = meetings_count
                        best_partner = user2

                    # Если нашли пользователя, с которым встреч не было, сразу берем его
                    if meetings_count == 0:
                        break

                if best_partner:
                    pairs.append((user1, best_partner))
                    used.add(user1)
                    used.add(best_partner)
                else:
                    unpaired.append(user1)

            # Если остались непарные пользователи, добавляем их к последней паре или создаем новую
            if unpaired:
                if pairs:
                    # Если есть хотя бы одна пара, добавляем непарных к последней паре
                    last_pair = list(pairs[-1])
                    last_pair.extend(unpaired)
                    pairs[-1] = tuple(last_pair)
                else:
                    # Если пар нет совсем, создаем одну из оставшихся
                    pairs.append(tuple(unpaired))

            # Сохраняем пары в базу данных и отправляем сообщение
            message = "🎉 Пары для встреч на следующую неделю:\n\n"

            for pair in pairs:
                # Получаем информацию о пользователях
                users = []
                for user_id in pair:
                    user = session.query(User).filter_by(id=user_id).first()
                    if user:
                        if user.username:
                            users.append(f"@{user.username}")
                        else:
                            users.append(
                                f"[Пользователь](tg://user?id={user.telegram_id})")

                # Добавляем пару в сообщение
                message += "👥 " + " и ".join(users) + "\n"

                # Сохраняем встречу в базу данных
                if len(pair) == 2:
                    user1, user2 = pair
                    meeting = Meeting(
                        user1_id=user1,
                        user2_id=user2,
                        scheduled_time=datetime.utcnow(),
                        status='scheduled',
                        created_at=datetime.utcnow()
                    )
                    session.add(meeting)
                elif len(pair) >= 3:
                    # Создаем встречи между всеми участниками группы
                    for i in range(len(pair)):
                        for j in range(i + 1, len(pair)):
                            meeting = Meeting(
                                user1_id=pair[i],
                                user2_id=pair[j],
                                scheduled_time=datetime.utcnow(),
                                status='scheduled',
                                created_at=datetime.utcnow()
                            )
                            session.add(meeting)

            message += "\nПожалуйста, договоритесь о времени и формате встречи в личных сообщениях 😊"

            # Сохраняем изменения в базе данных
            session.commit()

            # Отправляем сообщение в конкретный чат
            await context.bot.send_message(
                chat_id=chat.chat_id,
                text=message,
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Error sending poll to chat: {e}")


async def handle_new_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка добавления бота в новый чат"""
    if update.message.new_chat_members:
        for member in update.message.new_chat_members:
            if member.id == context.bot.id:
                # Bot was added to a new chat
                session = next(get_session())
                try:
                    chat = update.effective_chat
                    # Check if chat already exists
                    db_chat = session.query(Chat).filter_by(
                        chat_id=chat.id).first()
                    if not db_chat:
                        # Register new chat
                        db_chat = Chat(
                            chat_id=chat.id,
                            title=chat.title or str(chat.id),
                            is_active=True,
                            joined_at=datetime.utcnow()
                        )
                        session.add(db_chat)
                        session.commit()

                        await update.message.reply_text(
                            "Спасибо, что добавили меня! Я бот для организации случайных кофе-встреч. "
                            "Я буду отправлять еженедельные опросы и создавать пары для встреч. "
                            "Используйте /help для просмотра доступных команд."
                        )
                except Exception as e:
                    logger.error(f"Error handling new chat member: {e}")
                finally:
                    session.close()


async def handle_left_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка удаления бота из чата"""
    if update.message.left_chat_member and update.message.left_chat_member.id == context.bot.id:
        # Bot was removed from the chat
        session = next(get_session())
        try:
            chat = update.effective_chat
            # Mark chat as inactive
            db_chat = session.query(Chat).filter_by(chat_id=chat.id).first()
            if db_chat:
                db_chat.is_active = False
                session.commit()
        except Exception as e:
            logger.error(f"Error handling left chat member: {e}")
        finally:
            session.close()


def is_bot_running():
    """Проверяет, не запущен ли уже экземпляр бота"""
    session = next(get_session())
    try:
        # Проверяем, есть ли активные экземпляры бота
        running_instances = session.query(BotInstance).count()

        if running_instances > 0:
            # Проверяем, не устарели ли записи (старше 1 минуты)
            cutoff_time = datetime.utcnow() - timedelta(minutes=1)
            stale_instances = session.query(BotInstance).filter(
                BotInstance.last_heartbeat < cutoff_time
            ).all()

            # Удаляем устаревшие записи
            for instance in stale_instances:
                session.delete(instance)
            session.commit()

            # Проверяем оставшиеся записи
            running_instances = session.query(BotInstance).count()
            if running_instances > 0:
                logger.warning(
                    f"Found {running_instances} running bot instances")
                return True
        return False
    except Exception as e:
        logger.error(f"Error checking bot instances: {e}")
        return True  # В случае ошибки предполагаем худшее
    finally:
        session.close()


def register_bot_instance():
    """Регистрирует новый экземпляр бота"""
    session = next(get_session())
    try:
        # Удаляем все устаревшие записи
        cutoff_time = datetime.utcnow() - timedelta(minutes=1)
        stale_instances = session.query(BotInstance).filter(
            BotInstance.last_heartbeat < cutoff_time
        ).all()
        for instance in stale_instances:
            session.delete(instance)
        session.commit()

        # Проверяем, есть ли активные экземпляры
        if session.query(BotInstance).count() > 0:
            logger.warning("Another bot instance is already running")
            return False

        # Создаем запись о новом экземпляре
        instance = BotInstance(
            instance_id=str(uuid.uuid4()),
            last_heartbeat=datetime.utcnow()
        )
        session.add(instance)
        session.commit()
        logger.info(f"Registered new bot instance: {instance.instance_id}")
        return True
    except Exception as e:
        logger.error(f"Error registering bot instance: {e}")
        return False
    finally:
        session.close()


async def update_heartbeat(context: ContextTypes.DEFAULT_TYPE):
    """Обновляет время последнего heartbeat для текущего экземпляра"""
    session = next(get_session())
    try:
        latest_instance = session.query(BotInstance).order_by(
            BotInstance.last_heartbeat.desc()
        ).first()
        if latest_instance:
            latest_instance.last_heartbeat = datetime.utcnow()
            session.commit()
            logger.debug(
                f"Heartbeat updated for instance {latest_instance.instance_id}")
    except Exception as e:
        logger.error(f"Error updating heartbeat: {e}")
    finally:
        session.close()


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок для приложения Telegram"""
    logger.error("Exception while handling an update:", exc_info=context.error)

    if update and update.effective_message:
        error_message = "Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже."
        try:
            await update.effective_message.reply_text(error_message)
        except Exception as e:
            logger.error(f"Error sending error message: {e}", exc_info=True)


async def update_profile_field(update: Update, context: ContextTypes.DEFAULT_TYPE, field_name: str, field_display_name: str):
    """Универсальная функция для обновления полей профиля"""
    session = next(get_session())
    try:
        user = session.query(User).filter(
            User.telegram_id == update.effective_user.id).first()
        if not user:
            await update.message.reply_text("Произошла ошибка при получении данных пользователя.")
            return ConversationHandler.END

        # Обработка специальных случаев
        if field_name == 'birth_date':
            try:
                value = datetime.strptime(update.message.text, "%d.%m.%Y")
            except ValueError:
                await update.message.reply_text("Пожалуйста, введите дату в правильном формате (ДД.ММ.ГГГГ):")
                return SETTINGS_BIRTH_DATE
        elif field_name == 'avatar':
            if not update.message.photo:
                await update.message.reply_text("Пожалуйста, отправьте фотографию:")
                return SETTINGS_AVATAR
            value = update.message.photo[-1].file_id
        else:
            value = update.message.text

        # Обновляем значение поля
        setattr(user, field_name, value)
        session.commit()

        keyboard = [[InlineKeyboardButton(
            "◀️ Назад", callback_data='settings')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"{field_display_name} успешно обновлен!", reply_markup=reply_markup)
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in update_{field_name}: {e}")
        await update.message.reply_text(f"Произошла ошибка при обновлении {field_display_name}.")
        return ConversationHandler.END
    finally:
        session.close()


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /help"""
    help_text = (
        "🤖 Random Coffee Bot - бот для организации случайных кофе-встреч.\n\n"
        "📝 Основные команды:\n"
        "/start - начать работу с ботом\n"
        "/help - показать это сообщение\n"
        "/stats - показать статистику\n"
        "/settings - настроить профиль\n"
        "/cancel - отменить текущее действие\n\n"
        "ℹ️ Как это работает:\n"
        "1. Каждую неделю бот отправляет опрос о желании участвовать во встречах\n"
        "2. Те, кто ответил положительно, получают пару для встречи\n"
        "3. Участники договариваются о времени и формате встречи\n"
        "4. После встречи можно оставить отзыв о собеседнике\n\n"
        "⚙️ Настройки профиля:\n"
        "- Город\n"
        "- Социальная сеть\n"
        "- Информация о себе\n"
        "- Место работы\n"
        "- Дата рождения\n"
        "- Аватар\n"
        "- Хобби\n"
        "- Видимость профиля\n\n"
        "❓ Если у вас есть вопросы, используйте кнопку FAQ в главном меню."
    )
    await update.message.reply_text(help_text)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /stats"""
    session = next(get_session())
    try:
        # Получаем пользователя
        user = session.query(User).filter(
            User.telegram_id == update.effective_user.id).first()
        if not user:
            await update.message.reply_text("⚠️ Сначала нужно зарегистрироваться!")
            return

        # Получаем все встречи пользователя
        total_meetings = len(user.meetings_as_user1) + \
            len(user.meetings_as_user2)
        completed_meetings = session.query(Meeting).filter(
            ((Meeting.user1_id == user.id) | (Meeting.user2_id == user.id)) &
            (Meeting.status == 'completed')
        ).count()

        # Получаем средний рейтинг
        ratings = session.query(Rating).filter(
            Rating.to_user_id == user.id).all()
        avg_rating = sum([r.rating for r in ratings]) / \
            len(ratings) if ratings else 0

        # Определяем уровень опыта
        experience_level = "🌱 Новичок"
        if total_meetings >= 10:
            experience_level = "🌿 Регуляр"
        if total_meetings >= 20:
            experience_level = "🌳 Эксперт"

        stats_text = (
            "📊 Ваша статистика:\n\n"
            f"👥 Всего встреч: {total_meetings}\n"
            f"✅ Завершённых встреч: {completed_meetings}\n"
            f"⭐️ Средняя оценка: {avg_rating:.1f}\n"
            f"📈 Уровень опыта: {experience_level}\n"
            f"📅 В клубе с: {user.created_at.strftime('%d.%m.%Y')}\n\n"
            "🏆 Достижения:\n"
        )

        # Добавляем достижения
        if total_meetings >= 1:
            stats_text += "🎯 Первая встреча\n"
        if total_meetings >= 5:
            stats_text += "🔥 5 встреч\n"
        if total_meetings >= 10:
            stats_text += "💫 10 встреч\n"
        if total_meetings >= 20:
            stats_text += "🌟 20 встреч\n"
        if avg_rating >= 4.5:
            stats_text += "⭐️ Отличный собеседник\n"

        await update.message.reply_text(stats_text)
    except Exception as e:
        logger.error(f"Error in stats: {e}")
        await update.message.reply_text("Произошла ошибка при получении статистики.")
    finally:
        session.close()


async def main():
    """Основная функция запуска бота"""
    session = None
    try:
        # Проверяем, не запущен ли уже бот
        if is_bot_running():
            logger.error("Another instance of the bot is already running")
            return

        # Регистрируем новый экземпляр бота
        instance_id = register_bot_instance()
        if not instance_id:
            logger.error("Failed to register bot instance")
            return

        # Создаем приложение
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("profile", profile))
        application.add_handler(CommandHandler("settings", settings))
        application.add_handler(CommandHandler("stats", stats))
        application.add_handler(CommandHandler("faq", faq))
        application.add_handler(CommandHandler("cancel", start))

        # Добавляем обработчик разговора для регистрации
        conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(
                register, pattern='^register$')],
            states={
                ENTER_NAME: [
                    MessageHandler(filters.TEXT & ~
                                   filters.COMMAND, enter_name),
                    CallbackQueryHandler(register, pattern='^register$')
                ],
                ENTER_CITY: [
                    MessageHandler(filters.TEXT & ~
                                   filters.COMMAND, enter_city),
                    CallbackQueryHandler(register, pattern='^register$')
                ],
                ENTER_SOCIAL_LINK: [
                    MessageHandler(filters.TEXT & ~
                                   filters.COMMAND, enter_social_link),
                    CallbackQueryHandler(register, pattern='^register$')
                ],
                ENTER_ABOUT: [
                    MessageHandler(filters.TEXT & ~
                                   filters.COMMAND, enter_about),
                    CallbackQueryHandler(register, pattern='^register$')
                ],
                ENTER_JOB: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, enter_job),
                    CallbackQueryHandler(register, pattern='^register$')
                ],
                ENTER_BIRTH_DATE: [
                    MessageHandler(filters.TEXT & ~
                                   filters.COMMAND, enter_birth_date),
                    CallbackQueryHandler(register, pattern='^register$')
                ],
                ENTER_AVATAR: [
                    MessageHandler(filters.PHOTO, enter_avatar),
                    CallbackQueryHandler(register, pattern='^register$')
                ],
                ENTER_HOBBIES: [
                    MessageHandler(filters.TEXT & ~
                                   filters.COMMAND, enter_hobbies),
                    CallbackQueryHandler(register, pattern='^register$')
                ],
            },
            fallbacks=[CommandHandler('cancel', start)],
            per_chat=True,
            per_user=True,
            per_message=True
        )

        # Добавляем обработчик разговора для настроек
        settings_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(
                settings, pattern='^settings$')],
            states={
                SETTINGS_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_city)],
                SETTINGS_SOCIAL_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_social_link)],
                SETTINGS_ABOUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_about)],
                SETTINGS_JOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_job)],
                SETTINGS_BIRTH_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_birth_date)],
                SETTINGS_AVATAR: [MessageHandler(filters.PHOTO, update_avatar)],
                SETTINGS_HOBBIES: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_hobbies)],
                SETTINGS_VISIBILITY: [CallbackQueryHandler(
                    update_visibility, pattern='^visibility_')]
            },
            fallbacks=[CommandHandler('cancel', start)],
            per_chat=True,
            per_user=True,
            per_message=True
        )

        application.add_handler(conv_handler)
        application.add_handler(settings_handler)

        # Добавляем обработчики для кнопок и опросов
        application.add_handler(CallbackQueryHandler(button))
        application.add_handler(PollAnswerHandler(handle_poll_answer))

        # Настраиваем планировщик задач
        scheduler = AsyncIOScheduler()
        scheduler.add_job(send_weekly_poll, 'cron', day_of_week='mon',
                          hour=10, minute=0, timezone='Europe/Moscow')
        scheduler.add_job(distribute_pairs, 'cron', day_of_week='tue',
                          hour=10, minute=0, timezone='Europe/Moscow')
        scheduler.add_job(update_heartbeat, 'interval', minutes=1)
        scheduler.start()

        logger.info("Bot is starting...")
        await application.run_polling()

    except Exception as e:
        logger.error(f"Error in main: {e}")
        if session:
            try:
                # Удаляем запись о текущем экземпляре бота
                session.query(BotInstance).filter(
                    BotInstance.instance_id == instance_id).delete()
                session.commit()
                logger.info("Bot instance record removed")
            except Exception as e:
                logger.error(f"Error removing bot instance: {e}")
    finally:
        if session:
            session.close()


if __name__ == '__main__':
    try:
        # Запускаем бота
        asyncio.run(main())
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")
        logger.error(f"Error: {e}")
        sys.exit(1)
