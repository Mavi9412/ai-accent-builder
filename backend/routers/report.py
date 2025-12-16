"""
Report Export Router
Dedicated endpoints for generating PDF reports from pronunciation analysis
"""
from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import FileResponse
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

# Import PDF generator
from services.pdf_report_generator import pdf_report_generator


router = APIRouter(prefix="/api/report", tags=["Reports"])


class WordAnalysis(BaseModel):
    """Word-level analysis data"""
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


class Scores(BaseModel):
    """Score breakdown"""
    pronunciation: float = 0
    rhythm: float = 70
    intonation: float = 70
    stress: float = 70


class FollowUp(BaseModel):
    """Follow-up question data"""
    question: str = ""
    correction: str = ""
    accent_tip: str = ""
    vocabulary_tip: str = ""
    next_practice_sentence: str = ""


class ReportRequest(BaseModel):
    """Complete report request data"""
    session_id: int = Field(default=0)
    transcribed_text: str = Field(default="")
    target_text: Optional[str] = None
    overall_score: float = Field(default=0)
    scores: Optional[Scores] = None
    word_analyses: List[WordAnalysis] = Field(default=[])
    word_count: int = 0
    error_count: int = 0
    followup_question: Optional[FollowUp] = None
    audio_duration: float = 0
    
    # Advanced data
    advanced_analysis: Optional[Dict[str, Any]] = None
    grammar_analysis: Optional[Dict[str, Any]] = None
    dialect_analysis: Optional[Dict[str, Any]] = None
    voice_features: Optional[Dict[str, Any]] = None
    timing_comparison: Optional[Dict[str, Any]] = None


@router.post("/generate-pdf")
async def generate_pdf_report(data: ReportRequest):
    """
    Generate comprehensive PDF report from pronunciation analysis data
    
    Accepts all analysis data and generates a professional PDF report
    with watermark, styling, and detailed sections.
    """
    try:
        print(f"[Report] Generating PDF for session {data.session_id}")
        print(f"[Report] Text: '{data.transcribed_text[:50]}...'")
        print(f"[Report] Score: {data.overall_score}%, Words: {len(data.word_analyses)}")
        
        # Convert Pydantic models to dicts for the generator
        report_data = {
            'session_id': data.session_id,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'transcribed_text': data.transcribed_text,
            'target_text': data.target_text or data.transcribed_text,
            'overall_score': data.overall_score,
            'scores': data.scores.dict() if data.scores else {
                'pronunciation': data.overall_score,
                'rhythm': 70,
                'intonation': 70,
                'stress': 70
            },
            'word_analyses': [wa.dict() for wa in data.word_analyses],
            'word_count': data.word_count or len(data.word_analyses),
            'error_count': data.error_count,
            'followup_question': data.followup_question.dict() if data.followup_question else None,
            'audio_duration': data.audio_duration,
            'advanced_analysis': data.advanced_analysis,
            'grammar_analysis': data.grammar_analysis,
            'dialect_analysis': data.dialect_analysis,
            'voice_features': data.voice_features,
            'timing_comparison': data.timing_comparison,
        }
        
        # Generate PDF
        pdf_path = pdf_report_generator.generate_report(report_data)
        
        if not pdf_path:
            raise HTTPException(
                status_code=500, 
                detail="PDF generation failed - reportlab may not be installed"
            )
        
        print(f"[Report] PDF generated: {pdf_path}")
        
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
        print(f"[Report] Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@router.post("/export")
async def export_report(data: Dict[str, Any] = Body(...)):
    """
    Legacy/flexible endpoint that accepts raw dict data
    """
    try:
        print(f"[Report/Export] Generating PDF...")
        
        # Generate PDF directly from dict
        pdf_path = pdf_report_generator.generate_report(data)
        
        if not pdf_path:
            raise HTTPException(
                status_code=500, 
                detail="PDF generation failed"
            )
        
        session_id = data.get('session_id', datetime.now().strftime('%H%M%S'))
        filename = f"pronunciation_report_{session_id}.pdf"
        
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=filename,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Report/Export] Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
