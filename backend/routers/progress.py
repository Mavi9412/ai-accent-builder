"""
Progress tracking routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List
from datetime import datetime, timedelta
from database import get_db
from models import (
    User, UserProgress, PracticeSession, Achievement, ModuleProgress,
    LessonStatus, PracticeType
)
from schemas_base import (
    UserProgressCreate, UserProgressUpdate, UserProgressResponse,
    PracticeSessionCreate, PracticeSessionResponse,
    AchievementResponse, ModuleProgressCreate, ModuleProgressUpdate,
    ModuleProgressResponse, DashboardStats
)
from auth import get_current_active_user

router = APIRouter(prefix="/api/progress", tags=["Progress"])


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics for current user"""
    # Completed lessons count
    completed_lessons = db.query(UserProgress).filter(
        and_(
            UserProgress.user_id == current_user.id,
            UserProgress.status == LessonStatus.COMPLETED
        )
    ).count()

    # Calculate day streak
    # Get all completed lessons and find the longest streak
    progress_records = db.query(UserProgress).filter(
        and_(
            UserProgress.user_id == current_user.id,
            UserProgress.completed_at.isnot(None)
        )
    ).order_by(UserProgress.completed_at.desc()).all()

    day_streak = 0
    if progress_records:
        current_date = datetime.utcnow().date()
        streak_date = current_date
        for record in progress_records:
            if record.completed_at:
                record_date = record.completed_at.date()
                if record_date == streak_date or record_date == streak_date - timedelta(days=1):
                    if record_date == streak_date - timedelta(days=1):
                        streak_date = record_date
                    day_streak += 1
                else:
                    break

    # Overall progress percentage
    all_progress = db.query(UserProgress).filter(
        UserProgress.user_id == current_user.id
    ).all()
    overall_progress = 0.0
    if all_progress:
        total_progress = sum([p.progress_percentage for p in all_progress])
        overall_progress = total_progress / len(all_progress)

    # Achievements count
    achievements_count = db.query(Achievement).filter(
        Achievement.user_id == current_user.id
    ).count()

    # Total learning time in hours
    total_minutes = db.query(func.sum(UserProgress.time_spent_minutes)).filter(
        UserProgress.user_id == current_user.id
    ).scalar() or 0
    total_learning_time_hours = total_minutes / 60.0

    return DashboardStats(
        completed_lessons=completed_lessons,
        day_streak=day_streak,
        overall_progress=round(overall_progress, 2),
        achievements_unlocked=achievements_count,
        total_learning_time_hours=round(total_learning_time_hours, 2)
    )


