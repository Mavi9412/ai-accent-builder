"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from models import LessonStatus, PracticeType, UserRole


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    language: Optional[str] = "english"


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    language: Optional[str] = None
    level: Optional[str] = None


class UserResponse(UserBase):
    id: int
    level: str
    role: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# Settings Schemas
class UserSettingsBase(BaseModel):
    email_notifications: bool = True
    push_notifications: bool = True
    daily_reminders: bool = False
    dark_mode: bool = False
    sound_effects: bool = True
    progress_tracking: bool = True


class UserSettingsResponse(UserSettingsBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class UserSettingsUpdate(UserSettingsBase):
    pass


# Course Schemas
class CourseBase(BaseModel):
    title: str
    description: Optional[str] = None
    icon: Optional[str] = None
    duration_hours: float = 0
    lesson_count: int = 0


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    duration_hours: Optional[float] = None
    lesson_count: Optional[int] = None
    is_active: Optional[bool] = None


class CourseResponse(CourseBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# Lesson Schemas
class LessonBase(BaseModel):
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    order: int = 0
    duration_minutes: int = 0


class LessonCreate(LessonBase):
    course_id: int


class LessonUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    order: Optional[int] = None
    duration_minutes: Optional[int] = None
    is_active: Optional[bool] = None


class LessonResponse(LessonBase):
    id: int
    course_id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# Progress Schemas
class UserProgressBase(BaseModel):
    lesson_id: Optional[int] = None
    status: LessonStatus = LessonStatus.NOT_STARTED
    progress_percentage: float = 0.0
    accuracy: float = 0.0
    time_spent_minutes: int = 0


class UserProgressCreate(UserProgressBase):
    pass


class UserProgressUpdate(BaseModel):
    status: Optional[LessonStatus] = None
    progress_percentage: Optional[float] = None
    accuracy: Optional[float] = None
    time_spent_minutes: Optional[int] = None
    completed_at: Optional[datetime] = None


class UserProgressResponse(UserProgressBase):
    id: int
    user_id: int
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# Practice Session Schemas
class PracticeSessionBase(BaseModel):
    practice_type: PracticeType
    accuracy: float = 0.0
    duration_minutes: int = 0
    notes: Optional[str] = None


class PracticeSessionCreate(PracticeSessionBase):
    pass


class PracticeSessionResponse(PracticeSessionBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Achievement Schemas
class AchievementBase(BaseModel):
    title: str
    description: Optional[str] = None
    icon: Optional[str] = None


class AchievementCreate(AchievementBase):
    pass


class AchievementResponse(AchievementBase):
    id: int
    user_id: int
    unlocked_at: datetime

    class Config:
        from_attributes = True


# Module Progress Schemas
class ModuleProgressBase(BaseModel):
    module_name: str
    progress_percentage: float = 0.0
    accuracy: float = 0.0
    sessions_count: int = 0
    time_spent_minutes: int = 0


class ModuleProgressCreate(ModuleProgressBase):
    pass


class ModuleProgressUpdate(BaseModel):
    progress_percentage: Optional[float] = None
    accuracy: Optional[float] = None
    sessions_count: Optional[int] = None
    time_spent_minutes: Optional[int] = None


class ModuleProgressResponse(ModuleProgressBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# Dashboard Stats Schemas
class DashboardStats(BaseModel):
    completed_lessons: int
    day_streak: int
    overall_progress: float
    achievements_unlocked: int
    total_learning_time_hours: float


# Password Change Schema
class PasswordChange(BaseModel):
    current_password: str
    new_password: str

