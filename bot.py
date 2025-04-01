import os
import logging
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Poll, Bot, ReplyKeyboardMarkup, KeyboardButton, ChatMemberUpdated
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler, ChatMemberHandler, PollAnswerHandler
from database import init_db, User, UserPreferences, Meeting, Rating, WeeklyPoll, PollResponse

# Загружаем переменные окружения из файла .env, если он существует
load_dotenv(override=True)

# Получаем переменные окружения
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")

# Пытаемся получить GROUP_CHAT_ID из разных возможных переменных окружения
GROUP_CHAT_ID = os.getenv('TELEGRAM_GROUP_ID') or os.getenv(
    'GROUP_CHAT_ID') or os.getenv('CHAT_ID')
if not GROUP_CHAT_ID:
    print("Warning: GROUP_CHAT_ID not found in environment variables. Using default value.")
    GROUP_CHAT_ID = "439634804"  # Значение по умолчанию

# Конвертируем GROUP_CHAT_ID в int
GROUP_CHAT_ID = int(GROUP_CHAT_ID)

# Настройка базы данных
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("Warning: DATABASE_URL not found in environment variables. Using default SQLite database.")
    DATABASE_URL = "sqlite:///random_coffee.db"

# Настройка поддержки
SUPPORT_CHAT_ID = os.getenv('SUPPORT_CHAT_ID') or GROUP_CHAT_ID

