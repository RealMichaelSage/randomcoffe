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
from database import Base, User, UserPreferences, Meeting, Rating, WeeklyPoll, PollResponse, Chat
import uuid

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

# Функция для получения новой сессии


def get_session():
    """Создает и возвращает новую сессию базы данных"""
    return Session()


# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния регистрации
(
    ENTER_NAME,
    ENTER_AGE,
    ENTER_GENDER,
    ENTER_PROFESSION,
    ENTER_INTERESTS,
    ENTER_LANGUAGE,
    ENTER_MEETING_TIME,
    # Состояния настроек
    SETTINGS_GENDER,
    SETTINGS_AGE_MIN,
    SETTINGS_AGE_MAX,
    SETTINGS_LANGUAGE,
    SETTINGS_INTERESTS,
    SETTINGS_TIME
) = range(13)

# Словарь для хранения состояний пользователей
user_states = {}

# Словарь для хранения активных встреч
active_meetings = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start"""
    chat = update.effective_chat
    session = get_session()

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

            await update.message.reply_text(
                "Привет! Я бот для случайных кофе-встреч. "
                "Я помогу организовать неформальные встречи между участниками чата. "
                "Каждую неделю я буду отправлять опрос, чтобы узнать, кто хочет участвовать "
                "во встречах на следующей неделе.\n\n"
                "Основные команды:\n"
                "/help - показать справку\n"
                "/stats - показать статистику\n"
                "/settings - настроить предпочтения"
            )
        else:
            await update.message.reply_text(
                "Я уже работаю в этом чате! Используйте /help для просмотра доступных команд."
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

    await query.message.reply_text(
        "Давайте начнем регистрацию!\n"
        "Как вас зовут? (Введите ваше имя)"
    )
    return ENTER_NAME


async def enter_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода имени"""
    context.user_data['name'] = update.message.text

    await update.message.reply_text(
        "Отлично! Теперь введите ваш возраст (число)"
    )
    return ENTER_AGE


async def enter_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода возраста"""
    try:
        age = int(update.message.text)
        if age < 18 or age > 100:
            await update.message.reply_text("Пожалуйста, введите корректный возраст (от 18 до 100)")
            return ENTER_AGE

        context.user_data['age'] = age

        keyboard = [
            [KeyboardButton("Мужской"), KeyboardButton("Женский")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

        await update.message.reply_text(
            "Укажите ваш пол:",
            reply_markup=reply_markup
        )
        return ENTER_GENDER
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число")
        return ENTER_AGE


async def enter_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода пола"""
    gender = update.message.text
    if gender not in ["Мужской", "Женский"]:
        await update.message.reply_text("Пожалуйста, выберите пол, используя кнопки")
        return ENTER_GENDER

    context.user_data['gender'] = gender

    await update.message.reply_text(
        "Укажите вашу профессию или род деятельности:"
    )
    return ENTER_PROFESSION


