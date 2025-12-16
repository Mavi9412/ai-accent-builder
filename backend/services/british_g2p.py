"""
British English Grapheme-to-Phoneme Service
Uses pronouncing (CMU dict) and eng_to_ipa for British-style phonemes.
Fully offline, no Rust dependencies.
"""
from typing import Dict, List, Optional
import re

# Try importing libraries
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


# British English phoneme mappings (American → British)
AMERICAN_TO_BRITISH = {
    # Vowels
    'AA': 'ɑː',   # BATH, PALM
    'AE': 'æ',    # TRAP
    'AH': 'ʌ',    # STRUT
    'AO': 'ɔː',   # THOUGHT
    'AW': 'aʊ',   # MOUTH
    'AY': 'aɪ',   # PRICE
    'EH': 'e',    # DRESS
    'ER': 'ɜː',   # NURSE (non-rhotic)
    'EY': 'eɪ',   # FACE
    'IH': 'ɪ',    # KIT
    'IY': 'iː',   # FLEECE
    'OW': 'əʊ',   # GOAT (British diphthong)
    'OY': 'ɔɪ',   # CHOICE
    'UH': 'ʊ',    # FOOT
    'UW': 'uː',   # GOOSE
    # Consonants (mostly same)
    'B': 'b', 'CH': 'tʃ', 'D': 'd', 'DH': 'ð',
    'F': 'f', 'G': 'g', 'HH': 'h', 'JH': 'dʒ',
    'K': 'k', 'L': 'l', 'M': 'm', 'N': 'n',
    'NG': 'ŋ', 'P': 'p', 'R': 'ɹ', 'S': 's',
    'SH': 'ʃ', 'T': 't', 'TH': 'θ', 'V': 'v',
    'W': 'w', 'Y': 'j', 'Z': 'z', 'ZH': 'ʒ'
}


class BritishG2PService:
    """British English Grapheme-to-Phoneme converter."""
    
    def __init__(self):
        print(f"BritishG2PService: pronouncing={PRONOUNCING_AVAILABLE}, ipa={IPA_AVAILABLE}")
    
    def word_to_arpabet(self, word: str) -> List[str]:
        """Convert word to ARPAbet phonemes using CMU dict."""
        if not PRONOUNCING_AVAILABLE:
            return []
        
        word = word.lower().strip()
        phones = pronouncing.phones_for_word(word)
        
        if phones:
            # Return first pronunciation, split into phonemes
            return phones[0].split()
        return []
    
    def word_to_ipa(self, word: str) -> str:
        """Convert word to IPA using eng_to_ipa."""
        if not IPA_AVAILABLE:
            return ""
        
        try:
            result = ipa.convert(word)
            return result if result != word else ""
        except:
            return ""
    
    def arpabet_to_british_ipa(self, arpabet: List[str]) -> str:
        """Convert ARPAbet phonemes to British IPA."""
        british_ipa = []
        
        for phone in arpabet:
            # Remove stress markers (0, 1, 2)
            base_phone = re.sub(r'[012]', '', phone)
            
            if base_phone in AMERICAN_TO_BRITISH:
                british_ipa.append(AMERICAN_TO_BRITISH[base_phone])
            else:
                british_ipa.append(base_phone.lower())
        
        return ''.join(british_ipa)
    
    def convert(self, word: str) -> Dict:
        """
        Convert word to British English phonemes.
        Returns ARPAbet, IPA, and British IPA representations.
        """
        word = word.strip().lower()
        
        # Get ARPAbet from CMU dict
        arpabet = self.word_to_arpabet(word)
        
        # Get IPA from eng_to_ipa
        ipa_result = self.word_to_ipa(word)
        
        # Convert to British IPA
        british_ipa = self.arpabet_to_british_ipa(arpabet) if arpabet else ""
        
        return {
            'word': word,
            'arpabet': arpabet,
            'ipa': ipa_result,
            'british_ipa': british_ipa,
            'success': bool(arpabet or ipa_result)
        }
    
    def convert_sentence(self, sentence: str) -> Dict:
        """Convert entire sentence to phonemes."""
        words = re.findall(r'\b\w+\b', sentence.lower())
        results = []
        
        for word in words:
            results.append(self.convert(word))
        
        # Combine British IPA
        combined_ipa = ' '.join(r['british_ipa'] for r in results if r['british_ipa'])
        
        return {
            'sentence': sentence,
            'words': results,
            'combined_ipa': combined_ipa,
            'word_count': len(words)
        }


# Singleton
british_g2p = BritishG2PService()