@router.get("/lessons", response_model=List[UserProgressResponse])
def get_user_progress(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all progress records for current user"""
    progress = db.query(UserProgress).filter(
        UserProgress.user_id == current_user.id
    ).all()
    return progress


@router.post("/lessons", response_model=UserProgressResponse, status_code=status.HTTP_201_CREATED)
def create_user_progress(
    progress_data: UserProgressCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create or update user progress for a lesson"""
    # Check if progress already exists
    existing_progress = db.query(UserProgress).filter(
        and_(
            UserProgress.user_id == current_user.id,
            UserProgress.lesson_id == progress_data.lesson_id
        )
    ).first()

    if existing_progress:
        # Update existing progress
        update_data = progress_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(existing_progress, field, value)
        
        # Set completed_at if status is completed
        if progress_data.status == LessonStatus.COMPLETED and not existing_progress.completed_at:
            existing_progress.completed_at = datetime.utcnow()
        
        db.commit()
        db.refresh(existing_progress)
        return existing_progress
    else:
        # Create new progress
        db_progress = UserProgress(
            user_id=current_user.id,
            **progress_data.dict()
        )
        if progress_data.status == LessonStatus.COMPLETED:
            db_progress.completed_at = datetime.utcnow()
        
        db.add(db_progress)
        db.commit()
        db.refresh(db_progress)
        return db_progress


@router.put("/lessons/{progress_id}", response_model=UserProgressResponse)
def update_user_progress(
    progress_id: int,
    progress_update: UserProgressUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update user progress"""
    progress = db.query(UserProgress).filter(
        and_(
            UserProgress.id == progress_id,
            UserProgress.user_id == current_user.id
        )
    ).first()

    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Progress record not found"
        )

    update_data = progress_update.dict(exclude_unset=True)
    
    # Set completed_at if status is being set to completed
    if "status" in update_data and update_data["status"] == LessonStatus.COMPLETED:
        if not progress.completed_at:
            update_data["completed_at"] = datetime.utcnow()

    for field, value in update_data.items():
        setattr(progress, field, value)

    db.commit()
    db.refresh(progress)
    return progress


# Practice Session routes
@router.get("/practice", response_model=List[PracticeSessionResponse])
def get_practice_sessions(
    practice_type: PracticeType = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get practice sessions for current user"""
    query = db.query(PracticeSession).filter(
        PracticeSession.user_id == current_user.id
    )
    
    if practice_type:
        query = query.filter(PracticeSession.practice_type == practice_type)
    
    sessions = query.order_by(PracticeSession.created_at.desc()).all()
    return sessions


@router.post("/practice", response_model=PracticeSessionResponse, status_code=status.HTTP_201_CREATED)
def create_practice_session(
    session_data: PracticeSessionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new practice session"""
    db_session = PracticeSession(
        user_id=current_user.id,
        **session_data.dict()
    )
    db.add(db_session)
    
    # Update module progress
    module_name = session_data.practice_type.value.replace("_", " ").title()
    module_progress = db.query(ModuleProgress).filter(
        and_(
            ModuleProgress.user_id == current_user.id,
            ModuleProgress.module_name == module_name
        )
    ).first()
    
    if module_progress:
        module_progress.sessions_count += 1
        module_progress.time_spent_minutes += session_data.duration_minutes
        # Update accuracy (weighted average)
        total_sessions = module_progress.sessions_count
        module_progress.accuracy = (
            (module_progress.accuracy * (total_sessions - 1) + session_data.accuracy) / total_sessions
        )
    else:
        module_progress = ModuleProgress(
            user_id=current_user.id,
            module_name=module_name,
            sessions_count=1,
            time_spent_minutes=session_data.duration_minutes,
            accuracy=session_data.accuracy,
            progress_percentage=min(100, session_data.accuracy)
        )
        db.add(module_progress)
    
    db.commit()
    db.refresh(db_session)
    return db_session


# Achievement routes
@router.get("/achievements", response_model=List[AchievementResponse])
def get_achievements(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all achievements for current user"""
    achievements = db.query(Achievement).filter(
        Achievement.user_id == current_user.id
    ).order_by(Achievement.unlocked_at.desc()).all()
    return achievements


@router.post("/achievements", response_model=AchievementResponse, status_code=status.HTTP_201_CREATED)
def create_achievement(
    title: str,
    description: str = None,
    icon: str = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new achievement for current user"""
    db_achievement = Achievement(
        user_id=current_user.id,
        title=title,
        description=description,
        icon=icon
    )
    db.add(db_achievement)
    db.commit()
    db.refresh(db_achievement)
    return db_achievement


# Module Progress routes
@router.get("/modules", response_model=List[ModuleProgressResponse])
def get_module_progress(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all module progress for current user"""
    modules = db.query(ModuleProgress).filter(
        ModuleProgress.user_id == current_user.id
    ).all()
    return modules


@router.get("/modules/{module_name}", response_model=ModuleProgressResponse)
def get_module_progress_by_name(
    module_name: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get progress for a specific module"""
    module = db.query(ModuleProgress).filter(
        and_(
            ModuleProgress.user_id == current_user.id,
            ModuleProgress.module_name == module_name
        )
    ).first()
    
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module progress not found"
        )
    return module


@router.put("/modules/{module_id}", response_model=ModuleProgressResponse)
def update_module_progress(
    module_id: int,
    module_update: ModuleProgressUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update module progress"""
    module = db.query(ModuleProgress).filter(
        and_(
            ModuleProgress.id == module_id,
            ModuleProgress.user_id == current_user.id
        )
    ).first()

    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module progress not found"
        )

    update_data = module_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(module, field, value)

    db.commit()
    db.refresh(module)
    return module

