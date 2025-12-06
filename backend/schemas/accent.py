"""
Accent analysis schemas for request/response validation
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from models import AccentType


class AccentAnalysisRequest(BaseModel):
    """Request for analyzing user's accent from audio"""
    target_accent: AccentType = AccentType.BRITISH
    audio_format: str = "wav"


class WordFeedback(BaseModel):
    """Feedback for a single word"""
    word: str
    word_index: int
    is_correct: bool
    score: float
    transcribed_as: Optional[str] = None
    expected_phonemes: Optional[str] = None
    actual_phonemes: Optional[str] = None
    syllables: Optional[List[str]] = None
    syllable_breakdown: Optional[str] = None
    ipa: Optional[str] = None
    timestamp_start: float
    timestamp_end: float
    feedback: Optional[str] = None


class AccentAnalysisResponse(BaseModel):
    """Response from accent analysis"""
    session_id: int
    transcribed_text: str
    target_accent: AccentType
    
    # Scores (0-100)
    overall_score: float
    pronunciation_score: float
    rhythm_score: float
    intonation_score: float
    stress_score: float
    
    # Statistics
    word_count: int
    error_count: int
    audio_duration: float
    
    # Word-level feedback
    word_feedback: List[WordFeedback]
    
    # Audio paths
    original_audio_url: Optional[str] = None
    corrected_audio_url: Optional[str] = None
    
    created_at: datetime

    # Advanced analysis (optional, for detailed feedback)
    advanced_analysis: Optional[dict] = None

    class Config:
        from_attributes = True


class AccentSessionResponse(BaseModel):
    """Response for accent session details"""
    id: int
    user_id: int
    transcribed_text: Optional[str]
    target_accent: AccentType
    overall_score: float
    pronunciation_score: float
    rhythm_score: float
    intonation_score: float
    stress_score: float
    word_count: int
    error_count: int
    audio_duration: float
    original_audio_path: Optional[str]
    corrected_audio_path: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AccentComparisonResponse(BaseModel):
    """Response for comparing user audio vs correct audio"""
    session_id: int
    
    # Overall comparison
    similarity_score: float  # 0-100
    
    # Per-word comparison
    word_comparisons: List[dict]
    
    # Feature differences
    pitch_difference: float
    rhythm_difference: float
    stress_difference: float
    
    # Improvement suggestions
    suggestions: List[str]


class GenerateCorrectAudioRequest(BaseModel):
    """Request to generate correct pronunciation audio"""
    text: str
    accent: AccentType = AccentType.BRITISH
    speed: float = 1.0  # 0.5 to 2.0


class GenerateCorrectAudioResponse(BaseModel):
    """Response with generated audio information"""
    audio_url: str
    text: str
    accent: AccentType
    duration: float
