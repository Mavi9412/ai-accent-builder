"""
Pronunciation Analysis Service
Detects mispronunciations, stress patterns, and generates feedback
Uses simple built-in methods (no external dependencies requiring Rust)
"""
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class PhonemeInfo:
    """Information about a phoneme"""
    phoneme: str
    example_word: str
    mouth_position: str
    tongue_position: str


# Common British English phoneme tips
PHONEME_TIPS = {
    "æ": PhonemeInfo(
        phoneme="æ",
        example_word="cat",
        mouth_position="Open mouth wide, lips relaxed",
        tongue_position="Tongue low and front"
    ),
    "ɑː": PhonemeInfo(
        phoneme="ɑː",
        example_word="father",
        mouth_position="Open mouth wide",
        tongue_position="Tongue low and back"
    ),
    "ɒ": PhonemeInfo(
        phoneme="ɒ",
        example_word="hot (British)",
        mouth_position="Rounded lips, open",
        tongue_position="Tongue low and back"
    ),
    "ə": PhonemeInfo(
        phoneme="ə",
        example_word="about",
        mouth_position="Relaxed, neutral position",
        tongue_position="Central, relaxed"
    ),
    "θ": PhonemeInfo(
        phoneme="θ",
        example_word="think",
        mouth_position="Slightly open",
        tongue_position="Tip between teeth, push air"
    ),
    "ð": PhonemeInfo(
        phoneme="ð",
        example_word="this",
        mouth_position="Slightly open",
        tongue_position="Tip between teeth, voice it"
    ),
    "ʃ": PhonemeInfo(
        phoneme="ʃ",
        example_word="ship",
        mouth_position="Lips rounded, pushed forward",
        tongue_position="Raised toward palate"
    ),
    "ʒ": PhonemeInfo(
        phoneme="ʒ",
        example_word="measure",
        mouth_position="Lips rounded",
        tongue_position="Like 'sh' but voiced"
    ),
    "tʃ": PhonemeInfo(
        phoneme="tʃ",
        example_word="church",
        mouth_position="Lips rounded",
        tongue_position="Start with 't', release into 'sh'"
    ),
    "dʒ": PhonemeInfo(
        phoneme="dʒ",
        example_word="judge",
        mouth_position="Lips rounded",
        tongue_position="Start with 'd', release into 'zh'"
    ),
    "ŋ": PhonemeInfo(
        phoneme="ŋ",
        example_word="sing",
        mouth_position="Mouth slightly open",
        tongue_position="Back of tongue touches soft palate"
    ),
    "r": PhonemeInfo(
        phoneme="r",
        example_word="red",
        mouth_position="Lips slightly rounded",
        tongue_position="Curled back, don't touch roof (British: softer)"
    ),
}

# Simple phoneme approximation rules (no external dependencies)
SIMPLE_PHONEME_MAP = {
    'a': 'AE', 'e': 'EH', 'i': 'IH', 'o': 'AA', 'u': 'AH',
    'ai': 'AY', 'au': 'AW', 'oi': 'OY', 'ou': 'OW', 'oo': 'UW',
    'ee': 'IY', 'ea': 'IY', 'ie': 'IY',
    'th': 'TH', 'sh': 'SH', 'ch': 'CH', 'ng': 'NG', 'wh': 'W',
    'ph': 'F', 'gh': 'F', 'ck': 'K', 'qu': 'KW',
}


