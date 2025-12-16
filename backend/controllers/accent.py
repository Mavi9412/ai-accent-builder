"""
Accent Analysis Controller
Handles voice recording analysis, TTS generation, and comparison endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Body
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict
import os
import asyncio

from database import get_db
from auth import get_current_active_user, get_current_user_optional
from models import User, AccentSession, AccentType, WordAnalysis
from schemas.accent import (
    AccentAnalysisResponse, AccentSessionResponse, AccentComparisonResponse,
    GenerateCorrectAudioRequest, GenerateCorrectAudioResponse, WordFeedback,
    PracticeSentencesResponse
)
from services.audio_service import audio_service
from services.stt_service import stt_service
from services.tts_service import tts_service
from services.pronunciation_service import pronunciation_service
from services.comparison_service import comparison_service
from services.grammar_service import grammar_service
from services.dialect_service import dialect_service
from services.connected_speech_service import connected_speech_service
from services.followup_generation_service import FollowUpGenerationService

# Trained ML-based pronunciation scorer (hybrid approach)
try:
    from services.trained_pronunciation_service import trained_scorer
    TRAINED_SCORER_AVAILABLE = trained_scorer.is_loaded
    print(f"[AccentController] Trained scorer available: {TRAINED_SCORER_AVAILABLE}")
except Exception as e:
    print(f"[AccentController] Trained scorer not available: {e}")
    trained_scorer = None
    trained_scorer = None
    TRAINED_SCORER_AVAILABLE = False

# Initialize FollowUp Service
followup_service = FollowUpGenerationService(use_t5=True, t5_model_name="google/flan-t5-small")

router = APIRouter(prefix="/api/accent", tags=["Accent Analysis"])


@router.post("/analyze", response_model=AccentAnalysisResponse)
async def analyze_accent(
    file: UploadFile = File(...),
    target_accent: str = Form(default="british"),
    target_text: str = Form(default="The quick brown fox jumps over the lazy dog."),
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
        print(f"[DEBUG] Audio info: {audio_info}")
        
        # 2. Transcribe using Whisper
        print(f"[DEBUG] Transcribing audio: {user_audio_path}")
        transcription = stt_service.transcribe(user_audio_path)
        transcribed_text = transcription["transcribed_text"]
        word_timestamps = transcription["word_timestamps"]
        
        print(f"[DEBUG] Transcription result: text='{transcribed_text}', error={transcription.get('error')}")
        
        # Check for transcription errors first
        if transcription.get("error"):
            print(f"[ERROR] Transcription failed: {transcription['error']}")
            raise HTTPException(
                status_code=400,
                detail=f"Transcription error: {transcription['error']}"
            )
        
        if not transcribed_text.strip():
            print(f"[ERROR] Empty transcription for file: {user_audio_path}, size: {audio_info.get('size', 0)} bytes")
            raise HTTPException(
                status_code=400,
                detail="Could not detect any speech in the audio. Please speak clearly and try again."
            )
        
        # 3. Handle free practice mode vs targeted practice
        # If target_text is empty or special marker, use transcription as target (free practice)
        is_free_practice = not target_text or target_text.strip() == "" or target_text == "__FREE_PRACTICE__"
        
        if is_free_practice:
            # Free practice mode: use what user said as the target
            # This compares their pronunciation quality, not accuracy
            effective_target = transcribed_text
        else:
            # Targeted practice: compare against provided target
            effective_target = target_text
        
        # Generate correct pronunciation (TTS) with the effective target
        accent_enum = AccentType(target_accent.lower())
        tts_result = await tts_service.generate_british_pronunciation(effective_target)
        corrected_audio_path = tts_result["audio_path"]
        
        # 4. Analyze pronunciation - compare what user SAID vs what they SHOULD have said
        analysis_result = pronunciation_service.analyze_pronunciation(
            expected_text=effective_target,  # The target text (either provided or transcribed)
            transcribed_text=transcribed_text,  # What was actually transcribed from audio
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
        
        # Calculate scores - use trained hybrid model if available
        pronunciation_score = analysis_result["overall_score"]
        stress_score = 75.0
        
        # Use trained ML hybrid scorer for prosody/fluency if available
        ml_scores = None
        if TRAINED_SCORER_AVAILABLE and trained_scorer:
            try:
                import librosa
                audio_data, sr = librosa.load(user_audio_path, sr=16000)
                ml_scores = trained_scorer.score(audio_data, sr, use_hybrid=True)
                print(f"[AccentController] ML Hybrid scores: accuracy={ml_scores['accuracy']:.1f}, "
                      f"fluency={ml_scores['fluency']:.1f}, prosody={ml_scores['prosody']:.1f}")
                
                # Blend ML scores with heuristic scores
                # ML is better for fluency and prosody
                rhythm_score = ml_scores['fluency'] * 0.6 + rhythm_score * 0.4
                stress_score = ml_scores['prosody'] * 0.6 + stress_score * 0.4
                # Keep pronunciation score from text analysis (more accurate for word-level)
            except Exception as e:
                print(f"[AccentController] ML scoring failed, using heuristic: {e}")
        
        # Calculate REAL word accuracy: what % of target words were correctly transcribed
        target_words = [w.lower().strip('.,!?;:"\'') for w in effective_target.split() if w.strip()]
        transcribed_words = [w.lower().strip('.,!?;:"\'') for w in transcribed_text.split() if w.strip()]
        
        if target_words:
            matched_words = sum(1 for tw in target_words if tw in transcribed_words)
            word_accuracy_percentage = round((matched_words / len(target_words)) * 100, 1)
        else:
            word_accuracy_percentage = 0.0
        
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
                native_text=effective_target  # Compare against what they SHOULD have said
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
            word_accuracy_percentage=word_accuracy_percentage,
            audio_duration=session.audio_duration,
            word_feedback=word_feedback_list,
            original_audio_url=f"/api/accent/audio/{session.id}/original",
            corrected_audio_url=f"/api/accent/audio/{session.id}/corrected",
            created_at=session.created_at,
            advanced_analysis=advanced_result,
            timing_comparison=analysis_result.get("timing_comparison")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing accent: {str(e)}"
        )


@router.post("/analyze-stream")
async def analyze_accent_stream(
    file: UploadFile = File(...),
    target_accent: str = Form(default="british"),
    target_text: str = Form(default="The quick brown fox jumps over the lazy dog."),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Streaming analysis - returns results progressively as each stage completes.
    Uses Server-Sent Events (SSE) for real-time updates.
    """
    from fastapi.responses import StreamingResponse
    import json
    
    async def generate_stream():
        try:
            # Stage 1: Save audio
            yield f"data: {json.dumps({'stage': 'saving', 'progress': 10, 'message': 'Saving audio...'})}\n\n"
            
            audio_content = await file.read()
            user_audio_path, filename = await audio_service.save_user_recording(
                audio_content, current_user.id
            )
            
            if not file.filename.endswith('.wav'):
                user_audio_path = audio_service.convert_to_wav(user_audio_path)
            
            yield f"data: {json.dumps({'stage': 'saved', 'progress': 20, 'message': 'Audio saved'})}\n\n"
            await asyncio.sleep(0.1)
            
            # Stage 2: Transcription (STT)
            yield f"data: {json.dumps({'stage': 'transcribing', 'progress': 25, 'message': 'Transcribing speech...'})}\n\n"
            
            transcription = stt_service.transcribe(user_audio_path)
            transcribed_text = transcription["transcribed_text"]
            word_timestamps = transcription["word_timestamps"]
            
            yield f"data: {json.dumps({'stage': 'transcribed', 'progress': 40, 'message': 'Transcription complete', 'data': {'text': transcribed_text, 'word_count': len(word_timestamps)}})}\n\n"
            await asyncio.sleep(0.1)
            
            # Stage 3: Generate TTS
            yield f"data: {json.dumps({'stage': 'generating_tts', 'progress': 45, 'message': 'Generating native audio...'})}\n\n"
            
            is_free_practice = not target_text or target_text.strip() == "" or target_text == "__FREE_PRACTICE__"
            effective_target = transcribed_text if is_free_practice else target_text
            
            tts_result = await tts_service.generate_british_pronunciation(effective_target)
            corrected_audio_path = tts_result["audio_path"]
            
            yield f"data: {json.dumps({'stage': 'tts_ready', 'progress': 55, 'message': 'Native audio generated'})}\n\n"
            await asyncio.sleep(0.1)
            
            # Stage 4: Basic pronunciation analysis
            yield f"data: {json.dumps({'stage': 'analyzing_basic', 'progress': 60, 'message': 'Analyzing pronunciation...'})}\n\n"
            
            analysis_result = pronunciation_service.analyze_pronunciation(
                expected_text=effective_target,
                transcribed_text=transcribed_text,
                word_timestamps=word_timestamps
            )
            
            basic_scores = {
                'pronunciation_score': analysis_result["overall_score"],
                'word_count': analysis_result["word_count"],
                'error_count': analysis_result["error_count"]
            }
            
            yield f"data: {json.dumps({'stage': 'basic_complete', 'progress': 70, 'message': 'Basic analysis complete', 'data': basic_scores})}\n\n"
            await asyncio.sleep(0.1)
            
            # Stage 5: Advanced acoustic analysis
            yield f"data: {json.dumps({'stage': 'analyzing_acoustic', 'progress': 75, 'message': 'Analyzing acoustic features...'})}\n\n"
            
            try:
                advanced_result = pronunciation_service.analyze_advanced(
                    user_audio_path=user_audio_path,
                    native_audio_path=corrected_audio_path,
                    user_text=transcribed_text,
                    native_text=effective_target
                )
                
                # Send scores progressively
                if advanced_result and 'scores' in advanced_result:
                    scores = advanced_result['scores']
                    yield f"data: {json.dumps({'stage': 'scores_ready', 'progress': 85, 'message': 'Scores calculated', 'data': {'scores': scores}})}\n\n"
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                print(f"Advanced analysis error: {e}")
                advanced_result = None
            
            # Stage 6: Save to database
            yield f"data: {json.dumps({'stage': 'saving_results', 'progress': 90, 'message': 'Saving results...'})}\n\n"
            
            accent_enum = AccentType(target_accent.lower())
            audio_info = audio_service.get_audio_info(user_audio_path)
            
            pronunciation_score = analysis_result["overall_score"]
            rhythm_score = advanced_result.get('scores', {}).get('rhythm_timing', 70) if advanced_result else 70
            intonation_score = advanced_result.get('scores', {}).get('intonation', 70) if advanced_result else 70
            stress_score = advanced_result.get('scores', {}).get('stress', 70) if advanced_result else 70
            
            overall_score = (pronunciation_score * 0.4 + rhythm_score * 0.2 + 
                            intonation_score * 0.2 + stress_score * 0.2)
            
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
            db.commit()
            db.refresh(session)
            
            # Save Word Analysis details
            if "word_scores" in analysis_result:
                for idx, word_data in enumerate(analysis_result["word_scores"]):
                    word_analysis = WordAnalysis(
                        session_id=session.id,
                        word=word_data.get("word", ""),
                        word_index=idx,
                        expected_phonemes=word_data.get("phonemes", ""),
                        actual_phonemes=word_data.get("actual_phonemes", ""), # Assuming this might be available later
                        pronunciation_score=word_data.get("score", 0.0),
                        is_correct=word_data.get("score", 0) >= 80,
                        # Add other detailed scores if available per word
                    )
                    db.add(word_analysis)
                db.commit() # Commit all word analyses
            
            # Generate Follow-up Question (with T5)
            followup_question = followup_service.generate_followup({
                **analysis_result,
                'overall_score': overall_score,
                'transcribed_text': transcribed_text,
                'word_analyses': analysis_result.get('word_scores', []), # Ensure this maps correctly
                'transcription': transcribed_text
            })
            
            # Stage 7: Complete
            final_result = {
                'session_id': session.id,
                'followup_question': followup_question,
                'transcribed_text': transcribed_text,
                'overall_score': round(overall_score, 1),
                'pronunciation_score': round(pronunciation_score, 1),
                'rhythm_score': round(rhythm_score, 1),
                'intonation_score': round(intonation_score, 1),
                'stress_score': round(stress_score, 1),
                'word_count': session.word_count,
                'error_count': session.error_count,
                'audio_duration': session.audio_duration,
                'original_audio_url': f"/api/accent/audio/{session.id}/original",
                'corrected_audio_url': f"/api/accent/audio/{session.id}/corrected",
                'advanced_analysis': advanced_result
            }
            
            yield f"data: {json.dumps({'stage': 'complete', 'progress': 100, 'message': 'Analysis complete!', 'data': final_result})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'stage': 'error', 'progress': 0, 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
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


