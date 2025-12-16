"""
Phoneme Comparison Service
Advanced phoneme-level analysis using DTW alignment and detailed feedback
"""
from typing import Dict, List, Tuple, Optional
import re


# Phoneme categories for detailed analysis
VOWELS = {
    'AA', 'AE', 'AH', 'AO', 'AW', 'AX', 'AY', 'EH', 'ER', 'EY',
    'IH', 'IX', 'IY', 'OW', 'OY', 'UH', 'UW', 'UX'
}

CONSONANTS = {
    # Plosives
    'B', 'D', 'G', 'K', 'P', 'T',
    # Fricatives
    'CH', 'DH', 'F', 'HH', 'JH', 'S', 'SH', 'TH', 'V', 'Z', 'ZH',
    # Nasals
    'M', 'N', 'NG',
    # Liquids
    'L', 'R',
    # Glides
    'W', 'Y'
}

# Mouth/tongue positioning tips for each phoneme
PHONEME_TIPS = {
    # Vowels
    'AA': "Open your mouth wide, tongue flat and low. Like 'father'.",
    'AE': "Open mouth, tongue low and forward. Like 'cat'.",
    'AH': "Relax mouth, tongue in center. Like 'but'.",
    'AO': "Round lips slightly, tongue back and low. Like 'bought'.",
    'AW': "Start with 'ah', glide to 'oo'. Like 'cow'.",
    'AY': "Start with 'ah', glide to 'ee'. Like 'my'.",
    'EH': "Mouth slightly open, tongue mid-front. Like 'bed'.",
    'ER': "Curl tongue tip up slightly. Like 'bird'.",
    'EY': "Start with 'eh', glide to 'ee'. Like 'say'.",
    'IH': "Tongue high and forward, lips relaxed. Like 'bit'.",
    'IY': "Tongue very high and forward, lips spread. Like 'beat'.",
    'OW': "Round lips, start low, glide to 'oo'. Like 'go'.",
    'OY': "Start with 'aw', glide to 'ee'. Like 'boy'.",
    'UH': "Lips slightly rounded, tongue back. Like 'book'.",
    'UW': "Lips very rounded, tongue back and high. Like 'boot'.",
    
    # Consonants - Plosives
    'B': "Close lips completely, release with voice. Like 'boy'.",
    'D': "Tongue tip touches ridge behind upper teeth, release with voice.",
    'G': "Back of tongue touches soft palate, release with voice.",
    'K': "Back of tongue touches soft palate, release without voice.",
    'P': "Close lips completely, release without voice. Like 'pay'.",
    'T': "Tongue tip touches ridge behind upper teeth, release without voice.",
    
    # Consonants - Fricatives
    'CH': "Tongue touches ridge, then releases as 'sh'. Like 'church'.",
    'DH': "Tongue tip between teeth, add voice. Like 'this'.",
    'F': "Upper teeth touch lower lip, blow air. Like 'fun'.",
    'HH': "Breathe out with open throat. Like 'hello'.",
    'JH': "Like 'ch' but with voice. Like 'judge'.",
    'S': "Tongue near ridge, blow air through. Like 'sun'.",
    'SH': "Lips rounded, tongue back from 's'. Like 'shop'.",
    'TH': "Tongue tip between teeth, no voice. Like 'think'.",
    'V': "Upper teeth touch lower lip, add voice. Like 'very'.",
    'Z': "Like 's' but with voice. Like 'zoo'.",
    'ZH': "Like 'sh' but with voice. Like 'measure'.",
    
    # Consonants - Nasals
    'M': "Close lips, sound through nose. Like 'mom'.",
    'N': "Tongue tip on ridge, sound through nose. Like 'no'.",
    'NG': "Back of tongue on soft palate, sound through nose. Like 'sing'.",
    
    # Consonants - Liquids & Glides
    'L': "Tongue tip on ridge, air flows around sides. Like 'love'.",
    'R': "Tongue curls back slightly, lips may round. Like 'red'.",
    'W': "Round lips tightly, then release. Like 'we'.",
    'Y': "Tongue high and forward, glide down. Like 'yes'."
}


