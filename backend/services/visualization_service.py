"""
Visualization Service for Word-Level Analysis
Generates comparison plots for user vs reference audio per word

Plots Generated:
1. Waveform comparison (side-by-side)
2. Spectrogram comparison
3. Pitch contour overlay
4. Energy/RMS comparison
5. Phoneme alignment visualization

For FYP/Research-grade visual analysis.
"""

import os
import uuid
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import io
import base64

# Audio processing
try:
    import librosa
    import librosa.display
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    print("[Visualization] librosa not available")

# Plotting
try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend for server
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("[Visualization] matplotlib not available")

# Optional: Seaborn for better aesthetics
try:
    import seaborn as sns
    sns.set_style("darkgrid")
    SEABORN_AVAILABLE = True
except ImportError:
    SEABORN_AVAILABLE = False


class VisualizationService:
    """
    Service for generating word-level audio comparison visualizations.
    """
    
    def __init__(self, output_dir: str = None):
        """Initialize visualization service."""
        if output_dir is None:
            self.output_dir = Path(__file__).parent.parent / "uploads" / "visualizations"
        else:
            self.output_dir = Path(output_dir)
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Default parameters
        self.target_sr = 16000
        self.figure_dpi = 100
        self.figure_width = 12
        self.figure_height = 4
        
        # Color scheme
        self.user_color = '#FF6B6B'  # Coral red for user
        self.ref_color = '#4ECDC4'   # Teal for reference
        self.overlap_color = '#95E1D3'  # Light teal for overlap
        
        print(f"[Visualization] Initialized. matplotlib={MATPLOTLIB_AVAILABLE}, librosa={LIBROSA_AVAILABLE}")
    
    def generate_word_visualization(self, user_audio_path: str, 
                                     ref_audio_path: str,
                                     word: str,
                                     session_id: str = None) -> Dict[str, str]:
        """
        Generate all visualization plots for a single word comparison.
        
        Args:
            user_audio_path: Path to user's word audio
            ref_audio_path: Path to reference word audio
            word: The word being analyzed
            session_id: Optional session identifier
            
        Returns:
            Dict with paths to generated plot images
        """
        if not MATPLOTLIB_AVAILABLE or not LIBROSA_AVAILABLE:
            return {"error": "Required libraries not available"}
        
        try:
            # Load audio
            user_audio, sr = librosa.load(user_audio_path, sr=self.target_sr)
            ref_audio, _ = librosa.load(ref_audio_path, sr=self.target_sr)
            
            # Create session directory
            if session_id is None:
                session_id = uuid.uuid4().hex[:8]
            session_dir = self.output_dir / session_id
            session_dir.mkdir(parents=True, exist_ok=True)
            
            word_safe = self._sanitize_filename(word)
            
            # Generate all plots
            plots = {}
            
            # 1. Waveform comparison
            waveform_path = str(session_dir / f"{word_safe}_waveform.png")
            self.create_waveform_comparison(user_audio, ref_audio, word, sr, waveform_path)
            plots["waveform"] = waveform_path
            
            # 2. Spectrogram comparison
            spectrogram_path = str(session_dir / f"{word_safe}_spectrogram.png")
            self.create_spectrogram_comparison(user_audio, ref_audio, word, sr, spectrogram_path)
            plots["spectrogram"] = spectrogram_path
            
            # 3. Pitch contour overlay
            pitch_path = str(session_dir / f"{word_safe}_pitch.png")
            self.create_pitch_overlay(user_audio, ref_audio, word, sr, pitch_path)
            plots["pitch_contour"] = pitch_path
            
            # 4. Energy/RMS comparison
            energy_path = str(session_dir / f"{word_safe}_energy.png")
            self.create_energy_comparison(user_audio, ref_audio, word, sr, energy_path)
            plots["energy_rms"] = energy_path
            
            # 5. Combined dashboard
            dashboard_path = str(session_dir / f"{word_safe}_dashboard.png")
            self.create_combined_dashboard(user_audio, ref_audio, word, sr, dashboard_path)
            plots["dashboard"] = dashboard_path
            
            print(f"[Visualization] Generated {len(plots)} plots for word '{word}'")
            
            return {
                "success": True,
                "session_id": session_id,
                "word": word,
                "plots": plots
            }
            
        except Exception as e:
            print(f"[Visualization] Error: {e}")
            return {"success": False, "error": str(e)}
    
    def create_waveform_comparison(self, user_audio: np.ndarray, ref_audio: np.ndarray,
                                    word: str, sr: int, output_path: str) -> str:
        """
        Create side-by-side waveform plot.
        
        Args:
            user_audio: User audio data
            ref_audio: Reference audio data
            word: Word being analyzed
            sr: Sample rate
            output_path: Path to save plot
            
        Returns:
            Path to saved plot
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(self.figure_width, self.figure_height * 1.5))
        
        # User waveform
        time_user = np.arange(len(user_audio)) / sr
        ax1.plot(time_user, user_audio, color=self.user_color, linewidth=0.5, alpha=0.8)
        ax1.fill_between(time_user, user_audio, alpha=0.3, color=self.user_color)
        ax1.set_ylabel('Amplitude', fontsize=10)
        ax1.set_title(f'Your Pronunciation: "{word}"', fontsize=12, fontweight='bold', color=self.user_color)
        ax1.set_xlim([0, max(len(user_audio), len(ref_audio)) / sr])
        ax1.axhline(y=0, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)
        
        # Reference waveform
        time_ref = np.arange(len(ref_audio)) / sr
        ax2.plot(time_ref, ref_audio, color=self.ref_color, linewidth=0.5, alpha=0.8)
        ax2.fill_between(time_ref, ref_audio, alpha=0.3, color=self.ref_color)
        ax2.set_xlabel('Time (seconds)', fontsize=10)
        ax2.set_ylabel('Amplitude', fontsize=10)
        ax2.set_title(f'Reference (British RP): "{word}"', fontsize=12, fontweight='bold', color=self.ref_color)
        ax2.set_xlim([0, max(len(user_audio), len(ref_audio)) / sr])
        ax2.axhline(y=0, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.figure_dpi, bbox_inches='tight', 
                    facecolor='white', edgecolor='none')
        plt.close(fig)
        
        return output_path
    
    def create_spectrogram_comparison(self, user_audio: np.ndarray, ref_audio: np.ndarray,
                                       word: str, sr: int, output_path: str) -> str:
        """
        Create side-by-side spectrogram plot.
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(self.figure_width, self.figure_height))
        
        # User spectrogram
        D_user = librosa.amplitude_to_db(np.abs(librosa.stft(user_audio)), ref=np.max)
        img1 = librosa.display.specshow(D_user, sr=sr, x_axis='time', y_axis='hz', ax=ax1, cmap='magma')
        ax1.set_title(f'Your: "{word}"', fontsize=11, fontweight='bold')
        ax1.set_ylabel('Frequency (Hz)', fontsize=10)
        ax1.set_xlabel('Time (s)', fontsize=10)
        
        # Reference spectrogram
        D_ref = librosa.amplitude_to_db(np.abs(librosa.stft(ref_audio)), ref=np.max)
        img2 = librosa.display.specshow(D_ref, sr=sr, x_axis='time', y_axis='hz', ax=ax2, cmap='magma')
        ax2.set_title(f'Reference: "{word}"', fontsize=11, fontweight='bold')
        ax2.set_ylabel('', fontsize=10)
        ax2.set_xlabel('Time (s)', fontsize=10)
        
        # Add colorbar
        fig.colorbar(img2, ax=[ax1, ax2], format='%+2.0f dB', shrink=0.8)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.figure_dpi, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        plt.close(fig)
        
        return output_path
    
    def create_pitch_overlay(self, user_audio: np.ndarray, ref_audio: np.ndarray,
                              word: str, sr: int, output_path: str) -> str:
        """
        Create overlaid pitch contour plot showing both user and reference.
        """
        fig, ax = plt.subplots(figsize=(self.figure_width, self.figure_height))
        
        # Extract pitch using piptrack
        def get_pitch_contour(audio, sr):
            pitches, magnitudes = librosa.piptrack(y=audio, sr=sr, fmin=75, fmax=500)
            pitch_values = []
            times = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                if pitch > 0:
                    pitch_values.append(pitch)
                    times.append(t * (len(audio) / pitches.shape[1]) / sr)
            return times, pitch_values
        
        # Get pitch contours
        user_times, user_pitches = get_pitch_contour(user_audio, sr)
        ref_times, ref_pitches = get_pitch_contour(ref_audio, sr)
        
        # Plot with markers and lines
        if user_pitches:
            ax.plot(user_times, user_pitches, color=self.user_color, linewidth=2, 
                   label='Your pronunciation', marker='o', markersize=3, alpha=0.8)
        if ref_pitches:
            ax.plot(ref_times, ref_pitches, color=self.ref_color, linewidth=2, 
                   label='Reference (British RP)', marker='s', markersize=3, alpha=0.8)
        
        ax.set_xlabel('Time (seconds)', fontsize=10)
        ax.set_ylabel('Pitch (Hz)', fontsize=10)
        ax.set_title(f'Pitch Contour Comparison: "{word}"', fontsize=12, fontweight='bold')
        ax.legend(loc='upper right', fontsize=9)
        ax.grid(True, alpha=0.3)
        
        # Add annotations for pitch statistics
        if user_pitches and ref_pitches:
            user_mean = np.mean(user_pitches)
            ref_mean = np.mean(ref_pitches)
            ax.axhline(y=user_mean, color=self.user_color, linestyle='--', alpha=0.5, linewidth=1)
            ax.axhline(y=ref_mean, color=self.ref_color, linestyle='--', alpha=0.5, linewidth=1)
            
            # Add text annotations
            ax.text(0.02, 0.98, f'Your avg: {user_mean:.0f}Hz', transform=ax.transAxes,
                   fontsize=9, color=self.user_color, verticalalignment='top')
            ax.text(0.02, 0.92, f'Ref avg: {ref_mean:.0f}Hz', transform=ax.transAxes,
                   fontsize=9, color=self.ref_color, verticalalignment='top')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.figure_dpi, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        plt.close(fig)
        
        return output_path
    
    def create_energy_comparison(self, user_audio: np.ndarray, ref_audio: np.ndarray,
                                  word: str, sr: int, output_path: str) -> str:
        """
        Create energy/RMS envelope comparison plot.
        """
        fig, ax = plt.subplots(figsize=(self.figure_width, self.figure_height))
        
        # Calculate RMS energy
        frame_length = int(sr * 0.025)  # 25ms frames
        hop_length = int(sr * 0.010)    # 10ms hop
        
        user_rms = librosa.feature.rms(y=user_audio, frame_length=frame_length, hop_length=hop_length)[0]
        ref_rms = librosa.feature.rms(y=ref_audio, frame_length=frame_length, hop_length=hop_length)[0]
        
        # Convert to time
        user_times = np.arange(len(user_rms)) * hop_length / sr
        ref_times = np.arange(len(ref_rms)) * hop_length / sr
        
        # Plot
        ax.fill_between(user_times, user_rms, alpha=0.4, color=self.user_color, label='Your energy')
        ax.plot(user_times, user_rms, color=self.user_color, linewidth=1.5)
        
        ax.fill_between(ref_times, ref_rms, alpha=0.4, color=self.ref_color, label='Reference energy')
        ax.plot(ref_times, ref_rms, color=self.ref_color, linewidth=1.5)
        
        ax.set_xlabel('Time (seconds)', fontsize=10)
        ax.set_ylabel('Energy (RMS)', fontsize=10)
        ax.set_title(f'Energy/Stress Pattern: "{word}"', fontsize=12, fontweight='bold')
        ax.legend(loc='upper right', fontsize=9)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.figure_dpi, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        plt.close(fig)
        
        return output_path
    
    def create_combined_dashboard(self, user_audio: np.ndarray, ref_audio: np.ndarray,
                                   word: str, sr: int, output_path: str) -> str:
        """
        Create a combined dashboard with all visualizations.
        """
        fig = plt.figure(figsize=(14, 10))
        gs = GridSpec(3, 2, figure=fig, height_ratios=[1, 1, 1])
        
        # 1. Waveforms (top row)
        ax_wave_user = fig.add_subplot(gs[0, 0])
        ax_wave_ref = fig.add_subplot(gs[0, 1])
        
        time_user = np.arange(len(user_audio)) / sr
        ax_wave_user.plot(time_user, user_audio, color=self.user_color, linewidth=0.5)
        ax_wave_user.fill_between(time_user, user_audio, alpha=0.3, color=self.user_color)
        ax_wave_user.set_title('Your Waveform', fontsize=10, fontweight='bold')
        ax_wave_user.set_ylabel('Amplitude')
        
        time_ref = np.arange(len(ref_audio)) / sr
        ax_wave_ref.plot(time_ref, ref_audio, color=self.ref_color, linewidth=0.5)
        ax_wave_ref.fill_between(time_ref, ref_audio, alpha=0.3, color=self.ref_color)
        ax_wave_ref.set_title('Reference Waveform', fontsize=10, fontweight='bold')
        
        # 2. Spectrograms (middle row)
        ax_spec_user = fig.add_subplot(gs[1, 0])
        ax_spec_ref = fig.add_subplot(gs[1, 1])
        
        D_user = librosa.amplitude_to_db(np.abs(librosa.stft(user_audio)), ref=np.max)
        D_ref = librosa.amplitude_to_db(np.abs(librosa.stft(ref_audio)), ref=np.max)
        
        librosa.display.specshow(D_user, sr=sr, x_axis='time', y_axis='hz', ax=ax_spec_user, cmap='magma')
        ax_spec_user.set_title('Your Spectrogram', fontsize=10, fontweight='bold')
        ax_spec_user.set_ylabel('Frequency (Hz)')
        
        librosa.display.specshow(D_ref, sr=sr, x_axis='time', y_axis='hz', ax=ax_spec_ref, cmap='magma')
        ax_spec_ref.set_title('Reference Spectrogram', fontsize=10, fontweight='bold')
        
        # 3. Pitch and Energy overlay (bottom row)
        ax_pitch = fig.add_subplot(gs[2, 0])
        ax_energy = fig.add_subplot(gs[2, 1])
        
        # Pitch
        def get_pitch(audio, sr):
            pitches, magnitudes = librosa.piptrack(y=audio, sr=sr, fmin=75, fmax=500)
            pitch_values = []
            times = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                if pitch > 0:
                    pitch_values.append(pitch)
                    times.append(t * (len(audio) / pitches.shape[1]) / sr)
            return times, pitch_values
        
        user_t, user_p = get_pitch(user_audio, sr)
        ref_t, ref_p = get_pitch(ref_audio, sr)
        
        if user_p:
            ax_pitch.plot(user_t, user_p, color=self.user_color, linewidth=2, label='You', marker='o', markersize=2)
        if ref_p:
            ax_pitch.plot(ref_t, ref_p, color=self.ref_color, linewidth=2, label='Reference', marker='s', markersize=2)
        ax_pitch.set_title('Pitch Contour', fontsize=10, fontweight='bold')
        ax_pitch.set_xlabel('Time (s)')
        ax_pitch.set_ylabel('Pitch (Hz)')
        ax_pitch.legend(fontsize=8)
        ax_pitch.grid(True, alpha=0.3)
        
        # Energy
        frame_length = int(sr * 0.025)
        hop_length = int(sr * 0.010)
        user_rms = librosa.feature.rms(y=user_audio, frame_length=frame_length, hop_length=hop_length)[0]
        ref_rms = librosa.feature.rms(y=ref_audio, frame_length=frame_length, hop_length=hop_length)[0]
        
        user_rms_t = np.arange(len(user_rms)) * hop_length / sr
        ref_rms_t = np.arange(len(ref_rms)) * hop_length / sr
        
        ax_energy.fill_between(user_rms_t, user_rms, alpha=0.4, color=self.user_color, label='You')
        ax_energy.fill_between(ref_rms_t, ref_rms, alpha=0.4, color=self.ref_color, label='Reference')
        ax_energy.set_title('Energy Pattern', fontsize=10, fontweight='bold')
        ax_energy.set_xlabel('Time (s)')
        ax_energy.set_ylabel('RMS Energy')
        ax_energy.legend(fontsize=8)
        ax_energy.grid(True, alpha=0.3)
        
        # Main title
        fig.suptitle(f'Word Analysis Dashboard: "{word}"', fontsize=14, fontweight='bold', y=1.02)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.figure_dpi, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        plt.close(fig)
        
        return output_path
    
    def create_phoneme_alignment_plot(self, user_phonemes: List[Dict], 
                                       ref_phonemes: List[Dict],
                                       word: str, output_path: str) -> str:
        """
        Create phoneme-level alignment visualization.
        
        Args:
            user_phonemes: List of dicts with 'phoneme', 'start', 'end', 'score'
            ref_phonemes: List of dicts with 'phoneme', 'start', 'end'
            word: The word being analyzed
            output_path: Path to save plot
        """
        if not MATPLOTLIB_AVAILABLE:
            return None
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(self.figure_width, 4), sharex=True)
        
        # User phonemes
        for i, p in enumerate(user_phonemes):
            start = p.get('start', i * 0.1)
            end = p.get('end', start + 0.1)
            score = p.get('score', 100)
            
            # Color based on score
            if score >= 80:
                color = '#4ECDC4'  # Good
            elif score >= 60:
                color = '#FFE66D'  # OK
            else:
                color = '#FF6B6B'  # Needs work
            
            ax1.barh(0, end - start, left=start, height=0.5, color=color, edgecolor='white', linewidth=1)
            ax1.text((start + end) / 2, 0, p.get('phoneme', '?'), ha='center', va='center', 
                    fontsize=10, fontweight='bold')
        
        ax1.set_ylim(-0.5, 0.5)
        ax1.set_yticks([])
        ax1.set_title('Your Phonemes', fontsize=11, fontweight='bold', color=self.user_color)
        
        # Reference phonemes
        for i, p in enumerate(ref_phonemes):
            start = p.get('start', i * 0.1)
            end = p.get('end', start + 0.1)
            
            ax2.barh(0, end - start, left=start, height=0.5, color=self.ref_color, 
                    edgecolor='white', linewidth=1)
            ax2.text((start + end) / 2, 0, p.get('phoneme', '?'), ha='center', va='center',
                    fontsize=10, fontweight='bold')
        
        ax2.set_ylim(-0.5, 0.5)
        ax2.set_yticks([])
        ax2.set_xlabel('Time (seconds)', fontsize=10)
        ax2.set_title('Reference Phonemes', fontsize=11, fontweight='bold', color=self.ref_color)
        
        fig.suptitle(f'Phoneme Alignment: "{word}"', fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.figure_dpi, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        plt.close(fig)
        
        return output_path
    
    def plot_to_base64(self, fig) -> str:
        """Convert matplotlib figure to base64 string for embedding."""
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=self.figure_dpi, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()
        return f"data:image/png;base64,{img_base64}"
    
    def _sanitize_filename(self, word: str) -> str:
        """Sanitize word for use in filename."""
        sanitized = ''.join(c for c in word if c.isalnum())
        return sanitized[:20] if sanitized else "word"
    
    def cleanup_session(self, session_id: str) -> bool:
        """Clean up visualization files for a session."""
        try:
            session_dir = self.output_dir / session_id
            if session_dir.exists():
                import shutil
                shutil.rmtree(session_dir)
                return True
            return False
        except Exception as e:
            print(f"[Visualization] Cleanup error: {e}")
            return False


# Singleton instance
visualization_service = VisualizationService()
