"""
Phoneme utility functions for pronunciation analysis
"""
from typing import List, Dict, Optional, Tuple


# IPA to ARPABET mapping for common phonemes
IPA_TO_ARPABET = {
    'i': 'IY', 'ɪ': 'IH', 'e': 'EY', 'ɛ': 'EH', 'æ': 'AE',
    'ɑ': 'AA', 'ɔ': 'AO', 'o': 'OW', 'ʊ': 'UH', 'u': 'UW',
    'ə': 'AH', 'ʌ': 'AH', 'ɜ': 'ER', 'ɝ': 'ER',
    'aɪ': 'AY', 'aʊ': 'AW', 'ɔɪ': 'OY',
    'p': 'P', 'b': 'B', 't': 'T', 'd': 'D', 'k': 'K', 'g': 'G',
    'f': 'F', 'v': 'V', 'θ': 'TH', 'ð': 'DH', 's': 'S', 'z': 'Z',
    'ʃ': 'SH', 'ʒ': 'ZH', 'h': 'HH', 'tʃ': 'CH', 'dʒ': 'JH',
    'm': 'M', 'n': 'N', 'ŋ': 'NG', 'l': 'L', 'r': 'R',
    'w': 'W', 'j': 'Y'
}

# Common pronunciation difficulties for Indian English speakers learning British English
COMMON_DIFFICULTIES = {
    'θ': {'issue': 'th sound (think)', 'tip': 'Place tongue between teeth, blow air'},
    'ð': {'issue': 'th sound (this)', 'tip': 'Like θ but voiced'},
    'v': {'issue': 'v vs w confusion', 'tip': 'Bite lower lip lightly for v'},
    'w': {'issue': 'w sound', 'tip': 'Round lips, no teeth contact'},
    'æ': {'issue': 'short a (cat)', 'tip': 'Mouth wide open, tongue low'},
    'ə': {'issue': 'schwa sound', 'tip': 'Relax mouth completely'},
    'ɜ': {'issue': 'er sound (bird)', 'tip': 'Lips slightly rounded'},
}


def get_ipa_for_word(word: str) -> str:
    """
    Get IPA representation for a word using g2p-en
    """
    try:
        from g2p_en import G2p
        g2p = G2p()
        phonemes = g2p(word.lower())
        return ' '.join(phonemes)
    except ImportError:
        return word.upper()


def compare_phonemes(expected: str, actual: str) -> Dict:
    """
    Compare expected and actual phonemes
    
    Returns:
        Dict with match percentage and differences
    """
    expected_list = expected.split()
    actual_list = actual.split()
    
    matches = 0
    differences = []
    
    max_len = max(len(expected_list), len(actual_list))
    
    for i in range(max_len):
        exp = expected_list[i] if i < len(expected_list) else None
        act = actual_list[i] if i < len(actual_list) else None
        
        if exp == act:
            matches += 1
        else:
            differences.append({
                'position': i,
                'expected': exp,
                'actual': act,
                'type': 'substitution' if exp and act else ('deletion' if exp else 'insertion')
            })
    
    match_percentage = (matches / max_len * 100) if max_len > 0 else 100
    
    return {
        'match_percentage': round(match_percentage, 1),
        'matches': matches,
        'total': max_len,
        'differences': differences
    }


def get_phoneme_difficulty(phoneme: str) -> Optional[Dict]:
    """Get information about common difficulty with a phoneme"""
    # Remove stress markers
    clean_phoneme = ''.join(c for c in phoneme if not c.isdigit())
    return COMMON_DIFFICULTIES.get(clean_phoneme)


def syllabify(phonemes: List[str]) -> List[List[str]]:
    """
    Split phonemes into syllables
    
    Args:
        phonemes: List of ARPABET phonemes
        
    Returns:
        List of syllables (each syllable is a list of phonemes)
    """
    vowels = {'AA', 'AE', 'AH', 'AO', 'AW', 'AY', 'EH', 'ER', 'EY', 
              'IH', 'IY', 'OW', 'OY', 'UH', 'UW'}
    
    syllables = []
    current_syllable = []
    
    for phoneme in phonemes:
        # Remove stress markers for comparison
        base_phoneme = ''.join(c for c in phoneme if not c.isdigit())
        
        current_syllable.append(phoneme)
        
        if base_phoneme in vowels:
            syllables.append(current_syllable)
            current_syllable = []
    
    # Add remaining consonants to last syllable
    if current_syllable and syllables:
        syllables[-1].extend(current_syllable)
    elif current_syllable:
        syllables.append(current_syllable)
    
    return syllables


def get_stress_pattern(phonemes: List[str]) -> str:
    """
    Extract stress pattern from phonemes
    
    Returns:
        String like "1-0-2" where 1=primary, 2=secondary, 0=unstressed
    """
    pattern = []
    
    for phoneme in phonemes:
        # Check for stress markers (0, 1, 2)
        if phoneme and phoneme[-1].isdigit():
            pattern.append(phoneme[-1])
    
    return '-'.join(pattern) if pattern else '1'


def calculate_pronunciation_similarity(phonemes1: List[str], 
                                        phonemes2: List[str]) -> float:
    """
    Calculate similarity between two phoneme sequences using edit distance
    
    Returns:
        Similarity score from 0 to 1
    """
    if not phonemes1 or not phonemes2:
        return 0.0
    
    # Remove stress markers for comparison
    clean1 = [''.join(c for c in p if not c.isdigit()) for p in phonemes1]
    clean2 = [''.join(c for c in p if not c.isdigit()) for p in phonemes2]
    
    # Levenshtein distance
    m, n = len(clean1), len(clean2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if clean1[i-1] == clean2[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
    
    distance = dp[m][n]
    max_len = max(m, n)
    
    return 1.0 - (distance / max_len) if max_len > 0 else 1.0


def get_british_pronunciation_tips(word: str) -> List[str]:
    """
    Get pronunciation tips for British English
    """
    tips = []
    word_lower = word.lower()
    
    # Common patterns
    if word_lower.endswith('r'):
        tips.append("In British English, final 'r' is often not pronounced (non-rhotic)")
    
    if 'a' in word_lower:
        tips.append("The 'a' sound may be longer in British English (like in 'bath')")
    
    if word_lower.startswith('h'):
        tips.append("Make sure to pronounce the initial 'h' sound")
    
    if 't' in word_lower:
        tips.append("'t' in British English can be a glottal stop between vowels")
    
    return tips
