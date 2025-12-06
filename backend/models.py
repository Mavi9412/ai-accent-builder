"""
Database models for AI Accent application
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class UserRole(str, enum.Enum):
    STUDENT = "student"
    ADMIN = "admin"


class LessonStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class PracticeType(str, enum.Enum):
    CONVERSATION = "conversation"
    PRONUNCIATION = "pronunciation"
    SPEAKING = "speaking"
    SHADOWING = "shadowing"


# User Model
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    language = Column(String(50), default="english")
    level = Column(String(50), default="B2 - Upper Intermediate")
    role = Column(Enum(UserRole), default=UserRole.STUDENT)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    progress = relationship("UserProgress", back_populates="user", cascade="all, delete-orphan")
    achievements = relationship("Achievement", back_populates="user", cascade="all, delete-orphan")
    practice_sessions = relationship("PracticeSession", back_populates="user", cascade="all, delete-orphan")
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")


# User Settings Model
class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    email_notifications = Column(Boolean, default=True)
    push_notifications = Column(Boolean, default=True)
    daily_reminders = Column(Boolean, default=False)
    dark_mode = Column(Boolean, default=False)
    sound_effects = Column(Boolean, default=True)
    progress_tracking = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="settings")


# Course Model
class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    icon = Column(String(100))
    duration_hours = Column(Float, default=0)
    lesson_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    lessons = relationship("Lesson", back_populates="course", cascade="all, delete-orphan")


# Lesson Model
class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    content = Column(Text)
    order = Column(Integer, default=0)
    duration_minutes = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    course = relationship("Course", back_populates="lessons")
    user_progress = relationship("UserProgress", back_populates="lesson", cascade="all, delete-orphan")


# User Progress Model
class UserProgress(Base):
    __tablename__ = "user_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=True)
    status = Column(Enum(LessonStatus), default=LessonStatus.NOT_STARTED)
    progress_percentage = Column(Float, default=0.0)
    accuracy = Column(Float, default=0.0)
    time_spent_minutes = Column(Integer, default=0)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="progress")
    lesson = relationship("Lesson", back_populates="user_progress")


# Practice Session Model
class PracticeSession(Base):
    __tablename__ = "practice_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    practice_type = Column(Enum(PracticeType), nullable=False)
    accuracy = Column(Float, default=0.0)
    duration_minutes = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="practice_sessions")


# Achievement Model
class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    icon = Column(String(100))
    unlocked_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="achievements")


# Module Progress Model (for tracking practice modules)
class ModuleProgress(Base):
    __tablename__ = "module_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    module_name = Column(String(255), nullable=False)
    progress_percentage = Column(Float, default=0.0)
    accuracy = Column(Float, default=0.0)
    sessions_count = Column(Integer, default=0)
    time_spent_minutes = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# Accent Types
class AccentType(str, enum.Enum):
    BRITISH = "british"
    AMERICAN = "american"
    AUSTRALIAN = "australian"
    INDIAN = "indian"


# Accent Session Model
class AccentSession(Base):
    __tablename__ = "accent_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    transcribed_text = Column(Text)
    target_accent = Column(Enum(AccentType), default=AccentType.BRITISH)
    overall_score = Column(Float, default=0.0)
    pronunciation_score = Column(Float, default=0.0)
    rhythm_score = Column(Float, default=0.0)
    intonation_score = Column(Float, default=0.0)
    stress_score = Column(Float, default=0.0)
    word_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    audio_duration = Column(Float, default=0.0)
    original_audio_path = Column(String(500))
    corrected_audio_path = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    word_analyses = relationship("WordAnalysis", back_populates="session", cascade="all, delete-orphan")


# Word Analysis Model
class WordAnalysis(Base):
    __tablename__ = "word_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("accent_sessions.id", ondelete="CASCADE"), nullable=False)
    word = Column(String(255), nullable=False)
    word_index = Column(Integer, default=0)
    expected_phonemes = Column(String(500))
    actual_phonemes = Column(String(500))
    pronunciation_score = Column(Float, default=0.0)
    stress_score = Column(Float, default=0.0)
    rhythm_score = Column(Float, default=0.0)
    timestamp_start = Column(Float, default=0.0)
    timestamp_end = Column(Float, default=0.0)
    is_correct = Column(Boolean, default=True)
    feedback = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    session = relationship("AccentSession", back_populates="word_analyses")