# Practice sentences data - organized by category
PRACTICE_SENTENCES = {
    "Greetings": [
        {"id": 1, "text": "Hello, how are you today?", "difficulty": "Easy"},
        {"id": 2, "text": "Good morning, nice to meet you.", "difficulty": "Easy"},
        {"id": 3, "text": "Good afternoon, how have you been?", "difficulty": "Easy"},
        {"id": 4, "text": "Good evening, it is lovely to see you.", "difficulty": "Easy"},
        {"id": 5, "text": "Welcome to our home, please come in.", "difficulty": "Easy"},
    ],
    "Everyday": [
        {"id": 6, "text": "The weather is beautiful today.", "difficulty": "Easy"},
        {"id": 7, "text": "I would like a cup of tea, please.", "difficulty": "Easy"},
        {"id": 8, "text": "What time does the shop close?", "difficulty": "Easy"},
        {"id": 9, "text": "Could you help me find this address?", "difficulty": "Medium"},
        {"id": 10, "text": "I am looking for the nearest bus stop.", "difficulty": "Medium"},
    ],
    "Numbers": [
        {"id": 11, "text": "One, two, three, four, five.", "difficulty": "Easy"},
        {"id": 12, "text": "The price is twenty-five pounds.", "difficulty": "Easy"},
        {"id": 13, "text": "My phone number is zero seven nine.", "difficulty": "Medium"},
        {"id": 14, "text": "The meeting is at half past three.", "difficulty": "Medium"},
        {"id": 15, "text": "There are thirteen people in the room.", "difficulty": "Medium"},
    ],
    "Questions": [
        {"id": 16, "text": "Where is the nearest train station?", "difficulty": "Easy"},
        {"id": 17, "text": "How much does this cost?", "difficulty": "Easy"},
        {"id": 18, "text": "What would you like to eat?", "difficulty": "Easy"},
        {"id": 19, "text": "Could you repeat that, please?", "difficulty": "Medium"},
        {"id": 20, "text": "Would you mind opening the window?", "difficulty": "Medium"},
    ],
    "TH Sounds": [
        {"id": 21, "text": "This is the thing they need.", "difficulty": "Medium"},
        {"id": 22, "text": "The weather is rather rainy.", "difficulty": "Medium"},
        {"id": 23, "text": "Thank you for your thoughtfulness.", "difficulty": "Medium"},
        {"id": 24, "text": "I think that Thursday is better.", "difficulty": "Medium"},
        {"id": 25, "text": "The theatre is on the other side.", "difficulty": "Hard"},
    ],
    "Vowels": [
        {"id": 26, "text": "The cat sat on the mat.", "difficulty": "Easy"},
        {"id": 27, "text": "Please leave the keys on the table.", "difficulty": "Medium"},
        {"id": 28, "text": "I need to book a room for two nights.", "difficulty": "Medium"},
        {"id": 29, "text": "The food is really good here.", "difficulty": "Easy"},
        {"id": 30, "text": "She bought a beautiful blue dress.", "difficulty": "Medium"},
    ],
    "Consonants": [
        {"id": 31, "text": "She sells seashells by the seashore.", "difficulty": "Hard"},
        {"id": 32, "text": "Peter Piper picked a peck of peppers.", "difficulty": "Hard"},
        {"id": 33, "text": "Red lorry, yellow lorry.", "difficulty": "Hard"},
        {"id": 34, "text": "The rabbit ran really fast.", "difficulty": "Medium"},
        {"id": 35, "text": "Please pass the pepper and salt.", "difficulty": "Easy"},
    ],
    "Business": [
        {"id": 36, "text": "I would like to schedule a meeting.", "difficulty": "Medium"},
        {"id": 37, "text": "Thank you for your time today.", "difficulty": "Easy"},
        {"id": 38, "text": "Please find attached the report.", "difficulty": "Medium"},
        {"id": 39, "text": "I look forward to hearing from you.", "difficulty": "Medium"},
        {"id": 40, "text": "Could we discuss this further?", "difficulty": "Medium"},
    ],
    "Advanced": [
        {"id": 41, "text": "The quick brown fox jumps over the lazy dog.", "difficulty": "Medium"},
        {"id": 42, "text": "Pronunciation requires practice and patience.", "difficulty": "Hard"},
        {"id": 43, "text": "The cathedral stood majestically in the city centre.", "difficulty": "Hard"},
        {"id": 44, "text": "Environmental sustainability is crucially important.", "difficulty": "Hard"},
        {"id": 45, "text": "The pharmaceutical industry requires precise articulation.", "difficulty": "Hard"},
    ],
}


