"""
Word-by-Word Phoneme Analysis Service
Implements proper word segmentation, per-word phoneme recognition,
Levenshtein alignment, and detailed scoring.
"""
import os
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import warnings
warnings.filterwarnings("ignore")

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    print("[WordPhonemeService] librosa not available")

try:
    from g2p_en import G2p
    G2P_AVAILABLE = True
except ImportError:
    G2P_AVAILABLE = False
    print("[WordPhonemeService] g2p_en not available")


# ARPAbet phonemes
VOWEL_PHONEMES = {'AA', 'AE', 'AH', 'AO', 'AW', 'AY', 'EH', 'ER', 'EY', 'IH', 'IY', 'OW', 'OY', 'UH', 'UW'}
CONSONANT_PHONEMES = {'B', 'CH', 'D', 'DH', 'F', 'G', 'HH', 'JH', 'K', 'L', 'M', 'N', 'NG', 'P', 'R', 'S', 'SH', 'T', 'TH', 'V', 'W', 'Y', 'Z', 'ZH'}

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


@dataclass
class PhonemeAlignment:
    """Represents alignment between detected and target phoneme"""
    detected: str
    target: str
    match_type: str  # 'match', 'substitution', 'insertion', 'deletion'
    detected_ipa: str
    target_ipa: str


@dataclass
class WordAnalysis:
    """Complete analysis of a single word"""
    word: str
    word_index: int
    start_time: float
    end_time: float
    duration_ms: float
    target_phonemes: List[str]
    detected_phonemes: List[str]
    alignment: List[PhonemeAlignment]
    phoneme_score: float
    match_count: int
    substitution_count: int
    insertion_count: int
    deletion_count: int
    feedback: List[str]
    is_correct: bool


