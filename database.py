from datetime import datetime
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text, Float, Boolean
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
    telegram_id = Column(Integer, unique=True)
    nickname = Column(String(100))
    age = Column(Integer)
    gender = Column(String(10))
    profession = Column(String(100))
    interests = Column(Text)
    language = Column(String(50))
    meeting_time = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)
    experience = Column(Integer, default=0)
    total_meetings = Column(Integer, default=0)
    completed_meetings = Column(Integer, default=0)
    average_rating = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)

    # Связи с другими таблицами
    preferences = relationship(
        "UserPreferences", back_populates="user", uselist=False)
    ratings_given = relationship(
        "Rating", foreign_keys="Rating.from_user_id", back_populates="from_user")
    ratings_received = relationship(
        "Rating", foreign_keys="Rating.to_user_id", back_populates="to_user")


class UserPreferences(Base):
    __tablename__ = 'user_preferences'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True)
    preferred_gender = Column(String(10))
    age_range_min = Column(Integer)
    age_range_max = Column(Integer)
    preferred_languages = Column(String(100))
    preferred_interests = Column(Text)
    preferred_meeting_times = Column(String(50))

    # Связь с пользователем
    user = relationship("User", back_populates="preferences")


class Meeting(Base):
    __tablename__ = 'meetings'

    id = Column(Integer, primary_key=True)
    user1_id = Column(Integer, ForeignKey('users.id'))
    user2_id = Column(Integer, ForeignKey('users.id'))
    scheduled_at = Column(DateTime)
    status = Column(String(20))  # 'pending', 'completed', 'cancelled'
    created_at = Column(DateTime, default=datetime.now)


class Rating(Base):
    __tablename__ = 'ratings'

    id = Column(Integer, primary_key=True)
    from_user_id = Column(Integer, ForeignKey('users.id'))
    to_user_id = Column(Integer, ForeignKey('users.id'))
    meeting_id = Column(Integer, ForeignKey('meetings.id'))
    rating = Column(Integer)  # 1-5
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

    # Связи с пользователями
    from_user = relationship("User", foreign_keys=[
                             from_user_id], back_populates="ratings_given")
    to_user = relationship("User", foreign_keys=[
                           to_user_id], back_populates="ratings_received")


class WeeklyPoll(Base):
    __tablename__ = 'weekly_polls'

    id = Column(Integer, primary_key=True)
    week_start = Column(DateTime)
    week_end = Column(DateTime)
    poll_message_id = Column(Integer)
    status = Column(String(20))  # 'active', 'completed'
    created_at = Column(DateTime, default=datetime.now)


class PollResponse(Base):
    __tablename__ = 'poll_responses'

    id = Column(Integer, primary_key=True)
    poll_id = Column(Integer, ForeignKey('weekly_polls.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    response = Column(Boolean)
    created_at = Column(DateTime, default=datetime.now)


def init_db():
    """Инициализация базы данных"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment variables")

    # Создаем движок базы данных
    engine = create_engine(database_url)

    # Создаем все таблицы
    Base.metadata.create_all(engine)

    # Создаем сессию
    Session = sessionmaker(bind=engine)
    return Session()


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