class PhonemeComparisonService:
    """Service for comparing phoneme sequences with detailed feedback"""
    
    def __init__(self):
        self.g2p = None
        self._init_g2p()
    
    def _init_g2p(self):
        """Initialize grapheme-to-phoneme converter"""
        try:
            from g2p_en import G2p
            self.g2p = G2p()
        except ImportError:
            print("g2p_en not installed. Using fallback phoneme generation.")
    
    def text_to_phonemes(self, text: str) -> List[str]:
        """Convert text to phoneme sequence"""
        if self.g2p:
            # Use g2p_en for accurate conversion
            phonemes = self.g2p(text)
            # Filter out spaces and punctuation
            return [p for p in phonemes if p.strip() and p not in ' .,!?']
        else:
            # Fallback: simple rule-based (less accurate)
            return self._fallback_phonemes(text)
    
    def _fallback_phonemes(self, text: str) -> List[str]:
        """Fallback phoneme generation using simple rules"""
        # This is a simplified fallback - not as accurate as g2p_en
        text = text.lower()
        phonemes = []
        i = 0
        while i < len(text):
            char = text[i]
            if char in 'aeiou':
                if char == 'a':
                    phonemes.append('AE')
                elif char == 'e':
                    phonemes.append('EH')
                elif char == 'i':
                    phonemes.append('IH')
                elif char == 'o':
                    phonemes.append('OW')
                elif char == 'u':
                    phonemes.append('AH')
            elif char == 't' and i + 1 < len(text) and text[i + 1] == 'h':
                phonemes.append('TH')
                i += 1
            elif char == 's' and i + 1 < len(text) and text[i + 1] == 'h':
                phonemes.append('SH')
                i += 1
            elif char == 'c' and i + 1 < len(text) and text[i + 1] == 'h':
                phonemes.append('CH')
                i += 1
            elif char in 'bcdfghjklmnpqrstvwxyz':
                phonemes.append(char.upper())
            i += 1
        return phonemes
    
    def align_phonemes(self, user_phonemes: List[str], 
                       native_phonemes: List[str]) -> List[Dict]:
        """
        Align two phoneme sequences using DTW
        Returns list of alignment pairs with scores
        """
        try:
            from fastdtw import fastdtw
            from scipy.spatial.distance import hamming
            
            # Create distance matrix (0 for match, 1 for mismatch)
            def phoneme_distance(p1, p2):
                if p1 == p2:
                    return 0
                # Partial credit for same category
                if (p1 in VOWELS and p2 in VOWELS) or (p1 in CONSONANTS and p2 in CONSONANTS):
                    return 0.5
                return 1.0
            
            # Convert to numeric for DTW
            distance, path = fastdtw(
                [[ord(p[0]) if p else 0] for p in user_phonemes],
                [[ord(p[0]) if p else 0] for p in native_phonemes],
                dist=lambda x, y: abs(x[0] - y[0])
            )
            
            # Build alignment from path
            alignments = []
            for user_idx, native_idx in path:
                user_p = user_phonemes[user_idx] if user_idx < len(user_phonemes) else '-'
                native_p = native_phonemes[native_idx] if native_idx < len(native_phonemes) else '-'
                
                match_type = 'match' if user_p == native_p else 'mismatch'
                if user_p == '-':
                    match_type = 'deletion'
                elif native_p == '-':
                    match_type = 'insertion'
                
                alignments.append({
                    'user_phoneme': user_p,
                    'native_phoneme': native_p,
                    'match_type': match_type,
                    'user_index': user_idx,
                    'native_index': native_idx
                })
            
            return alignments
            
        except ImportError:
            # Fallback: simple sequential alignment
            return self._simple_align(user_phonemes, native_phonemes)
    
    def _simple_align(self, user_phonemes: List[str], 
                      native_phonemes: List[str]) -> List[Dict]:
        """Fallback simple sequential alignment"""
        alignments = []
        max_len = max(len(user_phonemes), len(native_phonemes))
        
        for i in range(max_len):
            user_p = user_phonemes[i] if i < len(user_phonemes) else '-'
            native_p = native_phonemes[i] if i < len(native_phonemes) else '-'
            
            match_type = 'match' if user_p == native_p else 'mismatch'
            if user_p == '-':
                match_type = 'deletion'
            elif native_p == '-':
                match_type = 'insertion'
            
            alignments.append({
                'user_phoneme': user_p,
                'native_phoneme': native_p,
                'match_type': match_type,
                'user_index': i,
                'native_index': i
            })
        
        return alignments
    
    def analyze_word(self, user_word: str, native_word: str) -> Dict:
        """
        Analyze pronunciation of a single word
        Returns detailed comparison with tips
        """
        user_phonemes = self.text_to_phonemes(user_word)
        native_phonemes = self.text_to_phonemes(native_word)
        
        alignments = self.align_phonemes(user_phonemes, native_phonemes)
        
        # Calculate similarity
        matches = sum(1 for a in alignments if a['match_type'] == 'match')
        total = len(alignments) if alignments else 1
        similarity = (matches / total) * 100
        
        # Find errors and generate tips
        errors = []
        for align in alignments:
            if align['match_type'] != 'match':
                error = {
                    'position': align['user_index'],
                    'user_phoneme': align['user_phoneme'],
                    'native_phoneme': align['native_phoneme'],
                    'error_type': align['match_type'],
                    'category': 'vowel' if align['native_phoneme'] in VOWELS else 'consonant',
                    'tip': self.get_correction_tip(align['native_phoneme'], align['user_phoneme'])
                }
                errors.append(error)
        
        # Get IPA and syllables using phoneme_utils
        ipa = None
        syllables = None
        try:
            from utils.phoneme_utils import get_word_phonetics
            word_phonetics = get_word_phonetics(native_word)
            ipa = word_phonetics.get('ipa', None)
            syllables = ' · '.join(word_phonetics.get('syllables', [])) if word_phonetics.get('syllables') else None
        except Exception:
            pass  # Fallback if phoneme_utils not available
        
        return {
            'word': native_word,
            'user_phonemes': user_phonemes,
            'native_phonemes': native_phonemes,
            'similarity': round(similarity, 1),
            'alignments': alignments,
            'errors': errors,
            'is_correct': similarity >= 90,
            'ipa': ipa,
            'syllables': syllables
        }
    
    def get_correction_tip(self, target_phoneme: str, actual_phoneme: str) -> str:
        """Get specific correction tip for a phoneme error"""
        target_clean = target_phoneme.rstrip('0123456789')
        
        if target_clean in PHONEME_TIPS:
            base_tip = PHONEME_TIPS[target_clean]
            
            # Add comparison context
            if actual_phoneme and actual_phoneme != '-':
                actual_clean = actual_phoneme.rstrip('0123456789')
                if target_clean in VOWELS and actual_clean in VOWELS:
                    return f"You said /{actual_clean}/, but should be /{target_clean}/. {base_tip}"
                elif target_clean in CONSONANTS and actual_clean in CONSONANTS:
                    return f"You used /{actual_clean}/ instead of /{target_clean}/. {base_tip}"
            
            return base_tip
        
        return f"Focus on producing the /{target_clean}/ sound correctly."
    
    def compare_sentences(self, user_text: str, native_text: str) -> Dict:
        """
        Compare full sentences word by word
        Returns comprehensive analysis
        """
        user_words = user_text.lower().split()
        native_words = native_text.lower().split()
        
        word_analyses = []
        total_similarity = 0
        
        max_words = max(len(user_words), len(native_words))
        for i in range(max_words):
            user_word = user_words[i] if i < len(user_words) else ''
            native_word = native_words[i] if i < len(native_words) else ''
            
            if native_word:
                analysis = self.analyze_word(user_word, native_word)
                word_analyses.append(analysis)
                total_similarity += analysis['similarity']
            else:
                # Extra word from user
                word_analyses.append({
                    'word': user_word,
                    'user_phonemes': self.text_to_phonemes(user_word),
                    'native_phonemes': [],
                    'similarity': 0,
                    'errors': [{'error_type': 'extra_word', 'tip': 'This word was not expected.'}],
                    'is_correct': False
                })
        
        avg_similarity = total_similarity / len(word_analyses) if word_analyses else 0
        
        # Identify problem areas
        problem_words = [w for w in word_analyses if w['similarity'] < 90]
        
        return {
            'overall_similarity': round(avg_similarity, 1),
            'word_count': len(word_analyses),
            'correct_words': len([w for w in word_analyses if w['is_correct']]),
            'problem_words': len(problem_words),
            'word_analyses': word_analyses,
            'needs_practice': [w['word'] for w in problem_words]
        }


# Singleton instance
phoneme_comparison_service = PhonemeComparisonService()
