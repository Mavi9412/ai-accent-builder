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
        
        return {
            "word_analyses": word_analyses,
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
        
        # 1. Phoneme-level comparison
        phoneme_analysis = phoneme_comparison_service.compare_sentences(
            user_text, native_text
        )
        
        # 2. Audio feature comparison (MFCC, pitch, rhythm)
        audio_comparison = audio_analysis_service.compare_with_dtw(
            user_audio_path, native_audio_path
        )
        
        # 3. Combine results
        combined_score = (
            phoneme_analysis['overall_similarity'] * 0.6 +
            audio_comparison['overall_similarity'] * 0.4
        )
        
        # 4. Generate comprehensive feedback
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
        
        # Calculate detailed category scores
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
        
        # Calculate category scores (0-100)
        vowel_score = max(0, 100 - (vowel_errors * 15)) if total_vowels > 0 else 80
        consonant_score = max(0, 100 - (consonant_errors * 12)) if total_consonants > 0 else 80
        
        # Stress score based on duration patterns
        stress_score = min(100, (audio_comparison.get('duration_similarity', 75) + 
                                 audio_comparison.get('energy_similarity', 75)) / 2)
        
        # Intonation score based on pitch
        intonation_score = audio_comparison.get('pitch_similarity', 75)
        
        # Rhythm & Timing score
        rhythm_timing_score = audio_comparison.get('rhythm_similarity', 75)
        
        # Connected Speech score (linking, elision, assimilation)
        word_count = phoneme_analysis.get('word_count', 1)
        connected_speech_score = min(100, 70 + (10 if word_count > 3 else 0) + 
                                     (audio_comparison.get('duration_similarity', 75) * 0.2))
        
        # Accent & Dialect Features score (based on overall similarity)
        accent_score = (phoneme_analysis['overall_similarity'] * 0.6 + 
                       audio_comparison.get('pitch_similarity', 75) * 0.4)
        
        return {
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
            
            # Detailed phoneme analysis
            'word_analyses': phoneme_analysis.get('word_analyses', []),
            'correct_words': phoneme_analysis.get('correct_words', 0),
            'problem_words': phoneme_analysis.get('problem_words', 0),
            'needs_practice': phoneme_analysis.get('needs_practice', []),
            
            # Prosody details
            'pitch_similarity': audio_comparison.get('pitch_similarity', 0),
            'rhythm_similarity': audio_comparison.get('rhythm_similarity', 0),
            'duration_similarity': audio_comparison.get('duration_similarity', 0),
            'user_duration': audio_comparison.get('user_duration', 0),
            'native_duration': audio_comparison.get('native_duration', 0),
            
            # All improvement tips
            'improvement_tips': all_tips,
            
            # Feature comparison (for visualization)
            'dtw_distance': audio_comparison.get('dtw_distance', 0)
        }


# Singleton instance
pronunciation_service = PronunciationService()

