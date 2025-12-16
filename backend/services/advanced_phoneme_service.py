"""
Advanced Phoneme Comparison Service - OPTIMIZED
Real phoneme-level analysis using audio features and G2P alignment.
Provides word-level and phoneme-level scoring.
OPTIMIZED: Single audio load, cached features, fast scoring.
"""
from typing import List, Dict, Tuple, Optional
import numpy as np
import re

# Library imports with availability checks
LIBROSA_AVAILABLE = False
PARSELMOUTH_AVAILABLE = False
FASTDTW_AVAILABLE = False

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    pass

try:
    import parselmouth
    PARSELMOUTH_AVAILABLE = True
except ImportError:
    pass

try:
    from fastdtw import fastdtw
    from scipy.spatial.distance import euclidean
    FASTDTW_AVAILABLE = True
except ImportError:
    pass

# G2P imports
try:
    import pronouncing
    PRONOUNCING_AVAILABLE = True
except ImportError:
    PRONOUNCING_AVAILABLE = False

try:
    import eng_to_ipa as ipa
    IPA_AVAILABLE = True
except ImportError:
    IPA_AVAILABLE = False


class AdvancedPhonemeComparisonService:
    """
    OPTIMIZED phoneme comparison with cached audio features.
    """
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self._audio_cache = {}
        self._mfcc_cache = {}
        self._pitch_cache = {}
        print(f"AdvancedPhonemeComparisonService (FAST) initialized")
    
    def clear_cache(self):
        """Clear audio caches."""
        self._audio_cache.clear()
        self._mfcc_cache.clear()
        self._pitch_cache.clear()
    
    # =========================================================================
    # CACHED AUDIO LOADING
    # =========================================================================
    
    def load_audio_cached(self, audio_path: str) -> Tuple[Optional[np.ndarray], int]:
        """Load audio with caching."""
        if audio_path in self._audio_cache:
            return self._audio_cache[audio_path], self.sample_rate
        
        if not LIBROSA_AVAILABLE:
            return None, self.sample_rate
        try:
            y, sr = librosa.load(audio_path, sr=self.sample_rate)
            self._audio_cache[audio_path] = y
            return y, sr
        except:
            return None, self.sample_rate
    
    def get_mfcc_cached(self, audio_path: str) -> np.ndarray:
        """Get MFCC features with caching."""
        if audio_path in self._mfcc_cache:
            return self._mfcc_cache[audio_path]
        
        audio, sr = self.load_audio_cached(audio_path)
        if audio is None or not LIBROSA_AVAILABLE:
            return np.array([])
        
        try:
            mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
            self._mfcc_cache[audio_path] = mfcc.T
            return mfcc.T
        except:
            return np.array([])
    
    def get_pitch_cached(self, audio_path: str) -> np.ndarray:
        """Get pitch with caching."""
        if audio_path in self._pitch_cache:
            return self._pitch_cache[audio_path]
        
        if not PARSELMOUTH_AVAILABLE:
            return np.array([])
        try:
            snd = parselmouth.Sound(audio_path)
            pitch = snd.to_pitch()
            pitch_values = pitch.selected_array['frequency']
            self._pitch_cache[audio_path] = pitch_values
            return pitch_values
        except:
            return np.array([])
    
    # =========================================================================
    # PHONEME EXTRACTION (Fast - no audio needed)
    # =========================================================================
    
    def word_to_phonemes(self, word: str) -> List[str]:
        """Convert word to ARPAbet phonemes."""
        if not PRONOUNCING_AVAILABLE:
            return []
        phones = pronouncing.phones_for_word(word.lower().strip())
        return phones[0].split() if phones else []
    
    def word_to_ipa(self, word: str) -> str:
        """Convert word to IPA."""
        if not IPA_AVAILABLE:
            return ""
        try:
            return ipa.convert(word.lower().strip())
        except:
            return ""
    
    def get_phoneme_category(self, phoneme: str) -> str:
        """Classify phoneme as vowel or consonant."""
        vowels = {'AA', 'AE', 'AH', 'AO', 'AW', 'AY', 'EH', 'ER', 'EY', 
                  'IH', 'IY', 'OW', 'OY', 'UH', 'UW'}
        base = re.sub(r'[0-9]', '', phoneme.upper())
        return 'vowel' if base in vowels else 'consonant'
    
    # =========================================================================
    # FAST PHONEME SCORING (No audio)
    # =========================================================================
    
    def score_phoneme_match(self, user_phoneme: str, target_phoneme: str) -> float:
        """Score phoneme match (100=exact, 90=stress diff, 70=similar, 30=different)."""
        user_base = re.sub(r'[0-9]', '', user_phoneme.upper())
        target_base = re.sub(r'[0-9]', '', target_phoneme.upper())
        
        if user_base == target_base:
            user_stress = re.search(r'[0-9]', user_phoneme)
            target_stress = re.search(r'[0-9]', target_phoneme)
            if user_stress and target_stress:
                return 100.0 if user_stress.group() == target_stress.group() else 90.0
            return 100.0
        
        similar_groups = [
            {'AA', 'AH', 'AO'}, {'IH', 'IY'}, {'EH', 'AE'}, {'UH', 'UW'},
            {'T', 'D'}, {'P', 'B'}, {'K', 'G'}, {'S', 'Z'},
            {'F', 'V'}, {'TH', 'DH'}, {'SH', 'ZH'}, {'CH', 'JH'}
        ]
        
        for group in similar_groups:
            if user_base in group and target_base in group:
                return 70.0
        return 30.0
    
    def align_phonemes(self, user_phonemes: List[str], 
                       target_phonemes: List[str]) -> List[Dict]:
        """Fast phoneme alignment."""
        if not user_phonemes or not target_phonemes:
            return []
        
        alignments = []
        max_len = max(len(user_phonemes), len(target_phonemes))
        
        for i in range(max_len):
            user_ph = user_phonemes[i] if i < len(user_phonemes) else None
            target_ph = target_phonemes[i] if i < len(target_phonemes) else None
            
            if user_ph and target_ph:
                score = self.score_phoneme_match(user_ph, target_ph)
                match_type = 'match' if score >= 90 else 'partial' if score >= 50 else 'mismatch'
            else:
                score = 0
                match_type = 'insertion' if user_ph else 'deletion'
            
            alignments.append({
                'user_phoneme': user_ph,
                'target_phoneme': target_ph,
                'score': score,
                'match_type': match_type,
                'category': self.get_phoneme_category(target_ph) if target_ph else None
            })
        
        return alignments
    
    # =========================================================================
    # FAST WORD ANALYSIS (Phoneme-only, no per-word audio)
    # =========================================================================
    
    def analyze_word_fast(self, user_word: str, target_word: str,
                          sentence_mfcc_score: float = 50.0,
                          sentence_pitch_score: float = 50.0) -> Dict:
        """
        FAST word analysis - only phoneme comparison, uses sentence audio scores.
        """
        user_phonemes = self.word_to_phonemes(user_word)
        target_phonemes = self.word_to_phonemes(target_word)
        target_ipa = self.word_to_ipa(target_word)
        
        alignments = self.align_phonemes(user_phonemes, target_phonemes)
        
        if alignments:
            phoneme_score = sum(a['score'] for a in alignments) / len(alignments)
        else:
            phoneme_score = 100 if user_word == target_word else 0
        
        # Use sentence-level audio scores (already computed once)
        word_score = (
            phoneme_score * 0.60 +
            sentence_mfcc_score * 0.25 +
            sentence_pitch_score * 0.15
        )
        
        vowel_errors = sum(1 for a in alignments if a['category'] == 'vowel' and a['score'] < 90)
        consonant_errors = sum(1 for a in alignments if a['category'] == 'consonant' and a['score'] < 90)
        
        return {
            'word': target_word,
            'user_word': user_word,
            'target_phonemes': target_phonemes,
            'target_ipa': target_ipa,
            'phoneme_score': round(phoneme_score, 1),
            'mfcc_score': round(sentence_mfcc_score, 1),
            'pitch_score': round(sentence_pitch_score, 1),
            'word_score': round(word_score, 1),
            'vowel_errors': vowel_errors,
            'consonant_errors': consonant_errors,
            'is_correct': word_score >= 80
        }