# Инициализация базы данных
init_db(DATABASE_URL)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация базы данных
db = init_db()

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
    # Проверяем, есть ли пользователь в базе данных
    user = db.query(User).filter(User.telegram_id ==
                                 update.effective_user.id).first()

    if not user:
        # Создаем клавиатуру с кнопками
        keyboard = [
            [InlineKeyboardButton("👤 Регистрация", callback_data='register')],
            [InlineKeyboardButton("⚙️ Настройки", callback_data='settings')],
            [InlineKeyboardButton("📊 Статистика", callback_data='stats')],
            [InlineKeyboardButton("❓ FAQ", callback_data='faq')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "Привет! Я бот Random Coffee. Я помогу вам организовать случайные встречи за кофе.\n\n"
            "Для начала работы нужно зарегистрироваться.\nНажмите кнопку 'Регистрация'.",
            reply_markup=reply_markup
        )
        return CHOOSING
    else:
        # Если пользователь уже зарегистрирован
        keyboard = [
            [InlineKeyboardButton("⚙️ Настройки", callback_data='settings')],
            [InlineKeyboardButton("📊 Статистика", callback_data='stats')],
            [InlineKeyboardButton("❓ FAQ", callback_data='faq')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"С возвращением, {user.name}! Что бы вы хотели сделать?",
            reply_markup=reply_markup
        )
        return CHOOSING


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

    # Сохраняем данные в базу
    user = User(
        telegram_id=update.effective_user.id,
        nickname=context.user_data['name'],
        age=context.user_data['age'],
        gender=context.user_data['gender'],
        profession=context.user_data['profession'],
        interests=context.user_data['interests'],
        language=context.user_data['language'],
        meeting_time=context.user_data['meeting_time'],
        created_at=datetime.now()
    )

    # Проверяем, существует ли пользователь
    existing_user = db.query(User).filter(
        User.telegram_id == update.effective_user.id).first()
    if existing_user:
        # Обновляем существующего пользователя
        existing_user.nickname = user.nickname
        existing_user.age = user.age
        existing_user.gender = user.gender
        existing_user.profession = user.profession
        existing_user.interests = user.interests
        existing_user.language = user.language
        existing_user.meeting_time = user.meeting_time
    else:
        # Добавляем нового пользователя
        db.add(user)

    db.commit()

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


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()

    if query.data == 'register':
        await register(update, context)
    elif query.data == 'profile':
        # Получаем профиль из базы данных
        user = db.query(User).filter(
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
        user = db.query(User).filter(
            User.telegram_id == query.from_user.id).first()
        if not user:
            await query.message.reply_text("⚠️ Сначала нужно зарегистрироваться!")
            return

        preferences = db.query(UserPreferences).filter(
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
        user = db.query(User).filter(
            User.telegram_id == query.from_user.id).first()
        if user:
            # Получаем все встречи пользователя
            total_meetings = len(user.meetings_as_user1) + \
                len(user.meetings_as_user2)
            completed_meetings = db.query(Meeting).filter(
                ((Meeting.user1_id == user.id) | (Meeting.user2_id == user.id)) &
                (Meeting.status == 'completed')
            ).count()

            # Получаем средний рейтинг
            ratings = db.query(Rating).filter(
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
    elif query.data == 'faq':
        await query.message.reply_text(
            "❓ Часто задаваемые вопросы:\n\n"
            "1. Как это работает?\n"
            "   - Каждую пятницу бот создает опрос участия\n"
            "   - В понедельник формируются случайные пары\n"
            "   - Участники договариваются о встрече\n\n"
            "2. Как зарегистрироваться?\n"
            "   - Нажмите кнопку 'Регистрация'\n"
            "   - Заполните анкету\n\n"
            "3. Как отменить встречу?\n"
            "   - Сообщите об этом в чате с партнером\n"
            "   - Дождитесь следующего распределения"
        )


async def create_weekly_poll(context: ContextTypes.DEFAULT_TYPE):
    """Создает еженедельный опрос"""
    # Создаем новый опрос
    poll = WeeklyPoll(
        week_start=datetime.now() + timedelta(days=1),
        week_end=datetime.now() + timedelta(days=7),
        status='active'
    )
    db.add(poll)
    db.commit()

    # Отправляем опрос в чат
    message = await context.bot.send_poll(
        chat_id=GROUP_CHAT_ID,
        question="Привет, будешь участвовать во встречах Random Coffee на следующей неделе? ☕️",
        options=["Да", "Нет"],
        is_anonymous=False
    )

    # Сохраняем ID сообщения
    poll.message_id = message.message_id
    db.commit()


async def distribute_pairs(context: ContextTypes.DEFAULT_TYPE):
    """Распределяет пары для встреч"""
    # Получаем активный опрос
    poll = db.query(WeeklyPoll).filter(
        WeeklyPoll.status == 'active',
        WeeklyPoll.week_start <= datetime.now()
    ).first()

    if not poll:
        return

    # Получаем положительные ответы
    responses = db.query(PollResponse).filter(
        PollResponse.poll_id == poll.id,
        PollResponse.response == True
    ).all()

    # Получаем пользователей
    user_ids = [response.user_id for response in responses]
    users = db.query(User).filter(User.id.in_(user_ids)).all()

    # Перемешиваем пользователей
    random.shuffle(users)

    # Формируем пары
    pairs = []
    for i in range(0, len(users)-1, 2):
        pairs.append((users[i], users[i+1]))

    # Отправляем сообщение с парами
    pairs_text = "Пары для Бесплатный клуб \"ТЭМП\" → Рандом-Кофе составлены! Ищи в списке ниже, с кем встречаешься на этой неделе:\n\n"

    for user1, user2 in pairs:
        pairs_text += f"👥 {user1.nickname} ↔️ {user2.nickname}\n"

    pairs_text += "\n➪ Напиши собеседнику в личку, чтобы договориться об удобном времени и формате встречи ☕️"

    await context.bot.send_message(
        chat_id=GROUP_CHAT_ID,
        text=pairs_text
    )

    # Создаем встречи в базе данных
    for user1, user2 in pairs:
        meeting = Meeting(
            user1_id=user1.id,
            user2_id=user2.id,
            status='active'
        )
        db.add(meeting)

    # Завершаем опрос
    poll.status = 'completed'
    db.commit()


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
    user = db.query(User).filter(
        User.telegram_id == query.from_user.id).first()
    if user:
        preferences = db.query(UserPreferences).filter(
            UserPreferences.user_id == user.id).first()
        if preferences:
            db.delete(preferences)
            db.commit()
            await query.message.reply_text("✅ Настройки успешно сброшены!")
        else:
            await query.message.reply_text("ℹ️ У вас пока нет сохраненных настроек.")
    else:
        await query.message.reply_text("⚠️ Сначала нужно зарегистрироваться!")


async def save_gender_preference(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение предпочитаемого пола"""
    user = db.query(User).filter(User.telegram_id ==
                                 update.effective_user.id).first()
    if not user:
        await update.message.reply_text("⚠️ Сначала нужно зарегистрироваться!")
        return ConversationHandler.END

    preferences = db.query(UserPreferences).filter(
        UserPreferences.user_id == user.id).first()
    if not preferences:
        preferences = UserPreferences(user_id=user.id)
        db.add(preferences)

    preferences.preferred_gender = update.message.text
    db.commit()

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

        user = db.query(User).filter(User.telegram_id ==
                                     update.effective_user.id).first()
        if not user:
            await update.message.reply_text("⚠️ Сначала нужно зарегистрироваться!")
            return ConversationHandler.END

        preferences = db.query(UserPreferences).filter(
            UserPreferences.user_id == user.id).first()
        if not preferences:
            preferences = UserPreferences(user_id=user.id)
            db.add(preferences)

        preferences.age_range_min = min_age
        preferences.age_range_max = age
        db.commit()

        await update.message.reply_text(
            f"✅ Возрастной диапазон собеседников установлен: {min_age}-{age} лет"
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число")
        return SETTINGS_AGE_MAX


async def save_language_preference(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение предпочитаемого языка"""
    user = db.query(User).filter(User.telegram_id ==
                                 update.effective_user.id).first()
    if not user:
        await update.message.reply_text("⚠️ Сначала нужно зарегистрироваться!")
        return ConversationHandler.END

    preferences = db.query(UserPreferences).filter(
        UserPreferences.user_id == user.id).first()
    if not preferences:
        preferences = UserPreferences(user_id=user.id)
        db.add(preferences)

    preferences.preferred_languages = update.message.text
    db.commit()

    await update.message.reply_text(f"✅ Предпочитаемый язык общения установлен: {update.message.text}")
    return ConversationHandler.END


async def save_interests_preference(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение предпочитаемых интересов"""
    user = db.query(User).filter(User.telegram_id ==
                                 update.effective_user.id).first()
    if not user:
        await update.message.reply_text("⚠️ Сначала нужно зарегистрироваться!")
        return ConversationHandler.END

    preferences = db.query(UserPreferences).filter(
        UserPreferences.user_id == user.id).first()
    if not preferences:
        preferences = UserPreferences(user_id=user.id)
        db.add(preferences)

    preferences.preferred_interests = update.message.text
    db.commit()

    await update.message.reply_text(f"✅ Предпочитаемые интересы установлены: {update.message.text}")
    return ConversationHandler.END


async def save_time_preference(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение предпочитаемого времени"""
    user = db.query(User).filter(User.telegram_id ==
                                 update.effective_user.id).first()
    if not user:
        await update.message.reply_text("⚠️ Сначала нужно зарегистрироваться!")
        return ConversationHandler.END

    preferences = db.query(UserPreferences).filter(
        UserPreferences.user_id == user.id).first()
    if not preferences:
        preferences = UserPreferences(user_id=user.id)
        db.add(preferences)

    preferences.preferred_meeting_times = update.message.text
    db.commit()

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
    user = db.query(User).filter(User.telegram_id ==
                                 update.effective_user.id).first()
    if user:
        # Получаем все встречи пользователя
        total_meetings = len(user.meetings_as_user1) + \
            len(user.meetings_as_user2)
        completed_meetings = db.query(Meeting).filter(
            ((Meeting.user1_id == user.id) | (Meeting.user2_id == user.id)) &
            (Meeting.status == 'completed')
        ).count()

        # Получаем средний рейтинг
        ratings = db.query(Rating).filter(
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
    poll = db.query(WeeklyPoll).filter(
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
    existing_response = db.query(PollResponse).filter(
        PollResponse.poll_id == poll.id,
        PollResponse.user_id == user_id
    ).first()

    if existing_response:
        # Обновляем существующий ответ
        existing_response.response = response_text
        existing_response.created_at = datetime.now()
    else:
        # Добавляем новый ответ
        db.add(poll_response)

    db.commit()

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
    poll = WeeklyPoll(
        created_at=datetime.now(),
        status='active'
    )
    db.add(poll)
    db.commit()

    message = await context.bot.send_poll(
        chat_id=GROUP_CHAT_ID,
        question="Привет! Будете участвовать во встречах Random Coffee на следующей неделе? ☕️",
        options=["Да", "Нет"],
        is_anonymous=False
    )

    poll.message_id = message.message_id
    db.commit()


async def create_pairs(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Создание пар для встреч"""
    chat_id = GROUP_CHAT_ID
    db = next(get_db())

    # Получаем последний опрос
    latest_poll = db.query(WeeklyPoll).order_by(
        WeeklyPoll.created_at.desc()).first()
    if not latest_poll:
        return

    # Получаем пользователей, которые ответили "Да"
    positive_responses = (
        db.query(PollResponse)
        .filter(PollResponse.poll_id == latest_poll.id)
        .filter(PollResponse.response == "Да")
        .all()
    )

    # Получаем ID пользователей, готовых к встрече
    available_users = [response.user_id for response in positive_responses]

    if len(available_users) < 2:
        await context.bot.send_message(
            chat_id=chat_id,
            text="К сожалению, недостаточно участников для формирования пар на эту неделю 😔"
        )
        return

    # Получаем историю встреч
    past_meetings = (
        db.query(Meeting)
        .filter(Meeting.user1_id.in_(available_users))
        .filter(Meeting.user2_id.in_(available_users))
        .all()
    )

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
    random.shuffle(available_users)

    # Создаем пары с учетом истории встреч
    pairs = []
    unpaired = []
    used = set()

    for user1 in available_users:
        if user1 in used:
            continue

        # Ищем подходящего партнера
        best_partner = None
        min_meetings = float('inf')

        for user2 in available_users:
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
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if user:
                users.append(
                    f"@{user.username}" if user.username else f"[Пользователь](tg://user?id={user_id})")

        # Добавляем пару в сообщение
        message += "👥 " + " и ".join(users) + "\n"

        # Сохраняем встречу в базу данных
        if len(pair) == 2:
            meeting = Meeting(
                user1_id=pair[0],
                user2_id=pair[1],
                week_number=datetime.now().isocalendar()[1]
            )
            db.add(meeting)
        elif len(pair) == 3:
            meeting1 = Meeting(
                user1_id=pair[0],
                user2_id=pair[1],
                week_number=datetime.now().isocalendar()[1]
            )
            meeting2 = Meeting(
                user1_id=pair[1],
                user2_id=pair[2],
                week_number=datetime.now().isocalendar()[1]
            )
            meeting3 = Meeting(
                user1_id=pair[0],
                user2_id=pair[2],
                week_number=datetime.now().isocalendar()[1]
            )
            db.add(meeting1)
            db.add(meeting2)
            db.add(meeting3)

    message += "\nПожалуйста, договоритесь о времени и формате встречи в личных сообщениях 😊"

    # Сохраняем изменения в базе данных
    db.commit()

    # Отправляем сообщение в чат
    await context.bot.send_message(
        chat_id=chat_id,
        text=message,
        parse_mode='Markdown'
    )


async def handle_new_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка добавления бота в новый чат"""
    if update.my_chat_member and update.my_chat_member.new_chat_member.user.id == context.bot.id:
        chat_name = update.effective_chat.title
        welcome_message = (
            f"Здравствуйте!\n"
            f"Я — рандом кофе бот, который теперь живёт в бесплатном сообществе {chat_name}. "
            f"Моя задача — помочь вам познакомиться и узнать друг друга поближе.\n\n"
            f"Как это работает?\n"
            f"В конце каждой недели я буду спрашивать вас, готовы ли вы встретиться на следующей неделе. "
            f"Пока пары не сформированы, вы можете передумать.\n\n"
            f"Чтобы изменить своё решение, нажмите на опрос (для этого нужно щёлкнуть правой кнопкой мыши "
            f"на рабочем столе Telegram) и выберите «отменить голосование». "
            f"Затем вы можете выбрать новый вариант.\n\n"
            f"В понедельник я составлю пары из всех зарегистрировавшихся и отправлю список в этот чат.\n\n"
            f"Вы можете выбрать день, время и формат встречи. Просто напишите своему партнёру в личные сообщения, "
            f"когда и в каком формате вам удобно встретиться.\n\n"
            f"Пары формируются случайным образом, но вы можете помочь мне улучшить подбор."
        )

        # Отправляем приветственное сообщение
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=welcome_message
        )

        # Отправляем первичный опрос
        await send_initial_poll(update.effective_chat.id, context)


async def send_initial_poll(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправка первичного опроса об интересе к встречам"""
    # Создаем опрос в базе данных
    poll = WeeklyPoll(
        created_at=datetime.now(),
        status='initial',  # Отмечаем, что это первичный опрос
        week_start=datetime.now(),
        week_end=datetime.now() + timedelta(days=7)
    )
    db.add(poll)
    db.commit()

    # Отправляем опрос
    message = await context.bot.send_message(
        chat_id=chat_id,
        text="Тебе интересна идея встреч в этом чате?"
    )

    # Сохраняем ID сообщения с опросом
    poll.message_id = message.message_id
    db.commit()

    # Отправляем опрос с вариантами ответов
    await context.bot.send_poll(
        chat_id=chat_id,
        question="Тебе интересна идея встреч в этом чате?",
        options=["Да", "Нет", "Пока что не знаю"],
        is_anonymous=False
    )


def main():
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Создаем обработчик разговора для регистрации
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(register, pattern='^register$')],
        states={
            ENTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_name)],
            ENTER_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_age)],
            ENTER_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_gender)],
            ENTER_PROFESSION: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_profession)],
            ENTER_INTERESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_interests)],
            ENTER_LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_language)],
            ENTER_MEETING_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_meeting_time)],
        },
        fallbacks=[CommandHandler('cancel', start)]
    )

    # Создаем обработчик разговора для настроек
    settings_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_settings, pattern='^set_')],
        states={
            SETTINGS_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_gender_preference)],
            SETTINGS_AGE_MIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_age_min_preference)],
            SETTINGS_AGE_MAX: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_age_max_preference)],
            SETTINGS_LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_language_preference)],
            SETTINGS_INTERESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_interests_preference)],
            SETTINGS_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_time_preference)],
        },
        fallbacks=[CommandHandler('cancel', start)]
    )

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats))

    # Добавляем обработчик разговора
    application.add_handler(conv_handler)
    application.add_handler(settings_handler)

    # Добавляем обработчик добавления бота в чат
    application.add_handler(ChatMemberHandler(
        handle_new_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))

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
            create_pairs,
            interval=timedelta(days=7),
            first=get_next_monday(hour=17)
        )

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