class WordPhonemeAnalysisService:
    """
    Service for word-by-word phoneme analysis.
    
    Pipeline:
    1. Split audio into words using silence detection
    2. Run phoneme recognition per word
    3. Align detected vs target phonemes using Levenshtein
    4. Generate per-word and sentence reports
    """
    
    def __init__(self):
        self.g2p = None
        if G2P_AVAILABLE:
            self.g2p = G2p()
        self.sr = 16000
    
    # ==================== STEP 1: Split Audio into Words ====================
    
    def split_audio_into_words(self, audio_path: str, 
                                expected_words: List[str] = None,
                                word_timestamps: List[Dict] = None) -> List[Dict]:
        """
        Split audio into word segments using silence detection or provided timestamps.
        
        Args:
            audio_path: Path to audio file
            expected_words: List of expected words (for reference)
            word_timestamps: Pre-computed word timestamps from STT
            
        Returns:
            List of word segments with audio data and timing
        """
        if not LIBROSA_AVAILABLE:
            return []
        
        try:
            # Load audio
            audio, sr = librosa.load(audio_path, sr=self.sr)
            duration = len(audio) / sr
            
            # If we have word timestamps from STT, use them
            if word_timestamps and len(word_timestamps) > 0:
                return self._segment_with_timestamps(audio, sr, word_timestamps)
            
            # Otherwise use silence detection
            return self._segment_with_silence_detection(audio, sr, expected_words)
            
        except Exception as e:
            print(f"[WordPhoneme] Audio split error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _segment_with_timestamps(self, audio: np.ndarray, sr: int, 
                                  word_timestamps: List[Dict]) -> List[Dict]:
        """Segment audio using pre-computed word timestamps"""
        segments = []
        
        for i, ts in enumerate(word_timestamps):
            word = ts.get('word', f'word_{i}')
            start = ts.get('start', 0)
            end = ts.get('end', start + 0.5)
            
            # Extract audio segment
            start_sample = int(start * sr)
            end_sample = int(end * sr)
            
            # Add padding (50ms each side)
            pad_samples = int(0.05 * sr)
            start_sample = max(0, start_sample - pad_samples)
            end_sample = min(len(audio), end_sample + pad_samples)
            
            segment_audio = audio[start_sample:end_sample]
            
            segments.append({
                'word': word,
                'word_index': i,
                'start_time': start,
                'end_time': end,
                'duration_ms': (end - start) * 1000,
                'audio': segment_audio,
                'sr': sr
            })
        
        return segments
    
    def _segment_with_silence_detection(self, audio: np.ndarray, sr: int,
                                         expected_words: List[str] = None) -> List[Dict]:
        """Segment audio using librosa silence detection"""
        # Use librosa.effects.split for VAD
        # top_db: threshold below reference to consider as silence
        intervals = librosa.effects.split(audio, top_db=25, hop_length=160)
        
        segments = []
        num_words = len(expected_words) if expected_words else len(intervals)
        
        for i, (start_sample, end_sample) in enumerate(intervals):
            # Convert to time
            start_time = start_sample / sr
            end_time = end_sample / sr
            
            # Get word if available
            word = expected_words[i] if expected_words and i < len(expected_words) else f'segment_{i}'
            
            # Extract audio
            segment_audio = audio[start_sample:end_sample]
            
            # Skip very short segments (< 50ms)
            if len(segment_audio) / sr < 0.05:
                continue
            
            segments.append({
                'word': word,
                'word_index': i,
                'start_time': start_time,
                'end_time': end_time,
                'duration_ms': (end_time - start_time) * 1000,
                'audio': segment_audio,
                'sr': sr
            })
        
        return segments
    
    # ==================== STEP 2: Phoneme Recognition per Word ====================
    
    def recognize_phonemes_from_segment(self, segment_audio: np.ndarray, sr: int) -> Dict:
        """
        Run phoneme recognition on a word audio segment.
        Uses MFCC-based acoustic analysis for phoneme estimation.
        
        Returns:
            {
                'phonemes': ['HH', 'AH', 'L', 'OW'],
                'phoneme_details': [...],
                'confidence': 0.75
            }
        """
        if len(segment_audio) == 0:
            return {'phonemes': [], 'phoneme_details': [], 'confidence': 0}
        
        duration = len(segment_audio) / sr
        
        # Extract acoustic features
        try:
            # MFCC for phoneme characteristics
            mfccs = librosa.feature.mfcc(y=segment_audio, sr=sr, n_mfcc=13, hop_length=160)
            
            # Energy (RMS)
            rms = librosa.feature.rms(y=segment_audio, hop_length=160)[0]
            
            # Zero crossing rate (fricatives/plosives)
            zcr = librosa.feature.zero_crossing_rate(segment_audio, hop_length=160)[0]
            
            # Spectral centroid (brightness)
            spectral_centroid = librosa.feature.spectral_centroid(y=segment_audio, sr=sr, hop_length=160)[0]
            
            # Spectral rolloff
            rolloff = librosa.feature.spectral_rolloff(y=segment_audio, sr=sr, hop_length=160)[0]
            
        except Exception as e:
            print(f"[WordPhoneme] Feature extraction error: {e}")
            return {'phonemes': [], 'phoneme_details': [], 'confidence': 0}
        
        # Normalize features
        rms_norm = self._normalize(rms)
        zcr_norm = self._normalize(zcr)
        sc_norm = self._normalize(spectral_centroid)
        rolloff_norm = self._normalize(rolloff)
        
        # Segment into phonemes based on acoustic changes
        phonemes = []
        phoneme_details = []
        time_per_frame = duration / len(rms) if len(rms) > 0 else 0.02
        
        # Find phoneme boundaries using feature changes
        boundaries = self._find_phoneme_boundaries(mfccs, rms_norm, zcr_norm)
        
        for i, (start_frame, end_frame) in enumerate(boundaries):
            # Get features for this segment
            seg_rms = np.mean(rms_norm[start_frame:end_frame])
            seg_zcr = np.mean(zcr_norm[start_frame:end_frame])
            seg_sc = np.mean(sc_norm[start_frame:end_frame])
            seg_rolloff = np.mean(rolloff_norm[start_frame:end_frame]) if len(rolloff_norm) > 0 else 0.5
            
            # Classify phoneme
            phoneme = self._classify_phoneme(seg_rms, seg_zcr, seg_sc, seg_rolloff, mfccs[:, start_frame:end_frame])
            
            # Calculate confidence
            confidence = min(0.95, 0.5 + seg_rms * 0.3 + (1 - seg_zcr) * 0.15)
            
            phonemes.append(phoneme)
            phoneme_details.append({
                'phoneme': phoneme,
                'ipa': ARPABET_TO_IPA.get(phoneme, phoneme.lower()),
                'start': round(start_frame * time_per_frame, 3),
                'end': round(end_frame * time_per_frame, 3),
                'confidence': round(confidence, 2),
                'is_vowel': phoneme in VOWEL_PHONEMES
            })
        
        avg_confidence = np.mean([p['confidence'] for p in phoneme_details]) if phoneme_details else 0
        
        return {
            'phonemes': phonemes,
            'phoneme_details': phoneme_details,
            'confidence': round(avg_confidence, 2)
        }
    
    def _normalize(self, arr: np.ndarray) -> np.ndarray:
        """Normalize array to 0-1 range"""
        if len(arr) == 0:
            return arr
        min_val = np.min(arr)
        max_val = np.max(arr)
        if max_val - min_val < 1e-6:
            return np.zeros_like(arr) + 0.5
        return (arr - min_val) / (max_val - min_val)
    
    def _find_phoneme_boundaries(self, mfccs: np.ndarray, 
                                  rms: np.ndarray, zcr: np.ndarray) -> List[Tuple[int, int]]:
        """Find phoneme boundaries using feature dynamics"""
        num_frames = len(rms)
        if num_frames < 3:
            return [(0, num_frames)]
        
        # Compute delta features for change detection
        delta_rms = np.abs(np.diff(rms))
        delta_zcr = np.abs(np.diff(zcr))
        
        # Combine deltas
        combined_delta = delta_rms * 0.6 + delta_zcr * 0.4
        
        # Find peaks (phoneme boundaries)
        threshold = np.mean(combined_delta) + 0.5 * np.std(combined_delta)
        boundaries = [0]
        
        min_frames = 3  # Minimum phoneme length (~30ms)
        
        for i in range(1, len(combined_delta)):
            if combined_delta[i] > threshold and (i - boundaries[-1]) >= min_frames:
                boundaries.append(i)
        
        boundaries.append(num_frames)
        
        # Create segments
        segments = []
        for i in range(len(boundaries) - 1):
            if boundaries[i+1] - boundaries[i] >= min_frames:
                segments.append((boundaries[i], boundaries[i+1]))
        
        # Ensure at least one segment
        if not segments:
            segments = [(0, num_frames)]
        
        return segments
    
    def _classify_phoneme(self, rms: float, zcr: float, sc: float, 
                          rolloff: float, mfcc_segment: np.ndarray) -> str:
        """Classify a segment as a specific phoneme based on acoustic features"""
        
        # Vowel vs Consonant classification
        # Vowels: high energy, low ZCR, moderate spectral centroid
        # Consonants: variable energy, often high ZCR
        
        # Get MFCC characteristics
        mfcc_mean = np.mean(mfcc_segment, axis=1) if mfcc_segment.size > 0 else np.zeros(13)
        
        if rms > 0.4 and zcr < 0.2:
            # Likely vowel
            return self._classify_vowel(sc, mfcc_mean, rolloff)
        elif zcr > 0.3:
            # Likely fricative
            return self._classify_fricative(sc, rms)
        elif rms < 0.2:
            # Likely stop consonant or silence
            return self._classify_stop(sc, zcr)
        else:
            # Sonorant consonant (L, R, N, M, etc.)
            return self._classify_sonorant(mfcc_mean, rms, sc)
    
    def _classify_vowel(self, sc: float, mfcc: np.ndarray, rolloff: float) -> str:
        """Classify vowel based on spectral characteristics"""
        # Map spectral centroid to vowel
        # Low SC: back vowels (UH, UW, OW, AO)
        # Mid SC: central vowels (AH, ER)
        # High SC: front vowels (IY, IH, EH, AE)
        
        if sc < 0.25:
            vowels = ['UW', 'UH', 'OW']
        elif sc < 0.4:
            vowels = ['OW', 'AO', 'AH']
        elif sc < 0.55:
            vowels = ['AH', 'ER', 'EH']
        elif sc < 0.7:
            vowels = ['EH', 'IH', 'AE']
        else:
            vowels = ['IY', 'IH', 'AE', 'EY']
        
        # Use MFCC to refine
        if len(mfcc) >= 2:
            idx = int(abs(mfcc[1]) * 10) % len(vowels)
            return vowels[idx]
        return vowels[0]
    
    def _classify_fricative(self, sc: float, rms: float) -> str:
        """Classify fricative consonant"""
        if sc > 0.7:
            return 'S' if rms > 0.15 else 'F'
        elif sc > 0.5:
            return 'SH' if rms > 0.2 else 'TH'
        else:
            return 'HH' if rms < 0.1 else 'V'
    
    def _classify_stop(self, sc: float, zcr: float) -> str:
        """Classify stop consonant"""
        stops = ['P', 'T', 'K', 'B', 'D', 'G']
        # Voiceless stops have lower ZCR
        if zcr < 0.15:
            return stops[int(sc * 3) % 3]  # P, T, K
        else:
            return stops[3 + int(sc * 3) % 3]  # B, D, G
    
    def _classify_sonorant(self, mfcc: np.ndarray, rms: float, sc: float) -> str:
        """Classify sonorant consonant (L, R, M, N, etc.)"""
        sonorants = ['L', 'R', 'M', 'N', 'NG', 'W', 'Y']
        if len(mfcc) >= 3:
            idx = int(abs(mfcc[2]) * 10) % len(sonorants)
            return sonorants[idx]
        return 'L' if sc > 0.4 else 'N'
    
    # ==================== STEP 3: Levenshtein Alignment ====================
    
    def get_target_phonemes(self, word: str) -> List[str]:
        """Get target phonemes from CMUdict/G2P"""
        if not self.g2p:
            return []
        
        phonemes = self.g2p(word.lower())
        # Clean: remove stress markers, filter punctuation
        cleaned = []
        for p in phonemes:
            if p.strip() and p not in ' .,!?\'-':
                cleaned.append(p.rstrip('0123456789'))
        return cleaned
    
    def align_phonemes_levenshtein(self, detected: List[str], 
                                    target: List[str]) -> Tuple[List[PhonemeAlignment], Dict]:
        """
        Align detected phonemes to target using Levenshtein distance with detailed operations.
        
        Returns:
            (alignments, stats) where:
            - alignments: List of PhonemeAlignment objects
            - stats: {matches, substitutions, insertions, deletions, score}
        """
        if not detected and not target:
            return [], {'matches': 0, 'substitutions': 0, 'insertions': 0, 'deletions': 0, 'score': 100}
        
        if not detected:
            # All deletions
            alignments = [
                PhonemeAlignment('-', t, 'deletion', '-', ARPABET_TO_IPA.get(t, t))
                for t in target
            ]
            return alignments, {'matches': 0, 'substitutions': 0, 'insertions': 0, 'deletions': len(target), 'score': 0}
        
        if not target:
            # All insertions
            alignments = [
                PhonemeAlignment(d, '-', 'insertion', ARPABET_TO_IPA.get(d, d), '-')
                for d in detected
            ]
            return alignments, {'matches': 0, 'substitutions': 0, 'insertions': len(detected), 'deletions': 0, 'score': 0}
        
        # Build DP matrix for Levenshtein distance
        m, n = len(detected), len(target)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        # Initialize
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        
        # Fill DP table
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if detected[i-1] == target[j-1]:
                    dp[i][j] = dp[i-1][j-1]  # Match
                else:
                    dp[i][j] = 1 + min(
                        dp[i-1][j],      # Deletion
                        dp[i][j-1],      # Insertion
                        dp[i-1][j-1]     # Substitution
                    )
        
        # Backtrack to get alignment
        alignments = []
        i, j = m, n
        
        while i > 0 or j > 0:
            if i > 0 and j > 0 and detected[i-1] == target[j-1]:
                # Match
                alignments.append(PhonemeAlignment(
                    detected[i-1], target[j-1], 'match',
                    ARPABET_TO_IPA.get(detected[i-1], detected[i-1]),
                    ARPABET_TO_IPA.get(target[j-1], target[j-1])
                ))
                i -= 1
                j -= 1
            elif i > 0 and j > 0 and dp[i][j] == dp[i-1][j-1] + 1:
                # Substitution
                alignments.append(PhonemeAlignment(
                    detected[i-1], target[j-1], 'substitution',
                    ARPABET_TO_IPA.get(detected[i-1], detected[i-1]),
                    ARPABET_TO_IPA.get(target[j-1], target[j-1])
                ))
                i -= 1
                j -= 1
            elif i > 0 and dp[i][j] == dp[i-1][j] + 1:
                # Deletion (extra in detected)
                alignments.append(PhonemeAlignment(
                    detected[i-1], '-', 'insertion',
                    ARPABET_TO_IPA.get(detected[i-1], detected[i-1]),
                    '-'
                ))
                i -= 1
            else:
                # Insertion (missing from detected)
                alignments.append(PhonemeAlignment(
                    '-', target[j-1], 'deletion',
                    '-',
                    ARPABET_TO_IPA.get(target[j-1], target[j-1])
                ))
                j -= 1
        
        # Reverse (we built it backwards)
        alignments.reverse()
        
        # Calculate stats
        matches = sum(1 for a in alignments if a.match_type == 'match')
        substitutions = sum(1 for a in alignments if a.match_type == 'substitution')
        insertions = sum(1 for a in alignments if a.match_type == 'insertion')
        deletions = sum(1 for a in alignments if a.match_type == 'deletion')
        
        # Score: percentage of matches
        total = max(len(detected), len(target))
        score = (matches / total * 100) if total > 0 else 100
        
        return alignments, {
            'matches': matches,
            'substitutions': substitutions,
            'insertions': insertions,
            'deletions': deletions,
            'score': round(score, 1)
        }
    
    # ==================== STEP 4: Generate Per-Word Report ====================
    
    def analyze_word(self, segment: Dict, expected_word: str = None) -> WordAnalysis:
        """
        Complete analysis of a single word segment.
        """
        word = expected_word or segment.get('word', 'unknown')
        audio = segment.get('audio', np.array([]))
        sr = segment.get('sr', self.sr)
        
        # Get target phonemes
        target_phonemes = self.get_target_phonemes(word)
        
        # Recognize phonemes from audio
        recognition = self.recognize_phonemes_from_segment(audio, sr)
        detected_phonemes = recognition.get('phonemes', [])
        
        # Align detected to target
        alignments, stats = self.align_phonemes_levenshtein(detected_phonemes, target_phonemes)
        
        # Generate feedback
        feedback = self._generate_word_feedback(alignments, word)
        
        return WordAnalysis(
            word=word,
            word_index=segment.get('word_index', 0),
            start_time=segment.get('start_time', 0),
            end_time=segment.get('end_time', 0),
            duration_ms=segment.get('duration_ms', 0),
            target_phonemes=target_phonemes,
            detected_phonemes=detected_phonemes,
            alignment=alignments,
            phoneme_score=stats['score'],
            match_count=stats['matches'],
            substitution_count=stats['substitutions'],
            insertion_count=stats['insertions'],
            deletion_count=stats['deletions'],
            feedback=feedback,
            is_correct=stats['score'] >= 80
        )
    
    def _generate_word_feedback(self, alignments: List[PhonemeAlignment], word: str) -> List[str]:
        """Generate helpful feedback for pronunciation issues"""
        feedback = []
        
        for align in alignments:
            if align.match_type == 'substitution':
                det_is_vowel = align.detected in VOWEL_PHONEMES
                tgt_is_vowel = align.target in VOWEL_PHONEMES
                
                if det_is_vowel and tgt_is_vowel:
                    feedback.append(f"Vowel error: /{align.detected_ipa}/ → should be /{align.target_ipa}/")
                elif not det_is_vowel and not tgt_is_vowel:
                    feedback.append(f"Consonant error: /{align.detected_ipa}/ → should be /{align.target_ipa}/")
                else:
                    feedback.append(f"Sound mismatch: /{align.detected_ipa}/ → /{align.target_ipa}/")
                    
            elif align.match_type == 'deletion':
                feedback.append(f"Missing sound: /{align.target_ipa}/ was not pronounced")
                
            elif align.match_type == 'insertion':
                feedback.append(f"Extra sound: /{align.detected_ipa}/ should not be there")
        
        return feedback
    
    # ==================== STEP 5: Sentence-Level Report ====================
    
    def analyze_sentence(self, audio_path: str, expected_text: str,
                         word_timestamps: List[Dict] = None) -> Dict:
        """
        Complete sentence-level phoneme analysis.
        
        Args:
            audio_path: Path to user audio file
            expected_text: Expected sentence text
            word_timestamps: Optional word timestamps from STT
            
        Returns:
            Complete analysis report with per-word and summary data
        """
        expected_words = expected_text.lower().split()
        
        # Step 1: Split audio into words
        segments = self.split_audio_into_words(audio_path, expected_words, word_timestamps)
        
        if not segments:
            return {
                'error': 'Could not segment audio into words',
                'word_analyses': [],
                'overall_score': 0
            }
        
        # Step 2-4: Analyze each word
        word_analyses = []
        for i, segment in enumerate(segments):
            expected_word = expected_words[i] if i < len(expected_words) else segment.get('word', '')
            analysis = self.analyze_word(segment, expected_word)
            word_analyses.append(analysis)
        
        # Step 5: Combine into sentence report
        return self._generate_sentence_report(word_analyses, expected_text)
    
    def _generate_sentence_report(self, word_analyses: List[WordAnalysis], 
                                   expected_text: str) -> Dict:
        """Generate comprehensive sentence-level report"""
        if not word_analyses:
            return {'error': 'No words analyzed', 'overall_score': 0}
        
        # Calculate averages
        scores = [w.phoneme_score for w in word_analyses]
        avg_score = np.mean(scores) if scores else 0
        
        # Count totals
        total_matches = sum(w.match_count for w in word_analyses)
        total_substitutions = sum(w.substitution_count for w in word_analyses)
        total_insertions = sum(w.insertion_count for w in word_analyses)
        total_deletions = sum(w.deletion_count for w in word_analyses)
        
        # Identify problem words
        problem_words = [w for w in word_analyses if not w.is_correct]
        
        # Collect all feedback
        all_feedback = []
        for w in word_analyses:
            for fb in w.feedback:
                all_feedback.append({'word': w.word, 'feedback': fb})
        
        # Convert word analyses to dicts for JSON serialization
        word_analysis_dicts = []
        for w in word_analyses:
            alignment_dicts = [
                {
                    'detected': a.detected,
                    'target': a.target,
                    'match_type': a.match_type,
                    'detected_ipa': a.detected_ipa,
                    'target_ipa': a.target_ipa
                }
                for a in w.alignment
            ]
            
            word_analysis_dicts.append({
                'word': w.word,
                'word_index': w.word_index,
                'start_time': w.start_time,
                'end_time': w.end_time,
                'duration_ms': w.duration_ms,
                'target_phonemes': w.target_phonemes,
                'target_phoneme_string': ' '.join(w.target_phonemes),
                'detected_phonemes': w.detected_phonemes,
                'detected_phoneme_string': ' '.join(w.detected_phonemes),
                'alignment': alignment_dicts,
                'phoneme_score': w.phoneme_score,
                'match_count': w.match_count,
                'substitution_count': w.substitution_count,
                'insertion_count': w.insertion_count,
                'deletion_count': w.deletion_count,
                'feedback': w.feedback,
                'is_correct': w.is_correct
            })
        
        return {
            'expected_text': expected_text,
            'word_count': len(word_analyses),
            'word_analyses': word_analysis_dicts,
            
            # Overall scores
            'overall_score': round(avg_score, 1),
            'correct_words': sum(1 for w in word_analyses if w.is_correct),
            'problem_words': len(problem_words),
            
            # Phoneme statistics
            'total_matches': total_matches,
            'total_substitutions': total_substitutions,
            'total_insertions': total_insertions,
            'total_deletions': total_deletions,
            
            # Feedback
            'all_feedback': all_feedback[:10],  # Limit to top 10
            'problem_word_list': [w.word for w in problem_words],
            
            # Method info
            'method': 'word_by_word_mfcc'
        }


# Singleton instance
word_phoneme_service = WordPhonemeAnalysisService()