class SentencePronunciationAnalyzer:
    """OPTIMIZED sentence analyzer - loads audio once."""
    
    def __init__(self):
        self.phoneme_service = AdvancedPhonemeComparisonService()
    
    def _compute_mfcc_similarity(self, user_mfcc: np.ndarray, 
                                  native_mfcc: np.ndarray) -> float:
        """Compute MFCC similarity once for whole sentence."""
        if len(user_mfcc) == 0 or len(native_mfcc) == 0:
            return 50.0
        
        if not FASTDTW_AVAILABLE:
            min_len = min(len(user_mfcc), len(native_mfcc))
            corr = np.corrcoef(user_mfcc[:min_len].flatten(), 
                              native_mfcc[:min_len].flatten())[0, 1]
            return (corr + 1) * 50 if not np.isnan(corr) else 50.0
        
        try:
            # Use radius to speed up DTW
            distance, _ = fastdtw(user_mfcc, native_mfcc, dist=euclidean, radius=10)
            return min(100, 1 / (1 + distance / 1000) * 100)
        except:
            return 50.0
    
    def _compute_pitch_similarity(self, user_pitch: np.ndarray,
                                   native_pitch: np.ndarray) -> float:
        """Compute pitch similarity once for whole sentence."""
        user_voiced = user_pitch[user_pitch > 0]
        native_voiced = native_pitch[native_pitch > 0]
        
        if len(user_voiced) == 0 or len(native_voiced) == 0:
            return 50.0
        
        if not FASTDTW_AVAILABLE:
            diff = abs(np.mean(user_voiced) - np.mean(native_voiced)) / max(np.mean(native_voiced), 1)
            return max(0, 100 - diff * 100)
        
        try:
            distance, _ = fastdtw(user_voiced.reshape(-1, 1), 
                                 native_voiced.reshape(-1, 1), 
                                 dist=euclidean, radius=10)
            return min(100, 1 / (1 + distance / 500) * 100)
        except:
            return 50.0
    
    def analyze_sentence(self, user_audio_path: str, native_audio_path: str,
                         user_text: str, native_text: str) -> Dict:
        """
        FAST sentence analysis - computes audio features ONCE.
        """
        # Clear cache from previous analysis
        self.phoneme_service.clear_cache()
        
        # Load audio ONCE
        user_mfcc = self.phoneme_service.get_mfcc_cached(user_audio_path)
        native_mfcc = self.phoneme_service.get_mfcc_cached(native_audio_path)
        user_pitch = self.phoneme_service.get_pitch_cached(user_audio_path)
        native_pitch = self.phoneme_service.get_pitch_cached(native_audio_path)
        
        # Compute sentence-level audio scores ONCE
        sentence_mfcc_score = self._compute_mfcc_similarity(user_mfcc, native_mfcc)
        sentence_pitch_score = self._compute_pitch_similarity(user_pitch, native_pitch)
        
        # Analyze words (text-only, fast)
        user_words = user_text.lower().split()
        native_words = native_text.lower().split()
        
        results = []
        total_word_score = 0.0
        total_vowel_errors = 0
        total_consonant_errors = 0
        
        max_len = max(len(user_words), len(native_words))
        for i in range(max_len):
            user_word = user_words[i] if i < len(user_words) else ""
            native_word = native_words[i] if i < len(native_words) else ""
            
            if native_word:
                word_analysis = self.phoneme_service.analyze_word_fast(
                    user_word or native_word, native_word,
                    sentence_mfcc_score, sentence_pitch_score
                )
                total_word_score += word_analysis['word_score']
                total_vowel_errors += word_analysis['vowel_errors']
                total_consonant_errors += word_analysis['consonant_errors']
                results.append(word_analysis)
            else:
                results.append({
                    'word': user_word,
                    'word_score': 0,
                    'is_correct': False,
                    'note': 'Extra word'
                })
        
        n_words = len(results)
        sentence_score = round(total_word_score / n_words, 1) if n_words > 0 else 0
        correct_words = sum(1 for r in results if r.get('is_correct', False))
        
        vowel_score = max(0, 100 - (total_vowel_errors * 15))
        consonant_score = max(0, 100 - (total_consonant_errors * 12))
        
        return {
            'sentence_score': sentence_score,
            'word_count': n_words,
            'correct_words': correct_words,
            'problem_words': n_words - correct_words,
            'total_vowel_errors': total_vowel_errors,
            'total_consonant_errors': total_consonant_errors,
            'vowel_score': round(vowel_score, 1),
            'consonant_score': round(consonant_score, 1),
            'sentence_mfcc_score': round(sentence_mfcc_score, 1),
            'sentence_pitch_score': round(sentence_pitch_score, 1),
            'results': results
        }


# Singleton instances
advanced_phoneme_service = AdvancedPhonemeComparisonService()
sentence_analyzer = SentencePronunciationAnalyzer()
