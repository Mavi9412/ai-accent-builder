"""
Database initialization script
Creates sample data for testing
"""
from database import SessionLocal, engine, Base
from models import (
    User, UserSettings, Course, Lesson, UserProgress,
    PracticeSession, Achievement, ModuleProgress,
    LessonStatus, PracticeType
)
from auth import get_password_hash
from datetime import datetime, timedelta

# Create all tables
Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    # Create sample user
    if not db.query(User).filter(User.email == "demo@example.com").first():
        user = User(
            email="demo@example.com",
            full_name="John Doe",
            hashed_password=get_password_hash("password123"),
            language="english",
            level="B2 - Upper Intermediate"
        )
        db.add(user)
        db.flush()

        # Create user settings
        user_settings = UserSettings(user_id=user.id)
        db.add(user_settings)

        # Create sample courses
        course1 = Course(
            title="Beginner's Guide",
            description="Start your language learning journey with fundamental concepts and basic vocabulary",
            icon="fas fa-book",
            duration_hours=4.0,
            lesson_count=12
        )
        db.add(course1)
        db.flush()

        course2 = Course(
            title="Conversation Skills",
            description="Master everyday conversations and improve your speaking confidence",
            icon="fas fa-comments",
            duration_hours=6.0,
            lesson_count=15
        )
        db.add(course2)
        db.flush()

        course3 = Course(
            title="Pronunciation Mastery",
            description="Perfect your pronunciation with expert guidance and practice exercises",
            icon="fas fa-microphone-alt",
            duration_hours=3.0,
            lesson_count=10
        )
        db.add(course3)
        db.flush()

        # Create sample lessons
        lessons_data = [
            {"course_id": course1.id, "title": "Introduction to Language", "order": 1, "duration_minutes": 20},
            {"course_id": course1.id, "title": "Basic Vocabulary", "order": 2, "duration_minutes": 25},
            {"course_id": course2.id, "title": "Greetings and Introductions", "order": 1, "duration_minutes": 30},
            {"course_id": course2.id, "title": "Daily Conversations", "order": 2, "duration_minutes": 35},
            {"course_id": course3.id, "title": "Vowel Sounds", "order": 1, "duration_minutes": 20},
            {"course_id": course3.id, "title": "Consonant Sounds", "order": 2, "duration_minutes": 25},
        ]

        for lesson_data in lessons_data:
            lesson = Lesson(**lesson_data)
            db.add(lesson)

        # Create sample progress
        progress1 = UserProgress(
            user_id=user.id,
            lesson_id=1,
            status=LessonStatus.COMPLETED,
            progress_percentage=100.0,
            accuracy=85.0,
            time_spent_minutes=20,
            completed_at=datetime.utcnow() - timedelta(days=1)
        )
        db.add(progress1)

        # Create sample practice sessions
        practice1 = PracticeSession(
            user_id=user.id,
            practice_type=PracticeType.CONVERSATION,
            accuracy=85.0,
            duration_minutes=30
        )
        db.add(practice1)

        practice2 = PracticeSession(
            user_id=user.id,
            practice_type=PracticeType.PRONUNCIATION,
            accuracy=78.0,
            duration_minutes=25
        )
        db.add(practice2)

        # Create sample achievements
        achievement1 = Achievement(
            user_id=user.id,
            title="Progress Master",
            description="Completed 10 lessons in a row",
            icon="fas fa-chart-bar"
        )
        db.add(achievement1)

        achievement2 = Achievement(
            user_id=user.id,
            title="Consistency King",
            description="7-day learning streak",
            icon="fas fa-calendar-check"
        )
        db.add(achievement2)

        # Create sample module progress
        module1 = ModuleProgress(
            user_id=user.id,
            module_name="Conversation Practice",
            progress_percentage=75.0,
            accuracy=85.0,
            sessions_count=15,
            time_spent_minutes=150
        )
        db.add(module1)

        module2 = ModuleProgress(
            user_id=user.id,
            module_name="Pronunciation Training",
            progress_percentage=60.0,
            accuracy=78.0,
            sessions_count=12,
            time_spent_minutes=105
        )
        db.add(module2)

        db.commit()
        print("Database initialized successfully!")
        print(f"Sample user created: demo@example.com / password123")
    else:
        print("Database already initialized!")

except Exception as e:
    db.rollback()
    print(f"Error initializing database: {e}")
finally:
    db.close()

