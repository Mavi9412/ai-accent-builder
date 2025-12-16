"""
Export Report Schema - Data models for PDF export requests
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any


class WordAnalysisData(BaseModel):
    """Word-level analysis data for export"""
    word: str = ""
    word_index: int = 0
    score: float = 0
    is_correct: bool = True
    expected_phonemes: str = ""
    transcribed_phonemes: str = ""
    feedback: str = ""
    duration: Optional[float] = None
    stress_correct: Optional[bool] = None
    timing_status: Optional[str] = None


class ExportScores(BaseModel):
    """Score breakdown for export"""
    pronunciation: float = 0
    rhythm: float = 70
    intonation: float = 70
    stress: float = 70


class FollowUpData(BaseModel):
    """Follow-up question data"""
    question: str = ""
    correction: str = ""
    accent_tip: str = ""
    vocabulary_tip: str = ""
    next_practice_sentence: str = ""


class ExportReportRequest(BaseModel):
    """
    Complete request body for PDF export.
    Contains all analysis data needed to generate a full report.
    """
    session_id: int = Field(default=0, description="Session ID (can be 0 for anonymous)")
    transcribed_text: str = Field(default="", description="What the user said")
    target_text: Optional[str] = Field(default=None, description="Target sentence (if guided practice)")
    overall_score: float = Field(default=0, description="Overall score out of 100")
    scores: Optional[ExportScores] = Field(default=None, description="Detailed score breakdown")
    word_analyses: List[WordAnalysisData] = Field(default=[], description="Word-by-word analysis")
    word_count: int = Field(default=0, description="Total words analyzed")
    error_count: int = Field(default=0, description="Number of errors")
    followup_question: Optional[FollowUpData] = Field(default=None, description="AI-generated follow-up")
    audio_duration: float = Field(default=0, description="Recording duration in seconds")
    
    # Additional data
    grammar_analysis: Optional[Dict[str, Any]] = None
    dialect_analysis: Optional[Dict[str, Any]] = None
    advanced_analysis: Optional[Dict[str, Any]] = None


class ExportReportResponse(BaseModel):
    """Response for export request (before file download)"""
    success: bool
    message: str
    filename: Optional[str] = None
