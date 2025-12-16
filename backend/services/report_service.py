"""
Diagnostic Report Generation Service
Creates comprehensive analysis reports for FYP/research use

Report Sections:
1. Overall Scores (Pronunciation, Accent, Dialect, Grammar)
2. Sentence-Level Analysis
3. Word-Level Breakdown with Metrics
4. Visual Analysis (embedded plots)
5. Error Pattern Analysis
6. Improvement Suggestions
7. Follow-Up Question

Supports JSON, HTML, and PDF export formats.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import uuid

# PDF generation (optional)
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        Image, PageBreak, ListFlowable, ListItem
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("[ReportService] reportlab not available - PDF export disabled")


@dataclass
class ScoreBreakdown:
    """Score breakdown for a category."""
    category: str
    score: float
    max_score: float = 100.0
    grade: str = ""
    description: str = ""


@dataclass 
class WordReport:
    """Report data for a single word."""
    word: str
    word_index: int
    pronunciation_score: float
    stress_correct: bool
    pitch_match: float
    rhythm_score: float
    is_correct: bool
    phonemes_expected: str
    phonemes_actual: str
    feedback: str
    visualization_path: Optional[str] = None


@dataclass
class SentenceReport:
    """Report data for a sentence."""
    text: str
    overall_score: float
    word_count: int
    error_count: int
    words: List[WordReport]


@dataclass
class DiagnosticReport:
    """Complete diagnostic report."""
    session_id: int
    user_id: int
    created_at: str
    
    # Overall scores
    pronunciation_score: float
    accent_score: float
    dialect_score: float
    grammar_score: float
    overall_score: float
    
    # Analysis data
    transcribed_text: str
    target_text: str
    audio_duration: float
    
    # Detailed breakdowns
    sentences: List[SentenceReport]
    word_analyses: List[WordReport]
    
    # Error patterns
    error_patterns: Dict[str, int]
    common_mistakes: List[str]
    
    # Suggestions
    improvement_suggestions: List[str]
    priority_areas: List[str]
    
    # Follow-up
    followup_question: str
    practice_words: List[str]


class ReportService:
    """
    Service for generating comprehensive diagnostic reports.
    """
    
    def __init__(self, output_dir: str = None):
        """Initialize report service."""
        if output_dir is None:
            self.output_dir = Path(__file__).parent.parent / "uploads" / "reports"
        else:
            self.output_dir = Path(output_dir)
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"[ReportService] Initialized. PDF={REPORTLAB_AVAILABLE}")
    
    def generate_report(self, session_data: Dict, 
                        word_analyses: List[Dict],
                        advanced_analysis: Optional[Dict] = None,
                        followup: Optional[Dict] = None) -> DiagnosticReport:
        """
        Generate complete diagnostic report from session data.
        
        Args:
            session_data: Session information from database
            word_analyses: List of word-level analysis data
            advanced_analysis: Optional advanced acoustic analysis
            followup: Optional follow-up question data
            
        Returns:
            DiagnosticReport object
        """
        # Extract session info
        session_id = session_data.get('session_id', session_data.get('id', 0))
        user_id = session_data.get('user_id', 0)
        
        # Calculate scores
        pronunciation_score = session_data.get('pronunciation_score', 0)
        rhythm_score = session_data.get('rhythm_score', 70)
        intonation_score = session_data.get('intonation_score', 70)
        stress_score = session_data.get('stress_score', 70)
        
        # Derive accent and dialect scores
        accent_score = (rhythm_score + intonation_score + stress_score) / 3
        dialect_score = self._calculate_dialect_score(word_analyses)
        grammar_score = self._calculate_grammar_score(session_data)
        overall_score = session_data.get('overall_score', 
            (pronunciation_score * 0.4 + accent_score * 0.3 + 
             dialect_score * 0.15 + grammar_score * 0.15))
        
        # Create word reports
        word_reports = []
        for wa in word_analyses:
            word_reports.append(WordReport(
                word=wa.get('word', ''),
                word_index=wa.get('word_index', 0),
                pronunciation_score=wa.get('score', wa.get('pronunciation_score', 0)),
                stress_correct=wa.get('stress_correct', True),
                pitch_match=wa.get('pitch_match', 70),
                rhythm_score=wa.get('rhythm_score', 70),
                is_correct=wa.get('is_correct', True),
                phonemes_expected=wa.get('expected_phonemes', ''),
                phonemes_actual=wa.get('actual_phonemes', ''),
                feedback=wa.get('feedback', ''),
                visualization_path=wa.get('visualization_path')
            ))
        
        # Create sentence report
        transcribed_text = session_data.get('transcribed_text', '')
        sentence_report = SentenceReport(
            text=transcribed_text,
            overall_score=overall_score,
            word_count=len(word_analyses),
            error_count=sum(1 for wa in word_analyses if not wa.get('is_correct', True)),
            words=word_reports
        )
        
        # Analyze error patterns
        error_patterns = self._analyze_error_patterns(word_analyses)
        common_mistakes = self._identify_common_mistakes(word_analyses)
        
        # Generate suggestions
        improvement_suggestions = self._generate_improvement_suggestions(
            word_analyses, error_patterns, advanced_analysis
        )
        priority_areas = self._identify_priority_areas(error_patterns)
        
        # Get follow-up data
        followup_question = ""
        practice_words = []
        if followup:
            followup_question = followup.get('question', '')
            practice_words = followup.get('practice_words', [])
        
        # Create report
        report = DiagnosticReport(
            session_id=session_id,
            user_id=user_id,
            created_at=datetime.now().isoformat(),
            pronunciation_score=round(pronunciation_score, 1),
            accent_score=round(accent_score, 1),
            dialect_score=round(dialect_score, 1),
            grammar_score=round(grammar_score, 1),
            overall_score=round(overall_score, 1),
            transcribed_text=transcribed_text,
            target_text=session_data.get('target_text', transcribed_text),
            audio_duration=session_data.get('audio_duration', 0),
            sentences=[sentence_report],
            word_analyses=word_reports,
            error_patterns=error_patterns,
            common_mistakes=common_mistakes,
            improvement_suggestions=improvement_suggestions,
            priority_areas=priority_areas,
            followup_question=followup_question,
            practice_words=practice_words
        )
        
        return report
    
    def _calculate_dialect_score(self, word_analyses: List[Dict]) -> float:
        """Calculate dialect accuracy score based on vocabulary and patterns."""
        if not word_analyses:
            return 85.0
        
        # Simple heuristic: high pronunciation accuracy suggests correct dialect
        avg_score = sum(wa.get('score', wa.get('pronunciation_score', 70)) 
                       for wa in word_analyses) / len(word_analyses)
        
        # Adjust for British English patterns (placeholder)
        return min(100, avg_score * 1.1)
    
    def _calculate_grammar_score(self, session_data: Dict) -> float:
        """Calculate grammar score from session data."""
        # Check if grammar analysis is available
        grammar_feedback = session_data.get('grammar_feedback', [])
        
        if not grammar_feedback:
            return 95.0  # Assume good grammar if no errors detected
        
        # Deduct points for each error
        base_score = 100.0
        for error in grammar_feedback:
            severity = error.get('severity', 'minor')
            if severity == 'major':
                base_score -= 10
            elif severity == 'moderate':
                base_score -= 5
            else:
                base_score -= 2
        
        return max(0, base_score)
    
    def _analyze_error_patterns(self, word_analyses: List[Dict]) -> Dict[str, int]:
        """Analyze and count error patterns."""
        patterns = {
            'phoneme_errors': 0,
            'stress_errors': 0,
            'rhythm_errors': 0,
            'missing_words': 0,
            'substitutions': 0
        }
        
        for wa in word_analyses:
            if not wa.get('is_correct', True):
                patterns['phoneme_errors'] += 1
                
                feedback = wa.get('feedback', '').lower()
                if 'stress' in feedback:
                    patterns['stress_errors'] += 1
                if 'rhythm' in feedback or 'timing' in feedback:
                    patterns['rhythm_errors'] += 1
                if 'missing' in feedback:
                    patterns['missing_words'] += 1
                if 'substitut' in feedback or 'said' in feedback:
                    patterns['substitutions'] += 1
        
        return patterns
    
    def _identify_common_mistakes(self, word_analyses: List[Dict]) -> List[str]:
        """Identify the most common pronunciation mistakes."""
        mistakes = []
        
        for wa in word_analyses:
            if not wa.get('is_correct', True):
                word = wa.get('word', '')
                feedback = wa.get('feedback', '')
                
                if word and feedback:
                    mistakes.append(f"'{word}': {feedback}")
        
        # Return top 5 mistakes
        return mistakes[:5]
    
    def _generate_improvement_suggestions(self, word_analyses: List[Dict],
                                           error_patterns: Dict[str, int],
                                           advanced_analysis: Optional[Dict]) -> List[str]:
        """Generate prioritized improvement suggestions."""
        suggestions = []
        
        # Based on error patterns
        if error_patterns.get('phoneme_errors', 0) > 2:
            suggestions.append(
                "Focus on individual sound production. Practice problematic phonemes "
                "using minimal pairs and listen to native speaker examples."
            )
        
        if error_patterns.get('stress_errors', 0) > 0:
            suggestions.append(
                "Work on word stress patterns. British English has specific stress rules - "
                "practice with multisyllabic words and pay attention to emphasized syllables."
            )
        
        if error_patterns.get('rhythm_errors', 0) > 0:
            suggestions.append(
                "Improve your speech rhythm. English is stress-timed, meaning stressed "
                "syllables occur at regular intervals. Try shadowing native speakers."
            )
        
        # Based on advanced analysis
        if advanced_analysis:
            scores = advanced_analysis.get('scores', {})
            
            if scores.get('intonation', 100) < 70:
                suggestions.append(
                    "Your intonation patterns need attention. Practice the rising and "
                    "falling tones of British English, especially in questions and statements."
                )
            
            if scores.get('vowel_quality', 100) < 70:
                suggestions.append(
                    "Work on vowel sounds. British RP has distinct vowel qualities - "
                    "pay attention to the difference between short and long vowels."
                )
        
        # Generic suggestions if nothing specific
        if not suggestions:
            suggestions.append(
                "Continue practicing regularly. Consistency is key to improving pronunciation."
            )
            suggestions.append(
                "Listen to British media (BBC, podcasts) to absorb natural speech patterns."
            )
        
        return suggestions
    
    def _identify_priority_areas(self, error_patterns: Dict[str, int]) -> List[str]:
        """Identify priority improvement areas."""
        priorities = []
        
        # Sort by error count
        sorted_patterns = sorted(
            error_patterns.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        area_names = {
            'phoneme_errors': 'Individual Sound Production',
            'stress_errors': 'Word Stress Patterns',
            'rhythm_errors': 'Speech Rhythm and Timing',
            'missing_words': 'Word Clarity',
            'substitutions': 'Sound Distinctions'
        }
        
        for pattern, count in sorted_patterns:
            if count > 0:
                priorities.append(area_names.get(pattern, pattern))
        
        return priorities[:3]  # Top 3 priorities
    
    def export_json(self, report: DiagnosticReport, output_path: str = None) -> str:
        """Export report to JSON format."""
        if output_path is None:
            output_path = str(self.output_dir / f"report_{report.session_id}.json")
        
        # Convert dataclass to dict
        report_dict = asdict(report)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def export_html(self, report: DiagnosticReport, output_path: str = None) -> str:
        """Export report to HTML format."""
        if output_path is None:
            output_path = str(self.output_dir / f"report_{report.session_id}.html")
        
        html = self._generate_html_report(report)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return output_path
    
    def _generate_html_report(self, report: DiagnosticReport) -> str:
        """Generate HTML content for report."""
        # Score color based on value
        def score_color(score):
            if score >= 80:
                return '#4ECDC4'  # Green
            elif score >= 60:
                return '#FFE66D'  # Yellow
            else:
                return '#FF6B6B'  # Red
        
        # Generate word analysis rows
        word_rows = ""
        for word in report.word_analyses:
            status = "✓" if word.is_correct else "✗"
            status_class = "correct" if word.is_correct else "incorrect"
            word_rows += f"""
            <tr class="{status_class}">
                <td>{word.word}</td>
                <td>{word.pronunciation_score:.1f}%</td>
                <td>{"Yes" if word.stress_correct else "No"}</td>
                <td>{word.pitch_match:.1f}%</td>
                <td>{status}</td>
                <td>{word.feedback}</td>
            </tr>
            """
        
        # Generate suggestions list
        suggestions_list = "\n".join(
            f"<li>{s}</li>" for s in report.improvement_suggestions
        )
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pronunciation Analysis Report - Session {report.session_id}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            padding: 2rem;
            min-height: 100vh;
        }}
        .container {{ max-width: 1000px; margin: 0 auto; }}
        .header {{
            text-align: center;
            padding: 2rem;
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            margin-bottom: 2rem;
        }}
        .header h1 {{ color: #4ECDC4; margin-bottom: 0.5rem; }}
        .header .date {{ color: #888; }}
        
        .scores-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .score-card {{
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
        }}
        .score-card .score {{
            font-size: 2.5rem;
            font-weight: bold;
            margin: 0.5rem 0;
        }}
        .score-card .label {{ color: #888; font-size: 0.9rem; }}
        
        .section {{
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
        }}
        .section h2 {{
            color: #4ECDC4;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        th {{ color: #4ECDC4; }}
        tr.correct td:first-child {{ color: #4ECDC4; }}
        tr.incorrect td:first-child {{ color: #FF6B6B; }}
        
        ul {{ padding-left: 1.5rem; }}
        li {{ margin: 0.5rem 0; }}
        
        .followup {{
            background: linear-gradient(135deg, #4ECDC4 0%, #44A08D 100%);
            color: #1a1a2e;
            border-radius: 12px;
            padding: 1.5rem;
            margin-top: 2rem;
        }}
        .followup h3 {{ margin-bottom: 0.5rem; }}
        
        .footer {{
            text-align: center;
            padding: 2rem;
            color: #666;
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Pronunciation Analysis Report</h1>
            <p class="date">Generated: {report.created_at}</p>
            <p>Session ID: {report.session_id}</p>
        </div>
        
        <div class="scores-grid">
            <div class="score-card">
                <div class="label">Overall Score</div>
                <div class="score" style="color: {score_color(report.overall_score)}">{report.overall_score}%</div>
            </div>
            <div class="score-card">
                <div class="label">Pronunciation</div>
                <div class="score" style="color: {score_color(report.pronunciation_score)}">{report.pronunciation_score}%</div>
            </div>
            <div class="score-card">
                <div class="label">Accent</div>
                <div class="score" style="color: {score_color(report.accent_score)}">{report.accent_score}%</div>
            </div>
            <div class="score-card">
                <div class="label">Dialect</div>
                <div class="score" style="color: {score_color(report.dialect_score)}">{report.dialect_score}%</div>
            </div>
            <div class="score-card">
                <div class="label">Grammar</div>
                <div class="score" style="color: {score_color(report.grammar_score)}">{report.grammar_score}%</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📝 Sentence Analysis</h2>
            <p><strong>Text:</strong> "{report.transcribed_text}"</p>
            <p><strong>Duration:</strong> {report.audio_duration:.1f} seconds</p>
            <p><strong>Words:</strong> {len(report.word_analyses)} total, {sum(1 for w in report.word_analyses if not w.is_correct)} with issues</p>
        </div>
        
        <div class="section">
            <h2>📊 Word-Level Breakdown</h2>
            <table>
                <thead>
                    <tr>
                        <th>Word</th>
                        <th>Score</th>
                        <th>Stress</th>
                        <th>Pitch</th>
                        <th>Status</th>
                        <th>Feedback</th>
                    </tr>
                </thead>
                <tbody>
                    {word_rows}
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>🎯 Priority Areas</h2>
            <ul>
                {"".join(f"<li>{area}</li>" for area in report.priority_areas)}
            </ul>
        </div>
        
        <div class="section">
            <h2>💡 Improvement Suggestions</h2>
            <ul>
                {suggestions_list}
            </ul>
        </div>
        
        {f'''
        <div class="followup">
            <h3>🔄 Next Step</h3>
            <p>{report.followup_question}</p>
            {f"<p><strong>Practice words:</strong> {', '.join(report.practice_words)}</p>" if report.practice_words else ""}
        </div>
        ''' if report.followup_question else ''}
        
        <div class="footer">
            <p>AI Accent Builder - British Pronunciation Training System</p>
            <p>Generated for FYP/Research purposes</p>
        </div>
    </div>
</body>
</html>
        """
        
        return html
    
    def export_pdf(self, report: DiagnosticReport, output_path: str = None) -> Optional[str]:
        """Export report to PDF format with watermark and enhanced styling."""
        if not REPORTLAB_AVAILABLE:
            print("[ReportService] PDF export not available - reportlab not installed")
            return None
        
        if output_path is None:
            output_path = str(self.output_dir / f"report_{report.session_id}.pdf")
        
        try:
            from reportlab.pdfgen import canvas
            
            # Custom watermark canvas
            class WatermarkCanvas(canvas.Canvas):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self._draw_background_watermark()
                
                def showPage(self):
                    super().showPage()
                    self._draw_background_watermark()
                
                def _draw_background_watermark(self):
                    """Draw low opacity watermark behind all content"""
                    self.saveState()
                    
                    # Very low opacity watermark text
                    self.setFillColor(colors.Color(0.1, 0.45, 0.91, alpha=0.08))
                    self.setFont('Helvetica-Bold', 50)
                    
                    # Draw watermark at multiple positions
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
                    
                    # Large centered logo
                    self.setFillColor(colors.Color(0.1, 0.45, 0.91, alpha=0.05))
                    self.setFont('Helvetica-Bold', 100)
                    self.saveState()
                    self.translate(A4[0]/2, A4[1]/2)
                    self.rotate(45)
                    self.drawCentredString(0, 0, "AI ACCENT")
                    self.restoreState()
                    
                    self.restoreState()
                    
                    # Subtle border
                    self.setStrokeColor(colors.HexColor('#1a73e8'))
                    self.setLineWidth(3)
                    self.rect(20, 20, A4[0]-40, A4[1]-40, stroke=1, fill=0)
            
            doc = SimpleDocTemplate(
                output_path, 
                pagesize=A4,
                rightMargin=50,
                leftMargin=50,
                topMargin=60,
                bottomMargin=50
            )
            styles = getSampleStyleSheet()
            story = []
            
            # Custom styles
            title_style = ParagraphStyle(
                'Title',
                parent=styles['Title'],
                fontSize=28,
                textColor=colors.HexColor('#1a73e8'),
                alignment=TA_CENTER,
                spaceAfter=5,
                fontName='Helvetica-Bold'
            )
            
            subtitle_style = ParagraphStyle(
                'Subtitle',
                parent=styles['Normal'],
                fontSize=14,
                textColor=colors.HexColor('#64748b'),
                alignment=TA_CENTER,
                spaceAfter=20
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=16,
                textColor=colors.HexColor('#1a73e8'),
                spaceBefore=15,
                spaceAfter=10,
                fontName='Helvetica-Bold'
            )
            
            # Header
            story.append(Paragraph("🎯 AI ACCENT BUILDER", title_style))
            story.append(Paragraph("Pronunciation Analysis Report", subtitle_style))
            story.append(Spacer(1, 0.2 * inch))
            
            # Session Info Box
            session_info = f"""
            <para align="center">
            <b>Session ID:</b> {report.session_id}<br/>
            <b>Report Generated:</b> {report.created_at}<br/>
            <b>Duration:</b> {report.audio_duration:.1f} seconds
            </para>
            """
            story.append(Paragraph(session_info, ParagraphStyle('SessionInfo', 
                parent=styles['Normal'], fontSize=11, alignment=TA_CENTER,
                backColor=colors.HexColor('#e0f2fe'), borderPadding=15)))
            story.append(Spacer(1, 0.3 * inch))
            
            # Overall Scores Grid
            story.append(Paragraph("📊 Score Summary", heading_style))
            
            score_data = [
                ["🎯 Overall", f"{report.overall_score}%", "🗣️ Pronunciation", f"{report.pronunciation_score}%"],
                ["🎭 Accent", f"{report.accent_score}%", "📝 Grammar", f"{report.grammar_score}%"]
            ]
            
            score_table = Table(score_data, colWidths=[2*inch, 1.2*inch, 2*inch, 1.2*inch])
            score_table.setStyle(TableStyle([
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
            story.append(score_table)
            story.append(Spacer(1, 0.3 * inch))
            
            # Transcribed Text
            story.append(Paragraph("🎤 Recorded Speech", heading_style))
            text_style = ParagraphStyle('TextBox', parent=styles['Normal'], 
                fontSize=12, backColor=colors.HexColor('#f8fafc'),
                borderPadding=10, spaceBefore=5, spaceAfter=10)
            story.append(Paragraph(f'"{report.transcribed_text}"', text_style))
            story.append(Spacer(1, 0.2 * inch))
            
            # Word-Level Breakdown
            if report.word_analyses:
                story.append(Paragraph("📋 Word-Level Breakdown", heading_style))
                word_data = [["Word", "Score", "Status", "Feedback"]]
                for word in report.word_analyses[:10]:
                    score = word.pronunciation_score
                    score_color = "🟢" if score >= 80 else ("🟡" if score >= 60 else "🔴")
                    status = "✓" if word.is_correct else "✗"
                    feedback = word.feedback[:35] + "..." if len(word.feedback) > 35 else word.feedback
                    word_data.append([
                        word.word,
                        f"{score_color} {score:.0f}%",
                        status,
                        feedback
                    ])
                
                word_table = Table(word_data, colWidths=[1.5*inch, 1*inch, 0.8*inch, 3*inch])
                word_table.setStyle(TableStyle([
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
                story.append(word_table)
                story.append(Spacer(1, 0.3 * inch))
            
            # Priority Areas
            if report.priority_areas:
                story.append(Paragraph("🎯 Priority Areas", heading_style))
                for area in report.priority_areas:
                    story.append(Paragraph(f"⚡ {area}", styles['Normal']))
                story.append(Spacer(1, 0.2 * inch))
            
            # Improvement Suggestions
            if report.improvement_suggestions:
                story.append(Paragraph("💡 Improvement Suggestions", heading_style))
                for suggestion in report.improvement_suggestions:
                    story.append(Paragraph(f"• {suggestion}", ParagraphStyle('Suggestion',
                        parent=styles['Normal'], fontSize=10, leftIndent=20,
                        spaceBefore=5, spaceAfter=5)))
                story.append(Spacer(1, 0.2 * inch))
            
            # Follow-up Question
            if report.followup_question:
                story.append(Paragraph("🔄 Next Practice", heading_style))
                followup_style = ParagraphStyle('Followup', parent=styles['Normal'],
                    fontSize=11, backColor=colors.HexColor('#fef3c7'),
                    borderPadding=10, textColor=colors.HexColor('#1f2937'))
                story.append(Paragraph(report.followup_question, followup_style))
                if report.practice_words:
                    story.append(Paragraph(f"<b>Practice words:</b> {', '.join(report.practice_words)}", styles['Normal']))
            
            story.append(Spacer(1, 0.5 * inch))
            
            # Footer
            footer_text = """
            <para align="center">
            <font color="#64748b" size="9">
            Generated by <b>AI Accent Builder</b> - Your British Accent Training Partner<br/>
            Keep practicing to improve your pronunciation! 🇬🇧
            </font>
            </para>
            """
            story.append(Paragraph(footer_text, styles['Normal']))
            
            # Build PDF with watermark
            doc.build(story, canvasmaker=WatermarkCanvas)
            
            return output_path
            
        except Exception as e:
            print(f"[ReportService] PDF export error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _get_grade(self, score: float) -> str:
        """Convert score to letter grade."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def get_report_summary(self, report: DiagnosticReport) -> Dict:
        """Get a concise summary of the report for API response."""
        return {
            "session_id": report.session_id,
            "overall_score": report.overall_score,
            "scores": {
                "pronunciation": report.pronunciation_score,
                "accent": report.accent_score,
                "dialect": report.dialect_score,
                "grammar": report.grammar_score
            },
            "word_count": len(report.word_analyses),
            "error_count": sum(1 for w in report.word_analyses if not w.is_correct),
            "priority_areas": report.priority_areas,
            "followup_question": report.followup_question,
            "created_at": report.created_at
        }


# Singleton instance
report_service = ReportService()
