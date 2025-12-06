"""
Accent Analysis Controller
Handles voice recording analysis, TTS generation, and comparison endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional
import os
import asyncio

from database import get_db
from auth import get_current_active_user
from models import User, AccentSession, AccentType, WordAnalysis
from schemas.accent import (
    AccentAnalysisResponse, AccentSessionResponse, AccentComparisonResponse,
    GenerateCorrectAudioRequest, GenerateCorrectAudioResponse, WordFeedback
)
from services.audio_service import audio_service
from services.stt_service import stt_service
from services.tts_service import tts_service
from services.pronunciation_service import pronunciation_service
from services.comparison_service import comparison_service

router = APIRouter(prefix="/api/accent", tags=["Accent Analysis"])


@router.post("/analyze", response_model=AccentAnalysisResponse)
async def analyze_accent(
    file: UploadFile = File(...),
    target_accent: str = Form(default="british"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Analyze user's accent from uploaded audio file
    
    Steps:
    1. Save uploaded audio
    2. Transcribe using Vosk (STT)
    3. Generate correct pronunciation using Edge TTS
    4. Compare audio features
    5. Generate feedback
    """
    # Validate file type
    if not file.filename.endswith(('.wav', '.mp3', '.webm', '.ogg')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Supported: wav, mp3, webm, ogg"
        )
    
    try:
        # 1. Save user's recording
        audio_content = await file.read()
        user_audio_path, filename = await audio_service.save_user_recording(
            audio_content, current_user.id
        )
        
        # Convert to WAV if needed
        if not file.filename.endswith('.wav'):
            user_audio_path = audio_service.convert_to_wav(user_audio_path)
        
        # Validate audio
        is_valid, error_msg = audio_service.validate_audio_file(user_audio_path)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Get audio info
        audio_info = audio_service.get_audio_info(user_audio_path)
        
        # 2. Transcribe using Vosk
        transcription = stt_service.transcribe(user_audio_path)
        transcribed_text = transcription["transcribed_text"]
        word_timestamps = transcription["word_timestamps"]
        
        if not transcribed_text.strip():
            raise HTTPException(
                status_code=400,
                detail="Could not detect any speech in the audio. Please try again."
            )
        
        # 3. Generate correct pronunciation (TTS)
        accent_enum = AccentType(target_accent.lower())
        tts_result = await tts_service.generate_british_pronunciation(transcribed_text)
        corrected_audio_path = tts_result["audio_path"]
        
        # 4. Analyze pronunciation
        analysis_result = pronunciation_service.analyze_pronunciation(
            expected_text=transcribed_text,  # The text user intended to say
            transcribed_text=transcribed_text,  # What was actually transcribed
            word_timestamps=word_timestamps
        )
        
        # 5. Compare audio features (if librosa available)
        try:
            comparison_result = comparison_service.compare_audio(
                user_audio_path, corrected_audio_path
            )
            rhythm_score = comparison_result["rhythm_similarity"]
            intonation_score = comparison_result["pitch_similarity"]
        except Exception:
            rhythm_score = 70.0  # Default scores
            intonation_score = 70.0
        
        # Calculate scores
        pronunciation_score = analysis_result["overall_score"]
        stress_score = 75.0  # Would need more analysis
        overall_score = (pronunciation_score * 0.4 + rhythm_score * 0.2 + 
                        intonation_score * 0.2 + stress_score * 0.2)
        
        # 6. Create session in database
        session = AccentSession(
            user_id=current_user.id,
            original_audio_path=user_audio_path,
            corrected_audio_path=corrected_audio_path,
            transcribed_text=transcribed_text,
            target_accent=accent_enum,
            overall_score=round(overall_score, 1),
            pronunciation_score=round(pronunciation_score, 1),
            rhythm_score=round(rhythm_score, 1),
            intonation_score=round(intonation_score, 1),
            stress_score=round(stress_score, 1),
            audio_duration=audio_info.get("duration", 0),
            word_count=analysis_result["word_count"],
            error_count=analysis_result["error_count"]
        )
        db.add(session)
        db.flush()  # Get session ID
        
        # 7. Save word analyses
        word_feedback_list = []
        for word_data in analysis_result["word_analyses"]:
            word_analysis = WordAnalysis(
                session_id=session.id,
                word=word_data["word"],
                word_index=word_data["word_index"],
                expected_phonemes=word_data.get("expected_phonemes"),
                actual_phonemes=word_data.get("actual_phonemes"),
                pronunciation_score=word_data["score"],
                stress_score=75.0,
                rhythm_score=rhythm_score,
                timestamp_start=word_data["timestamp_start"],
                timestamp_end=word_data["timestamp_end"],
                is_correct=word_data["is_correct"],
                feedback=word_data.get("feedback")
            )
            db.add(word_analysis)
            
            word_feedback_list.append(WordFeedback(
                word=word_data["word"],
                word_index=word_data["word_index"],
                is_correct=word_data["is_correct"],
                score=word_data["score"],
                transcribed_as=word_data.get("transcribed_as"),
                expected_phonemes=word_data.get("expected_phonemes"),
                actual_phonemes=word_data.get("actual_phonemes"),
                syllables=word_data.get("syllables"),
                syllable_breakdown=word_data.get("syllable_breakdown"),
                ipa=word_data.get("ipa"),
                timestamp_start=word_data["timestamp_start"],
                timestamp_end=word_data["timestamp_end"],
                feedback=word_data.get("feedback")
            ))
        
        db.commit()
        db.refresh(session)
        
        # 8. Perform advanced analysis (phoneme DTW + audio features)
        try:
            advanced_result = pronunciation_service.analyze_advanced(
                user_audio_path=user_audio_path,
                native_audio_path=corrected_audio_path,
                user_text=transcribed_text,
                native_text=transcribed_text  # Same text, comparing pronunciation
            )
        except Exception as e:
            print(f"Advanced analysis error (non-fatal): {e}")
            advanced_result = None
        
        return AccentAnalysisResponse(
            session_id=session.id,
            transcribed_text=transcribed_text,
            target_accent=accent_enum,
            overall_score=session.overall_score,
            pronunciation_score=session.pronunciation_score,
            rhythm_score=session.rhythm_score,
            intonation_score=session.intonation_score,
            stress_score=session.stress_score,
            word_count=session.word_count,
            error_count=session.error_count,
            audio_duration=session.audio_duration,
            word_feedback=word_feedback_list,
            original_audio_url=f"/api/accent/audio/{session.id}/original",
            corrected_audio_url=f"/api/accent/audio/{session.id}/corrected",
            created_at=session.created_at,
            advanced_analysis=advanced_result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing accent: {str(e)}"
        )


