"""
Progress tracking routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
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
import os
from pathlib import Path

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

    # === Pronunciation Session Stats ===
    from models import AccentSession, WordAnalysis
    
    # Get all pronunciation sessions for this user
    accent_sessions = db.query(AccentSession).filter(
        AccentSession.user_id == current_user.id
    ).all()
    
    pronunciation_sessions = len(accent_sessions)
    avg_pronunciation_score = 0.0
    words_practiced = 0
    grammar_corrections = 0
    
    if accent_sessions:
        # Calculate average pronunciation score
        total_score = sum([s.overall_score or 0 for s in accent_sessions])
        avg_pronunciation_score = total_score / len(accent_sessions)
        
        # Count total words practiced and errors
        words_practiced = sum([s.word_count or 0 for s in accent_sessions])
        grammar_corrections = sum([s.error_count or 0 for s in accent_sessions])
    
    # === Weekly Data for Charts ===
    weekly_scores = []
    weekly_labels = []
    
    # Get last 7 days of data
    for i in range(6, -1, -1):
        day = datetime.utcnow().date() - timedelta(days=i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        
        # Get sessions for this day
        day_sessions = db.query(AccentSession).filter(
            and_(
                AccentSession.user_id == current_user.id,
                AccentSession.created_at >= day_start,
                AccentSession.created_at <= day_end
            )
        ).all()
        
        # Calculate average score for this day
        if day_sessions:
            day_avg = sum([s.overall_score or 0 for s in day_sessions]) / len(day_sessions)
        else:
            day_avg = 0
        
        weekly_scores.append(round(day_avg, 1))
        weekly_labels.append(day.strftime("%a"))  # Mon, Tue, etc.

    return DashboardStats(
        completed_lessons=completed_lessons,
        day_streak=day_streak,
        overall_progress=round(overall_progress, 2),
        achievements_unlocked=achievements_count,
        total_learning_time_hours=round(total_learning_time_hours, 2),
        pronunciation_sessions=pronunciation_sessions,
        avg_pronunciation_score=round(avg_pronunciation_score, 1),
        words_practiced=words_practiced,
        grammar_corrections=grammar_corrections,
        weekly_scores=weekly_scores,
        weekly_labels=weekly_labels
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


# ==================== PDF EXPORT ====================

@router.get("/export/pdf")
def export_progress_pdf(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Export user progress report as PDF with charts and watermark"""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch, cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.pdfgen import canvas
        from reportlab.platypus.flowables import Flowable
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PDF export not available. Install reportlab: pip install reportlab"
        )
    
    # Try to import matplotlib for charts
    try:
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        import matplotlib.pyplot as plt
        import numpy as np
        from io import BytesIO
        MATPLOTLIB_AVAILABLE = True
    except ImportError:
        MATPLOTLIB_AVAILABLE = False
    
    from models import AccentSession
    
    # Get user stats
    accent_sessions = db.query(AccentSession).filter(
        AccentSession.user_id == current_user.id
    ).order_by(AccentSession.created_at.desc()).all()
    
    pronunciation_sessions = len(accent_sessions)
    avg_score = 0.0
    words_practiced = 0
    total_errors = 0
    
    if accent_sessions:
        avg_score = sum([s.overall_score or 0 for s in accent_sessions]) / len(accent_sessions)
        words_practiced = sum([s.word_count or 0 for s in accent_sessions])
        total_errors = sum([s.error_count or 0 for s in accent_sessions])
    
    # Get weekly data
    weekly_scores = []
    weekly_labels = []
    for i in range(6, -1, -1):
        day = datetime.utcnow().date() - timedelta(days=i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        day_sessions = db.query(AccentSession).filter(
            and_(
                AccentSession.user_id == current_user.id,
                AccentSession.created_at >= day_start,
                AccentSession.created_at <= day_end
            )
        ).all()
        if day_sessions:
            day_avg = sum([s.overall_score or 0 for s in day_sessions]) / len(day_sessions)
        else:
            day_avg = 0
        weekly_scores.append(round(day_avg, 1))
        weekly_labels.append(day.strftime("%a"))
    
    # Get achievements
    achievements = db.query(Achievement).filter(
        Achievement.user_id == current_user.id
    ).all()
    
    # Create output directory
    output_dir = Path(__file__).parent.parent / "uploads" / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    charts_dir = output_dir / "charts"
    charts_dir.mkdir(exist_ok=True)
    
    filename = f"progress_report_{current_user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    output_path = output_dir / filename
    
    # Generate charts if matplotlib available
    chart_paths = []
    if MATPLOTLIB_AVAILABLE:
        plt.style.use('default')
        
        # 1. Skills Radar Chart
        fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(projection='polar'))
        categories = ['Pronunciation', 'Fluency', 'Accuracy', 'Vocabulary', 'Grammar']
        N = len(categories)
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]
        
        # Calculate skill scores from sessions
        pronunciation_skill = min(100, avg_score)
        fluency_skill = min(100, max(0, 100 - (total_errors * 5))) if pronunciation_sessions > 0 else 0
        accuracy_skill = min(100, (words_practiced / max(1, pronunciation_sessions)) * 10) if pronunciation_sessions > 0 else 0
        vocab_skill = min(100, words_practiced / 5) if words_practiced > 0 else 0
        grammar_skill = min(100, max(0, 100 - (total_errors * 3))) if pronunciation_sessions > 0 else 0
        
        values = [pronunciation_skill, fluency_skill, accuracy_skill, vocab_skill, grammar_skill]
        values += values[:1]
        
        ax.plot(angles, values, 'o-', linewidth=2, color='#1a73e8')
        ax.fill(angles, values, alpha=0.25, color='#1a73e8')
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=10)
        ax.set_ylim(0, 100)
        ax.set_title('Skills Overview', fontsize=14, fontweight='bold', color='#1a73e8', pad=20)
        
        skills_path = charts_dir / f"skills_{current_user.id}.png"
        plt.savefig(skills_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        chart_paths.append(('skills', skills_path))
        
        # 2. Weekly Progress Chart
        fig, ax = plt.subplots(figsize=(6, 3))
        bars = ax.bar(weekly_labels, weekly_scores, color='#1a73e8', edgecolor='white', linewidth=1)
        ax.set_ylabel('Score (%)', fontsize=10)
        ax.set_title('Weekly Progress', fontsize=14, fontweight='bold', color='#1a73e8')
        ax.set_ylim(0, 100)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        for bar, score in zip(bars, weekly_scores):
            if score > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, f'{score:.0f}', 
                       ha='center', va='bottom', fontsize=9)
        
        weekly_path = charts_dir / f"weekly_{current_user.id}.png"
        plt.savefig(weekly_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        chart_paths.append(('weekly', weekly_path))
        
        # 3. Score Distribution Pie Chart
        if pronunciation_sessions > 0:
            fig, ax = plt.subplots(figsize=(4, 4))
            excellent = sum(1 for s in accent_sessions if (s.overall_score or 0) >= 80)
            good = sum(1 for s in accent_sessions if 60 <= (s.overall_score or 0) < 80)
            needs_work = sum(1 for s in accent_sessions if (s.overall_score or 0) < 60)
            
            sizes = [excellent, good, needs_work]
            labels_pie = ['Excellent (80+)', 'Good (60-79)', 'Needs Work (<60)']
            colors_pie = ['#22c55e', '#facc15', '#ef4444']
            explode = (0.05, 0, 0)
            
            if sum(sizes) > 0:
                ax.pie(sizes, explode=explode, labels=labels_pie, colors=colors_pie, autopct='%1.0f%%',
                      shadow=False, startangle=90)
                ax.set_title('Score Distribution', fontsize=14, fontweight='bold', color='#1a73e8')
                
                dist_path = charts_dir / f"distribution_{current_user.id}.png"
                plt.savefig(dist_path, dpi=150, bbox_inches='tight', facecolor='white')
                plt.close()
                chart_paths.append(('distribution', dist_path))
    
    # Custom watermark canvas - draws BEFORE content (background)
    class WatermarkCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._draw_background_watermark()
        
        def showPage(self):
            super().showPage()
            # Draw watermark on new page too
            self._draw_background_watermark()
        
        def _draw_background_watermark(self):
            """Draw low opacity watermark behind all content"""
            self.saveState()
            
            # Very low opacity watermark text - multiple instances for coverage
            self.setFillColor(colors.Color(0.1, 0.45, 0.91, alpha=0.08))  # Blue with 8% opacity
            self.setFont('Helvetica-Bold', 50)
            
            # Draw watermark text at multiple positions for full coverage
            positions = [
                (A4[0]/2, A4[1]*0.85, 35),
                (A4[0]/2, A4[1]*0.65, 35),
                (A4[0]/2, A4[1]*0.45, 35),
                (A4[0]/2, A4[1]*0.25, 35),
            ]
            
            for x, y, angle in positions:
                self.saveState()
                self.translate(x, y)
                self.rotate(angle)
                self.drawCentredString(0, 0, "AI ACCENT BUILDER")
                self.restoreState()
            
            # Draw large centered logo text with very low opacity
            self.setFillColor(colors.Color(0.1, 0.45, 0.91, alpha=0.05))  # 5% opacity
            self.setFont('Helvetica-Bold', 100)
            self.saveState()
            self.translate(A4[0]/2, A4[1]/2)
            self.rotate(45)
            self.drawCentredString(0, 0, "AI ACCENT")
            self.restoreState()
            
            self.restoreState()
            
            # Add subtle border
            self.setStrokeColor(colors.HexColor('#1a73e8'))
            self.setLineWidth(3)
            self.rect(20, 20, A4[0]-40, A4[1]-40, stroke=1, fill=0)
    
    # Build PDF with watermark
    doc = SimpleDocTemplate(
        str(output_path), 
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=60,
        bottomMargin=50
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=28,
        spaceAfter=5,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#1a73e8'),
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=14,
        spaceBefore=0,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#64748b')
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceBefore=15,
        spaceAfter=10,
        textColor=colors.HexColor('#1a73e8'),
        fontName='Helvetica-Bold'
    )
    
    achievement_style = ParagraphStyle(
        'Achievement',
        parent=styles['Normal'],
        fontSize=11,
        spaceBefore=8,
        spaceAfter=8,
        leftIndent=20,
        textColor=colors.HexColor('#1f2937'),
        backColor=colors.HexColor('#fef3c7'),
        borderPadding=8
    )
    
    elements = []
    
    # Header
    elements.append(Paragraph("🎯 AI ACCENT BUILDER", title_style))
    elements.append(Paragraph("Progress Report", subtitle_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # User Info Box
    user_info = f"""
    <para align="center">
    <b>User:</b> {current_user.email}<br/>
    <b>Report Generated:</b> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}<br/>
    <b>Total Sessions:</b> {pronunciation_sessions} | <b>Words Practiced:</b> {words_practiced}
    </para>
    """
    elements.append(Paragraph(user_info, ParagraphStyle('UserInfo', parent=styles['Normal'], 
                                                         fontSize=11, alignment=TA_CENTER,
                                                         backColor=colors.HexColor('#e0f2fe'),
                                                         borderPadding=15)))
    elements.append(Spacer(1, 0.3*inch))
    
    # Summary Statistics with colored boxes
    elements.append(Paragraph("📊 Summary Statistics", heading_style))
    
    stats_data = [
        ["📈 Practice Sessions", str(pronunciation_sessions), "🎯 Avg Score", f"{avg_score:.1f}%"],
        ["📝 Words Practiced", str(words_practiced), "🏆 Achievements", str(len(achievements))]
    ]
    
    stats_table = Table(stats_data, colWidths=[2*inch, 1.2*inch, 2*inch, 1.2*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#dbeafe')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#dcfce7')),
        ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#e0f2fe')),
        ('BACKGROUND', (3, 0), (3, -1), colors.HexColor('#d1fae5')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('FONTSIZE', (1, 0), (1, -1), 14),
        ('FONTSIZE', (3, 0), (3, -1), 14),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1a73e8')),
        ('TEXTCOLOR', (3, 0), (3, -1), colors.HexColor('#16a34a')),
        ('PADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 2, colors.white),
        ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#1a73e8'))
    ]))
    elements.append(stats_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Add Charts
    if chart_paths:
        elements.append(Paragraph("📈 Performance Charts", heading_style))
        
        for chart_type, chart_path in chart_paths:
            if chart_path.exists():
                img = Image(str(chart_path))
                if chart_type == 'skills':
                    img.drawWidth = 4*inch
                    img.drawHeight = 4*inch
                elif chart_type == 'weekly':
                    img.drawWidth = 5.5*inch
                    img.drawHeight = 2.5*inch
                else:
                    img.drawWidth = 3.5*inch
                    img.drawHeight = 3.5*inch
                elements.append(img)
                elements.append(Spacer(1, 0.2*inch))
    
    # Recent Sessions Table
    if accent_sessions:
        elements.append(Paragraph("📋 Recent Practice Sessions", heading_style))
        
        session_data = [["Date", "Score", "Words", "Transcription"]]
        for session in accent_sessions[:8]:
            score = session.overall_score or 0
            score_color = "🟢" if score >= 80 else ("🟡" if score >= 60 else "🔴")
            session_data.append([
                session.created_at.strftime("%b %d, %Y"),
                f"{score_color} {score}%",
                str(session.word_count or 0),
                (session.transcribed_text or "")[:35] + "..."
            ])
        
        session_table = Table(session_data, colWidths=[1.3*inch, 1*inch, 0.8*inch, 3.2*inch])
        session_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a73e8')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (3, 1), (3, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')])
        ]))
        elements.append(session_table)
        elements.append(Spacer(1, 0.3*inch))
    
    # Achievements Section
    elements.append(Paragraph("🏆 Achievements", heading_style))
    
    if achievements:
        for achievement in achievements:
            ach_text = f"⭐ <b>{achievement.title}</b> - {achievement.description or 'Achievement unlocked!'}"
            elements.append(Paragraph(ach_text, achievement_style))
    else:
        # Default achievements
        default_achievements = [
            ("🎤 First Steps", "Complete your first practice session"),
            ("📈 Rising Star", "Achieve 70% accuracy in pronunciation"),
            ("🔥 Consistency King", "Practice for 7 days in a row"),
            ("💎 Perfectionist", "Score 100% on any session"),
        ]
        for title, desc in default_achievements:
            ach_text = f"⬜ <b>{title}</b> - {desc} (Locked)"
            elements.append(Paragraph(ach_text, ParagraphStyle('LockedAchievement', 
                parent=styles['Normal'], fontSize=10, leftIndent=20,
                textColor=colors.HexColor('#9ca3af'), spaceBefore=5, spaceAfter=5)))
    
    elements.append(Spacer(1, 0.5*inch))
    
    # Footer
    footer_text = """
    <para align="center">
    <font color="#64748b" size="9">
    Generated by <b>AI Accent Builder</b> - Your British Accent Training Partner<br/>
    Keep practicing to improve your scores! 🇬🇧
    </font>
    </para>
    """
    elements.append(Paragraph(footer_text, styles['Normal']))
    
    # Build PDF with watermark
    doc.build(elements, canvasmaker=WatermarkCanvas)
    
    # Clean up chart images
    for _, chart_path in chart_paths:
        try:
            if chart_path.exists():
                chart_path.unlink()
        except:
            pass
    
    return FileResponse(
        path=str(output_path),
        filename=filename,
        media_type="application/pdf"
    )

