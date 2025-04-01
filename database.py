from datetime import datetime
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text, Float, Boolean, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from typing import Dict
from sqlalchemy import or_

# Загружаем переменные окружения
load_dotenv()

# Создаем базовый класс для моделей
Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String)
    nickname = Column(String)
    city = Column(String)
    social_link = Column(String)
    about = Column(Text)
    job = Column(String)
    birth_date = Column(DateTime)
    avatar = Column(String)  # Храним file_id от Telegram
    hobbies = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(8))
    is_active = Column(Boolean, default=True)
    show_profile = Column(Boolean, default=True)
    experience_level = Column(Integer, default=0)
    total_meetings = Column(Integer, default=0)
    average_rating = Column(Float, default=0.0)

    # Связи с другими таблицами
    meetings_as_user1 = relationship(
        'Meeting', foreign_keys='Meeting.user1_id', back_populates='user1')
    meetings_as_user2 = relationship(
        'Meeting', foreign_keys='Meeting.user2_id', back_populates='user2')
    preferences = relationship(
        'UserPreferences', back_populates='user', uselist=False)
    ratings_given = relationship(
        'Rating', foreign_keys='Rating.from_user_id', back_populates='from_user')
    ratings_received = relationship(
        'Rating', foreign_keys='Rating.to_user_id', back_populates='to_user')
    poll_responses = relationship('PollResponse', back_populates='user')


class UserPreferences(Base):
    __tablename__ = 'user_preferences'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    preferred_gender = Column(String(50))
    age_range_min = Column(Integer)
    age_range_max = Column(Integer)
    preferred_languages = Column(String(255))
    preferred_interests = Column(String(500))
    preferred_meeting_times = Column(String(100))
    only_new_users = Column(Boolean, default=False)
    only_experienced = Column(Boolean, default=False)

    # Связь с пользователем
    user = relationship("User", back_populates="preferences")


class Meeting(Base):
    __tablename__ = 'meetings'

    id = Column(Integer, primary_key=True)
    user1_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user2_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    scheduled_time = Column(DateTime)
    status = Column(String(50))  # scheduled, completed, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи с пользователями
    user1 = relationship("User", foreign_keys=[
                         user1_id], back_populates="meetings_as_user1")
    user2 = relationship("User", foreign_keys=[
                         user2_id], back_populates="meetings_as_user2")
    ratings = relationship("Rating", back_populates="meeting")


class Rating(Base):
    """Модель рейтинга"""
    __tablename__ = 'ratings'

    id = Column(Integer, primary_key=True)
    meeting_id = Column(Integer, ForeignKey('meetings.id'), nullable=False)
    from_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    to_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    rating = Column(Float)
    comment = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Отношения
    meeting = relationship("Meeting", back_populates="ratings")
    from_user = relationship("User", foreign_keys=[
                             from_user_id], back_populates="ratings_given")
    to_user = relationship("User", foreign_keys=[
                           to_user_id], back_populates="ratings_received")


class Chat(Base):
    """Модель для хранения информации о чатах"""
    __tablename__ = 'chats'

    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, unique=True, nullable=False)
    title = Column(String(255))
    is_active = Column(Boolean, default=True)
    joined_at = Column(DateTime, default=datetime.utcnow)

    # Связи с другими таблицами
    polls = relationship("WeeklyPoll", back_populates="chat")


class WeeklyPoll(Base):
    """Модель для хранения еженедельных опросов"""
    __tablename__ = 'weekly_polls'

    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, ForeignKey('chats.id'), nullable=False)
    message_id = Column(Integer)
    week_start = Column(DateTime)
    week_end = Column(DateTime)
    status = Column(String(50))  # active, closed
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи с другими таблицами
    chat = relationship("Chat", back_populates="polls")
    responses = relationship("PollResponse", back_populates="poll")


class PollResponse(Base):
    __tablename__ = 'poll_responses'

    id = Column(Integer, primary_key=True)
    poll_id = Column(Integer, ForeignKey('weekly_polls.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    response = Column(Boolean)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи с другими таблицами
    poll = relationship("WeeklyPoll", back_populates="responses")
    user = relationship("User", back_populates="poll_responses")


class BotInstance(Base):
    """Модель для отслеживания экземпляров бота"""
    __tablename__ = 'bot_instances'

    instance_id = Column(String(36), primary_key=True)
    last_heartbeat = Column(DateTime, nullable=False)


def init_db():
    """Инициализация базы данных"""
    database_url = os.getenv('DATABASE_URL', 'sqlite:///random_coffee.db')
    engine = create_engine(database_url)

    # Удаляем все существующие таблицы
    Base.metadata.drop_all(engine)

    # Создаем все таблицы заново
    Base.metadata.create_all(engine)

    return engine


# Создаем глобальную сессию базы данных
db = init_db()


def get_user_stats(self, user_id: int) -> Dict:
    """Получить статистику пользователя"""
    with self.get_session() as session:
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            return None

        # Получаем все встречи пользователя
        meetings = session.query(Meeting).filter(
            or_(
                Meeting.user1_id == user.id,
                Meeting.user2_id == user.id
            )
        ).all()

        # Получаем все оценки пользователя
        ratings = session.query(Rating).filter(
            Rating.rated_user_id == user.id
        ).all()

        # Подсчитываем статистику
        total_meetings = len(meetings)
        completed_meetings = len(
            [m for m in meetings if m.status == 'completed'])
        avg_rating = sum(r.rating for r in ratings) / \
            len(ratings) if ratings else 0

        # Определяем уровень опыта
        experience_level = "Новичок"
        if completed_meetings >= 10:
            experience_level = "Опытный"
        elif completed_meetings >= 5:
            experience_level = "Средний"

        # Получаем достижения
        achievements = []
        if completed_meetings >= 1:
            achievements.append("Первая встреча")
        if completed_meetings >= 5:
            achievements.append("5 встреч")
        if completed_meetings >= 10:
            achievements.append("10 встреч")
        if avg_rating >= 4.5:
            achievements.append("Высокий рейтинг")

        return {
            "total_meetings": total_meetings,
            "completed_meetings": completed_meetings,
            "avg_rating": round(avg_rating, 1),
            "experience_level": experience_level,
            "registration_date": user.created_at.strftime("%d.%m.%Y"),
            "achievements": achievements
        }