async def enter_profession(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода профессии"""
    context.user_data['profession'] = update.message.text

    await update.message.reply_text(
        "Расскажите о ваших интересах (например: программирование, спорт, музыка)"
    )
    return ENTER_INTERESTS


async def enter_interests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода интересов"""
    context.user_data['interests'] = update.message.text

    keyboard = [
        [KeyboardButton("Русский"), KeyboardButton("English")],
        [KeyboardButton("Русский + English")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    await update.message.reply_text(
        "На каком языке вы предпочитаете общаться?",
        reply_markup=reply_markup
    )
    return ENTER_LANGUAGE


async def enter_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода языка"""
    context.user_data['language'] = update.message.text

    keyboard = [
        [KeyboardButton("Утро"), KeyboardButton("День")],
        [KeyboardButton("Вечер"), KeyboardButton("Любое время")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    await update.message.reply_text(
        "В какое время вам удобно встречаться?",
        reply_markup=reply_markup
    )
    return ENTER_MEETING_TIME


async def enter_meeting_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершение регистрации"""
    context.user_data['meeting_time'] = update.message.text
    session = get_session()

    try:
        # Проверяем, существует ли пользователь
        existing_user = session.query(User).filter(
            User.telegram_id == update.effective_user.id).first()

        if existing_user:
            # Обновляем существующего пользователя
            existing_user.nickname = context.user_data['name']
            existing_user.age = context.user_data['age']
            existing_user.gender = context.user_data['gender']
            existing_user.profession = context.user_data['profession']
            existing_user.interests = context.user_data['interests']
            existing_user.language = context.user_data['language']
            existing_user.meeting_time = context.user_data['meeting_time']
        else:
            # Создаем нового пользователя
            user = User(
                telegram_id=update.effective_user.id,
                nickname=context.user_data['name'],
                age=context.user_data['age'],
                gender=context.user_data['gender'],
                profession=context.user_data['profession'],
                interests=context.user_data['interests'],
                language=context.user_data['language'],
                meeting_time=context.user_data['meeting_time'],
                created_at=datetime.utcnow()
            )
            session.add(user)

        session.commit()

        profile_text = (
            "✅ Регистрация завершена! Ваш профиль:\n\n"
            f"👤 Имя: {context.user_data['name']}\n"
            f"📅 Возраст: {context.user_data['age']}\n"
            f"⚧ Пол: {context.user_data['gender']}\n"
            f"💼 Профессия: {context.user_data['profession']}\n"
            f"🎯 Интересы: {context.user_data['interests']}\n"
            f"🗣 Язык общения: {context.user_data['language']}\n"
            f"🕒 Удобное время: {context.user_data['meeting_time']}"
        )

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

        await update.message.reply_text(profile_text, reply_markup=reply_markup)
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in enter_meeting_time: {e}")
        await update.message.reply_text("Произошла ошибка при сохранении профиля.")
        return ConversationHandler.END
    finally:
        session.close()


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    session = get_session()

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
                    f"📅 Возраст: {user.age}\n"
                    f"⚧ Пол: {user.gender}\n"
                    f"💼 Профессия: {user.profession}\n"
                    f"🎯 Интересы: {user.interests}\n"
                    f"🗣 Язык общения: {user.language}\n"
                    f"🕒 Удобное время: {user.meeting_time}\n"
                    f"📆 Дата регистрации: {user.created_at.strftime('%d.%m.%Y')}"
                )
            else:
                profile_text = "👤 Ваш профиль:\n\nПрофиль не найден. Пожалуйста, зарегистрируйтесь."

            await query.message.reply_text(profile_text)
        elif query.data == 'settings':
            # Получаем настройки пользователя
            user = session.query(User).filter(
                User.telegram_id == query.from_user.id).first()
            if not user:
                await query.message.reply_text("⚠️ Сначала нужно зарегистрироваться!")
                return

            preferences = session.query(UserPreferences).filter(
                UserPreferences.user_id == user.id).first()

            keyboard = [
                [
                    InlineKeyboardButton("👥 Предпочитаемый пол",
                                         callback_data='set_gender'),
                    InlineKeyboardButton(
                        "📅 Возрастной диапазон", callback_data='set_age')
                ],
                [
                    InlineKeyboardButton(
                        "🗣 Язык общения", callback_data='set_language'),
                    InlineKeyboardButton(
                        "🎯 Интересы", callback_data='set_interests')
                ],
                [
                    InlineKeyboardButton(
                        "🕒 Удобное время", callback_data='set_time'),
                    InlineKeyboardButton("🔄 Сбросить настройки",
                                         callback_data='reset_settings')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            settings_text = "⚙️ Настройки подбора собеседников:\n\n"
            if preferences:
                settings_text += (
                    f"👥 Предпочитаемый пол: {preferences.preferred_gender or 'Любой'}\n"
                    f"📅 Возраст: {preferences.age_range_min or '18'}-{preferences.age_range_max or '100'} лет\n"
                    f"🗣 Язык общения: {preferences.preferred_languages or 'Любой'}\n"
                    f"🎯 Интересы: {preferences.preferred_interests or 'Любые'}\n"
                    f"🕒 Удобное время: {preferences.preferred_meeting_times or 'Любое'}\n"
                )
            else:
                settings_text += "Настройки пока не заданы. Используйте кнопки ниже для настройки предпочтений."

            await query.message.reply_text(settings_text, reply_markup=reply_markup)
        elif query.data.startswith('set_'):
            # получаем тип настройки (gender, age, language и т.д.)
            setting_type = query.data[4:]
            await handle_settings(update, context, setting_type)
        elif query.data == 'reset_settings':
            await reset_settings(update, context)
        elif query.data == 'stats':
            # Получаем статистику пользователя
            user = session.query(User).filter(
                User.telegram_id == query.from_user.id).first()
            if user:
                # Получаем все встречи пользователя
                total_meetings = len(user.meetings_as_user1) + \
                    len(user.meetings_as_user2)
                completed_meetings = session.query(Meeting).filter(
                    ((Meeting.user1_id == user.id) | (Meeting.user2_id == user.id)) &
                    (Meeting.status == 'completed')
                ).count()

                # Получаем средний рейтинг
                ratings = session.query(Rating).filter(
                    Rating.rated_user_id == user.id).all()
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

            else:
                stats_text = "📊 Статистика:\n\nПрофиль не найден. Пожалуйста, зарегистрируйтесь."

            await query.message.reply_text(stats_text)
    except Exception as e:
        logger.error(f"Error in button_handler: {e}")
        await query.message.reply_text("Произошла ошибка при обработке запроса.")
    finally:
        session.close()


async def create_weekly_poll(context: ContextTypes.DEFAULT_TYPE):
    """Создает еженедельный опрос"""
    session = get_session()
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
    finally:
        session.close()


async def distribute_pairs(context: ContextTypes.DEFAULT_TYPE):
    """Распределяет пары для встреч"""
    session = get_session()
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
                    last_pair = pairs[-1]
                    pairs[-1] = (last_pair[0], last_pair[1], unpaired[0])
                else:
                    # Если пар нет совсем, создаем одну из оставшихся
                    pairs.append(tuple(unpaired))

            # Сохраняем пары в базу данных и отправляем сообщение
            message = "🎉 Пары для встреч на следующую неделю:\n\n"

            for pair in pairs:
                # Получаем информацию о пользователях
                users = []
                for user_id in pair:
                    user = session.query(User).filter_by(
                        telegram_id=user_id).first()
                    if user:
                        users.append(
                            f"@{user.username}" if user.username else f"[Пользователь](tg://user?id={user_id})")

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
                elif len(pair) == 3:
                    user1, user2, user3 = pair
                    meeting1 = Meeting(
                        user1_id=user1,
                        user2_id=user2,
                        scheduled_time=datetime.utcnow(),
                        status='scheduled',
                        created_at=datetime.utcnow()
                    )
                    meeting2 = Meeting(
                        user1_id=user2,
                        user2_id=user3,
                        scheduled_time=datetime.utcnow(),
                        status='scheduled',
                        created_at=datetime.utcnow()
                    )
                    meeting3 = Meeting(
                        user1_id=user1,
                        user2_id=user3,
                        scheduled_time=datetime.utcnow(),
                        status='scheduled',
                        created_at=datetime.utcnow()
                    )
                    session.add(meeting1)
                    session.add(meeting2)
                    session.add(meeting3)

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
        logger.error(f"Error creating pairs for chat: {e}")
    finally:
        session.close()


async def handle_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка изменения настроек"""
    query = update.callback_query
    setting_type = query.data[4:]

    if setting_type == 'gender':
        keyboard = [
            [KeyboardButton("Мужской"), KeyboardButton("Женский")],
            [KeyboardButton("Любой")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await query.message.reply_text("Выберите предпочитаемый пол собеседника:", reply_markup=reply_markup)
        return SETTINGS_GENDER

    elif setting_type == 'age':
        await query.message.reply_text("Введите минимальный возраст собеседника (от 18):")
        return SETTINGS_AGE_MIN

    elif setting_type == 'language':
        keyboard = [
            [KeyboardButton("Русский"), KeyboardButton("English")],
            [KeyboardButton("Русский + English"), KeyboardButton("Любой")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await query.message.reply_text("Выберите предпочитаемый язык общения:", reply_markup=reply_markup)
        return SETTINGS_LANGUAGE

    elif setting_type == 'interests':
        await query.message.reply_text(
            "Введите интересующие вас темы через запятую\n"
            "(например: программирование, спорт, музыка)\n"
            "или напишите 'Любые':"
        )
        return SETTINGS_INTERESTS

    elif setting_type == 'time':
        keyboard = [
            [KeyboardButton("Утро"), KeyboardButton("День")],
            [KeyboardButton("Вечер"), KeyboardButton("Любое время")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await query.message.reply_text("Выберите предпочитаемое время для встреч:", reply_markup=reply_markup)
        return SETTINGS_TIME


async def reset_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сброс настроек пользователя"""
    query = update.callback_query
    user = get_session().query(User).filter(
        User.telegram_id == query.from_user.id).first()
    if user:
        preferences = get_session().query(UserPreferences).filter(
            UserPreferences.user_id == user.id).first()
        if preferences:
            get_session().delete(preferences)
            get_session().commit()
            await query.message.reply_text("✅ Настройки успешно сброшены!")
        else:
            await query.message.reply_text("ℹ️ У вас пока нет сохраненных настроек.")
    else:
        await query.message.reply_text("⚠️ Сначала нужно зарегистрироваться!")


async def save_gender_preference(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение предпочитаемого пола"""
    user = get_session().query(User).filter(User.telegram_id ==
                                            update.effective_user.id).first()
    if not user:
        await update.message.reply_text("⚠️ Сначала нужно зарегистрироваться!")
        return ConversationHandler.END

    preferences = get_session().query(UserPreferences).filter(
        UserPreferences.user_id == user.id).first()
    if not preferences:
        preferences = UserPreferences(user_id=user.id)
        get_session().add(preferences)

    preferences.preferred_gender = update.message.text
    get_session().commit()

    await update.message.reply_text(f"✅ Предпочитаемый пол собеседника установлен: {update.message.text}")
    return ConversationHandler.END


async def save_age_min_preference(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение минимального возраста"""
    try:
        age = int(update.message.text)
        if age < 18 or age > 100:
            await update.message.reply_text("Пожалуйста, введите корректный возраст (от 18 до 100)")
            return SETTINGS_AGE_MIN

        context.user_data['min_age'] = age
        await update.message.reply_text("Теперь введите максимальный возраст собеседника:")
        return SETTINGS_AGE_MAX
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число")
        return SETTINGS_AGE_MIN


async def save_age_max_preference(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение максимального возраста"""
    try:
        age = int(update.message.text)
        min_age = context.user_data.get('min_age', 18)

        if age < min_age or age > 100:
            await update.message.reply_text(f"Пожалуйста, введите корректный возраст (от {min_age} до 100)")
            return SETTINGS_AGE_MAX

        user = get_session().query(User).filter(User.telegram_id ==
                                                update.effective_user.id).first()
        if not user:
            await update.message.reply_text("⚠️ Сначала нужно зарегистрироваться!")
            return ConversationHandler.END

        preferences = get_session().query(UserPreferences).filter(
            UserPreferences.user_id == user.id).first()
        if not preferences:
            preferences = UserPreferences(user_id=user.id)
            get_session().add(preferences)

        preferences.age_range_min = min_age
        preferences.age_range_max = age
        get_session().commit()

        await update.message.reply_text(
            f"✅ Возрастной диапазон собеседников установлен: {min_age}-{age} лет"
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число")
        return SETTINGS_AGE_MAX


async def save_language_preference(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение предпочитаемого языка"""
    user = get_session().query(User).filter(User.telegram_id ==
                                            update.effective_user.id).first()
    if not user:
        await update.message.reply_text("⚠️ Сначала нужно зарегистрироваться!")
        return ConversationHandler.END

    preferences = get_session().query(UserPreferences).filter(
        UserPreferences.user_id == user.id).first()
    if not preferences:
        preferences = UserPreferences(user_id=user.id)
        get_session().add(preferences)

    preferences.preferred_languages = update.message.text
    get_session().commit()

    await update.message.reply_text(f"✅ Предпочитаемый язык общения установлен: {update.message.text}")
    return ConversationHandler.END


async def save_interests_preference(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение предпочитаемых интересов"""
    user = get_session().query(User).filter(User.telegram_id ==
                                            update.effective_user.id).first()
    if not user:
        await update.message.reply_text("⚠️ Сначала нужно зарегистрироваться!")
        return ConversationHandler.END

    preferences = get_session().query(UserPreferences).filter(
        UserPreferences.user_id == user.id).first()
    if not preferences:
        preferences = UserPreferences(user_id=user.id)
        get_session().add(preferences)

    preferences.preferred_interests = update.message.text
    get_session().commit()

    await update.message.reply_text(f"✅ Предпочитаемые интересы установлены: {update.message.text}")
    return ConversationHandler.END


async def save_time_preference(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение предпочитаемого времени"""
    user = get_session().query(User).filter(User.telegram_id ==
                                            update.effective_user.id).first()
    if not user:
        await update.message.reply_text("⚠️ Сначала нужно зарегистрироваться!")
        return ConversationHandler.END

    preferences = get_session().query(UserPreferences).filter(
        UserPreferences.user_id == user.id).first()
    if not preferences:
        preferences = UserPreferences(user_id=user.id)
        get_session().add(preferences)

    preferences.preferred_meeting_times = update.message.text
    get_session().commit()

    await update.message.reply_text(f"✅ Предпочитаемое время встреч установлено: {update.message.text}")
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет сообщение с помощью"""
    help_text = (
        "🤖 Команды бота:\n\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать это сообщение\n"
        "/stats - Показать вашу статистику\n\n"
        "ℹ️ Как это работает:\n"
        "1. Зарегистрируйтесь, нажав кнопку 'Регистрация'\n"
        "2. Настройте предпочтения в разделе 'Настройки'\n"
        "3. Каждую пятницу бот создает опрос для участия\n"
        "4. В понедельник формируются пары для встреч\n"
        "5. После встречи не забудьте оставить отзыв\n\n"
        "📅 Расписание:\n"
        "- Пятница 18:00 - Опрос на следующую неделю\n"
        "- Понедельник 10:00 - Формирование пар\n\n"
        "❓ Если у вас есть вопросы, нажмите кнопку FAQ"
    )
    await update.message.reply_text(help_text)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет статистику пользователя"""
    user = get_session().query(User).filter(User.telegram_id ==
                                            update.effective_user.id).first()
    if user:
        # Получаем все встречи пользователя
        total_meetings = len(user.meetings_as_user1) + \
            len(user.meetings_as_user2)
        completed_meetings = get_session().query(Meeting).filter(
            ((Meeting.user1_id == user.id) | (Meeting.user2_id == user.id)) &
            (Meeting.status == 'completed')
        ).count()

        # Получаем средний рейтинг
        ratings = get_session().query(Rating).filter(
            Rating.rated_user_id == user.id).all()
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

    else:
        stats_text = "📊 Статистика:\n\nПрофиль не найден. Пожалуйста, зарегистрируйтесь."

    await update.message.reply_text(stats_text)


async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка ответов на опросы"""
    answer = update.poll_answer
    user_id = answer.user.id
    poll_id = answer.poll_id

    # Получаем последний опрос из базы данных
    poll = get_session().query(WeeklyPoll).filter(
        WeeklyPoll.message_id == poll_id).first()
    if not poll:
        return

    # Получаем выбранный вариант ответа
    selected_option = answer.option_ids[0] if answer.option_ids else None
    if selected_option is None:
        return

    # Преобразуем индекс варианта в текст ответа
    response_text = ["Да", "Нет", "Пока что не знаю"][selected_option]

    # Сохраняем ответ в базу данных
    poll_response = PollResponse(
        poll_id=poll.id,
        user_id=user_id,
        response=response_text,
        created_at=datetime.now()
    )

    # Проверяем, существует ли уже ответ от этого пользователя
    existing_response = get_session().query(PollResponse).filter(
        PollResponse.poll_id == poll.id,
        PollResponse.user_id == user_id
    ).first()

    if existing_response:
        # Обновляем существующий ответ
        existing_response.response = response_text
        existing_response.created_at = datetime.now()
    else:
        # Добавляем новый ответ
        get_session().add(poll_response)

    get_session().commit()

    # Если это первичный опрос и пользователь ответил "Да",
    # предлагаем ему зарегистрироваться
    if poll.status == 'initial' and response_text == "Да":
        keyboard = [
            [InlineKeyboardButton("👤 Регистрация", callback_data='register')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text="Отлично! Для участия в Random Coffee нужно зарегистрироваться. "
                 "Нажмите кнопку ниже, чтобы начать регистрацию:",
            reply_markup=reply_markup
        )


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
    session = get_session()
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
                    last_pair = pairs[-1]
                    pairs[-1] = (last_pair[0], last_pair[1], unpaired[0])
                else:
                    # Если пар нет совсем, создаем одну из оставшихся
                    pairs.append(tuple(unpaired))

            # Сохраняем пары в базу данных и отправляем сообщение
            message = "🎉 Пары для встреч на следующую неделю:\n\n"

            for pair in pairs:
                # Получаем информацию о пользователях
                users = []
                for user_id in pair:
                    user = session.query(User).filter_by(
                        telegram_id=user_id).first()
                    if user:
                        users.append(
                            f"@{user.username}" if user.username else f"[Пользователь](tg://user?id={user_id})")

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
                elif len(pair) == 3:
                    user1, user2, user3 = pair
                    meeting1 = Meeting(
                        user1_id=user1,
                        user2_id=user2,
                        scheduled_time=datetime.utcnow(),
                        status='scheduled',
                        created_at=datetime.utcnow()
                    )
                    meeting2 = Meeting(
                        user1_id=user2,
                        user2_id=user3,
                        scheduled_time=datetime.utcnow(),
                        status='scheduled',
                        created_at=datetime.utcnow()
                    )
                    meeting3 = Meeting(
                        user1_id=user1,
                        user2_id=user3,
                        scheduled_time=datetime.utcnow(),
                        status='scheduled',
                        created_at=datetime.utcnow()
                    )
                    session.add(meeting1)
                    session.add(meeting2)
                    session.add(meeting3)

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
    finally:
        session.close()


async def handle_new_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка добавления бота в новый чат"""
    if update.message.new_chat_members:
        for member in update.message.new_chat_members:
            if member.id == context.bot.id:
                # Bot was added to a new chat
                session = get_session()
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
        session = get_session()
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
    session = get_session()
    try:
        # Проверяем, есть ли активные экземпляры бота
        running_instances = session.query(func.count()).select_from(
            Base.metadata.tables['bot_instances']
        ).scalar()

        if running_instances > 0:
            # Проверяем, не устарели ли записи (старше 5 минут)
            session.execute(
                "DELETE FROM bot_instances WHERE datetime(last_heartbeat) < datetime('now', '-5 minutes')"
            )
            session.commit()

            # Проверяем оставшиеся записи
            running_instances = session.query(func.count()).select_from(
                Base.metadata.tables['bot_instances']
            ).scalar()

            return running_instances > 0
        return False
    finally:
        session.close()


def register_bot_instance():
    """Регистрирует новый экземпляр бота"""
    session = get_session()
    try:
        # Создаем запись о новом экземпляре
        instance_id = str(uuid.uuid4())
        session.execute(
            "INSERT INTO bot_instances (instance_id, last_heartbeat) VALUES (?, datetime('now'))",
            (instance_id,)
        )
        session.commit()
        return True
    except Exception as e:
        logger.error(f"Error registering bot instance: {e}")
        return False
    finally:
        session.close()


def update_heartbeat():
    """Обновляет время последнего heartbeat для текущего экземпляра"""
    session = get_session()
    try:
        session.execute(
            "UPDATE bot_instances SET last_heartbeat = datetime('now') WHERE instance_id = (SELECT instance_id FROM bot_instances ORDER BY last_heartbeat DESC LIMIT 1)"
        )
        session.commit()
    finally:
        session.close()


def main():
    """Запуск бота"""
    # Проверяем, не запущен ли уже экземпляр бота
    if is_bot_running():
        logger.error("Another instance of the bot is already running")
        sys.exit(1)

    # Регистрируем новый экземпляр
    if not register_bot_instance():
        logger.error("Failed to register bot instance")
        sys.exit(1)

    try:
        # Создаем приложение
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        # Создаем обработчик разговора для регистрации
        conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(
                register, pattern='^register$')],
            states={
                ENTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_name)],
                ENTER_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_age)],
                ENTER_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_gender)],
                ENTER_PROFESSION: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_profession)],
                ENTER_INTERESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_interests)],
                ENTER_LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_language)],
                ENTER_MEETING_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_meeting_time)],
            },
            fallbacks=[CommandHandler('cancel', start)],
            per_chat=True,
            per_user=True,
            per_message=True
        )

        # Создаем обработчик разговора для настроек
        settings_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(
                handle_settings, pattern='^set_')],
            states={
                SETTINGS_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_gender_preference)],
                SETTINGS_AGE_MIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_age_min_preference)],
                SETTINGS_AGE_MAX: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_age_max_preference)],
                SETTINGS_LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_language_preference)],
                SETTINGS_INTERESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_interests_preference)],
                SETTINGS_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_time_preference)],
            },
            fallbacks=[CommandHandler('cancel', start)],
            per_chat=True,
            per_user=True,
            per_message=True
        )

        # Добавляем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("stats", stats))

        # Добавляем обработчик разговора
        application.add_handler(conv_handler)
        application.add_handler(settings_handler)

        # Добавляем обработчики для отслеживания изменений в чате
        application.add_handler(MessageHandler(
            filters.ALL, handle_new_chat_member))
        application.add_handler(MessageHandler(
            filters.ALL, handle_left_chat_member))

        # Добавляем обработчик ответов на опросы
        application.add_handler(PollAnswerHandler(handle_poll_answer))

        # Настраиваем отправку еженедельных опросов
        if application.job_queue:
            # Отправляем опрос каждый понедельник в 10:00
            application.job_queue.run_repeating(
                send_weekly_poll,
                interval=timedelta(days=7),
                first=get_next_monday()
            )

            # Отправляем результаты и создаем пары каждый понедельник в 17:00
            application.job_queue.run_repeating(
                distribute_pairs,
                interval=timedelta(days=7),
                first=get_next_monday(hour=17)
            )

        # Запускаем бота
        print("Бот запускается...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    finally:
        # Удаляем запись о текущем экземпляре
        session = get_session()
        try:
            session.execute(
                "DELETE FROM bot_instances WHERE instance_id = (SELECT instance_id FROM bot_instances ORDER BY last_heartbeat DESC LIMIT 1)"
            )
            session.commit()
        finally:
            session.close()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nБот остановлен пользователем")
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")
        logger.error(f"Error: {e}")
