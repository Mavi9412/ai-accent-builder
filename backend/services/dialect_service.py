"""
Dialect Detection Service
Detects regional pronunciation markers, vocabulary patterns, and dialectal features
Compares against Received Pronunciation (RP) British English standard
"""
from typing import Dict, List, Optional
import re


class DialectService:
    """
    Service for detecting dialectal variations from Received Pronunciation (RP).
    Identifies regional markers, vocabulary differences, and pronunciation patterns.
    """
    
    def __init__(self):
        # Regional pronunciation markers for British dialects
        self.regional_markers = {
            'scottish': {
                'patterns': [
                    # Scottish vowel patterns
                    (r'\bhoose\b', 'house', 'Scottish /u:/ instead of /aʊ/'),
                    (r'\bdoon\b', 'down', 'Scottish /u:/ instead of /aʊ/'),
                    (r'\baye\b', 'yes', 'Scottish vocabulary'),
                    (r'\bwee\b', 'small', 'Scottish vocabulary'),
                    (r'\bken\b', 'know', 'Scottish vocabulary'),
                    (r'\bnae\b', 'no/not', 'Scottish negation'),
                    (r"\bcannae\b", "cannot", 'Scottish negation'),
                ],
                'phoneme_patterns': {
                    '/r/': 'Rhotic R (Scottish keeps R after vowels)',
                    '/x/': 'Velar fricative in "loch"',
                }
            },
            'northern_english': {
                'patterns': [
                    (r'\bnowt\b', 'nothing', 'Northern vocabulary'),
                    (r'\bsummat\b', 'something', 'Northern vocabulary'),
                    (r'\blass\b', 'girl', 'Northern vocabulary'),
                    (r'\blad\b', 'boy', 'Northern vocabulary'),
                    (r'\bmardy\b', 'moody', 'Northern vocabulary'),
                ],
                'phoneme_patterns': {
                    '/ʊ/': 'Short U in "bus" (Northern /bʊs/ vs RP /bʌs/)',
                    '/a/': 'Flat A in "bath" (Northern /baθ/ vs RP /bɑːθ/)',
                }
            },
            'cockney': {
                'patterns': [
                    (r'\binnit\b', "isn't it", 'Cockney tag question'),
                    (r'\bguv\b', 'governor/sir', 'Cockney address'),
                    (r'\bbloke\b', 'man', 'Cockney vocabulary'),
                ],
                'phoneme_patterns': {
                    '/ʔ/': 'Glottal stop (replacing /t/)',
                    '/f/': 'TH-fronting (/f/ for /θ/)',
                    '/v/': 'TH-fronting (/v/ for /ð/)',
                }
            },
            'estuary': {
                'patterns': [],
                'phoneme_patterns': {
                    '/ʔ/': 'Glottal stop in word-final position',
                    '/w/': 'L-vocalization (milk → miwk)',
                }
            },
            'irish': {
                'patterns': [
                    (r'\bcraic\b', 'fun/news', 'Irish vocabulary'),
                    (r'\bgrand\b', 'fine/okay', 'Irish usage'),
                    (r'\bwee\b', 'small', 'Irish vocabulary'),
                ],
                'phoneme_patterns': {
                    '/r/': 'Rhotic R',
                    '/t/': 'Dental /t/ and /d/',
                }
            },
            'welsh': {
                'patterns': [
                    (r'\bboyo\b', 'friend', 'Welsh vocabulary'),
                    (r'\blush\b', 'nice', 'Welsh vocabulary'),
                ],
                'phoneme_patterns': {
                    '/ɬ/': 'Welsh voiceless lateral fricative',
                }
            }
        }
        
        # RP standard features
        self.rp_features = {
            'non_rhotic': 'No R after vowels (car → /kɑː/)',
            'trap_bath_split': 'Long /ɑː/ in "bath", "grass", "dance"',
            'long_vowels': 'Distinct long/short vowel pairs',
            'clear_t': 'Clear /t/ pronunciation, minimal glottalization',
            'linking_r': 'Linking R between vowels',
        }
        
        # Words that differ between dialects
        self.vocabulary_markers = {
            # RP vs Regional vocabulary
            'trousers': {'scottish': 'breeks', 'northern': 'kecks'},
            'alleyway': {'scottish': 'close', 'northern': 'ginnel', 'cockney': 'alley'},
            'bread_roll': {'scottish': 'bap', 'northern': 'barm', 'west_midlands': 'cob'},
            'pleased': {'scottish': 'chuffed', 'northern': 'chuffed', 'cockney': 'chuffed'},
        }
        
        # Pronunciation test words for dialect detection
        self.test_words = {
            'bath': {'rp': '/bɑːθ/', 'northern': '/baθ/'},
            'bus': {'rp': '/bʌs/', 'northern': '/bʊs/'},
            'butter': {'rp': '/ˈbʌtə/', 'cockney': '/ˈbʌʔə/'},
            'water': {'rp': '/ˈwɔːtə/', 'cockney': '/ˈwɔːʔə/', 'estuary': '/ˈwɔːʔə/'},
            'nothing': {'rp': '/ˈnʌθɪŋ/', 'cockney': '/ˈnʌfɪŋ/'},
            'think': {'rp': '/θɪŋk/', 'cockney': '/fɪŋk/'},
            'brother': {'rp': '/ˈbrʌðə/', 'cockney': '/ˈbrʌvə/'},
            'milk': {'rp': '/mɪlk/', 'estuary': '/mɪʊk/'},
        }
    
    def detect_dialect(self, text: str, phonemes: List[str] = None) -> Dict:
        """
        Detect dialectal features in text and phonemes.
        
        Args:
            text: Transcribed text to analyze
            phonemes: Optional list of detected phonemes
            
        Returns:
            Dict with dialect analysis results
        """
        text_lower = text.lower()
        detected_features = []
        dialect_scores = {dialect: 0.0 for dialect in self.regional_markers.keys()}
        dialect_scores['rp'] = 100.0  # Start with assumption of RP
        
        # Check vocabulary patterns
        for dialect, markers in self.regional_markers.items():
            for pattern, standard, description in markers.get('patterns', []):
                if re.search(pattern, text_lower):
                    detected_features.append({
                        'type': 'vocabulary',
                        'dialect': dialect,
                        'found': pattern,
                        'standard_rp': standard,
                        'description': description
                    })
                    dialect_scores[dialect] += 20
                    dialect_scores['rp'] -= 10
        
        # Analyze for common non-RP phonetic patterns (based on text spelling)
        phonetic_indicators = [
            # Glottal stops (common in Cockney/Estuary)
            (r"wa'er|bu'er|be'er|li'le", 'glottal_stop', ['cockney', 'estuary'], 
             'Glottal stop replacing /t/'),
            # TH-fronting
            (r'\bfink\b|\bbruvver\b|\bnuffin\b', 'th_fronting', ['cockney'], 
             'TH-fronting: /f/ for /θ/, /v/ for /ð/'),
            # H-dropping
            (r"\b'ouse\b|\b'appy\b|\b'ello\b", 'h_dropping', ['cockney', 'northern_english'],
             'H-dropping: silent initial H'),
            # Double negatives
            (r"don't know nothing|ain't got no", 'double_negative', ['cockney', 'northern_english'],
             'Non-standard double negatives'),
        ]
        
        for pattern, feature_type, dialects, description in phonetic_indicators:
            if re.search(pattern, text_lower):
                for dialect in dialects:
                    detected_features.append({
                        'type': 'phonetic',
                        'dialect': dialect,
                        'feature': feature_type,
                        'description': description
                    })
                    dialect_scores[dialect] += 15
                    dialect_scores['rp'] -= 10
        
        # Normalize scores
        max_score = max(dialect_scores.values())
        if max_score > 0:
            dialect_scores = {k: round(v / max_score * 100, 1) for k, v in dialect_scores.items()}
        
        # Determine primary dialect
        primary_dialect = max(dialect_scores, key=dialect_scores.get)
        
        # Calculate RP compliance
        rp_compliance = dialect_scores.get('rp', 100)
        
        return {
            'primary_dialect': primary_dialect,
            'rp_compliance': round(rp_compliance, 1),
            'dialect_scores': dialect_scores,
            'detected_features': detected_features,
            'is_rp_standard': primary_dialect == 'rp' and rp_compliance >= 80,
            'recommendations': self._generate_recommendations(detected_features, primary_dialect)
        }
    
    def _generate_recommendations(self, features: List[Dict], primary_dialect: str) -> List[str]:
        """Generate recommendations for achieving RP pronunciation."""
        recommendations = []
        
        if not features:
            recommendations.append("Your speech closely matches Received Pronunciation (RP).")
            return recommendations
        
        feature_types = set(f['type'] for f in features)
        
        if 'vocabulary' in feature_types:
            recommendations.append(
                "Consider using standard British vocabulary in formal contexts."
            )
        
        if any(f.get('feature') == 'glottal_stop' for f in features):
            recommendations.append(
                "Practice pronouncing /t/ clearly in words like 'water', 'butter', 'better'."
            )
        
        if any(f.get('feature') == 'th_fronting' for f in features):
            recommendations.append(
                "Practice the 'th' sounds: /θ/ in 'think' and /ð/ in 'this'. "
                "Place tongue between teeth."
            )
        
        if any(f.get('feature') == 'h_dropping' for f in features):
            recommendations.append(
                "Ensure initial H is pronounced in words like 'house', 'happy', 'hello'."
            )
        
        if primary_dialect != 'rp':
            recommendations.append(
                f"Your speech shows {primary_dialect.replace('_', ' ').title()} influences. "
                "For RP, focus on the specific features noted above."
            )
        
        return recommendations
    
    def get_rp_pronunciation_guide(self, word: str) -> Dict:
        """Get RP pronunciation guide for a specific word."""
        word_lower = word.lower()
        
        if word_lower in self.test_words:
            return {
                'word': word,
                'rp_pronunciation': self.test_words[word_lower].get('rp', 'Unknown'),
                'regional_variants': {
                    k: v for k, v in self.test_words[word_lower].items() if k != 'rp'
                }
            }
        
        return {
            'word': word,
            'rp_pronunciation': 'Standard RP',
            'regional_variants': {}
        }
    
    def analyze_formality(self, text: str) -> Dict:
        """Analyze formality level of speech."""
        text_lower = text.lower()
        
        informal_markers = [
            (r'\bgonna\b', 'going to'),
            (r'\bwanna\b', 'want to'),
            (r'\bgotta\b', 'got to/have to'),
            (r'\bkinda\b', 'kind of'),
            (r'\bsorta\b', 'sort of'),
            (r'\bdunno\b', "don't know"),
            (r'\byeah\b', 'yes'),
            (r'\bnope\b', 'no'),
            (r'\bcool\b', 'good/acceptable'),
            (r'\bawesome\b', 'excellent'),
        ]
        
        found_informal = []
        for pattern, formal in informal_markers:
            if re.search(pattern, text_lower):
                found_informal.append({
                    'informal': pattern.strip('\\b'),
                    'formal_alternative': formal
                })
        
        formality_score = max(0, 100 - len(found_informal) * 10)
        
        return {
            'formality_score': formality_score,
            'formality_level': 'formal' if formality_score >= 80 else 'neutral' if formality_score >= 50 else 'informal',
            'informal_markers': found_informal,
            'recommendations': [
                f"Replace '{m['informal']}' with '{m['formal_alternative']}' in formal contexts"
                for m in found_informal
            ] if found_informal else ["Speech formality is appropriate for formal contexts."]
        }


# Singleton instance
dialect_service = DialectService()
