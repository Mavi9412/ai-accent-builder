"""
Stress Detection Service
Uses pyphen with en_GB dictionary for syllabification and stress detection.
Fully offline, no Rust dependencies.
"""
from typing import Dict, List, Tuple
import re

# Try importing pyphen
try:
    import pyphen
    PYPHEN_AVAILABLE = True
except ImportError:
    PYPHEN_AVAILABLE = False

# Try importing pronouncing for stress patterns
try:
    import pronouncing
    PRONOUNCING_AVAILABLE = True
except ImportError:
    PRONOUNCING_AVAILABLE = False


class StressDetectorService:
    """Syllable and stress pattern detector for British English."""
    
    def __init__(self):
        self.dic = None
        if PYPHEN_AVAILABLE:
            try:
                self.dic = pyphen.Pyphen(lang='en_GB')
            except:
                try:
                    self.dic = pyphen.Pyphen(lang='en')
                except:
                    pass
        
        print(f"StressDetectorService: pyphen={PYPHEN_AVAILABLE}, dic={self.dic is not None}")
    
    def get_syllables(self, word: str) -> List[str]:
        """Split word into syllables using pyphen."""
        if not self.dic:
            return self._fallback_syllables(word)
        
        word = word.lower().strip()
        hyphenated = self.dic.inserted(word)
        syllables = hyphenated.split('-')
        
        return [s for s in syllables if s]
    
    def _fallback_syllables(self, word: str) -> List[str]:
        """Simple vowel-based syllable estimation."""
        vowels = 'aeiouy'
        syllables = []
        current = ""
        
        for i, char in enumerate(word.lower()):
            current += char
            if char in vowels:
                # Check if next char is consonant or end
                if i == len(word) - 1 or word[i+1] not in vowels:
                    syllables.append(current)
                    current = ""
        
        if current:
            if syllables:
                syllables[-1] += current
            else:
                syllables.append(current)
        
        return syllables if syllables else [word]
    
    def get_stress_pattern(self, word: str) -> Dict:
        """
        Get stress pattern from CMU dict.
        0 = no stress, 1 = primary, 2 = secondary
        """
        if not PRONOUNCING_AVAILABLE:
            return self._estimate_stress(word)
        
        word = word.lower().strip()
        phones = pronouncing.phones_for_word(word)
        
        if not phones:
            return self._estimate_stress(word)
        
        # Extract stress markers (0, 1, 2) from vowels
        stress_pattern = []
        for phone in phones[0].split():
            for char in phone:
                if char in '012':
                    stress_pattern.append(int(char))
        
        # Find primary stress position
        primary_idx = stress_pattern.index(1) if 1 in stress_pattern else 0
        
        # Build stress string
        stress_string = ''.join(['ˈ' if s == 1 else 'ˌ' if s == 2 else '·' for s in stress_pattern])
        
        return {
            'word': word,
            'pattern': stress_pattern,
            'primary_stress_syllable': primary_idx,
            'stress_string': stress_string,
            'has_secondary': 2 in stress_pattern
        }
    
    def _estimate_stress(self, word: str) -> Dict:
        """Estimate stress pattern for unknown words."""
        syllables = self.get_syllables(word)
        n = len(syllables)
        
        # Default rules:
        # 1 syllable: primary stress
        # 2 syllables: usually first
        # 3+ syllables: often penultimate
        
        if n == 1:
            pattern = [1]
            primary = 0
        elif n == 2:
            pattern = [1, 0]
            primary = 0
        else:
            pattern = [0] * n
            primary = max(0, n - 2)  # Penultimate
            pattern[primary] = 1
        
        stress_string = ''.join(['ˈ' if s == 1 else '·' for s in pattern])
        
        return {
            'word': word,
            'pattern': pattern,
            'primary_stress_syllable': primary,
            'stress_string': stress_string,
            'has_secondary': False,
            'estimated': True
        }
    
    def analyze(self, word: str) -> Dict:
        """
        Full stress analysis for a word.
        Returns syllables, stress pattern, and formatted output.
        """
        word = word.lower().strip()
        syllables = self.get_syllables(word)
        stress = self.get_stress_pattern(word)
        
        # Combine syllables with stress markers
        marked_syllables = []
        pattern = stress.get('pattern', [])
        
        for i, syl in enumerate(syllables):
            if i < len(pattern):
                if pattern[i] == 1:
                    marked_syllables.append(f"ˈ{syl}")
                elif pattern[i] == 2:
                    marked_syllables.append(f"ˌ{syl}")
                else:
                    marked_syllables.append(syl)
            else:
                marked_syllables.append(syl)
        
        return {
            'word': word,
            'syllables': syllables,
            'syllable_count': len(syllables),
            'stress_pattern': stress['pattern'],
            'primary_stress': stress['primary_stress_syllable'],
            'stress_string': stress['stress_string'],
            'marked_syllables': marked_syllables,
            'formatted': '-'.join(marked_syllables)
        }
    
    def analyze_sentence(self, sentence: str) -> Dict:
        """Analyze stress patterns for entire sentence."""
        words = re.findall(r'\b\w+\b', sentence.lower())
        results = []
        
        for word in words:
            results.append(self.analyze(word))
        
        return {
            'sentence': sentence,
            'words': results,
            'word_count': len(words),
            'total_syllables': sum(r['syllable_count'] for r in results)
        }


# Singleton
stress_detector = StressDetectorService()
