"""
Real Acoustic Analysis Service
Comprehensive signal-based pronunciation analysis using:
- librosa: MFCC, RMS energy
- parselmouth (Praat): F0 pitch extraction
- fastdtw: Dynamic Time Warping for all comparisons
- Whisper: Word-level timestamps for connected speech

All scoring is based on real acoustic signals with DTW comparison.
"""
from typing import Dict, List, Optional
import os
import json

# Check library availability
LIBROSA_AVAILABLE = False
PARSELMOUTH_AVAILABLE = False
FASTDTW_AVAILABLE = False
WHISPER_AVAILABLE = False

try:
    import numpy as np
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    print("librosa not available - MFCC/RMS features disabled")

try:
    import parselmouth
    PARSELMOUTH_AVAILABLE = True
except ImportError:
    print("parselmouth not available - F0 pitch extraction disabled")

try:
    from fastdtw import fastdtw
    from scipy.spatial.distance import euclidean
    FASTDTW_AVAILABLE = True
except ImportError:
    print("fastdtw not available - DTW comparison disabled")

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    print("whisper not available - word timestamps disabled")


class RealAcousticPronunciationAnalyzer:
    """
    Real signal-based pronunciation analyzer.
    All scores derived from DTW comparison of actual audio signals.
    Uses Whisper for word-level timestamps.
    """
    
    def __init__(self, whisper_model: str = "base"):
        self.sample_rate = 16000
        self.whisper_model = None
        self._word_cache = {}
        
        if WHISPER_AVAILABLE:
            try:
                print(f"Loading Whisper model '{whisper_model}'...")
                self.whisper_model = whisper.load_model(whisper_model)
                print("Whisper model loaded successfully!")
            except Exception as e:
                print(f"Could not load Whisper model: {e}")
        
        print(f"RealAcousticPronunciationAnalyzer initialized:")
        print(f"  - librosa: {LIBROSA_AVAILABLE}")
        print(f"  - parselmouth: {PARSELMOUTH_AVAILABLE}")
        print(f"  - fastdtw: {FASTDTW_AVAILABLE}")
        print(f"  - whisper: {WHISPER_AVAILABLE and self.whisper_model is not None}")
    
    def clear_cache(self):
        """Clear word timestamp cache."""
        self._word_cache.clear()
    
    # =========================================================================
    # AUDIO LOADING
    # =========================================================================
    
    def load_audio(self, path: str) -> tuple:
        """Load audio file and return (audio, sample_rate)"""
        if not LIBROSA_AVAILABLE:
            return None, self.sample_rate
        
        try:
            audio, sr = librosa.load(path, sr=self.sample_rate)
            return audio, sr
        except Exception as e:
            print(f"Error loading audio: {e}")
            return None, self.sample_rate
    
    # =========================================================================
    # MFCC EXTRACTION (Spectral Features)
    # =========================================================================
    
    def extract_mfcc(self, audio, sr: int) -> Optional[np.ndarray]:
        """Extract MFCC features from audio."""
        if not LIBROSA_AVAILABLE or audio is None:
            return None
        
        try:
            mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
            return mfcc.T
        except Exception as e:
            print(f"MFCC extraction error: {e}")
            return None
    
    # =========================================================================
    # PITCH (F0) EXTRACTION using Parselmouth
    # =========================================================================
    
    def extract_pitch(self, audio_path: str) -> Optional[np.ndarray]:
        """Extract F0 pitch using Parselmouth (Praat algorithm)."""
        if not PARSELMOUTH_AVAILABLE:
            return self._fallback_pitch(audio_path)
        
        try:
            snd = parselmouth.Sound(audio_path)
            pitch = snd.to_pitch()
            pitch_values = pitch.selected_array['frequency']
            voiced_pitch = pitch_values[pitch_values > 0]
            return voiced_pitch if len(voiced_pitch) > 0 else None
        except Exception as e:
            print(f"Parselmouth pitch extraction error: {e}")
            return self._fallback_pitch(audio_path)
    
    def _fallback_pitch(self, audio_path: str) -> Optional[np.ndarray]:
        """Fallback pitch extraction using librosa pyin"""
        if not LIBROSA_AVAILABLE:
            return None
        
        try:
            y, sr = librosa.load(audio_path, sr=self.sample_rate)
            f0, voiced_flag, voiced_probs = librosa.pyin(
                y, fmin=librosa.note_to_hz('C2'),
                fmax=librosa.note_to_hz('C7'), sr=sr
            )
            f0_clean = f0[~np.isnan(f0)]
            return f0_clean if len(f0_clean) > 0 else None
        except:
            return None
    
    # =========================================================================
    # RMS ENERGY EXTRACTION (Stress Detection)
    # =========================================================================
    
    def extract_energy(self, audio) -> Optional[np.ndarray]:
        """Extract RMS energy for stress pattern detection."""
        if not LIBROSA_AVAILABLE or audio is None:
            return None
        
        try:
            rms = librosa.feature.rms(y=audio)[0]
            return rms
        except Exception as e:
            print(f"RMS extraction error: {e}")
            return None
    
    # =========================================================================
    # DTW SIMILARITY CALCULATION
    # =========================================================================
    
    def dtw_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate DTW similarity. Returns 0-100 score."""
        if a is None or b is None or len(a) == 0 or len(b) == 0:
            return 50.0
        
        if not FASTDTW_AVAILABLE:
            try:
                min_len = min(len(a), len(b))
                a_flat = a[:min_len].flatten() if len(a.shape) > 1 else a[:min_len]
                b_flat = b[:min_len].flatten() if len(b.shape) > 1 else b[:min_len]
                corr = np.corrcoef(a_flat, b_flat)[0, 1]
                return (corr + 1) * 50 if not np.isnan(corr) else 50.0
            except:
                return 50.0
        
        try:
            a_dtw = a.reshape(-1, 1) if len(a.shape) == 1 else a
            b_dtw = b.reshape(-1, 1) if len(b.shape) == 1 else b
            
            # Use radius for faster computation
            distance, _ = fastdtw(a_dtw, b_dtw, dist=euclidean, radius=10)
            score = 1 / (1 + distance / 1000) * 100
            return min(100, score)
        except Exception as e:
            print(f"DTW error: {e}")
            return 50.0
    
    # =========================================================================
    # WHISPER WORD TIMESTAMPS
    # =========================================================================
    
    def extract_word_timestamps(self, audio_path: str) -> List[Dict]:
        """
        Extract word-level timestamps using Whisper.
        Returns: List of {word, start, end} dictionaries
        """
        if audio_path in self._word_cache:
            return self._word_cache[audio_path]
        
        if not WHISPER_AVAILABLE or self.whisper_model is None:
            return []
        
        try:
            # Transcribe with word timestamps
            result = self.whisper_model.transcribe(
                audio_path,
                word_timestamps=True,
                language="en"
            )
            
            words = []
            for segment in result.get("segments", []):
                for word_info in segment.get("words", []):
                    words.append({
                        "word": word_info.get("word", "").strip(),
                        "start": word_info.get("start", 0),
                        "end": word_info.get("end", 0)
                    })
            
            self._word_cache[audio_path] = words
            return words
            
        except Exception as e:
            print(f"Whisper word extraction error: {e}")
            return []
    
    # =========================================================================
    # CONNECTED SPEECH DETECTION
    # =========================================================================
    
    def analyze_connected_speech(self, word_timestamps: List[Dict]) -> Dict:
        """
        Analyze connected speech patterns from Whisper word timestamps.
        Detects: linking, elision, assimilation based on word gaps.
        """
        if len(word_timestamps) < 2:
            return {
                'linking_count': 0,
                'short_gaps': 0,
                'linking_ratio': 0,
                'score': 50.0
            }
        
        linking_count = 0
        very_short_gaps = 0
        gaps = []
        
        for i in range(len(word_timestamps) - 1):
            current = word_timestamps[i]
            next_word = word_timestamps[i + 1]
            
            gap = next_word.get('start', 0) - current.get('end', 0)
            gaps.append(gap)
            
            # Linking: gap < 100ms (connected speech)
            if gap < 0.1:
                linking_count += 1
            # Very short gap: < 50ms (elision/assimilation)
            if gap < 0.05:
                very_short_gaps += 1
        
        total_transitions = len(word_timestamps) - 1
        linking_ratio = linking_count / max(total_transitions, 1)
        avg_gap = np.mean(gaps) if gaps else 0.2
        
        # Score based on linking ratio and average gap
        # Good connected speech: 40-80% linking, avg gap < 150ms
        if 0.4 <= linking_ratio <= 0.8 and avg_gap < 0.15:
            score = 85 + (1 - abs(0.6 - linking_ratio) / 0.2) * 15
        elif linking_ratio > 0.3:
            score = 65 + linking_ratio * 30
        else:
            score = 50 + linking_ratio * 40
        
        return {
            'linking_count': linking_count,
            'short_gaps': very_short_gaps,
            'linking_ratio': round(linking_ratio, 3),
            'avg_gap_ms': round(avg_gap * 1000, 1),
            'score': round(min(100, max(0, score)), 1)
        }
    
    # =========================================================================
    # MAIN COMPARISON METHOD
    # =========================================================================
    
    def compare(self, user_audio_path: str, native_audio_path: str) -> Dict:
        """
        Full pronunciation comparison using real acoustic signals.
        All scores are DTW-based signal comparisons.
        """
        # Clear cache
        self.clear_cache()
        
        # Load audio files
        u_audio, sr = self.load_audio(user_audio_path)
        n_audio, _ = self.load_audio(native_audio_path)
        
        # Extract features
        u_mfcc = self.extract_mfcc(u_audio, sr)
        n_mfcc = self.extract_mfcc(n_audio, sr)
        
        u_pitch = self.extract_pitch(user_audio_path)
        n_pitch = self.extract_pitch(native_audio_path)
        
        u_energy = self.extract_energy(u_audio)
        n_energy = self.extract_energy(n_audio)
        
        # DTW Similarities
        mfcc_score = self.dtw_similarity(u_mfcc, n_mfcc)
        pitch_score = self.dtw_similarity(u_pitch, n_pitch)
        energy_score = self.dtw_similarity(u_energy, n_energy)
        
        # Whisper word timestamps for connected speech
        u_words = self.extract_word_timestamps(user_audio_path)
        n_words = self.extract_word_timestamps(native_audio_path)
        
        # Connected speech analysis
        connected = self.analyze_connected_speech(u_words)
        connected_score = connected['score']
        
        # Word overlap score
        if u_words and n_words:
            u_word_set = set(w.get('word', '').lower().strip() for w in u_words)
            n_word_set = set(w.get('word', '').lower().strip() for w in n_words)
            if n_word_set:
                word_overlap = len(u_word_set.intersection(n_word_set)) / len(n_word_set) * 100
            else:
                word_overlap = 50.0
        else:
            word_overlap = 50.0
        
        # Duration/rhythm comparison
        u_duration = len(u_audio) / sr if u_audio is not None else 0
        n_duration = len(n_audio) / sr if n_audio is not None else 0
        
        if n_duration > 0:
            duration_ratio = u_duration / n_duration
            rhythm_score = max(0, 100 - abs(1 - duration_ratio) * 50)
        else:
            rhythm_score = 50.0
        
        # Final Weighted Score
        final_score = (
            mfcc_score * 0.25 +       # Prosody/spectral
            pitch_score * 0.25 +      # Intonation
            energy_score * 0.15 +     # Stress
            rhythm_score * 0.15 +     # Rhythm/timing
            connected_score * 0.10 +  # Connected speech
            word_overlap * 0.10       # Word accuracy
        )
        
        return {
            'overall_score': round(final_score, 1),
            'scores': {
                'prosody': round(mfcc_score, 1),
                'intonation': round(pitch_score, 1),
                'stress': round(energy_score, 1),
                'rhythm_timing': round(rhythm_score, 1),
                'connected_speech': round(connected_score, 1)
            },
            'mfcc_analysis': {
                'similarity': round(mfcc_score, 1),
                'user_frames': len(u_mfcc) if u_mfcc is not None else 0,
                'native_frames': len(n_mfcc) if n_mfcc is not None else 0
            },
            'pitch_analysis': {
                'similarity': round(pitch_score, 1),
                'user_pitch': {
                    'pitch_mean': float(np.mean(u_pitch)) if u_pitch is not None and len(u_pitch) > 0 else 0,
                    'pitch_std': float(np.std(u_pitch)) if u_pitch is not None and len(u_pitch) > 0 else 0,
                    'pitch_min': float(np.min(u_pitch)) if u_pitch is not None and len(u_pitch) > 0 else 0,
                    'pitch_max': float(np.max(u_pitch)) if u_pitch is not None and len(u_pitch) > 0 else 0
                },
                'native_pitch': {
                    'pitch_mean': float(np.mean(n_pitch)) if n_pitch is not None and len(n_pitch) > 0 else 0,
                    'pitch_std': float(np.std(n_pitch)) if n_pitch is not None and len(n_pitch) > 0 else 0,
                    'pitch_min': float(np.min(n_pitch)) if n_pitch is not None and len(n_pitch) > 0 else 0,
                    'pitch_max': float(np.max(n_pitch)) if n_pitch is not None and len(n_pitch) > 0 else 0
                }
            },
            'stress_analysis': {
                'similarity': round(energy_score, 1),
                'user_mean_energy': float(np.mean(u_energy)) if u_energy is not None else 0,
                'native_mean_energy': float(np.mean(n_energy)) if n_energy is not None else 0
            },
            'rhythm_analysis': {
                'similarity': round(rhythm_score, 1),
                'user_duration': round(u_duration, 2),
                'native_duration': round(n_duration, 2),
                'duration_ratio': round(duration_ratio, 2) if n_duration > 0 else 1.0
            },
            'connected_analysis': {
                'similarity': round(connected_score, 1),
                'linking_count': connected['linking_count'],
                'linking_ratio': connected['linking_ratio'],
                'avg_gap_ms': connected.get('avg_gap_ms', 0),
                'source': 'whisper' if u_words else 'fallback'
            },
            'word_timestamps': {
                'user_words': [w.get('word', '') for w in u_words],
                'native_words': [w.get('word', '') for w in n_words],
                'user_word_count': len(u_words),
                'native_word_count': len(n_words),
                'word_overlap_score': round(word_overlap, 1)
            },
            'features_available': {
                'librosa': LIBROSA_AVAILABLE,
                'parselmouth': PARSELMOUTH_AVAILABLE,
                'fastdtw': FASTDTW_AVAILABLE,
                'whisper': WHISPER_AVAILABLE and self.whisper_model is not None
            }
        }


# Singleton instance - use "tiny" model for faster loading, "base" for better quality
real_acoustic_service = RealAcousticPronunciationAnalyzer(whisper_model="small")


# Backward compatibility wrapper
def analyze_pronunciation_signals(user_audio_path: str, native_audio_path: str,
                                   user_timestamps: List[Dict] = None,
                                   native_timestamps: List[Dict] = None) -> Dict:
    """Wrapper function for backward compatibility"""
    return real_acoustic_service.compare(user_audio_path, native_audio_path)
