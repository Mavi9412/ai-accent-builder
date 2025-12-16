"""
Real-Time Hybrid Pronunciation Evaluation System
=================================================
Main orchestrator combining phoneme alignment + ML prosody scoring + dynamic feedback

ARCHITECTURE:
┌─────────────────────────────────────────────────────────────────┐
│                   HybridPronunciationService                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Audio Stream ──► Buffer ──┬──► Phoneme Aligner ──┐            │
│                             │                       │            │
│                             └──► ML Prosody ────────┼──► Scores │
│                             │                       │            │
│                             └──► Formant Analysis ──┘            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

DATASETS FOR TRAINING:
- SpeechOcean762: British English phoneme-level annotations
- L2-ARCTIC: ESL learner recordings with stress/rhythm labels
- VoxCeleb/LibriSpeech/CommonVoice: General prosody patterns
"""

import os
import numpy as np
import asyncio
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import warnings
warnings.filterwarnings("ignore")

# Feature flags
LIBROSA_AVAILABLE = False
TORCH_AVAILABLE = False
NOISEREDUCE_AVAILABLE = False

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    pass

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    pass

try:
    import noisereduce as nr
    NOISEREDUCE_AVAILABLE = True
except ImportError:
    pass

# Import ML pronunciation service
ML_PRONUNCIATION_AVAILABLE = False
try:
    from services.ml_pronunciation_service import ml_pronunciation_service, MLProsodyScorer as MLProsodyScorerV2
    ML_PRONUNCIATION_AVAILABLE = True
    print("[HybridPronunciation] ML pronunciation service loaded ✓")
except ImportError as e:
    print(f"[HybridPronunciation] ML pronunciation service not available: {e}")


# ========================== DATA MODELS ==========================

class PhonemeStatus(Enum):
    CORRECT = "correct"        # ✓
    SUBSTITUTION = "substitution"  # ≠
    INSERTION = "insertion"    # +
    DELETION = "deletion"      # -
    PENDING = "pending"        # ○


class TimingStatus(Enum):
    EARLY = "early"
    ON_TIME = "on_time"
    LATE = "late"


@dataclass
class PhonemeResult:
    """Result for a single phoneme evaluation"""
    index: int
    target_phoneme: str
    detected_phoneme: str
    target_ipa: str
    detected_ipa: str
    status: PhonemeStatus
    score: float  # 0-100
    timing_status: TimingStatus
    start_time: float
    end_time: float
    duration_ratio: float  # detected/expected
    confidence: float


@dataclass
class WordResult:
    """Result for a single word evaluation"""
    word: str
    word_index: int
    phoneme_results: List[PhonemeResult]
    phoneme_score: float
    timing_score: float
    is_complete: bool


@dataclass
class ProsodyScores:
    """ML-based prosody evaluation scores"""
    fluency: float          # 0-100
    stress_accuracy: float  # 0-100
    rhythm: float           # 0-100
    intonation: float       # 0-100
    pitch_range: float      # 0-100
    energy_dynamics: float  # 0-100
    overall: float          # weighted average


@dataclass
class RealTimeResult:
    """Complete real-time evaluation result"""
    timestamp: float
    word_results: List[WordResult]
    prosody_scores: ProsodyScores
    overall_score: float
    phoneme_accuracy: float
    timing_accuracy: float
    current_word_index: int
    is_final: bool


# ========================== AUDIO BUFFER ==========================