@router.get("/sessions", response_model=list[AccentSessionResponse])
def get_sessions(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all accent analysis sessions for current user"""
    sessions = db.query(AccentSession).filter(
        AccentSession.user_id == current_user.id
    ).order_by(AccentSession.created_at.desc()).offset(offset).limit(limit).all()
    
    return sessions


@router.get("/sessions/{session_id}", response_model=AccentSessionResponse)
def get_session(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get specific accent analysis session"""
    session = db.query(AccentSession).filter(
        AccentSession.id == session_id,
        AccentSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session


@router.post("/generate-correct", response_model=GenerateCorrectAudioResponse)
async def generate_correct_audio(
    request: GenerateCorrectAudioRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Generate correct pronunciation audio for given text"""
    try:
        accent = request.accent.value if hasattr(request.accent, 'value') else request.accent
        
        # Adjust rate based on speed parameter
        rate = "+0%"
        if request.speed < 1.0:
            rate = f"-{int((1.0 - request.speed) * 50)}%"
        elif request.speed > 1.0:
            rate = f"+{int((request.speed - 1.0) * 50)}%"
        
        result = await tts_service.generate_speech(
            text=request.text,
            accent=accent,
            rate=rate
        )
        
        return GenerateCorrectAudioResponse(
            audio_url=audio_service.get_audio_url(result["audio_path"]),
            text=request.text,
            accent=request.accent,
            duration=result["duration"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating audio: {str(e)}"
        )


@router.post("/compare/{session_id}", response_model=AccentComparisonResponse)
def compare_audio(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Compare user's audio with correct pronunciation for a session"""
    session = db.query(AccentSession).filter(
        AccentSession.id == session_id,
        AccentSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not session.original_audio_path or not session.corrected_audio_path:
        raise HTTPException(status_code=400, detail="Audio files not available")
    
    try:
        comparison = comparison_service.compare_audio(
            session.original_audio_path,
            session.corrected_audio_path
        )
        
        # Get word-level comparison
        word_analyses = db.query(WordAnalysis).filter(
            WordAnalysis.session_id == session_id
        ).all()
        
        word_comparisons = []
        for wa in word_analyses:
            word_comparisons.append({
                "word": wa.word,
                "score": wa.pronunciation_score,
                "is_correct": wa.is_correct,
                "feedback": wa.feedback
            })
        
        return AccentComparisonResponse(
            session_id=session_id,
            similarity_score=comparison["similarity_score"],
            word_comparisons=word_comparisons,
            pitch_difference=comparison.get("pitch_difference", 0),
            rhythm_difference=comparison.get("tempo_difference", 0),
            stress_difference=0,  # Would need additional analysis
            suggestions=comparison.get("suggestions", [])
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error comparing audio: {str(e)}"
        )


@router.get("/audio/public/{session_id}/corrected")
def get_corrected_audio_public(
    session_id: int,
    db: Session = Depends(get_db)
):
    """Get corrected (native speaker) audio - public endpoint"""
    session = db.query(AccentSession).filter(
        AccentSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    audio_path = session.corrected_audio_path
    
    if not audio_path or not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    # Determine media type
    if audio_path.endswith('.mp3'):
        media_type = "audio/mpeg"
    else:
        media_type = "audio/wav"
    
    return FileResponse(audio_path, media_type=media_type)


@router.get("/audio/public/{session_id}/{audio_type}")
def get_public_session_audio(
    session_id: int,
    audio_type: str,
    db: Session = Depends(get_db)
):
    """Get audio file for a session (public access for audio player)"""
    session = db.query(AccentSession).filter(AccentSession.id == session_id).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if audio_type == "original":
        audio_path = session.original_audio_path
    elif audio_type == "corrected":
        audio_path = session.corrected_audio_path
    else:
        raise HTTPException(status_code=400, detail="Invalid audio type")
    
    if not audio_path or not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    # Determine media type
    if audio_path.endswith('.mp3'):
        media_type = "audio/mpeg"
    else:
        media_type = "audio/wav"
    
    return FileResponse(audio_path, media_type=media_type)


@router.get("/audio/{session_id}/{audio_type}")
def get_session_audio(
    session_id: int,
    audio_type: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get audio file for a session (original or corrected)"""
    session = db.query(AccentSession).filter(
        AccentSession.id == session_id,
        AccentSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if audio_type == "original":
        audio_path = session.original_audio_path
    elif audio_type == "corrected":
        audio_path = session.corrected_audio_path
    else:
        raise HTTPException(status_code=400, detail="Invalid audio type")
    
    if not audio_path or not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    # Determine media type
    if audio_path.endswith('.mp3'):
        media_type = "audio/mpeg"
    else:
        media_type = "audio/wav"
    
    return FileResponse(audio_path, media_type=media_type)


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete an accent analysis session"""
    session = db.query(AccentSession).filter(
        AccentSession.id == session_id,
        AccentSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Delete audio files
    if session.original_audio_path:
        audio_service.delete_audio(session.original_audio_path)
    if session.corrected_audio_path:
        audio_service.delete_audio(session.corrected_audio_path)
    
    db.delete(session)
    db.commit()
    
    return {"message": "Session deleted successfully"}