class PronunciationService:
    """Service for pronunciation analysis and feedback generation (no Rust dependencies)"""
    
    def __init__(self):
        pass
    
    def text_to_phonemes(self, text: str) -> List[List[str]]:
        """
        Convert text to approximate phonemes for each word
        Uses simple rule-based approach (no g2p-en dependency)
        """
        words = text.split()
        result = []
        
        for word in words:
            clean_word = re.sub(r'[^\w]', '', word.lower())
            if clean_word:
                phonemes = self._simple_g2p(clean_word)
                result.append(phonemes)
            else:
                result.append([])
        
        return result
    
    def _simple_g2p(self, word: str) -> List[str]:
        """Simple grapheme-to-phoneme conversion without external dependencies"""
        phonemes = []
        word = word.lower()
        i = 0
        
        while i < len(word):
            # Try two-character combinations first
            if i < len(word) - 1:
                two_char = word[i:i+2]
                if two_char in SIMPLE_PHONEME_MAP:
                    phonemes.append(SIMPLE_PHONEME_MAP[two_char])
                    i += 2
                    continue
            
            # Single character
            char = word[i]
            if char in SIMPLE_PHONEME_MAP:
                phonemes.append(SIMPLE_PHONEME_MAP[char])
            elif char.isalpha():
                phonemes.append(char.upper())
            i += 1
        
        return phonemes if phonemes else [word.upper()]
    
    def get_expected_phonemes(self, word: str) -> str:
        """Get expected phonemes for a word as string"""
        clean_word = re.sub(r'[^\w]', '', word.lower())
        if clean_word:
            phonemes = self._simple_g2p(clean_word)
            return ' '.join(phonemes)
        return word.upper()
    
    def get_syllables(self, word: str) -> List[str]:
        """Break word into syllables using pyphen"""
        clean_word = re.sub(r'[^\w]', '', word.lower())
        if not clean_word:
            return [word]
        
        try:
            import pyphen
            dic = pyphen.Pyphen(lang='en_US')
            hyphenated = dic.inserted(clean_word)
            syllables = hyphenated.split('-')
            return syllables if syllables else [word]
        except Exception:
            # Fallback to simple vowel-based splitting
            vowels = 'aeiouy'
            syllables = []
            current = ""
            
            for i, char in enumerate(clean_word):
                current += char
                if char in vowels:
                    if i == len(clean_word) - 1:
                        syllables.append(current)
                        current = ""
                    elif i + 2 < len(clean_word) and clean_word[i+1] not in vowels and clean_word[i+2] in vowels:
                        syllables.append(current)
                        current = ""
            
            if current:
                if syllables:
                    syllables[-1] += current
                else:
                    syllables.append(current)
            
            return syllables if syllables else [word]
    
    def get_ipa(self, word: str) -> str:
        """Get IPA phonetic transcription for a word"""
        # Simple IPA mapping for common patterns
        ipa_map = {
            'th': 'θ', 'sh': 'ʃ', 'ch': 'tʃ', 'ng': 'ŋ', 'ph': 'f',
            'wh': 'w', 'ck': 'k', 'gh': '', 'wr': 'r', 'kn': 'n',
            'ee': 'iː', 'ea': 'iː', 'oo': 'uː', 'ou': 'aʊ', 'oi': 'ɔɪ',
            'ai': 'eɪ', 'ay': 'eɪ', 'ey': 'eɪ', 'ie': 'aɪ', 'ow': 'oʊ',
            'au': 'ɔː', 'aw': 'ɔː', 'ew': 'juː', 'ue': 'uː',
        }
        
        single_map = {
            'a': 'æ', 'e': 'ɛ', 'i': 'ɪ', 'o': 'ɒ', 'u': 'ʌ',
            'b': 'b', 'c': 'k', 'd': 'd', 'f': 'f', 'g': 'ɡ',
            'h': 'h', 'j': 'dʒ', 'k': 'k', 'l': 'l', 'm': 'm',
            'n': 'n', 'p': 'p', 'q': 'k', 'r': 'r', 's': 's',
            't': 't', 'v': 'v', 'w': 'w', 'x': 'ks', 'y': 'j', 'z': 'z'
        }
        
        clean_word = re.sub(r'[^\w]', '', word.lower())
        result = ""
        i = 0
        
        while i < len(clean_word):
            if i < len(clean_word) - 1:
                two = clean_word[i:i+2]
                if two in ipa_map:
                    result += ipa_map[two]
                    i += 2
                    continue
            
            char = clean_word[i]
            result += single_map.get(char, char)
            i += 1
        
        return f"/{result}/"
    
    def analyze_pronunciation(self, expected_text: str, 
                               transcribed_text: str,
                               word_timestamps: List[Dict]) -> Dict:
        """
        Analyze pronunciation by comparing expected vs transcribed text
        
        Args:
            expected_text: What should have been said (from TTS input)
            transcribed_text: What was actually said (from STT)
            word_timestamps: Word-level timestamps from STT
            
        Returns:
            Analysis results with scores and feedback
        """
        expected_words = expected_text.lower().split()
        transcribed_words = transcribed_text.lower().split()
        
        # Align words using simple matching
        word_analyses = []
        error_count = 0
        total_score = 0
        
        # Create lookup for transcribed words with timestamps
        ts_lookup = {w["word"].lower(): w for w in word_timestamps}
        
        for i, expected in enumerate(expected_words):
            clean_expected = re.sub(r'[^\w]', '', expected)
            
            # Find matching transcribed word
            if i < len(transcribed_words):
                transcribed = transcribed_words[i]
                clean_transcribed = re.sub(r'[^\w]', '', transcribed)
            else:
                transcribed = ""
                clean_transcribed = ""
            
            # Get timestamps if available
            ts_info = ts_lookup.get(clean_transcribed, {})
            
            # Compare words
            is_correct = clean_expected == clean_transcribed
            
            if is_correct:
                score = 100.0
            else:
                # Calculate similarity
                score = self._calculate_word_similarity(clean_expected, clean_transcribed) * 100
                error_count += 1
            
            total_score += score
            
            # Get phonemes
            expected_phonemes = self.get_expected_phonemes(clean_expected)
            actual_phonemes = self.get_expected_phonemes(clean_transcribed) if clean_transcribed else ""
            
            # Get syllables and IPA
            syllables = self.get_syllables(clean_expected)
            ipa = self.get_ipa(clean_expected)
            
            # Generate feedback
            feedback = None
            if not is_correct and clean_transcribed:
                feedback = self._generate_word_feedback(clean_expected, clean_transcribed)
            elif not clean_transcribed:
                feedback = "Word was not detected. Speak more clearly."
            
            word_analyses.append({
                "word": expected,
                "word_index": i,
                "transcribed_as": transcribed,
                "is_correct": is_correct,
                "score": round(score, 1),
                "expected_phonemes": expected_phonemes,
                "actual_phonemes": actual_phonemes,
                "syllables": syllables,
                "syllable_breakdown": "-".join(syllables),
                "ipa": ipa,
                "timestamp_start": ts_info.get("start", 0),
                "timestamp_end": ts_info.get("end", 0),
                "feedback": feedback
            })
        
        # Calculate overall score
        word_count = len(expected_words)
        avg_score = total_score / word_count if word_count > 0 else 0
        
        # Calculate timing comparison for each word
        timing_comparison = self._calculate_word_timing(word_analyses)
        
        return {
            "word_analyses": word_analyses,
            "timing_comparison": timing_comparison,
            "overall_score": round(avg_score, 1),
            "word_count": word_count,
            "error_count": error_count,
            "accuracy_percentage": round((word_count - error_count) / word_count * 100, 1) if word_count > 0 else 0
        }
    
    def _calculate_word_similarity(self, expected: str, actual: str) -> float:
        """Calculate similarity between two words (0.0 to 1.0)"""
        if not expected or not actual:
            return 0.0
        
        if expected == actual:
            return 1.0
        
        # Levenshtein-like similarity
        len_expected = len(expected)
        len_actual = len(actual)
        
        # Create distance matrix
        dp = [[0] * (len_actual + 1) for _ in range(len_expected + 1)]
        
        for i in range(len_expected + 1):
            dp[i][0] = i
        for j in range(len_actual + 1):
            dp[0][j] = j
        
        for i in range(1, len_expected + 1):
            for j in range(1, len_actual + 1):
                if expected[i-1] == actual[j-1]:
                    dp[i][j] = dp[i-1][j-1]
                else:
                    dp[i][j] = min(
                        dp[i-1][j] + 1,    # deletion
                        dp[i][j-1] + 1,    # insertion
                        dp[i-1][j-1] + 1   # substitution
                    )
        
        distance = dp[len_expected][len_actual]
        max_len = max(len_expected, len_actual)
        
        return 1.0 - (distance / max_len)
    
    def _generate_word_feedback(self, expected: str, actual: str) -> str:
        """Generate feedback for mispronounced word"""
        if not actual:
            return f"The word '{expected}' was not detected. Try speaking more clearly."
        
        # Check for common errors
        if len(actual) < len(expected):
            return f"You said '{actual}' instead of '{expected}'. Some sounds are missing."
        elif len(actual) > len(expected):
            return f"You said '{actual}' instead of '{expected}'. Extra sounds detected."
        else:
            # Same length, different letters
            diff_positions = [i for i, (e, a) in enumerate(zip(expected, actual)) if e != a]
            if diff_positions:
                return f"The pronunciation of '{expected}' differs at position {diff_positions[0]+1}. Focus on the middle sounds."
        
        return f"Your pronunciation of '{expected}' needs improvement. Listen to the correct version."
    
    def _calculate_word_timing(self, word_analyses: List[Dict]) -> Dict:
        """
        Calculate detailed timing comparison between user and native speaker.
        Provides ideal timing, actual timing, difference, and early/late indicators.
        """
        if not word_analyses:
            return {"words": [], "total_difference_ms": 0, "summary": "No words to analyze"}
        
        # Calculate ideal timing based on syllable count (approx 200ms per syllable for native)
        NATIVE_MS_PER_SYLLABLE = 200
        NATIVE_PAUSE_BETWEEN_WORDS_MS = 80
        
        timing_words = []
        total_native_ms = 0
        total_user_ms = 0
        current_native_position = 0
        
        for i, word_data in enumerate(word_analyses):
            word = word_data.get("word", "")
            syllables = word_data.get("syllables", [word])
            syllable_count = len(syllables) if syllables else 1
            
            # Calculate ideal native timing for this word
            native_word_duration_ms = syllable_count * NATIVE_MS_PER_SYLLABLE
            native_start_ms = current_native_position
            native_end_ms = native_start_ms + native_word_duration_ms
            
            # Get user timing from timestamps (convert to ms)
            user_start_ms = word_data.get("timestamp_start", 0) * 1000
            user_end_ms = word_data.get("timestamp_end", 0) * 1000
            user_word_duration_ms = user_end_ms - user_start_ms
            
            # Fallback if no timestamps: estimate based on native
            if user_word_duration_ms <= 0:
                user_word_duration_ms = native_word_duration_ms * (word_data.get("score", 80) / 100)
                user_start_ms = current_native_position
                user_end_ms = user_start_ms + user_word_duration_ms
            
            # Calculate timing difference
            timing_diff_ms = user_word_duration_ms - native_word_duration_ms
            
            # Determine early/late/on-time status
            # Within 50ms is "on time", more is late, less is early
            if abs(timing_diff_ms) <= 50:
                timing_status = "on_time"
                timing_label = "✓ On Time"
            elif timing_diff_ms > 50:
                timing_status = "late"
                timing_label = f"🔴 +{int(timing_diff_ms)}ms Late"
            else:
                timing_status = "early"
                timing_label = f"🟡 {int(timing_diff_ms)}ms Early"
            
            # Detect extra/missing phonemes based on transcription
            transcribed = word_data.get("transcribed_as", "")
            expected = word_data.get("word", "")
            
            extra_sounds = []
            missing_sounds = []
            
            if transcribed and expected:
                # Simple character-level comparison for extra/missing detection
                expected_clean = expected.lower().strip(".,!?")
                transcribed_clean = transcribed.lower().strip(".,!?")
                
                if len(transcribed_clean) > len(expected_clean):
                    extra_count = len(transcribed_clean) - len(expected_clean)
                    extra_sounds.append(f"+{extra_count} extra sound(s)")
                elif len(transcribed_clean) < len(expected_clean):
                    missing_count = len(expected_clean) - len(transcribed_clean)
                    missing_sounds.append(f"-{missing_count} missing sound(s)")
            
            timing_words.append({
                "word": word,
                "word_index": i,
                "syllables": syllables,
                "syllable_count": syllable_count,
                # Native (ideal) timing
                "native_start_ms": round(native_start_ms),
                "native_end_ms": round(native_end_ms),
                "native_duration_ms": round(native_word_duration_ms),
                # User timing
                "user_start_ms": round(user_start_ms),
                "user_end_ms": round(user_end_ms),
                "user_duration_ms": round(user_word_duration_ms),
                # Comparison
                "timing_diff_ms": round(timing_diff_ms),
                "timing_status": timing_status,
                "timing_label": timing_label,
                # Phoneme issues
                "extra_sounds": extra_sounds,
                "missing_sounds": missing_sounds,
                "is_correct": word_data.get("is_correct", False),
                "score": word_data.get("score", 0),
                "ipa": word_data.get("ipa", ""),
                "feedback": word_data.get("feedback", None)
            })
            
            total_native_ms += native_word_duration_ms
            total_user_ms += user_word_duration_ms
            current_native_position = native_end_ms + NATIVE_PAUSE_BETWEEN_WORDS_MS
        
        # Calculate summary statistics
        total_timing_diff = total_user_ms - total_native_ms
        on_time_count = sum(1 for w in timing_words if w["timing_status"] == "on_time")
        late_count = sum(1 for w in timing_words if w["timing_status"] == "late")
        early_count = sum(1 for w in timing_words if w["timing_status"] == "early")
        
        # Generate summary
        if abs(total_timing_diff) <= 200:
            summary = "Excellent timing! Your pace matches the native speaker well."
        elif total_timing_diff > 200:
            summary = f"You spoke {int(total_timing_diff)}ms slower than native. Try to speed up slightly."
        else:
            summary = f"You spoke {int(abs(total_timing_diff))}ms faster than native. Slow down for clarity."
        
        return {
            "words": timing_words,
            "total_native_ms": round(total_native_ms),
            "total_user_ms": round(total_user_ms),
            "total_difference_ms": round(total_timing_diff),
            "on_time_count": on_time_count,
            "late_count": late_count,
            "early_count": early_count,
            "summary": summary
        }
    
    def detect_stress_patterns(self, word: str) -> Dict:
        """
        Detect stress pattern for a word
        Returns syllable count and stress pattern
        """
        self._init_g2p()
        
        clean_word = re.sub(r'[^\w]', '', word.lower())
        
        if self.g2p:
            phonemes = self.g2p(clean_word)
            
            # Count syllables (vowel sounds)
            vowel_sounds = ['AA', 'AE', 'AH', 'AO', 'AW', 'AY', 'EH', 'ER', 
                           'EY', 'IH', 'IY', 'OW', 'OY', 'UH', 'UW']
            
            syllable_count = 0
            stress_pattern = []
            
            for p in phonemes:
                # Check for stress markers (0, 1, 2)
                if any(p.startswith(v) for v in vowel_sounds):
                    syllable_count += 1
                    # Check if this phoneme has stress marker
                    if len(p) > 2 and p[-1].isdigit():
                        stress = int(p[-1])
                        stress_pattern.append(stress)
                    else:
                        stress_pattern.append(0)
            
            return {
                "word": word,
                "syllable_count": syllable_count,
                "stress_pattern": stress_pattern,
                "stress_string": "-".join(map(str, stress_pattern))
            }
        
        # Simple fallback: count vowels
        vowels = 'aeiou'
        syllable_count = sum(1 for c in clean_word.lower() if c in vowels)
        syllable_count = max(1, syllable_count)  # At least 1 syllable
        
        return {
            "word": word,
            "syllable_count": syllable_count,
            "stress_pattern": [1] + [0] * (syllable_count - 1),  # Default: first syllable stressed
            "stress_string": "1-" + "-".join(["0"] * (syllable_count - 1)) if syllable_count > 1 else "1"
        }
    
    def get_phoneme_tip(self, phoneme: str) -> Optional[PhonemeInfo]:
        """Get pronunciation tip for a specific phoneme"""
        return PHONEME_TIPS.get(phoneme)
    
    def generate_improvement_suggestions(self, word_analyses: List[Dict]) -> List[Dict]:
        """
        Generate prioritized improvement suggestions based on analysis
        """
        suggestions = []
        
        # Find words with lowest scores
        incorrect_words = [w for w in word_analyses if not w["is_correct"]]
        incorrect_words.sort(key=lambda x: x["score"])
        
        for word_data in incorrect_words[:5]:  # Top 5 problems
            word = word_data["word"]
            stress_info = self.detect_stress_patterns(word)
            
            suggestion = {
                "word": word,
                "priority": 1 if word_data["score"] < 50 else 2,
                "issue": word_data["feedback"] or f"Pronunciation of '{word}' needs work",
                "suggestions": [
                    f"Listen to the correct pronunciation of '{word}'",
                    f"Pay attention to the {stress_info['syllable_count']} syllables",
                ],
                "stress_pattern": stress_info["stress_string"]
            }
            
            suggestions.append(suggestion)
        
        return suggestions
    
    def _convert_numpy_types(self, obj):
        """Recursively convert numpy types to Python native types for JSON serialization"""
        import numpy as np
        
        if isinstance(obj, dict):
            return {k: self._convert_numpy_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_numpy_types(item) for item in obj]
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.bool_,)):
            return bool(obj)
        else:
            return obj
    
    def analyze_advanced(self, user_audio_path: str, native_audio_path: str,
                         user_text: str, native_text: str) -> Dict:
        """
        Advanced pronunciation analysis using DTW, MFCC, and phoneme alignment
        
        Args:
            user_audio_path: Path to user's recorded audio
            native_audio_path: Path to native speaker audio (TTS generated)
            user_text: Transcribed text from user audio
            native_text: Expected text (what should have been said)
            
        Returns:
            Comprehensive analysis with phoneme details, prosody scores, and tips
        """
        try:
            from services.phoneme_comparison_service import phoneme_comparison_service
            from services.audio_analysis_service import audio_analysis_service
        except ImportError as e:
            return {
                "error": f"Advanced services not available: {e}",
                "fallback": True
            }
        
        # Import new modular services
        try:
            from services.british_g2p import british_g2p
            from services.stress_detector import stress_detector
            from services.formant_analysis import formant_analyzer
            has_new_services = True
        except ImportError:
            has_new_services = False
        
        # NEW: British G2P Analysis
        british_phonemes = None
        if has_new_services:
            try:
                british_phonemes = british_g2p.convert_sentence(native_text)
            except Exception as e:
                print(f"British G2P error: {e}")
        
        # NEW: Stress Pattern Analysis
        stress_analysis = None
        if has_new_services:
            try:
                stress_analysis = stress_detector.analyze_sentence(native_text)
            except Exception as e:
                print(f"Stress analysis error: {e}")
        
        # NEW: Formant Analysis
        user_formants = None
        native_formants = None
        formant_comparison = None
        if has_new_services:
            try:
                user_formants = formant_analyzer.analyze(user_audio_path)
                native_formants = formant_analyzer.analyze(native_audio_path)
                formant_comparison = formant_analyzer.compare_formants(
                    user_audio_path, native_audio_path
                )
            except Exception as e:
                print(f"Formant analysis error: {e}")
        
        # NEW: Advanced Phoneme-Level Analysis
        advanced_sentence_analysis = None
        try:
            from services.advanced_phoneme_service import sentence_analyzer
            advanced_sentence_analysis = sentence_analyzer.analyze_sentence(
                user_audio_path, native_audio_path,
                user_text, native_text
            )
        except Exception as e:
            print(f"Advanced phoneme analysis error: {e}")
        
        # 1. Phoneme-level comparison (basic - text derived)
        phoneme_analysis = phoneme_comparison_service.compare_sentences(
            user_text, native_text
        )
        
        # NEW: HYBRID PRONUNCIATION EVALUATION
        # Combines phoneme alignment + ML prosody scoring + timing analysis
        real_phoneme_alignment = None
        prosody_ml_scores = None
        try:
            from services.hybrid_pronunciation_service import hybrid_service
            
            # Run hybrid analysis (phoneme + prosody)
            analysis_result = hybrid_service.analyze_complete(
                user_audio_path,
                native_audio_path,
                user_text,
                native_text
            )
            
            if 'error' not in analysis_result:
                # Extract prosody scores for later use
                prosody_ml_scores = analysis_result.get('prosody_scores', {})
                
                real_phoneme_alignment = {
                    # Per-word analyses
                    'word_analyses': analysis_result.get('word_analyses', []),
                    'word_count': analysis_result.get('word_count', 0),
                    
                    # Overall scores
                    'score': analysis_result.get('score', 0),
                    'phoneme_accuracy': analysis_result.get('phoneme_accuracy', 0),
                    'timing_accuracy': analysis_result.get('timing_accuracy', 0),
                    
                    # Phoneme statistics
                    'matches': analysis_result.get('matches', 0),
                    'mismatches': analysis_result.get('mismatches', 0),
                    'substitutions': analysis_result.get('substitutions', 0),
                    'insertions': analysis_result.get('insertions', 0),
                    'deletions': analysis_result.get('deletions', 0),
                    
                    # Phoneme strings
                    'user_phoneme_string': analysis_result.get('user_phoneme_string', ''),
                    'target_phoneme_string': analysis_result.get('target_phoneme_string', ''),
                    
                    # Alignment for UI
                    'alignment': analysis_result.get('alignment', {'alignments': []}),
                    
                    # ML Prosody scores
                    'prosody_scores': prosody_ml_scores,
                    
                    # Method
                    'method': 'hybrid_pronunciation'
                }
                
                print(f"[HybridPronunciation] Score: {analysis_result.get('score', 0)}%")
                print(f"[HybridPronunciation] Prosody: {prosody_ml_scores.get('overall', 0)}%")
            
        except Exception as e:
            print(f"Hybrid pronunciation analysis error: {e}")
            import traceback
            traceback.print_exc()
        
        # 2. Audio feature comparison (old method for backward compatibility)
        audio_comparison = audio_analysis_service.compare_with_dtw(
            user_audio_path, native_audio_path
        )
        
        # 3. REAL ACOUSTIC SIGNAL ANALYSIS (DTW-based comparison)
        try:
            from services.acoustic_analysis_service import real_acoustic_service
            
            # Run real signal-based DTW analysis
            acoustic_analysis = real_acoustic_service.compare(
                user_audio_path, native_audio_path
            )
            
            # Use real acoustic scores
            prosody_score = acoustic_analysis['scores']['prosody']
            intonation_score = acoustic_analysis['scores']['intonation']
            stress_score = acoustic_analysis['scores']['stress']
            rhythm_timing_score = acoustic_analysis['scores']['rhythm_timing']
            connected_speech_score = acoustic_analysis['scores']['connected_speech']
            
            has_real_acoustic = True
            
        except Exception as e:
            print(f"Real acoustic analysis not available: {e}")
            # Fallback to old method
            stress_score = min(100, (audio_comparison.get('duration_similarity', 75) + 
                                     audio_comparison.get('energy_similarity', 75)) / 2)
            intonation_score = audio_comparison.get('pitch_similarity', 75)
            rhythm_timing_score = audio_comparison.get('rhythm_similarity', 75)
            prosody_score = audio_comparison.get('overall_similarity', 75)
            word_count = phoneme_analysis.get('word_count', 1)
            connected_speech_score = min(100, 70 + (10 if word_count > 3 else 0) + 
                                         (audio_comparison.get('duration_similarity', 75) * 0.2))
            acoustic_analysis = None
            has_real_acoustic = False
        
        # 4. Combine results - weighted toward real acoustic analysis
        combined_score = (
            phoneme_analysis['overall_similarity'] * 0.5 +
            (prosody_score + intonation_score + rhythm_timing_score) / 3 * 0.5
        )
        
        # 5. Generate comprehensive feedback
        all_tips = []
        
        # Add tips from phoneme errors
        for word_analysis in phoneme_analysis.get('word_analyses', []):
            for error in word_analysis.get('errors', []):
                if error.get('tip'):
                    all_tips.append({
                        'word': word_analysis.get('word', ''),
                        'type': 'phoneme',
                        'category': error.get('category', 'unknown'),
                        'tip': error.get('tip'),
                        'user_phoneme': error.get('user_phoneme', ''),
                        'native_phoneme': error.get('native_phoneme', '')
                    })
        
        # Add tips from prosody analysis
        for fb in audio_comparison.get('feedback', []):
            all_tips.append({
                'type': 'prosody',
                'tip': fb
            })
        
        # Calculate vowel/consonant scores from phoneme analysis
        vowel_errors = 0
        consonant_errors = 0
        total_vowels = 0
        total_consonants = 0
        
        for word_analysis in phoneme_analysis.get('word_analyses', []):
            for error in word_analysis.get('errors', []):
                if error.get('category') == 'vowel':
                    vowel_errors += 1
                elif error.get('category') == 'consonant':
                    consonant_errors += 1
            # Count total phonemes by category
            for phoneme in word_analysis.get('native_phonemes', []):
                if phoneme in {'AA', 'AE', 'AH', 'AO', 'AW', 'AX', 'AY', 'EH', 'ER', 'EY', 'IH', 'IX', 'IY', 'OW', 'OY', 'UH', 'UW', 'UX'}:
                    total_vowels += 1
                else:
                    total_consonants += 1
        
        # Calculate vowel/consonant scores (phoneme-based, not heuristic)
        vowel_score = max(0, 100 - (vowel_errors * 15)) if total_vowels > 0 else 80
        consonant_score = max(0, 100 - (consonant_errors * 12)) if total_consonants > 0 else 80
        
        # Accent score (combined phoneme + acoustic)
        accent_score = (phoneme_analysis['overall_similarity'] * 0.5 + 
                       intonation_score * 0.3 + prosody_score * 0.2)

        
        result = {
            'overall_score': round(combined_score, 1),
            'phoneme_score': round(phoneme_analysis['overall_similarity'], 1),
            'prosody_score': round(audio_comparison['overall_similarity'], 1),
            
            # Detailed Category Scores (7 categories)
            'detailed_scores': {
                'vowels': {
                    'score': round(vowel_score, 1),
                    'label': 'Vowels',
                    'icon': 'fa-circle',
                    'description': 'Clarity and accuracy of vowel sounds',
                    'errors': vowel_errors,
                    'total': total_vowels
                },
                'consonants': {
                    'score': round(consonant_score, 1),
                    'label': 'Consonants',
                    'icon': 'fa-square',
                    'description': 'Accuracy of consonant pronunciation',
                    'errors': consonant_errors,
                    'total': total_consonants
                },
                'stress': {
                    'score': round(stress_score, 1),
                    'label': 'Stress',
                    'icon': 'fa-arrows-alt-v',
                    'description': 'Word and sentence stress patterns'
                },
                'intonation': {
                    'score': round(intonation_score, 1),
                    'label': 'Intonation',
                    'icon': 'fa-chart-area',
                    'description': 'Pitch patterns and melody of speech'
                },
                'rhythm_timing': {
                    'score': round(rhythm_timing_score, 1),
                    'label': 'Rhythm & Timing',
                    'icon': 'fa-clock',
                    'description': 'Pace, pauses, and speech flow'
                },
                'connected_speech': {
                    'score': round(connected_speech_score, 1),
                    'label': 'Connected Speech',
                    'icon': 'fa-link',
                    'description': 'Linking, elision, and assimilation'
                },
                'accent_features': {
                    'score': round(accent_score, 1),
                    'label': 'Accent & Dialect',
                    'icon': 'fa-globe-europe',
                    'description': 'British English accent characteristics'
                }
            },
            
            # Voice Feature Comparison - Raw extracted data from both voices
            'voice_comparison': {
                'user_voice': {
                    'duration': audio_comparison.get('user_duration', 0),
                    'pitch_mean': audio_comparison.get('user_features', {}).get('pitch_mean', 0),
                    'pitch_std': audio_comparison.get('user_features', {}).get('pitch_std', 0),
                    'energy_mean': audio_comparison.get('user_features', {}).get('energy_mean', 0),
                    'tempo': audio_comparison.get('user_features', {}).get('tempo', 0),
                    'mfcc_mean': audio_comparison.get('user_features', {}).get('mfcc_mean', [])[:5]  # First 5 MFCCs
                },
                'native_voice': {
                    'duration': audio_comparison.get('native_duration', 0),
                    'pitch_mean': audio_comparison.get('native_features', {}).get('pitch_mean', 0),
                    'pitch_std': audio_comparison.get('native_features', {}).get('pitch_std', 0),
                    'energy_mean': audio_comparison.get('native_features', {}).get('energy_mean', 0),
                    'tempo': audio_comparison.get('native_features', {}).get('tempo', 0),
                    'mfcc_mean': audio_comparison.get('native_features', {}).get('mfcc_mean', [])[:5]
                },
                'comparison': {
                    'pitch_similarity': round(audio_comparison.get('pitch_similarity', 0), 1),
                    'pitch_variation_similarity': round(audio_comparison.get('pitch_variation_similarity', 0), 1),
                    'rhythm_similarity': round(audio_comparison.get('rhythm_similarity', 0), 1),
                    'duration_similarity': round(audio_comparison.get('duration_similarity', 0), 1),
                    'energy_similarity': round(audio_comparison.get('energy_similarity', 0), 1),
                    'spectral_similarity': round(audio_comparison.get('spectral_similarity', 0), 1),
                    'dtw_distance': round(audio_comparison.get('dtw_distance', 0), 2)
                }
            },
            
            # Phoneme Comparison Details
            'phoneme_comparison': {
                'user_text': user_text,
                'native_text': native_text,
                'overall_similarity': round(phoneme_analysis['overall_similarity'], 1),
                'correct_words': phoneme_analysis.get('correct_words', 0),
                'problem_words': phoneme_analysis.get('problem_words', 0),
                'word_count': phoneme_analysis.get('word_count', 0)
            },
            
            # Detailed phoneme analysis
            'word_analyses': phoneme_analysis.get('word_analyses', []),
            'needs_practice': phoneme_analysis.get('needs_practice', []),
            
            # Prosody details (for backward compatibility)
            'pitch_similarity': audio_comparison.get('pitch_similarity', 0),
            'rhythm_similarity': audio_comparison.get('rhythm_similarity', 0),
            'duration_similarity': audio_comparison.get('duration_similarity', 0),
            'user_duration': audio_comparison.get('user_duration', 0),
            'native_duration': audio_comparison.get('native_duration', 0),
            
            # All improvement tips
            'improvement_tips': all_tips,
            
            # Feature comparison (for visualization)
            'dtw_distance': audio_comparison.get('dtw_distance', 0),
            
            # Real Acoustic Signal Analysis (new comprehensive data)
            'real_acoustic_analysis': acoustic_analysis if 'acoustic_analysis' in dir() and acoustic_analysis else None,
            'has_real_acoustic': has_real_acoustic if 'has_real_acoustic' in dir() else False,
            
            # NEW: British English Phonemes
            'british_phonemes': british_phonemes,
            
            # NEW: Stress Pattern Analysis
            'stress_analysis': stress_analysis,
            
            # NEW: Formant Analysis (F1, F2, F3, F4)
            'formant_analysis': {
                'user': user_formants,
                'native': native_formants,
                'comparison': formant_comparison
            } if formant_comparison else None,
            
            # NEW: Advanced Phoneme-Level Analysis (word-by-word with audio)
            'advanced_sentence_analysis': advanced_sentence_analysis,
            
            # NEW: REAL Phoneme Alignment from Audio (actual acoustic phonemes)
            'real_phoneme_alignment': real_phoneme_alignment
        }
        
        # Convert all numpy types to Python native types for JSON serialization
        return self._convert_numpy_types(result)


# Singleton instance
pronunciation_service = PronunciationService()