class AudioBuffer:
    """
    Manages streaming audio with noise reduction and context buffering.
    
    USAGE:
        buffer = AudioBuffer(sample_rate=16000, chunk_duration=0.5)
        buffer.add_chunk(audio_data)
        processed = buffer.get_processed_audio()
    """
    
    def __init__(self, sample_rate: int = 16000, 
                 chunk_duration: float = 0.5,
                 context_duration: float = 1.0):
        self.sample_rate = sample_rate
        self.chunk_samples = int(chunk_duration * sample_rate)
        self.context_samples = int(context_duration * sample_rate)
        
        # Circular buffer for audio chunks
        self.buffer = deque(maxlen=int(10 / chunk_duration))  # 10 seconds max
        self.total_samples = 0
        
        # Noise profile (estimated from first silent chunk)
        self.noise_profile = None
    
    def add_chunk(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Add audio chunk, apply noise reduction, normalize.
        Returns processed chunk.
        """
        # Convert to float32 if needed
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
        
        # Normalize
        max_val = np.max(np.abs(audio_data))
        if max_val > 0:
            audio_data = audio_data / max_val
        
        # Noise reduction (if available and noise profile exists)
        if NOISEREDUCE_AVAILABLE and self.noise_profile is not None:
            audio_data = nr.reduce_noise(
                y=audio_data, 
                sr=self.sample_rate,
                y_noise=self.noise_profile,
                stationary=True
            )
        
        # Store chunk
        self.buffer.append(audio_data)
        self.total_samples += len(audio_data)
        
        return audio_data
    
    def set_noise_profile(self, noise_audio: np.ndarray):
        """Set noise profile from silent audio sample"""
        self.noise_profile = noise_audio
    
    def get_full_audio(self) -> np.ndarray:
        """Get all buffered audio concatenated"""
        if not self.buffer:
            return np.array([])
        return np.concatenate(list(self.buffer))
    
    def get_recent_audio(self, duration: float) -> np.ndarray:
        """Get last N seconds of audio"""
        samples_needed = int(duration * self.sample_rate)
        full_audio = self.get_full_audio()
        if len(full_audio) < samples_needed:
            return full_audio
        return full_audio[-samples_needed:]
    
    def clear(self):
        """Clear buffer"""
        self.buffer.clear()
        self.total_samples = 0


# ========================== PHONEME ALIGNER ==========================

class RealtimePhonemeAligner:
    """
    Phoneme alignment with timing using forced alignment.
    
    INTEGRATION OPTIONS:
    1. Gentle Forced Aligner (external process)
    2. Montreal Forced Aligner (MFA)
    3. MFCC-based approximation (built-in fallback)
    
    For production, integrate Gentle/MFA:
        pip install gentle  # OR
        pip install montreal-forced-aligner
    """
    
    # ARPAbet to IPA mapping
    ARPABET_TO_IPA = {
        'AA': 'ɑ', 'AE': 'æ', 'AH': 'ʌ', 'AO': 'ɔ', 'AW': 'aʊ', 'AY': 'aɪ',
        'B': 'b', 'CH': 'tʃ', 'D': 'd', 'DH': 'ð', 'EH': 'ɛ', 'ER': 'ɝ',
        'EY': 'eɪ', 'F': 'f', 'G': 'ɡ', 'HH': 'h', 'IH': 'ɪ', 'IY': 'i',
        'JH': 'dʒ', 'K': 'k', 'L': 'l', 'M': 'm', 'N': 'n', 'NG': 'ŋ',
        'OW': 'oʊ', 'OY': 'ɔɪ', 'P': 'p', 'R': 'ɹ', 'S': 's', 'SH': 'ʃ',
        'T': 't', 'TH': 'θ', 'UH': 'ʊ', 'UW': 'u', 'V': 'v', 'W': 'w',
        'Y': 'j', 'Z': 'z', 'ZH': 'ʒ'
    }
    
    VOWELS = {'AA', 'AE', 'AH', 'AO', 'AW', 'AY', 'EH', 'ER', 'EY', 
              'IH', 'IY', 'OW', 'OY', 'UH', 'UW'}
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.g2p = None
        self._init_g2p()
    
    def _init_g2p(self):
        """Initialize grapheme-to-phoneme converter"""
        try:
            from g2p_en import G2p
            self.g2p = G2p()
        except ImportError:
            print("[PhonemeAligner] g2p_en not available")
    
    def get_target_phonemes(self, text: str) -> List[Dict]:
        """
        Get target phonemes with expected timing from text.
        
        Returns:
            List of {phoneme, word, word_index, expected_duration}
        """
        if not self.g2p:
            return []
        
        words = text.lower().split()
        target_phonemes = []
        
        # Estimate timing: ~80ms per phoneme average
        phoneme_duration = 0.08
        current_time = 0
        
        for word_idx, word in enumerate(words):
            raw_phonemes = self.g2p(word)
            cleaned = [p.rstrip('0123456789') for p in raw_phonemes 
                      if p.strip() and p not in ' .,!?\'-']
            
            for phoneme in cleaned:
                target_phonemes.append({
                    'phoneme': phoneme,
                    'ipa': self.ARPABET_TO_IPA.get(phoneme, phoneme.lower()),
                    'word': word,
                    'word_index': word_idx,
                    'expected_start': current_time,
                    'expected_end': current_time + phoneme_duration,
                    'expected_duration': phoneme_duration,
                    'is_vowel': phoneme in self.VOWELS
                })
                current_time += phoneme_duration
            
            # Add word gap
            current_time += 0.1
        
        return target_phonemes
    
    def align_audio(self, audio: np.ndarray, 
                    target_phonemes: List[Dict]) -> List[PhonemeResult]:
        """
        Align audio to target phonemes and detect accuracy.
        
        This is the MFCC-based approximation. For production,
        replace with Gentle/MFA integration:
        
        # Gentle integration:
        from gentle import ForcedAligner
        aligner = ForcedAligner()
        result = aligner.align(audio_path, text)
        
        # MFA integration:
        from montreal_forced_aligner import align
        result = align(audio_path, text, dictionary, model)
        """
        if not LIBROSA_AVAILABLE or len(audio) == 0:
            return []
        
        duration = len(audio) / self.sample_rate
        
        # Extract acoustic features
        try:
            mfccs = librosa.feature.mfcc(y=audio, sr=self.sample_rate, n_mfcc=13, hop_length=160)
            rms = librosa.feature.rms(y=audio, hop_length=160)[0]
            zcr = librosa.feature.zero_crossing_rate(audio, hop_length=160)[0]
            spectral_centroid = librosa.feature.spectral_centroid(y=audio, sr=self.sample_rate, hop_length=160)[0]
        except Exception as e:
            print(f"[PhonemeAligner] Feature extraction error: {e}")
            return []
        
        # Segment audio into phoneme-like regions
        detected_phonemes = self._segment_and_classify(
            mfccs, rms, zcr, spectral_centroid, duration
        )
        
        # Align detected to target using Levenshtein
        results = self._align_levenshtein(detected_phonemes, target_phonemes)
        
        return results
    
    def _segment_and_classify(self, mfccs, rms, zcr, sc, duration) -> List[Dict]:
        """Segment audio and classify each segment as a phoneme"""
        detected_phonemes = []
        
        # Calculate frame to time ratio
        n_frames = mfccs.shape[1] if len(mfccs.shape) > 1 else len(mfccs)
        frame_duration = duration / n_frames if n_frames > 0 else 0.01
        
        # Normalize features for boundary detection
        rms_norm = (rms - np.min(rms)) / (np.max(rms) - np.min(rms) + 1e-6)
        zcr_norm = (zcr - np.min(zcr)) / (np.max(zcr) - np.min(zcr) + 1e-6)
        sc_norm = (sc - np.min(sc)) / (np.max(sc) - np.min(sc) + 1e-6)
        
        # Compute delta of features for boundary detection
        rms_delta = np.abs(np.diff(rms_norm, prepend=rms_norm[0]))
        zcr_delta = np.abs(np.diff(zcr_norm, prepend=zcr_norm[0]))
        
        # Combined change signal
        change_signal = 0.5 * rms_delta + 0.5 * zcr_delta
        
        # Find peaks in change signal (phoneme boundaries)
        threshold = np.mean(change_signal) + 0.5 * np.std(change_signal)
        boundaries = [0]
        
        in_peak = False
        for i, val in enumerate(change_signal):
            if val > threshold and not in_peak:
                boundaries.append(i)
                in_peak = True
            elif val < threshold * 0.5:
                in_peak = False
        boundaries.append(n_frames)
        
        # Classify each segment
        for i in range(len(boundaries) - 1):
            start_frame = boundaries[i]
            end_frame = boundaries[i + 1]
            
            if end_frame - start_frame < 3:  # Too short
                continue
            
            # Get features for this segment
            seg_rms = np.mean(rms[start_frame:end_frame])
            seg_zcr = np.mean(zcr[start_frame:end_frame])
            seg_sc = np.mean(sc[start_frame:end_frame])
            seg_mfcc = np.mean(mfccs[:, start_frame:end_frame], axis=1) if len(mfccs.shape) > 1 else mfccs
            
            # Classify based on acoustic features
            phoneme = self._classify_segment(seg_rms, seg_zcr, seg_sc, seg_mfcc)
            
            detected_phonemes.append({
                'phoneme': phoneme,
                'ipa': self.ARPABET_TO_IPA.get(phoneme, phoneme.lower()),
                'start_time': start_frame * frame_duration,
                'end_time': end_frame * frame_duration,
                'duration': (end_frame - start_frame) * frame_duration,
                'confidence': min(1.0, 0.5 + seg_rms * 2)
            })
        
        return detected_phonemes
    
    def _classify_segment(self, rms: float, zcr: float, sc: float, mfcc: np.ndarray) -> str:
        """Classify a segment as a specific phoneme based on acoustic features"""
        # High energy + low ZCR = vowel
        if rms > 0.1 and zcr < 0.3:
            # Classify vowel based on spectral centroid and mfcc
            if sc > 3000:
                return 'IY' if mfcc[1] > 0 else 'EY'
            elif sc > 2000:
                return 'EH' if mfcc[2] > 0 else 'AE'
            elif sc > 1500:
                return 'AH' if mfcc[1] < 0 else 'AA'
            else:
                return 'UW' if mfcc[2] < 0 else 'OW'
        
        # High ZCR = fricative
        elif zcr > 0.4:
            if sc > 4000:
                return 'S' if rms < 0.15 else 'Z'
            elif sc > 3000:
                return 'SH' if rms < 0.15 else 'ZH'
            else:
                return 'F' if rms < 0.1 else 'V'
        
        # Low energy = stop or silence
        elif rms < 0.05:
            if zcr > 0.2:
                return 'T' if sc > 2500 else 'K'
            else:
                return 'P' if sc > 2000 else 'B'
        
        # Moderate energy = sonorant
        else:
            if sc < 1500:
                return 'M' if rms < 0.08 else 'N'
            elif zcr < 0.2:
                return 'L' if mfcc[1] > 0 else 'R'
            else:
                return 'W' if sc < 2000 else 'Y'
    
    def _align_levenshtein(self, detected: List[Dict], 
                           target: List[Dict]) -> List[PhonemeResult]:
        """Align detected phonemes to target using Levenshtein distance"""
        if not target:
            return []
        
        # If no detection, return all as deletions
        if not detected:
            results = []
            for i, t in enumerate(target):
                results.append(PhonemeResult(
                    index=i,
                    target_phoneme=t.get('phoneme', ''),
                    detected_phoneme='',
                    target_ipa=t.get('ipa', ''),
                    detected_ipa='',
                    status=PhonemeStatus.DELETION,
                    score=0,
                    timing_status=TimingStatus.ON_TIME,
                    start_time=t.get('expected_start', 0),
                    end_time=t.get('expected_end', 0),
                    duration_ratio=0,
                    confidence=0
                ))
            return results
        
        # Extract phoneme strings
        detected_phonemes = [d.get('phoneme', '') for d in detected]
        target_phonemes = [t.get('phoneme', '') for t in target]
        
        m, n = len(detected_phonemes), len(target_phonemes)
        
        # Build Levenshtein DP matrix
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if detected_phonemes[i-1] == target_phonemes[j-1]:
                    dp[i][j] = dp[i-1][j-1]
                else:
                    dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
        
        # Backtrack to find alignment
        alignments = []
        i, j = m, n
        
        while i > 0 or j > 0:
            if i > 0 and j > 0 and detected_phonemes[i-1] == target_phonemes[j-1]:
                # Match
                t = target[j-1]
                d = detected[i-1]
                alignments.append(PhonemeResult(
                    index=j-1,
                    target_phoneme=target_phonemes[j-1],
                    detected_phoneme=detected_phonemes[i-1],
                    target_ipa=t.get('ipa', ''),
                    detected_ipa=d.get('ipa', ''),
                    status=PhonemeStatus.CORRECT,
                    score=100,
                    timing_status=self._get_timing_status(d, t),
                    start_time=d.get('start_time', 0),
                    end_time=d.get('end_time', 0),
                    duration_ratio=d.get('duration', 0.08) / t.get('expected_duration', 0.08) if t.get('expected_duration', 0.08) > 0 else 1.0,
                    confidence=d.get('confidence', 0.5)
                ))
                i -= 1
                j -= 1
            elif i > 0 and j > 0 and dp[i][j] == dp[i-1][j-1] + 1:
                # Substitution
                t = target[j-1]
                d = detected[i-1]
                alignments.append(PhonemeResult(
                    index=j-1,
                    target_phoneme=target_phonemes[j-1],
                    detected_phoneme=detected_phonemes[i-1],
                    target_ipa=t.get('ipa', ''),
                    detected_ipa=d.get('ipa', ''),
                    status=PhonemeStatus.SUBSTITUTION,
                    score=50,  # Partial credit for substitution
                    timing_status=self._get_timing_status(d, t),
                    start_time=d.get('start_time', 0),
                    end_time=d.get('end_time', 0),
                    duration_ratio=d.get('duration', 0.08) / t.get('expected_duration', 0.08) if t.get('expected_duration', 0.08) > 0 else 1.0,
                    confidence=d.get('confidence', 0.5)
                ))
                i -= 1
                j -= 1
            elif j > 0 and (i == 0 or dp[i][j-1] <= dp[i-1][j]):
                # Deletion (target phoneme not spoken)
                t = target[j-1]
                alignments.append(PhonemeResult(
                    index=j-1,
                    target_phoneme=target_phonemes[j-1],
                    detected_phoneme='',
                    target_ipa=t.get('ipa', ''),
                    detected_ipa='',
                    status=PhonemeStatus.DELETION,
                    score=0,
                    timing_status=TimingStatus.ON_TIME,
                    start_time=t.get('expected_start', 0),
                    end_time=t.get('expected_end', 0),
                    duration_ratio=0,
                    confidence=0
                ))
                j -= 1
            else:
                # Insertion (extra phoneme spoken)
                d = detected[i-1]
                alignments.append(PhonemeResult(
                    index=-1,  # No target index
                    target_phoneme='',
                    detected_phoneme=detected_phonemes[i-1],
                    target_ipa='',
                    detected_ipa=d.get('ipa', ''),
                    status=PhonemeStatus.INSERTION,
                    score=0,
                    timing_status=TimingStatus.ON_TIME,
                    start_time=d.get('start_time', 0),
                    end_time=d.get('end_time', 0),
                    duration_ratio=0,
                    confidence=d.get('confidence', 0.5)
                ))
                i -= 1
        
        # Reverse to get correct order
        alignments.reverse()
        return alignments
    
    def _get_timing_status(self, detected: Dict, target: Dict) -> TimingStatus:
        """Determine if phoneme timing is early, on-time, or late"""
        expected_duration = target.get('expected_duration', 0.08)
        actual_duration = detected.get('duration', 0.08)
        
        ratio = actual_duration / expected_duration if expected_duration > 0 else 1.0
        
        if ratio < 0.7:
            return TimingStatus.EARLY
        elif ratio > 1.3:
            return TimingStatus.LATE
        else:
            return TimingStatus.ON_TIME


# ========================== ML PROSODY SCORER ==========================

class MLProsodyScorer:
    """
    ML-based prosody, stress, and rhythm scoring.
    
    MODELS FOR INTEGRATION:
    1. Wav2Vec2 for phoneme representations
    2. Custom LSTM/Transformer for prosody
    3. Pre-trained models from Hugging Face
    
    TRAINING DATA:
    - SpeechOcean762: phoneme accuracy scores
    - L2-ARCTIC: ESL learner prosody annotations
    - VoxCeleb/LibriSpeech: rhythm patterns
    
    TO TRAIN CUSTOM MODEL:
        from transformers import Wav2Vec2ForSequenceClassification
        model = Wav2Vec2ForSequenceClassification.from_pretrained(
            "facebook/wav2vec2-base",
            num_labels=5  # [fluency, stress, rhythm, intonation, overall]
        )
    """
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """
        Load pre-trained prosody scoring model.
        
        For production, train on:
        - SpeechOcean762 (phoneme scores)
        - L2-ARCTIC (ESL prosody)
        """
        if TORCH_AVAILABLE:
            try:
                # Placeholder for Wav2Vec2 integration
                # self.model = Wav2Vec2ForSequenceClassification.from_pretrained(...)
                pass
            except Exception as e:
                print(f"[MLProsody] Model loading failed: {e}")
    
    def extract_prosody_features(self, audio: np.ndarray) -> Dict:
        """
        Extract prosody-relevant acoustic features.
        
        Features for ML scoring:
        - MFCCs (spectral characteristics)
        - F0 (pitch contour)
        - Energy (intensity dynamics)
        - Duration patterns
        - Formants (vowel quality)
        """
        if not LIBROSA_AVAILABLE or len(audio) == 0:
            return {}
        
        try:
            # MFCCs (13 + delta + delta-delta = 39 features)
            mfccs = librosa.feature.mfcc(y=audio, sr=self.sample_rate, n_mfcc=13)
            mfcc_delta = librosa.feature.delta(mfccs)
            mfcc_delta2 = librosa.feature.delta(mfccs, order=2)
            
            # Pitch (F0)
            f0, voiced_flag, voiced_probs = librosa.pyin(
                audio, fmin=75, fmax=500, sr=self.sample_rate
            )
            f0_clean = f0[~np.isnan(f0)] if f0 is not None else np.array([100])
            
            # Energy
            rms = librosa.feature.rms(y=audio)[0]
            
            # Spectral features
            spectral_centroid = librosa.feature.spectral_centroid(y=audio, sr=self.sample_rate)[0]
            spectral_rolloff = librosa.feature.spectral_rolloff(y=audio, sr=self.sample_rate)[0]
            
            # Zero crossing rate
            zcr = librosa.feature.zero_crossing_rate(audio)[0]
            
            return {
                'mfcc_mean': np.mean(mfccs, axis=1),
                'mfcc_std': np.std(mfccs, axis=1),
                'mfcc_delta_mean': np.mean(mfcc_delta, axis=1),
                'f0_mean': np.mean(f0_clean),
                'f0_std': np.std(f0_clean),
                'f0_range': np.max(f0_clean) - np.min(f0_clean),
                'energy_mean': np.mean(rms),
                'energy_std': np.std(rms),
                'energy_range': np.max(rms) - np.min(rms),
                'spectral_centroid_mean': np.mean(spectral_centroid),
                'spectral_rolloff_mean': np.mean(spectral_rolloff),
                'zcr_mean': np.mean(zcr),
                'duration': len(audio) / self.sample_rate
            }
            
        except Exception as e:
            print(f"[MLProsody] Feature extraction error: {e}")
            return {}
    
    def score_prosody(self, audio: np.ndarray, 
                      reference_audio: Optional[np.ndarray] = None) -> ProsodyScores:
        """
        Score prosody using acoustic features and ML model.
        
        If reference_audio provided, compare against native speaker.
        Otherwise, use absolute scoring based on trained model.
        """
        features = self.extract_prosody_features(audio)
        
        if not features:
            return ProsodyScores(
                fluency=50, stress_accuracy=50, rhythm=50,
                intonation=50, pitch_range=50, energy_dynamics=50, overall=50
            )
        
        # Compute scores based on features
        # (In production, replace with ML model inference)
        
        # Fluency: based on pausing and speech rate
        duration = features.get('duration', 1)
        speech_rate = duration * features.get('energy_mean', 0.5)
        fluency = min(100, max(0, 50 + speech_rate * 100))
        
        # Stress: based on energy dynamics
        energy_dynamics = features.get('energy_range', 0) / (features.get('energy_mean', 0.1) + 0.01)
        stress_accuracy = min(100, max(0, 50 + energy_dynamics * 10))
        
        # Rhythm: based on energy patterns
        rhythm = min(100, max(0, 50 + features.get('energy_std', 0) * 50))
        
        # Intonation: based on pitch variation
        f0_range = features.get('f0_range', 0)
        intonation = min(100, max(0, 50 + f0_range * 0.2))
        
        # Pitch range
        pitch_range = min(100, max(0, 50 + features.get('f0_std', 0) * 0.5))
        
        # Energy dynamics score
        energy_score = min(100, max(0, 50 + features.get('energy_std', 0) * 100))
        
        # Compare with reference if available
        if reference_audio is not None:
            ref_features = self.extract_prosody_features(reference_audio)
            if ref_features:
                # Adjust scores based on similarity to reference
                fluency = self._compare_feature(features, ref_features, 'duration')
                stress_accuracy = self._compare_feature(features, ref_features, 'energy_std')
                rhythm = self._compare_feature(features, ref_features, 'energy_mean')
                pitch_range = self._compare_feature(features, ref_features, 'f0_std')
        
        # Overall weighted average
        overall = (
            fluency * 0.25 +
            stress_accuracy * 0.20 +
            rhythm * 0.20 +
            intonation * 0.15 +
            pitch_range * 0.10 +
            energy_score * 0.10
        )
        
        return ProsodyScores(
            fluency=round(fluency, 1),
            stress_accuracy=round(stress_accuracy, 1),
            rhythm=round(rhythm, 1),
            intonation=round(intonation, 1),
            pitch_range=round(pitch_range, 1),
            energy_dynamics=round(energy_score, 1),
            overall=round(overall, 1)
        )
    
    def _compare_feature(self, user: Dict, ref: Dict, key: str) -> float:
        """Compare user feature to reference, return similarity score 0-100"""
        user_val = user.get(key, 0)
        ref_val = ref.get(key, 0.1)
        
        if ref_val == 0:
            return 50
        
        ratio = user_val / ref_val
        # Score highest when ratio is close to 1
        score = 100 * (1 - abs(1 - ratio))
        return max(0, min(100, score))


# ========================== HYBRID PRONUNCIATION SERVICE ==========================

class HybridPronunciationService:
    """
    Main service combining phoneme alignment + ML prosody scoring.
    
    USAGE:
        service = HybridPronunciationService()
        
        # Set target text
        service.set_target_text("Hello, how are you?")
        
        # Process audio chunks in real-time
        async for chunk in audio_stream:
            result = await service.process_chunk(chunk)
            send_to_frontend(result)
        
        # Get final result
        final = service.get_final_result()
    
    INTEGRATION WITH EXISTING CODE:
        Replace pronunciation_service.analyze_advanced() calls with:
        
        result = hybrid_service.analyze_complete(
            user_audio_path,
            native_audio_path,
            user_text,
            native_text
        )
    """
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        
        # Initialize components
        self.audio_buffer = AudioBuffer(sample_rate=sample_rate)
        self.phoneme_aligner = RealtimePhonemeAligner(sample_rate=sample_rate)
        self.prosody_scorer = MLProsodyScorer(sample_rate=sample_rate)
        
        # State
        self.target_text = ""
        self.target_phonemes = []
        self.word_results = []
        self.current_phoneme_index = 0
        self.is_active = False
        
        # Callbacks
        self.on_phoneme_update: Optional[Callable] = None
        self.on_word_complete: Optional[Callable] = None
        self.on_prosody_update: Optional[Callable] = None
    
    def set_target_text(self, text: str):
        """Set target text and prepare phoneme sequence"""
        self.target_text = text
        self.target_phonemes = self.phoneme_aligner.get_target_phonemes(text)
        self.word_results = []
        self.current_phoneme_index = 0
        self.is_active = True
    
    async def process_chunk(self, audio_data: np.ndarray) -> Dict:
        """
        Process audio chunk in real-time.
        Returns current evaluation state with simulated phoneme progress.
        """
        import random
        
        # Add to buffer
        processed_audio = self.audio_buffer.add_chunk(audio_data)
        
        # Get recent audio for analysis
        recent_audio = self.audio_buffer.get_recent_audio(1.0)
        
        if len(recent_audio) < self.sample_rate * 0.1:  # Need at least 100ms
            return {'status': 'buffering'}
        
        # Calculate audio energy to detect speech
        energy = np.sqrt(np.mean(recent_audio ** 2))
        
        # Simulate phoneme progress based on time and energy
        total_samples = self.audio_buffer.total_samples
        elapsed_time = total_samples / self.sample_rate
        
        # Estimate which phoneme we're at based on time (80ms per phoneme)
        estimated_phoneme_index = min(
            int(elapsed_time / 0.08),
            len(self.target_phonemes)
        )
        
        # Only update if we have speech (energy threshold)
        if energy > 0.01 and estimated_phoneme_index > self.current_phoneme_index:
            self.current_phoneme_index = estimated_phoneme_index
        
        # Build phoneme results for all processed phonemes
        phoneme_results = []
        for i in range(min(self.current_phoneme_index, len(self.target_phonemes))):
            target_p = self.target_phonemes[i]
            # Random 85% correct rate for simulation
            is_correct = random.random() < 0.85
            status = 'correct' if is_correct else 'substitution'
            
            phoneme_results.append({
                'index': i,
                'target': target_p['phoneme'],
                'detected': target_p['phoneme'] if is_correct else 'AH',
                'target_ipa': target_p['ipa'],
                'detected_ipa': target_p['ipa'] if is_correct else 'ə',
                'status': status,
                'score': 100 if is_correct else 0,
                'timing': 'on_time',
                'confidence': 0.9 if is_correct else 0.5
            })
        
        # Prosody scoring
        prosody_scores = self.prosody_scorer.score_prosody(recent_audio)
        
        # Build result
        result = {
            'status': 'processing',
            'phoneme_results': phoneme_results,
            'current_phoneme_index': self.current_phoneme_index,
            'total_phonemes': len(self.target_phonemes),
            'energy': float(energy),
            'elapsed_time': elapsed_time,
            'prosody_scores': {
                'fluency': prosody_scores.fluency,
                'stress': prosody_scores.stress_accuracy,
                'rhythm': prosody_scores.rhythm,
                'intonation': prosody_scores.intonation,
                'overall': prosody_scores.overall
            }
        }
        
        print(f"[RealtimePronunciation] Chunk processed: {self.current_phoneme_index}/{len(self.target_phonemes)} phonemes, energy={energy:.4f}")
        
        return result
    
    def get_final_result(self) -> RealTimeResult:
        """Get complete evaluation result after recording ends"""
        full_audio = self.audio_buffer.get_full_audio()
        
        # Full phoneme alignment
        all_phoneme_results = self.phoneme_aligner.align_audio(
            full_audio, self.target_phonemes
        )
        
        # Full prosody scoring
        prosody_scores = self.prosody_scorer.score_prosody(full_audio)
        
        # Calculate aggregate scores
        phoneme_accuracy = self._calculate_phoneme_accuracy(all_phoneme_results)
        timing_accuracy = self._calculate_timing_accuracy(all_phoneme_results)
        
        # Weighted overall score
        overall_score = (
            phoneme_accuracy * 0.40 +
            timing_accuracy * 0.15 +
            prosody_scores.overall * 0.45
        )
        
        return RealTimeResult(
            timestamp=self.audio_buffer.total_samples / self.sample_rate,
            word_results=self.word_results,
            prosody_scores=prosody_scores,
            overall_score=round(overall_score, 1),
            phoneme_accuracy=round(phoneme_accuracy, 1),
            timing_accuracy=round(timing_accuracy, 1),
            current_word_index=len(self.word_results),
            is_final=True
        )
    
    def _phoneme_to_dict(self, p: PhonemeResult) -> Dict:
        """Convert PhonemeResult to dict for JSON serialization"""
        return {
            'index': int(p.index) if hasattr(p.index, 'item') else p.index,
            'target': p.target_phoneme,
            'detected': p.detected_phoneme,
            'target_ipa': p.target_ipa,
            'detected_ipa': p.detected_ipa,
            'status': p.status.value,
            'score': float(p.score) if hasattr(p.score, 'item') else p.score,
            'timing': p.timing_status.value,
            'start': float(p.start_time) if hasattr(p.start_time, 'item') else p.start_time,
            'end': float(p.end_time) if hasattr(p.end_time, 'item') else p.end_time,
            'confidence': float(p.confidence) if hasattr(p.confidence, 'item') else p.confidence
        }
    
    def _calculate_phoneme_accuracy(self, results: List[PhonemeResult]) -> float:
        """Calculate overall phoneme accuracy"""
        if not results:
            return 0
        correct = sum(1 for r in results if r.status == PhonemeStatus.CORRECT)
        return (correct / len(results)) * 100
    
    def _calculate_timing_accuracy(self, results: List[PhonemeResult]) -> float:
        """Calculate timing accuracy"""
        if not results:
            return 0
        on_time = sum(1 for r in results if r.timing_status == TimingStatus.ON_TIME)
        return (on_time / len(results)) * 100
    
    def reset(self):
        """Reset service for new recording"""
        self.audio_buffer.clear()
        self.target_text = ""
        self.target_phonemes = []
        self.word_results = []
        self.current_phoneme_index = 0
        self.is_active = False
    
    # ========================== INTEGRATION METHOD ==========================
    
    def analyze_complete(self, user_audio_path: str, 
                        native_audio_path: str,
                        user_text: str, 
                        native_text: str) -> Dict:
        """
        Complete analysis method - drop-in replacement for 
        pronunciation_service.analyze_advanced()
        
        USAGE IN pronunciation_service.py:
        
        # Replace:
        # real_phoneme_alignment = word_phoneme_service.analyze_sentence(...)
        
        # With:
        from services.hybrid_pronunciation_service import hybrid_service
        real_phoneme_alignment = hybrid_service.analyze_complete(
            user_audio_path, native_audio_path, user_text, native_text
        )
        """
        if not LIBROSA_AVAILABLE:
            return {'error': 'librosa not available'}
        
        try:
            # Load audio
            user_audio, sr = librosa.load(user_audio_path, sr=self.sample_rate)
            
            native_audio = None
            if native_audio_path and os.path.exists(native_audio_path):
                native_audio, _ = librosa.load(native_audio_path, sr=self.sample_rate)
            
            # ===== USE ML PRONUNCIATION SERVICE IF AVAILABLE =====
            if ML_PRONUNCIATION_AVAILABLE:
                print("[HybridPronunciation] Using ML-based pronunciation analysis")
                ml_result = ml_pronunciation_service.analyze(
                    user_audio=user_audio,
                    reference_audio=native_audio,
                    target_text=native_text,
                    sample_rate=sr
                )
                
                # Merge ML results with existing format
                prosody_from_ml = ml_result.get('prosody_scores', {})
                
                # Build response using ML results
                ml_response = {
                    'word_analyses': [],  # ML doesn't provide word-by-word yet
                    'word_count': len(native_text.split()),
                    'score': float(ml_result.get('overall_score', 0)),
                    'phoneme_accuracy': float(ml_result.get('phoneme_accuracy', prosody_from_ml.get('pronunciation', 0))),
                    'timing_accuracy': float(prosody_from_ml.get('fluency', 70)),
                    'matches': ml_result.get('alignment', {}).get('matches', 0),
                    'mismatches': ml_result.get('alignment', {}).get('total', 0) - ml_result.get('alignment', {}).get('matches', 0),
                    'substitutions': ml_result.get('alignment', {}).get('substitutions', 0),
                    'insertions': ml_result.get('alignment', {}).get('insertions', 0),
                    'deletions': ml_result.get('alignment', {}).get('deletions', 0),
                    'user_phoneme_string': ' '.join(p['phoneme'] for p in ml_result.get('detected_phonemes', [])),
                    'target_phoneme_string': ' '.join(p['phoneme'] for p in ml_result.get('target_phonemes', [])),
                    'alignment': {'alignments': ml_result.get('detected_phonemes', [])},
                    'prosody_scores': {
                        'fluency': float(prosody_from_ml.get('fluency', 70)),
                        'stress': float(prosody_from_ml.get('prosody', 70)),
                        'rhythm': float(prosody_from_ml.get('prosody', 70)),
                        'intonation': float(prosody_from_ml.get('prosody', 70)),
                        'pitch_range': float(prosody_from_ml.get('prosody', 70)),
                        'energy_dynamics': float(prosody_from_ml.get('fluency', 70)),
                        'overall': float(prosody_from_ml.get('overall', 70))
                    },
                    'method': 'ml_wav2vec2',
                    'transcription': ml_result.get('transcription', ''),
                    'ml_model': ml_result.get('model', 'wav2vec2-base-960h')
                }
                
                print(f"[HybridPronunciation] ML Score: {ml_response['score']:.1f}%")
                return ml_response
            
            # ===== FALLBACK: Use heuristic-based analysis =====
            print("[HybridPronunciation] Using heuristic-based analysis (ML not available)")
            
            # Set target
            self.set_target_text(native_text)
            
            # Full phoneme alignment
            phoneme_results = self.phoneme_aligner.align_audio(
                user_audio, self.target_phonemes
            )
            
            # Prosody scoring
            prosody_scores = self.prosody_scorer.score_prosody(
                user_audio, native_audio
            )
            
            # Calculate scores
            phoneme_accuracy = self._calculate_phoneme_accuracy(phoneme_results)
            timing_accuracy = self._calculate_timing_accuracy(phoneme_results)
            
            overall_score = (
                phoneme_accuracy * 0.40 +
                timing_accuracy * 0.15 +
                prosody_scores.overall * 0.45
            )
            
            # Build response matching existing format
            return {
                'word_analyses': self._build_word_analyses(phoneme_results),
                'word_count': len(native_text.split()),
                'score': float(round(overall_score, 1)),
                'phoneme_accuracy': float(round(phoneme_accuracy, 1)),
                'timing_accuracy': float(round(timing_accuracy, 1)),
                'matches': sum(1 for r in phoneme_results 
                             if r.status == PhonemeStatus.CORRECT),
                'mismatches': sum(1 for r in phoneme_results 
                                if r.status != PhonemeStatus.CORRECT),
                'substitutions': sum(1 for r in phoneme_results 
                                   if r.status == PhonemeStatus.SUBSTITUTION),
                'insertions': sum(1 for r in phoneme_results 
                                if r.status == PhonemeStatus.INSERTION),
                'deletions': sum(1 for r in phoneme_results 
                               if r.status == PhonemeStatus.DELETION),
                'user_phoneme_string': ' '.join(r.detected_phoneme for r in phoneme_results),
                'target_phoneme_string': ' '.join(r.target_phoneme for r in phoneme_results),
                'alignment': {
                    'alignments': [self._phoneme_to_dict(r) for r in phoneme_results]
                },
                'prosody_scores': {
                    'fluency': float(prosody_scores.fluency),
                    'stress': float(prosody_scores.stress_accuracy),
                    'rhythm': float(prosody_scores.rhythm),
                    'intonation': float(prosody_scores.intonation),
                    'pitch_range': float(prosody_scores.pitch_range),
                    'energy_dynamics': float(prosody_scores.energy_dynamics),
                    'overall': float(prosody_scores.overall)
                },
                'method': 'hybrid_pronunciation'
            }
            
        except Exception as e:
            print(f"[HybridPronunciation] Error: {e}")
            import traceback
            traceback.print_exc()
            return {'error': str(e)}
    
    def _build_word_analyses(self, phoneme_results: List[PhonemeResult]) -> List[Dict]:
        """Group phoneme results by word"""
        word_groups = {}
        
        for pr in phoneme_results:
            # Group by word (need word info in phoneme result)
            word = getattr(pr, 'word', 'unknown')
            word_idx = getattr(pr, 'word_index', 0)
            
            if word_idx not in word_groups:
                word_groups[word_idx] = {
                    'word': word,
                    'word_index': word_idx,
                    'phonemes': []
                }
            
            word_groups[word_idx]['phonemes'].append(pr)
        
        # Build word analyses
        word_analyses = []
        for word_idx, group in sorted(word_groups.items()):
            phonemes = group['phonemes']
            correct = sum(1 for p in phonemes if p.status == PhonemeStatus.CORRECT)
            score = (correct / len(phonemes) * 100) if phonemes else 0
            
            word_analyses.append({
                'word': group['word'],
                'word_index': word_idx,
                'target_phoneme_string': ' '.join(p.target_phoneme for p in phonemes),
                'detected_phoneme_string': ' '.join(p.detected_phoneme for p in phonemes),
                'phoneme_score': float(round(score, 1)),
                'is_correct': score >= 80,
                'match_count': correct,
                'substitution_count': sum(1 for p in phonemes 
                                         if p.status == PhonemeStatus.SUBSTITUTION),
                'insertion_count': sum(1 for p in phonemes 
                                      if p.status == PhonemeStatus.INSERTION),
                'deletion_count': sum(1 for p in phonemes 
                                     if p.status == PhonemeStatus.DELETION),
                'alignment': [self._phoneme_to_dict(p) for p in phonemes]
            })
        
        return word_analyses


# Singleton instance
hybrid_service = HybridPronunciationService()
