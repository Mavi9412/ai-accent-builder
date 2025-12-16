"""
Comprehensive PDF Report Generator Service with Charts
Generates professional PDF reports with ALL pronunciation analysis data
including visual charts for prosody, timing, voice features, etc.
"""
import os
import io
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Any

# Try to import reportlab
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, Image, KeepTogether
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("[PDFReportGenerator] reportlab not available")

# Try to import matplotlib for charts
try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("[PDFReportGenerator] matplotlib not available for charts")


class WatermarkCanvas(canvas.Canvas):
    """Custom canvas that draws watermark behind content"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def showPage(self):
        self._draw_watermark()
        self._draw_border()
        super().showPage()
    
    def _draw_watermark(self):
        """Draw watermark text behind content"""
        self.saveState()
        self.setFillColor(colors.Color(0.4, 0.6, 0.9, alpha=0.05))
        self.setFont('Helvetica-Bold', 35)
        
        positions = [
            (letter[0]/2, letter[1]*0.80),
            (letter[0]/2, letter[1]*0.50),
            (letter[0]/2, letter[1]*0.20),
        ]
        
        for x, y in positions:
            self.saveState()
            self.translate(x, y)
            self.rotate(30)
            self.drawCentredString(0, 0, "AI ACCENT BUILDER")
            self.restoreState()
        
        self.restoreState()
    
    def _draw_border(self):
        """Draw decorative border"""
        self.saveState()
        self.setStrokeColor(colors.Color(0.29, 0.56, 0.89, alpha=0.2))
        self.setLineWidth(1.5)
        margin = 15
        self.rect(margin, margin, letter[0] - 2*margin, letter[1] - 2*margin)
        self.restoreState()


class PDFReportGenerator:
    """
    Comprehensive PDF Report Generator with Visual Charts
    """
    
    def __init__(self):
        self.output_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'uploads', 'reports'
        )
        os.makedirs(self.output_dir, exist_ok=True)
        
        if REPORTLAB_AVAILABLE:
            self.styles = getSampleStyleSheet()
            self._setup_custom_styles()
        
        print(f"[PDFReportGenerator] Initialized. PDF={REPORTLAB_AVAILABLE}, Charts={MATPLOTLIB_AVAILABLE}")
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=20,
            textColor=colors.Color(0.17, 0.24, 0.31),
            spaceAfter=15,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=colors.Color(0.29, 0.56, 0.89),
            spaceBefore=12,
            spaceAfter=8
        ))
        
        self.styles.add(ParagraphStyle(
            name='ReportBody',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.Color(0.3, 0.3, 0.3),
            spaceAfter=4
        ))
        
        self.styles.add(ParagraphStyle(
            name='SmallText',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.Color(0.4, 0.4, 0.4),
            spaceAfter=2
        ))
    
    def _get_score_color(self, score: float) -> colors.Color:
        """Get color based on score"""
        if score >= 80:
            return colors.Color(0.18, 0.8, 0.44)
        elif score >= 60:
            return colors.Color(0.95, 0.77, 0.06)
        else:
            return colors.Color(0.91, 0.30, 0.24)
    
    def _create_bar_chart(self, data: Dict[str, float], title: str, width: int = 400, height: int = 180) -> Optional[Image]:
        """Create a horizontal bar chart"""
        if not MATPLOTLIB_AVAILABLE or not data:
            return None
        
        try:
            fig, ax = plt.subplots(figsize=(width/100, height/100), dpi=100)
            
            labels = list(data.keys())
            values = list(data.values())
            colors_list = ['#2ecc71' if v >= 80 else '#f1c40f' if v >= 60 else '#e74c3c' for v in values]
            
            y_pos = np.arange(len(labels))
            bars = ax.barh(y_pos, values, color=colors_list, height=0.6)
            
            ax.set_yticks(y_pos)
            ax.set_yticklabels(labels, fontsize=8)
            ax.set_xlim(0, 100)
            ax.set_xlabel('Score (%)', fontsize=8)
            ax.set_title(title, fontsize=10, fontweight='bold', color='#2c3e50')
            
            # Add value labels on bars
            for bar, val in zip(bars, values):
                ax.text(bar.get_width() + 2, bar.get_y() + bar.get_height()/2, 
                       f'{val:.0f}%', va='center', fontsize=7)
            
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(axis='x', alpha=0.3)
            
            plt.tight_layout()
            
            # Save to buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            buf.seek(0)
            plt.close(fig)
            
            return Image(buf, width=width*0.8, height=height*0.8)
        except Exception as e:
            print(f"[Chart] Error creating bar chart: {e}")
            return None
    
    def _create_comparison_chart(self, user_data: Dict, native_data: Dict, title: str, width: int = 400, height: int = 180) -> Optional[Image]:
        """Create a comparison bar chart (user vs native)"""
        if not MATPLOTLIB_AVAILABLE:
            return None
        
        try:
            fig, ax = plt.subplots(figsize=(width/100, height/100), dpi=100)
            
            labels = list(user_data.keys())
            user_values = list(user_data.values())
            native_values = [native_data.get(k, 0) for k in labels]
            
            x = np.arange(len(labels))
            bar_width = 0.35
            
            bars1 = ax.bar(x - bar_width/2, user_values, bar_width, label='Your Voice', color='#3498db')
            bars2 = ax.bar(x + bar_width/2, native_values, bar_width, label='Native', color='#2ecc71')
            
            ax.set_ylabel('Value', fontsize=8)
            ax.set_title(title, fontsize=10, fontweight='bold', color='#2c3e50')
            ax.set_xticks(x)
            ax.set_xticklabels(labels, fontsize=7)
            ax.legend(fontsize=7, loc='upper right')
            
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            plt.tight_layout()
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
            buf.seek(0)
            plt.close(fig)
            
            return Image(buf, width=width*0.8, height=height*0.8)
        except Exception as e:
            print(f"[Chart] Error creating comparison chart: {e}")
            return None
    
    def _create_timing_chart(self, timing_data: List[Dict], width: int = 400, height: int = 150) -> Optional[Image]:
        """Create a timing comparison chart"""
        if not MATPLOTLIB_AVAILABLE or not timing_data:
            return None
        
        try:
            fig, ax = plt.subplots(figsize=(width/100, height/100), dpi=100)
            
            words = [t.get('word', '')[:8] for t in timing_data[:8]]
            diffs = [t.get('diff', 0) for t in timing_data[:8]]
            
            colors_list = ['#2ecc71' if abs(d) < 50 else '#f1c40f' if abs(d) < 100 else '#e74c3c' for d in diffs]
            
            x = np.arange(len(words))
            bars = ax.bar(x, diffs, color=colors_list)
            
            ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
            ax.set_ylabel('Difference (ms)', fontsize=8)
            ax.set_title('Timing Difference (User - Native)', fontsize=10, fontweight='bold', color='#2c3e50')
            ax.set_xticks(x)
            ax.set_xticklabels(words, fontsize=7, rotation=45)
            
            # Add legend
            from matplotlib.patches import Patch
            legend_elements = [
                Patch(facecolor='#2ecc71', label='On Time (<50ms)'),
                Patch(facecolor='#f1c40f', label='Slight (50-100ms)'),
                Patch(facecolor='#e74c3c', label='Off (>100ms)')
            ]
            ax.legend(handles=legend_elements, fontsize=6, loc='upper right')
            
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            plt.tight_layout()
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
            buf.seek(0)
            plt.close(fig)
            
            return Image(buf, width=width*0.8, height=height*0.8)
        except Exception as e:
            print(f"[Chart] Error creating timing chart: {e}")
            return None
    
    def _create_radar_chart(self, data: Dict[str, float], title: str, width: int = 300, height: int = 300) -> Optional[Image]:
        """Create a radar/spider chart for prosody analysis"""
        if not MATPLOTLIB_AVAILABLE or not data:
            return None
        
        try:
            categories = list(data.keys())
            values = list(data.values())
            
            # Close the radar chart
            values += values[:1]
            
            angles = [n / float(len(categories)) * 2 * np.pi for n in range(len(categories))]
            angles += angles[:1]
            
            fig, ax = plt.subplots(figsize=(width/100, height/100), subplot_kw=dict(polar=True), dpi=100)
            
            ax.plot(angles, values, 'o-', linewidth=2, color='#3498db')
            ax.fill(angles, values, alpha=0.25, color='#3498db')
            
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(categories, fontsize=8)
            ax.set_ylim(0, 100)
            ax.set_title(title, fontsize=10, fontweight='bold', color='#2c3e50', y=1.08)
            
            plt.tight_layout()
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
            buf.seek(0)
            plt.close(fig)
            
            return Image(buf, width=width*0.7, height=height*0.7)
        except Exception as e:
            print(f"[Chart] Error creating radar chart: {e}")
            return None
    
    def generate_report(self, data: Dict[str, Any]) -> Optional[str]:
        """Generate comprehensive PDF report with charts"""
        if not REPORTLAB_AVAILABLE:
            return None
        
        try:
            session_id = data.get('session_id', datetime.now().strftime('%Y%m%d_%H%M%S'))
            filename = f"pronunciation_report_{session_id}.pdf"
            filepath = os.path.join(self.output_dir, filename)
            
            doc = SimpleDocTemplate(
                filepath,
                pagesize=letter,
                rightMargin=40,
                leftMargin=40,
                topMargin=40,
                bottomMargin=40
            )
            
            story = []
            
            # Title
            story.append(Paragraph("Pronunciation Analysis Report", self.styles['ReportTitle']))
            story.append(self._build_session_info(data))
            
            # Main Scores with Chart
            story.extend(self._build_main_scores_with_chart(data))
            
            # Transcription
            story.extend(self._build_transcription(data))
            
            # Phoneme Alignment
            story.extend(self._build_phoneme_alignment(data))
            
            # Timing Comparison with Chart
            story.extend(self._build_timing_with_chart(data))
            
            # Detailed Analysis with Chart
            story.extend(self._build_detailed_analysis_with_chart(data))
            
            # Voice Feature Comparison with Chart
            story.extend(self._build_voice_features_with_chart(data))
            
            # ML Prosody Analysis with Radar Chart
            story.extend(self._build_ml_prosody_with_chart(data))
            
            # British English IPA
            story.extend(self._build_ipa_section(data))
            
            # Formant Analysis
            story.extend(self._build_formant_analysis(data))
            
            # Signal Analysis
            story.extend(self._build_signal_analysis(data))
            
            # Improvement Tips
            story.extend(self._build_improvement_tips(data))
            
            # Follow-up
            if data.get('followup_question'):
                story.extend(self._build_followup(data))
            
            # Footer
            story.append(self._build_footer())
            
            doc.build(story, canvasmaker=WatermarkCanvas)
            print(f"[PDFReportGenerator] Generated with charts: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"[PDFReportGenerator] Error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _build_session_info(self, data: Dict) -> Paragraph:
        """Build session info"""
        timestamp = data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M'))
        session_id = data.get('session_id', 'N/A')
        return Paragraph(f"Session: {session_id} | Date: {timestamp}", self.styles['SmallText'])
    
    def _build_main_scores_with_chart(self, data: Dict) -> List:
        """Build main scores with chart"""
        elements = []
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Overall Scores", self.styles['SectionHeader']))
        
        overall = data.get('overall_score', 0)
        scores = data.get('scores', {})
        
        # Score table
        score_data = [[
            f"Overall\n{overall:.0f}%",
            f"Pronunciation\n{scores.get('pronunciation', overall):.0f}%",
            f"Rhythm\n{scores.get('rhythm', 70):.0f}%",
            f"Intonation\n{scores.get('intonation', 70):.0f}%"
        ]]
        
        table = Table(score_data, colWidths=[115, 115, 115, 115])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), self._get_score_color(overall)),
            ('BACKGROUND', (1, 0), (1, 0), self._get_score_color(scores.get('pronunciation', overall))),
            ('BACKGROUND', (2, 0), (2, 0), self._get_score_color(scores.get('rhythm', 70))),
            ('BACKGROUND', (3, 0), (3, 0), self._get_score_color(scores.get('intonation', 70))),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('PADDING', (0, 0), (-1, -1), 10),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 10))
        return elements
    
    def _build_transcription(self, data: Dict) -> List:
        """Build transcription section"""
        elements = []
        elements.append(Paragraph("You Said", self.styles['SectionHeader']))
        text = data.get('transcribed_text', '')
        elements.append(Paragraph(f'"{text}"', self.styles['ReportBody']))
        elements.append(Spacer(1, 8))
        return elements
    
    def _build_phoneme_alignment(self, data: Dict) -> List:
        """Build phoneme alignment table"""
        elements = []
        word_analyses = data.get('word_analyses', [])
        if not word_analyses:
            return elements
        
        elements.append(Paragraph("Phoneme Alignment", self.styles['SectionHeader']))
        
        header = ['Word', 'Status', 'Phonemes', 'IPA', 'Score']
        table_data = [header]
        
        for wa in word_analyses[:8]:
            status = "✓" if wa.get('is_correct', True) else "✗"
            score = wa.get('score', 0)
            table_data.append([
                wa.get('word', ''),
                status,
                wa.get('expected_phonemes', '')[:15],
                wa.get('ipa', '')[:12],
                f"{score:.0f}%"
            ])
        
        table = Table(table_data, colWidths=[80, 40, 130, 100, 50])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.29, 0.56, 0.89)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8)),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.97, 0.97, 0.97)]),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 10))
        return elements
    
    def _build_timing_with_chart(self, data: Dict) -> List:
        """Build timing comparison with chart"""
        elements = []
        word_analyses = data.get('word_analyses', [])
        
        elements.append(Paragraph("Timing Comparison", self.styles['SectionHeader']))
        
        timing_stats = {'on_time': 0, 'early': 0, 'late': 0}
        timing_details = []
        
        for wa in word_analyses:
            status = wa.get('timing_status', 'on_time')
            if status in timing_stats:
                timing_stats[status] += 1
            
            native_duration = wa.get('native_duration', 200)
            user_duration = wa.get('duration', native_duration)
            diff = (user_duration - native_duration) if native_duration else 0
            timing_details.append({
                'word': wa.get('word', ''),
                'status': status,
                'diff': diff * 1000 if diff < 10 else diff  # Convert to ms if in seconds
            })
        
        stats_text = f"✓ {timing_stats['on_time']} On Time | ⚡ {timing_stats['early']} Early | 🐢 {timing_stats['late']} Late"
        elements.append(Paragraph(stats_text, self.styles['ReportBody']))
        
        # Add timing chart
        if timing_details:
            chart = self._create_timing_chart(timing_details)
            if chart:
                elements.append(Spacer(1, 5))
                elements.append(chart)
        
        elements.append(Spacer(1, 10))
        return elements
    
    def _build_detailed_analysis_with_chart(self, data: Dict) -> List:
        """Build detailed analysis with chart"""
        elements = []
        elements.append(Paragraph("Detailed Analysis", self.styles['SectionHeader']))
        
        advanced = data.get('advanced_analysis', {})
        
        detail_scores = {
            'Vowels': advanced.get('vowel_score', 80),
            'Consonants': advanced.get('consonant_score', 100),
            'Stress': advanced.get('stress_score', 70),
            'Intonation': advanced.get('intonation_score', 70),
            'Rhythm': advanced.get('rhythm_score', 70),
            'Connected': advanced.get('connected_speech_score', 70),
            'Accent': advanced.get('accent_score', 70),
        }
        
        # Add bar chart
        chart = self._create_bar_chart(detail_scores, 'Detailed Scores')
        if chart:
            elements.append(chart)
        else:
            # Fallback to table
            table_data = [['Category', 'Score']]
            for k, v in detail_scores.items():
                table_data.append([k, f"{v:.0f}%"])
            
            table = Table(table_data, colWidths=[150, 80])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.29, 0.56, 0.89)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8)),
                ('PADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(table)
        
        elements.append(Spacer(1, 10))
        return elements
    
    def _build_voice_features_with_chart(self, data: Dict) -> List:
        """Build voice feature comparison with chart"""
        elements = []
        advanced = data.get('advanced_analysis', {})
        acoustic = advanced.get('real_acoustic_analysis', {})
        
        if not acoustic:
            return elements
        
        elements.append(Paragraph("Voice Feature Comparison", self.styles['SectionHeader']))
        
        user_features = acoustic.get('user_features', {})
        native_features = acoustic.get('native_features', {})
        
        # Prepare data for chart
        user_data = {
            'Duration': user_features.get('duration', 1) * 100,  # Scale for visibility
            'Pitch': user_features.get('f0_mean', 100),
            'Energy': user_features.get('rms_mean', 5) * 20,
        }
        
        native_data = {
            'Duration': native_features.get('duration', 1) * 100,
            'Pitch': native_features.get('f0_mean', 100),
            'Energy': native_features.get('rms_mean', 5) * 20,
        }
        
        # Add comparison chart
        chart = self._create_comparison_chart(user_data, native_data, 'Voice Features (Your Voice vs Native)')
        if chart:
            elements.append(chart)
        
        # Add feature table
        voice_data = [
            ['Feature', 'Your Voice', 'Native'],
            ['Duration', f"{user_features.get('duration', 0):.2f}s", f"{native_features.get('duration', 0):.2f}s"],
            ['Pitch (avg)', f"{user_features.get('f0_mean', 0):.0f} Hz", f"{native_features.get('f0_mean', 0):.0f} Hz"],
            ['Pitch (var)', f"±{user_features.get('f0_std', 0):.0f} Hz", f"±{native_features.get('f0_std', 0):.0f} Hz"],
        ]
        
        table = Table(voice_data, colWidths=[120, 120, 120])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.4, 0.4, 0.4)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8)),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(Spacer(1, 5))
        elements.append(table)
        
        elements.append(Spacer(1, 10))
        return elements
    
    def _build_ml_prosody_with_chart(self, data: Dict) -> List:
        """Build ML prosody analysis with radar chart"""
        elements = []
        advanced = data.get('advanced_analysis', {})
        ml_prosody = advanced.get('ml_prosody', {})
        
        # Get prosody scores
        prosody_data = {
            'Fluency': ml_prosody.get('fluency', 70),
            'Stress': ml_prosody.get('stress', 70),
            'Rhythm': ml_prosody.get('rhythm', 70),
            'Intonation': ml_prosody.get('intonation', 70),
            'Overall': ml_prosody.get('overall', 70),
        }
        
        elements.append(Paragraph("ML Prosody Analysis", self.styles['SectionHeader']))
        
        # Add radar chart
        chart = self._create_radar_chart(prosody_data, 'Prosody Profile')
        if chart:
            elements.append(chart)
        
        # Add data table
        prosody_table = [['Metric', 'Score']]
        for k, v in prosody_data.items():
            prosody_table.append([k, f"{v:.0f}%"])
        
        table = Table(prosody_table, colWidths=[120, 80])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.5, 0.5, 0.5)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8)),
            ('PADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(table)
        
        elements.append(Spacer(1, 10))
        return elements
    
    def _build_ipa_section(self, data: Dict) -> List:
        """Build British English IPA section"""
        elements = []
        advanced = data.get('advanced_analysis', {})
        ipa_analysis = advanced.get('ipa_analysis', {})
        
        elements.append(Paragraph("British English IPA", self.styles['SectionHeader']))
        
        if ipa_analysis:
            full_ipa = ipa_analysis.get('full_ipa', '')
            if full_ipa:
                elements.append(Paragraph(f"Complete IPA: /{full_ipa}/", self.styles['ReportBody']))
            
            word_phonetics = ipa_analysis.get('word_phonetics', [])
            if word_phonetics:
                ipa_data = [['Word', 'IPA', 'Syllables']]
                for wp in word_phonetics[:6]:
                    ipa_data.append([
                        wp.get('word', ''),
                        wp.get('ipa', ''),
                        wp.get('syllables', '')
                    ])
                
                table = Table(ipa_data, colWidths=[100, 150, 100])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.5, 0.5, 0.5)),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8)),
                    ('PADDING', (0, 0), (-1, -1), 3),
                ]))
                elements.append(table)
        else:
            elements.append(Paragraph("IPA transcription not available", self.styles['SmallText']))
        
        elements.append(Spacer(1, 8))
        return elements
    
    def _build_formant_analysis(self, data: Dict) -> List:
        """Build formant analysis section"""
        elements = []
        advanced = data.get('advanced_analysis', {})
        formant = advanced.get('formant_analysis', {})
        
        if not formant:
            return elements
        
        elements.append(Paragraph("Formant Analysis (Vowel Quality)", self.styles['SectionHeader']))
        
        user_formants = formant.get('user_formants', {})
        native_formants = formant.get('native_formants', {})
        similarity = formant.get('similarity', {})
        
        formant_data = [
            ['', 'Your Voice', 'Native', 'Match'],
            ['F1', f"{user_formants.get('f1', 0):.0f} Hz", f"{native_formants.get('f1', 0):.0f} Hz", f"{similarity.get('f1', 0):.0f}%"],
            ['F2', f"{user_formants.get('f2', 0):.0f} Hz", f"{native_formants.get('f2', 0):.0f} Hz", f"{similarity.get('f2', 0):.0f}%"],
            ['F3', f"{user_formants.get('f3', 0):.0f} Hz", f"{native_formants.get('f3', 0):.0f} Hz", f"{similarity.get('f3', 0):.0f}%"],
        ]
        
        table = Table(formant_data, colWidths=[50, 100, 100, 70])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.4, 0.4, 0.4)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8)),
            ('PADDING', (0, 0), (-1, -1), 3),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 8))
        return elements
    
    def _build_signal_analysis(self, data: Dict) -> List:
        """Build signal analysis section"""
        elements = []
        advanced = data.get('advanced_analysis', {})
        acoustic = advanced.get('real_acoustic_analysis', {})
        
        if not acoustic:
            return elements
        
        elements.append(Paragraph("Real Signal Analysis", self.styles['SectionHeader']))
        
        overall_signal = acoustic.get('overall_score', 0)
        elements.append(Paragraph(f"Overall Signal Score: {overall_signal:.1f}%", self.styles['ReportBody']))
        
        signal_data = {
            'MFCC Prosody': acoustic.get('prosody_score', 0),
            'Intonation (F0)': acoustic.get('intonation_score', 0),
            'Stress (RMS)': acoustic.get('stress_score', 0),
            'Rhythm': acoustic.get('rhythm_score', 0),
        }
        
        chart = self._create_bar_chart(signal_data, 'Signal Analysis')
        if chart:
            elements.append(chart)
        
        elements.append(Spacer(1, 8))
        return elements
    
    def _build_improvement_tips(self, data: Dict) -> List:
        """Build improvement tips"""
        elements = []
        elements.append(Paragraph("Improvement Tips", self.styles['SectionHeader']))
        
        advanced = data.get('advanced_analysis', {})
        suggestions = advanced.get('suggestions', [])
        
        if suggestions:
            for tip in suggestions[:4]:
                elements.append(Paragraph(f"• {tip}", self.styles['ReportBody']))
        else:
            overall = data.get('overall_score', 0)
            if overall >= 80:
                elements.append(Paragraph("• Excellent pronunciation! Continue practicing.", self.styles['ReportBody']))
            else:
                elements.append(Paragraph("• Focus on the highlighted areas for improvement.", self.styles['ReportBody']))
        
        elements.append(Spacer(1, 8))
        return elements
    
    def _build_followup(self, data: Dict) -> List:
        """Build follow-up section"""
        elements = []
        elements.append(Paragraph("Follow-Up Practice", self.styles['SectionHeader']))
        
        followup = data.get('followup_question', {})
        
        if followup.get('correction'):
            elements.append(Paragraph(f"Correction: {followup['correction']}", self.styles['ReportBody']))
        if followup.get('accent_tip'):
            elements.append(Paragraph(f"Accent Tip: {followup['accent_tip']}", self.styles['ReportBody']))
        if followup.get('next_practice_sentence'):
            elements.append(Paragraph(f"Next: {followup['next_practice_sentence']}", self.styles['ReportBody']))
        
        elements.append(Spacer(1, 8))
        return elements
    
    def _build_footer(self) -> Paragraph:
        """Build footer"""
        return Paragraph(
            f"Generated by AI Accent Builder • {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            ParagraphStyle(
                name='Footer',
                parent=self.styles['Normal'],
                fontSize=7,
                textColor=colors.Color(0.5, 0.5, 0.5),
                alignment=TA_CENTER
            )
        )


# Singleton instance
pdf_report_generator = PDFReportGenerator()