@router.get("/sentences", response_model=PracticeSentencesResponse)
async def get_practice_sentences():
    """
    Get all practice sentences organized by category
    
    Returns sentences for pronunciation practice with difficulty levels
    """
    return {"categories": PRACTICE_SENTENCES}


@router.get("/phonetics/word/{word}")
async def get_word_phonetics_endpoint(
    word: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get phonetic information for a single word
    
    Returns:
        - IPA transcription
        - Syllables list
        - Respelling (phonetic spelling)
        - Syllable count
    """
    from utils.phoneme_utils import get_word_phonetics
    return get_word_phonetics(word)


@router.post("/phonetics/sentence")
async def get_sentence_phonetics_endpoint(
    sentence: str = Form(...),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get phonetic information for all words in a sentence
    
    Returns list of phonetic info for each word including:
        - IPA transcription
        - Syllables list
        - Respelling
    """
    from utils.phoneme_utils import get_sentence_phonetics
    words_phonetics = get_sentence_phonetics(sentence)
    return {"sentence": sentence, "words": words_phonetics}


# ==================== ENHANCED ANALYSIS ENDPOINTS ====================

# Import new services
from services.audio_enhancement_service import audio_enhancement_service
from services.word_segmentation_service import word_segmentation_service
from services.visualization_service import visualization_service
from services.followup_generation_service import followup_generation_service
from services.report_service import report_service


@router.post("/analyze-enhanced")
async def analyze_enhanced(
    file: UploadFile = File(...),
    target_accent: str = Form(default="british"),
    target_text: str = Form(default=""),
    fast_mode: str = Form(default="false"),  # Skip heavy ML models for speed
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Enhanced analysis with audio cleaning, word segmentation, and visualization.
    
    Pipeline:
    1. Save and enhance audio (noise reduction, VAD, normalization)
    2. Transcribe with word timestamps
    3. Check grammar (British English)
    4. Generate reference TTS audio
    5. Segment both audios into word-level files
    6. Generate visualizations per word
    7. Analyze pronunciation and prosody
    8. Generate follow-up question
    9. Create diagnostic report
    """
    # Check file format (be lenient - accept common audio formats)
    filename = file.filename or "recording.webm"
    valid_extensions = ('.wav', '.mp3', '.webm', '.ogg', '.m4a', '.opus')
    if not filename.lower().endswith(valid_extensions):
        print(f"[analyze-enhanced] Warning: Unusual file format: {filename}")
    
    try:
        # Handle anonymous users (for testing)
        user_id = current_user.id if current_user else 0
        
        # 1. Save raw audio
        audio_content = await file.read()
        print(f"[analyze-enhanced] Received {len(audio_content)} bytes from {file.filename}")
        
        user_audio_path, filename = await audio_service.save_user_recording(
            audio_content, user_id, file.filename
        )
        print(f"[analyze-enhanced] Saved to: {user_audio_path}")
        
        # Convert to WAV if needed (webm, mp3, ogg need conversion)
        if not user_audio_path.endswith('.wav'):
            user_audio_path = audio_service.convert_to_wav(user_audio_path)
            print(f"[analyze-enhanced] Converted to: {user_audio_path}")
        
        # 2. Skip audio enhancement for now (can cause issues)
        # enhancement_result = audio_enhancement_service.enhance_audio(user_audio_path)
        # clean_audio_path = enhancement_result.get("clean_audio_path", user_audio_path)
        clean_audio_path = user_audio_path  # Use converted audio directly
        enhancement_result = {"noise_reduced": False, "vad_applied": False, "original_duration": 0, "clean_duration": 0}
        print(f"[analyze-enhanced] Using audio: {clean_audio_path}")
        
        # 3. Transcribe audio
        print(f"[analyze-enhanced] Starting transcription...")
        transcription = stt_service.transcribe(clean_audio_path)
        transcribed_text = transcription["transcribed_text"]
        word_timestamps = transcription["word_timestamps"]
        print(f"[analyze-enhanced] Transcribed: '{transcribed_text[:100] if transcribed_text else 'EMPTY'}'")
        
        if not transcribed_text.strip():
            raise HTTPException(
                status_code=400,
                detail="Could not detect any speech in the audio. Try speaking louder and closer to the microphone."
            )
        
        # 4. Check grammar (British English)
        grammar_result = None
        try:
            grammar_result = grammar_service.check_grammar(transcribed_text)
            print(f"[analyze-enhanced] Grammar check: {grammar_result.get('error_count', 0)} errors")
        except Exception as gram_error:
            print(f"Grammar check error: {gram_error}")
            grammar_result = {"corrected_text": transcribed_text, "errors": [], "error_count": 0}
        
        # 5. Determine effective target
        is_free_practice = not target_text or target_text.strip() == "" or target_text == "__FREE_PRACTICE__"
        effective_target = transcribed_text if is_free_practice else target_text
        
        # Check fast_mode - skip heavy processing
        is_fast_mode = fast_mode.lower() == "true"
        
        # 5. Generate reference TTS (SKIP in fast mode)
        ref_audio_path = None
        if not is_fast_mode:
            tts_result = await tts_service.generate_british_pronunciation(effective_target)
            ref_audio_path = tts_result["audio_path"]
        
        # 6. Segment user audio into words (SKIP in fast mode)
        session_id_str = f"session_{user_id}_{os.urandom(4).hex()}"
        word_visualizations = []
        user_segmentation = {}
        ref_segmentation = {}
        
        # Check if visualizations should be skipped for speed
        skip_visualizations = is_fast_mode or form.get("skip_visualizations", "false").lower() == "true"
        visualization_limit = 3  # Only visualize first 3 words for speed
        
        # Word segmentation (SKIP in fast mode)
        if not is_fast_mode and ref_audio_path:
            try:
                user_segmentation = word_segmentation_service.segment_audio(
                    clean_audio_path, word_timestamps, session_id_str
                )
                
                # 7. Segment reference audio
                ref_segmentation = word_segmentation_service.segment_reference_audio(
                    ref_audio_path, effective_target, 
                    user_segmentation.get("word_data", []),
                    session_id_str
                )
            
                # 8. Generate visualizations for each word (optional, limited for speed)
                if not skip_visualizations:
                    paired_words = ref_segmentation.get("paired_words", [])
                    
                    for paired in paired_words[:visualization_limit]:
                        try:
                            if paired.get("has_match") and paired.get("ref_audio_path"):
                                vis_result = visualization_service.generate_word_visualization(
                                    paired["user_audio_path"],
                                    paired["ref_audio_path"],
                                    paired["word"],
                                    session_id_str
                                )
                                word_visualizations.append({
                                    "word": paired["word"],
                                    "word_index": paired["word_index"],
                                    "plots": vis_result.get("plots", {})
                                })
                        except Exception as vis_error:
                            print(f"Visualization error for word {paired.get('word', 'unknown')}: {vis_error}")
                            continue
            except Exception as seg_error:
                print(f"Word segmentation error (continuing without): {seg_error}")
        
        # 9. Analyze pronunciation (FAST - rule-based)
        analysis_result = pronunciation_service.analyze_pronunciation(
            expected_text=effective_target,
            transcribed_text=transcribed_text,
            word_timestamps=word_timestamps
        )
        
        # 10. Advanced acoustic analysis (SKIP in fast mode - uses Wav2Vec2, Whisper)
        advanced_result = None
        if not is_fast_mode:
            try:
                advanced_result = pronunciation_service.analyze_advanced(
                    user_audio_path=clean_audio_path,
                    native_audio_path=ref_audio_path,
                    user_text=transcribed_text,
                    native_text=effective_target
                )
            except Exception as e:
                print(f"Advanced analysis error: {e}")
                advanced_result = None
        
        # 11. Generate follow-up question (optional)
        try:
            followup = followup_generation_service.generate_followup({
                "word_analyses": analysis_result.get("word_analyses", []),
                "transcribed_text": transcribed_text,
                "overall_score": analysis_result.get("overall_score", 0)
            })
        except Exception as fu_error:
            print(f"Follow-up generation error: {fu_error}")
            followup = {"question": "Continue practicing to improve your pronunciation.", "practice_words": []}
        
        # 12. Dialect detection (optional)
        dialect_result = None
        try:
            dialect_result = dialect_service.detect_dialect(transcribed_text)
            print(f"[analyze-enhanced] Dialect: {dialect_result.get('primary_dialect', 'rp')}")
        except Exception as dial_error:
            print(f"Dialect detection error: {dial_error}")
            dialect_result = {"primary_dialect": "rp", "rp_compliance": 100, "detected_features": []}
        
        # 13. Connected speech and L1 influence analysis (optional)
        connected_speech_result = None
        l1_influence_result = None
        try:
            connected_speech_result = connected_speech_service.analyze_connected_speech(
                transcribed_text, word_timestamps
            )
            l1_influence_result = connected_speech_service.detect_l1_influence(transcribed_text)
            print(f"[analyze-enhanced] L1 influence: {l1_influence_result.get('likely_l1', 'none')}")
        except Exception as cs_error:
            print(f"Connected speech analysis error: {cs_error}")
            connected_speech_result = {"fluency_score": 100, "linking_opportunities": []}
            l1_influence_result = {"influence_score": 0, "detected_patterns": []}
        
        # 14. Create database session (skip for anonymous users)
        accent_enum = AccentType(target_accent.lower())
        audio_info = audio_service.get_audio_info(clean_audio_path)
        
        pronunciation_score = analysis_result["overall_score"]
        rhythm_score = advanced_result.get('scores', {}).get('rhythm_timing', 70) if advanced_result else 70
        intonation_score = advanced_result.get('scores', {}).get('intonation', 70) if advanced_result else 70
        stress_score = advanced_result.get('scores', {}).get('stress', 70) if advanced_result else 70
        
        overall_score = (pronunciation_score * 0.4 + rhythm_score * 0.2 + 
                        intonation_score * 0.2 + stress_score * 0.2)
        
        session_id = None
        if user_id > 0:  # Only save to DB for authenticated users
            session = AccentSession(
                user_id=user_id,
                original_audio_path=user_audio_path,
                corrected_audio_path=ref_audio_path,
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
            db.commit()
            db.refresh(session)
            session_id = session.id
        else:
            # For anonymous users, generate a temporary session ID
            import random
            session_id = random.randint(100000, 999999)
        
        # 13. Generate diagnostic report (optional)
        report_summary = None
        # 15. Enrich word_analyses with timing and stress data
        enriched_word_analyses = analysis_result.get("word_analyses", [])
        timing_comparison = analysis_result.get("timing_comparison", {})
        timing_words = timing_comparison.get("words", [])
        
        for wa in enriched_word_analyses:
            word_idx = wa.get("word_index", -1)
            # Find matching timing data
            timing_data = next((tw for tw in timing_words if tw.get("word_index") == word_idx), None)
            if timing_data:
                # Add duration (in seconds)
                wa["duration"] = round(timing_data.get("user_duration_ms", 0) / 1000, 3)
                wa["expected_duration"] = round(timing_data.get("native_duration_ms", 0) / 1000, 3)
                wa["duration_diff"] = round(timing_data.get("timing_diff_ms", 0) / 1000, 3)
                wa["timing_status"] = timing_data.get("timing_status", "unknown")
                wa["stress_pattern"] = timing_data.get("ipa", "") # Use IPA as stress indicator
                wa["stress_correct"] = timing_data.get("is_correct", False)
                wa["tips"] = []
                if timing_data.get("feedback"):
                    wa["tips"].append(timing_data["feedback"])
            
            # Add acoustic data from advanced analysis if available
            if advanced_result:
                scores = advanced_result.get("scores", {})
                wa["pitch_correlation"] = scores.get("pitch_correlation", 70)
                wa["mfcc_similarity"] = scores.get("mfcc_similarity", 70)
        
        # 16. Generate TTS audio for follow-up question
        followup_audio_url = None
        if followup and followup.get("question"):
            try:
                followup_tts = await tts_service.generate_british_pronunciation(
                    followup["question"]
                )
                if followup_tts.get("audio_path"):
                    # Copy to public accessible location
                    followup_audio_url = f"/api/accent/audio/followup/{session_id if session_id else 'temp'}"
                    followup["audio_url"] = followup_audio_url
            except Exception as tts_err:
                print(f"Follow-up TTS error: {tts_err}")
        
        # 17. Generate report
        try:
            report = report_service.generate_report(
                session_data={
                    "session_id": session_id,
                    "user_id": user_id,
                    "transcribed_text": transcribed_text,
                    "target_text": effective_target,
                    "pronunciation_score": pronunciation_score,
                    "rhythm_score": rhythm_score,
                    "intonation_score": intonation_score,
                    "stress_score": stress_score,
                    "overall_score": overall_score,
                    "audio_duration": audio_info.get("duration", 0)
                },
                word_analyses=enriched_word_analyses,
                advanced_analysis=advanced_result,
                followup=followup
            )
            report_summary = report_service.get_report_summary(report)
        except Exception as rpt_error:
            print(f"Report generation error: {rpt_error}")
        
        return {
            "session_id": session_id,
            "transcribed_text": transcribed_text,
            "overall_score": round(overall_score, 1),
            "scores": {
                "pronunciation": round(pronunciation_score, 1),
                "rhythm": round(rhythm_score, 1),
                "intonation": round(intonation_score, 1),
                "stress": round(stress_score, 1)
            },
            "enhancement": {
                "noise_reduced": enhancement_result.get("noise_reduced", False),
                "vad_applied": enhancement_result.get("vad_applied", False),
                "original_duration": enhancement_result.get("original_duration", 0),
                "clean_duration": enhancement_result.get("clean_duration", 0)
            },
            "word_count": analysis_result.get("word_count", 0),
            "error_count": analysis_result.get("error_count", 0),
            "word_analyses": enriched_word_analyses,
            "word_visualizations": word_visualizations,
            "followup_question": followup,
            "followup_audio": followup_audio_url,
            "report_summary": report_summary,
            "grammar_analysis": grammar_result,
            "dialect_analysis": dialect_result,
            "connected_speech": connected_speech_result,
            "l1_influence": l1_influence_result,
            "audio_urls": {
                "original": f"/api/accent/audio/public/{session_id}/original",
                "corrected": f"/api/accent/audio/public/{session_id}/corrected"
            },
            "advanced_analysis": advanced_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Enhanced analysis error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error in enhanced analysis: {str(e)}"
        )


@router.get("/word-visualization/{session_id}/{word_index}")
async def get_word_visualization(
    session_id: int,
    word_index: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Get visualization plots for a specific word in a session.
    """
    # For authenticated users, verify ownership
    if current_user:
        session = db.query(AccentSession).filter(
            AccentSession.id == session_id,
            AccentSession.user_id == current_user.id
        ).first()
    else:
        # For anonymous users, just check if session exists
        session = db.query(AccentSession).filter(
            AccentSession.id == session_id
        ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    word_analysis = db.query(WordAnalysis).filter(
        WordAnalysis.session_id == session_id,
        WordAnalysis.word_index == word_index
    ).first()
    
    if not word_analysis:
        raise HTTPException(status_code=404, detail="Word analysis not found")
    
    session_dir = visualization_service.output_dir / f"session_{current_user.id}"
    word_safe = ''.join(c for c in word_analysis.word if c.isalnum())[:20]
    
    plots = {}
    for plot_type in ["waveform", "spectrogram", "pitch", "energy", "dashboard"]:
        plot_path = session_dir / f"{word_safe}_{plot_type}.png"
        if plot_path.exists():
            plots[plot_type] = f"/api/accent/visualization/{session_id}/{word_index}/{plot_type}"
    
    return {
        "word": word_analysis.word,
        "word_index": word_index,
        "session_id": session_id,
        "plots": plots,
        "score": word_analysis.pronunciation_score,
        "is_correct": word_analysis.is_correct,
        "feedback": word_analysis.feedback
    }


@router.get("/visualization/{session_id}/{word_index}/{plot_type}")
async def get_visualization_image(
    session_id: int,
    word_index: int,
    plot_type: str,
    db: Session = Depends(get_db)
):
    """Get a specific visualization image file."""
    session = db.query(AccentSession).filter(AccentSession.id == session_id).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    word_analysis = db.query(WordAnalysis).filter(
        WordAnalysis.session_id == session_id,
        WordAnalysis.word_index == word_index
    ).first()
    
    if not word_analysis:
        raise HTTPException(status_code=404, detail="Word not found")
    
    session_dir = visualization_service.output_dir / f"session_{session.user_id}"
    word_safe = ''.join(c for c in word_analysis.word if c.isalnum())[:20]
    plot_path = session_dir / f"{word_safe}_{plot_type}.png"
    
    if not plot_path.exists():
        raise HTTPException(status_code=404, detail="Visualization not found")
    
    return FileResponse(str(plot_path), media_type="image/png")


@router.get("/word-audio/{session_id}/{word_index}/{audio_type}")
async def get_word_audio(
    session_id: int,
    word_index: int,
    audio_type: str,
    db: Session = Depends(get_db)
):
    """Get audio file for a specific word segment (user or reference)."""
    # Try database session first
    session = db.query(AccentSession).filter(AccentSession.id == session_id).first()
    
    if session:
        user_dir = f"session_{session.user_id}"
    else:
        # For anonymous sessions, try user_0 directory
        user_dir = "session_0"
    
    segments_dir = word_segmentation_service.output_dir / user_dir
    
    # For anonymous sessions, try to find any matching word audio
    if not segments_dir.exists():
        # Check all session directories for matching word
        base_dir = word_segmentation_service.output_dir
        if base_dir.exists():
            for subdir in base_dir.iterdir():
                if subdir.is_dir():
                    segments_dir = subdir
                    break
    
    if not segments_dir.exists():
        raise HTTPException(status_code=404, detail="Audio segments not found")
    
    # Get word info from database or search by index
    word_safe = None
    if session:
        word_analysis = db.query(WordAnalysis).filter(
            WordAnalysis.session_id == session_id,
            WordAnalysis.word_index == word_index
        ).first()
        if word_analysis:
            word_safe = ''.join(c for c in word_analysis.word if c.isalnum())[:20]
    
    # Build file pattern
    if audio_type == "user":
        pattern = f"word_{word_index:03d}_*.wav"
    elif audio_type == "reference":
        pattern = f"ref_word_{word_index:03d}_*.wav"
    else:
        raise HTTPException(status_code=400, detail="Invalid audio_type")
    
    # Search for matching file
    import glob
    matches = list(segments_dir.glob(pattern))
    
    if matches:
        return FileResponse(str(matches[0]), media_type="audio/wav")
    
    # Try exact name if word_safe is known
    if word_safe:
        if audio_type == "user":
            audio_path = segments_dir / f"word_{word_index:03d}_{word_safe}.wav"
        else:
            audio_path = segments_dir / f"ref_word_{word_index:03d}_{word_safe}.wav"
        
        if audio_path.exists():
            return FileResponse(str(audio_path), media_type="audio/wav")
    
    raise HTTPException(status_code=404, detail=f"Word audio not found: {pattern}")


@router.get("/followup-question/{session_id}")
async def get_followup_question(
    session_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Get AI-generated follow-up practice question for a session."""
    # For authenticated users, verify ownership
    if current_user:
        session = db.query(AccentSession).filter(
            AccentSession.id == session_id,
            AccentSession.user_id == current_user.id
        ).first()
    else:
        # For anonymous users, just check if session exists
        session = db.query(AccentSession).filter(
            AccentSession.id == session_id
        ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    word_analyses = db.query(WordAnalysis).filter(
        WordAnalysis.session_id == session_id
    ).order_by(WordAnalysis.word_index).all()
    
    word_data = [
        {
            "word": wa.word,
            "word_index": wa.word_index,
            "score": wa.pronunciation_score,
            "is_correct": wa.is_correct,
            "expected_phonemes": wa.expected_phonemes,
            "actual_phonemes": wa.actual_phonemes,
            "feedback": wa.feedback or ""
        }
        for wa in word_analyses
    ]
    
    followup = followup_generation_service.generate_followup({
        "word_analyses": word_data,
        "transcribed_text": session.transcribed_text,
        "overall_score": session.overall_score
    })
    
    return followup


@router.get("/diagnostic-report/{session_id}")
async def get_diagnostic_report(
    session_id: int,
    format: str = "json",
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Get comprehensive diagnostic report (json, html, or pdf format)."""
    # For authenticated users, verify ownership
    if current_user:
        session = db.query(AccentSession).filter(
            AccentSession.id == session_id,
            AccentSession.user_id == current_user.id
        ).first()
    else:
        # For anonymous users, just check if session exists
        session = db.query(AccentSession).filter(
            AccentSession.id == session_id
        ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    word_analyses = db.query(WordAnalysis).filter(
        WordAnalysis.session_id == session_id
    ).order_by(WordAnalysis.word_index).all()
    
    word_data = [
        {
            "word": wa.word,
            "word_index": wa.word_index,
            "score": wa.pronunciation_score,
            "pronunciation_score": wa.pronunciation_score,
            "is_correct": wa.is_correct,
            "expected_phonemes": wa.expected_phonemes or "",
            "actual_phonemes": wa.actual_phonemes or "",
            "feedback": wa.feedback or "",
            "stress_correct": True,
            "pitch_match": wa.rhythm_score or 70,
            "rhythm_score": wa.rhythm_score or 70
        }
        for wa in word_analyses
    ]
    
    followup = followup_generation_service.generate_followup({
        "word_analyses": word_data,
        "transcribed_text": session.transcribed_text,
        "overall_score": session.overall_score
    })
    
    report = report_service.generate_report(
        session_data={
            "session_id": session.id,
            "user_id": session.user_id,
            "transcribed_text": session.transcribed_text,
            "target_text": session.transcribed_text,
            "pronunciation_score": session.pronunciation_score,
            "rhythm_score": session.rhythm_score,
            "intonation_score": session.intonation_score,
            "stress_score": session.stress_score,
            "overall_score": session.overall_score,
            "audio_duration": session.audio_duration
        },
        word_analyses=word_data,
        advanced_analysis=None,
        followup=followup
    )
    
    if format == "json":
        return report_service.get_report_summary(report)
    elif format == "html":
        html_path = report_service.export_html(report)
        return FileResponse(html_path, media_type="text/html", filename=f"report_{session_id}.html")
    elif format == "pdf":
        pdf_path = report_service.export_pdf(report)
        if pdf_path is None:
            raise HTTPException(status_code=500, detail="PDF export not available")
        return FileResponse(pdf_path, media_type="application/pdf", filename=f"report_{session_id}.pdf")
    else:
        raise HTTPException(status_code=400, detail="Invalid format")


# Import export schema
from schemas.export_report import ExportReportRequest, WordAnalysisData, ExportScores, FollowUpData


@router.post("/export-report")
async def export_report_pdf(
    data: ExportReportRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Generate comprehensive PDF report from analysis data.
    
    This is a dedicated endpoint for PDF export that accepts complete
    analysis data and generates a professional report.
    
    Works for both authenticated and anonymous users.
    """
    try:
        print(f"[export-report] Received request for session {data.session_id}")
        print(f"[export-report] Text: {data.transcribed_text[:50]}...")
        print(f"[export-report] Score: {data.overall_score}, Words: {len(data.word_analyses)}")
        
        # Prepare scores
        scores = data.scores or ExportScores()
        
        # Create session data for report
        session_data = {
            'session_id': data.session_id,
            'user_id': current_user.id if current_user else 0,
            'transcribed_text': data.transcribed_text,
            'target_text': data.target_text or data.transcribed_text,
            'pronunciation_score': scores.pronunciation or data.overall_score,
            'rhythm_score': scores.rhythm,
            'intonation_score': scores.intonation,
            'stress_score': scores.stress,
            'overall_score': data.overall_score,
            'audio_duration': data.audio_duration,
            'word_count': data.word_count or len(data.word_analyses),
            'error_count': data.error_count
        }
        
        # Convert word analyses to expected format for report service
        formatted_words = []
        for wa in data.word_analyses:
            formatted_words.append({
                'word': wa.word,
                'word_index': wa.word_index,
                'score': wa.score,
                'pronunciation_score': wa.score,
                'is_correct': wa.is_correct,
                'expected_phonemes': wa.expected_phonemes,
                'actual_phonemes': wa.transcribed_phonemes,
                'feedback': wa.feedback,
                'stress_correct': wa.stress_correct if wa.stress_correct is not None else True,
                'pitch_match': 70,
                'rhythm_score': 70,
                'duration': wa.duration,
                'timing_status': wa.timing_status
            })
        
        # Prepare follow-up data
        followup = None
        if data.followup_question:
            followup = {
                'question': data.followup_question.question,
                'correction': data.followup_question.correction,
                'accent_tip': data.followup_question.accent_tip,
                'vocabulary_tip': data.followup_question.vocabulary_tip,
                'next_practice_sentence': data.followup_question.next_practice_sentence,
                'practice_words': []
            }
        
        # Generate report
        report = report_service.generate_report(
            session_data=session_data,
            word_analyses=formatted_words,
            advanced_analysis=data.advanced_analysis,
            followup=followup
        )
        
        # Export to PDF
        pdf_path = report_service.export_pdf(report)
        
        if pdf_path is None:
            raise HTTPException(status_code=500, detail="PDF export not available - reportlab not installed")
        
        print(f"[export-report] PDF generated: {pdf_path}")
        
        filename = f"pronunciation_report_{data.session_id or 'session'}.pdf"
        return FileResponse(
            pdf_path, 
            media_type="application/pdf", 
            filename=filename,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[export-report] Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


@router.post("/export-pdf")
async def export_pdf_direct(
    request_data: Dict = Body(...),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Legacy endpoint - redirects to export-report with Dict data.
    Maintained for backwards compatibility.
    """
    try:
        # Convert Dict to ExportReportRequest format
        scores_data = request_data.get('scores', {})
        scores = ExportScores(
            pronunciation=scores_data.get('pronunciation', request_data.get('overall_score', 0)),
            rhythm=scores_data.get('rhythm', 70),
            intonation=scores_data.get('intonation', 70),
            stress=scores_data.get('stress', 70)
        )
        
        word_analyses = []
        for wa in request_data.get('word_analyses', []):
            word_analyses.append(WordAnalysisData(
                word=wa.get('word', ''),
                word_index=wa.get('word_index', 0),
                score=wa.get('score', 70),
                is_correct=wa.get('is_correct', True),
                expected_phonemes=wa.get('expected_phonemes', ''),
                transcribed_phonemes=wa.get('transcribed_phonemes', wa.get('actual_phonemes', '')),
                feedback=wa.get('feedback', ''),
                duration=wa.get('duration'),
                stress_correct=wa.get('stress_correct'),
                timing_status=wa.get('timing_status')
            ))
        
        followup_data = request_data.get('followup_question', {})
        followup = None
        if followup_data:
            followup = FollowUpData(
                question=followup_data.get('question', ''),
                correction=followup_data.get('correction', ''),
                accent_tip=followup_data.get('accent_tip', ''),
                vocabulary_tip=followup_data.get('vocabulary_tip', ''),
                next_practice_sentence=followup_data.get('next_practice_sentence', '')
            )
        
        export_data = ExportReportRequest(
            session_id=request_data.get('session_id', 0),
            transcribed_text=request_data.get('transcribed_text', ''),
            target_text=request_data.get('target_text'),
            overall_score=request_data.get('overall_score', 0),
            scores=scores,
            word_analyses=word_analyses,
            word_count=request_data.get('word_count', len(word_analyses)),
            error_count=request_data.get('error_count', 0),
            followup_question=followup,
            audio_duration=request_data.get('audio_duration', 0),
            grammar_analysis=request_data.get('grammar_analysis'),
            dialect_analysis=request_data.get('dialect_analysis'),
            advanced_analysis=request_data.get('advanced_analysis')
        )
        
        return await export_report_pdf(export_data, current_user)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[export-pdf] Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
