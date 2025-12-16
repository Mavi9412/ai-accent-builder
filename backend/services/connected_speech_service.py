"""
Connected Speech & L1 Influence Detection Service
Detects linking, elision, assimilation patterns and native language transfer errors
"""
from typing import Dict, List, Tuple, Optional
import re


class ConnectedSpeechService:
    """
    Service for analyzing connected speech patterns and detecting L1 (native language) influence.
    Identifies linking, elision, assimilation, and common transfer errors from various L1 backgrounds.
    """
    
    def __init__(self):
        # Connected speech patterns in English
        self.linking_patterns = {
            'linking_r': {
                'description': 'Linking R between vowel sounds',
                'examples': ['far away → fa-r-away', 'car is → ca-r-is'],
                'pattern': r'(\w+r)\s+([aeiou]\w*)',
            },
            'intrusive_r': {
                'description': 'Intrusive R (non-standard but common)',
                'examples': ['idea of → idea-r-of', 'law and → law-r-and'],
                'pattern': r'(\w+[aə])\s+([aeiou]\w*)',
            },
            'consonant_vowel_linking': {
                'description': 'Final consonant links to next vowel',
                'examples': ['an apple → a-napple', 'get up → ge-tup'],
                'pattern': r'(\w+[bcdfghjklmnpqrstvwxyz])\s+([aeiou]\w*)',
            },
            'vowel_vowel_linking': {
                'description': 'Glide insertion between vowels',
                'examples': ['go away → go-w-away', 'see it → see-y-it'],
                'pattern': r'(\w+[oui])\s+([aeiou]\w*)',
            }
        }
        
        # Elision patterns (sound deletion)
        self.elision_patterns = {
            'final_t_deletion': {
                'description': 'Deletion of /t/ in consonant clusters',
                'examples': ['last night → las\' night', 'next day → nex\' day'],
                'words': ['last', 'next', 'most', 'just', 'first', 'must', 'fast', 'past'],
            },
            'final_d_deletion': {
                'description': 'Deletion of /d/ in consonant clusters',
                'examples': ['old man → ol\' man', 'and then → an\' then'],
                'words': ['old', 'and', 'hand', 'land', 'send', 'wind', 'mind', 'find'],
            },
            'schwa_deletion': {
                'description': 'Deletion of schwa in unstressed syllables',
                'examples': ['chocolate → choc\'lat', 'comfortable → comf\'table'],
                'words': ['chocolate', 'comfortable', 'vegetable', 'interesting', 'different'],
            },
            'h_dropping': {
                'description': 'H-dropping in unstressed function words',
                'examples': ['give him → give \'im', 'tell her → tell \'er'],
                'words': ['him', 'her', 'his', 'have', 'has', 'had'],
            }
        }
        
        # Assimilation patterns
        self.assimilation_patterns = {
            'place_assimilation': {
                'description': 'Consonant changes place of articulation',
                'examples': ['in Paris → im Paris', 'ten people → tem people'],
                'rules': ['/n/ → /m/ before /p,b,m/', '/n/ → /ŋ/ before /k,g/'],
            },
            'voice_assimilation': {
                'description': 'Consonant changes voicing',
                'examples': ['have to → hafta', 'used to → useta'],
                'rules': ['Voiced → voiceless before voiceless'],
            },
            'coalescence': {
                'description': 'Two sounds merge into one',
                'examples': ['got you → gotcha', 'would you → wouldja'],
                'rules': ['/t/ + /j/ → /tʃ/', '/d/ + /j/ → /dʒ/'],
            }
        }
        
        # L1 Influence patterns by native language
        self.l1_patterns = {
            'arabic': {
                'name': 'Arabic L1 Transfer',
                'common_errors': [
                    {'pattern': '/p/ → /b/', 'example': 'park → bark', 'reason': 'No /p/ in Arabic'},
                    {'pattern': '/v/ → /f/', 'example': 'very → fery', 'reason': 'No /v/ in Arabic'},
                    {'pattern': 'Vowel insertion', 'example': 'street → istreet', 'reason': 'No initial consonant clusters'},
                    {'pattern': 'Emphatic consonants', 'example': 'Dark L in all positions', 'reason': 'Arabic pharyngealization'},
                ],
                'vowel_issues': ['Short/long vowel confusion', 'Schwa difficulties'],
            },
            'chinese': {
                'name': 'Chinese L1 Transfer',
                'common_errors': [
                    {'pattern': '/r/ → /l/', 'example': 'right → light', 'reason': 'No /r/ in Mandarin'},
                    {'pattern': '/θ/ → /s/', 'example': 'think → sink', 'reason': 'No dental fricatives'},
                    {'pattern': '/ð/ → /z/', 'example': 'this → zis', 'reason': 'No dental fricatives'},
                    {'pattern': 'Final consonant deletion', 'example': 'hand → han', 'reason': 'Chinese syllables end in vowels/n/ng'},
                ],
                'vowel_issues': ['Tense/lax distinction', 'Diphthong difficulties'],
                'prosody_issues': ['Syllable-timed rhythm instead of stress-timed'],
            },
            'spanish': {
                'name': 'Spanish L1 Transfer',
                'common_errors': [
                    {'pattern': '/b/ and /v/ confusion', 'example': 'both sound like /b/', 'reason': 'Spanish /b/ and /v/ are allophones'},
                    {'pattern': '/s/ + consonant', 'example': 'school → eschool', 'reason': 'Spanish adds /e/ before /s/ clusters'},
                    {'pattern': '/h/ dropping', 'example': 'house → ouse', 'reason': 'Spanish H is silent'},
                    {'pattern': '/dʒ/ → /j/', 'example': 'job → yob', 'reason': 'No /dʒ/ in Spanish'},
                ],
                'vowel_issues': ['5-vowel system vs English 12+ vowels'],
            },
            'french': {
                'name': 'French L1 Transfer',
                'common_errors': [
                    {'pattern': '/h/ dropping', 'example': 'house → ouse', 'reason': 'French H is silent'},
                    {'pattern': '/θ/ → /s/ or /z/', 'example': 'think → sink', 'reason': 'No dental fricatives'},
                    {'pattern': '/ð/ → /z/', 'example': 'this → zis', 'reason': 'No dental fricatives'},
                    {'pattern': 'Stress on final syllable', 'example': 'development → develoPMENT', 'reason': 'French stress pattern'},
                ],
                'vowel_issues': ['Nasalized vowels transfer', 'Tense vowels in unstressed positions'],
            },
            'hindi_urdu': {
                'name': 'Hindi/Urdu L1 Transfer',
                'common_errors': [
                    {'pattern': '/v/ and /w/ confusion', 'example': 'very → wery', 'reason': 'Different /v-w/ distinction'},
                    {'pattern': 'Retroflex consonants', 'example': 't/d sound different', 'reason': 'Hindi has retroflex t/d'},
                    {'pattern': '/θ/ → /t/', 'example': 'think → tink', 'reason': 'No dental fricatives'},
                    {'pattern': '/ð/ → /d/', 'example': 'this → dis', 'reason': 'No dental fricatives'},
                ],
                'vowel_issues': ['Short vowel clarity'],
            },
            'japanese': {
                'name': 'Japanese L1 Transfer',
                'common_errors': [
                    {'pattern': '/r/ and /l/ confusion', 'example': 'right/light', 'reason': 'Single liquid in Japanese'},
                    {'pattern': 'Vowel insertion', 'example': 'street → sutorito', 'reason': 'CV syllable structure'},
                    {'pattern': '/θ/ → /s/', 'example': 'think → sink', 'reason': 'No dental fricatives'},
                    {'pattern': '/v/ → /b/', 'example': 'very → bery', 'reason': 'No /v/ in Japanese'},
                ],
                'vowel_issues': ['5-vowel system', 'No reduced vowels'],
                'prosody_issues': ['Mora-timed instead of stress-timed'],
            },
            'korean': {
                'name': 'Korean L1 Transfer',
                'common_errors': [
                    {'pattern': '/f/ → /p/', 'example': 'fish → pish', 'reason': 'No /f/ in Korean'},
                    {'pattern': '/v/ → /b/', 'example': 'very → bery', 'reason': 'No /v/ in Korean'},
                    {'pattern': '/z/ → /j/', 'example': 'zoo → joo', 'reason': 'No /z/ in Korean'},
                    {'pattern': '/θ/ → /s/', 'example': 'think → sink', 'reason': 'No dental fricatives'},
                ],
                'vowel_issues': ['Vowel length', 'Diphthongs'],
            },
            'russian': {
                'name': 'Russian L1 Transfer',
                'common_errors': [
                    {'pattern': '/θ/ → /t/ or /s/', 'example': 'think → tink/sink', 'reason': 'No dental fricatives'},
                    {'pattern': '/ð/ → /d/ or /z/', 'example': 'this → dis/zis', 'reason': 'No dental fricatives'},
                    {'pattern': '/w/ → /v/', 'example': 'water → vater', 'reason': 'No /w/ in Russian'},
                    {'pattern': '/ŋ/ → /ng/', 'example': 'singing → singing-g', 'reason': 'No final /ŋ/'},
                ],
                'vowel_issues': ['Vowel reduction patterns differ'],
            },
        }
    
    def analyze_connected_speech(self, text: str, word_timestamps: List[Dict] = None) -> Dict:
        """
        Analyze connected speech patterns in the text.
        
        Args:
            text: Transcribed text
            word_timestamps: Optional word timing information
            
        Returns:
            Dict with connected speech analysis
        """
        text_lower = text.lower()
        
        # Detect linking opportunities
        linking_opportunities = []
        for link_type, info in self.linking_patterns.items():
            matches = list(re.finditer(info['pattern'], text_lower))
            for match in matches:
                linking_opportunities.append({
                    'type': link_type,
                    'context': match.group(0),
                    'description': info['description'],
                    'position': match.span()
                })
        
        # Check for elision patterns (potential)
        elision_potential = []
        words = text_lower.split()
        for i, word in enumerate(words):
            for elision_type, info in self.elision_patterns.items():
                if word in info.get('words', []) and i < len(words) - 1:
                    elision_potential.append({
                        'type': elision_type,
                        'word': word,
                        'context': f"{word} {words[i+1]}",
                        'description': info['description']
                    })
        
        # Detect informal contractions (coalescence)
        contractions = []
        contraction_patterns = [
            (r'\bgonna\b', 'going to', 'Informal contraction'),
            (r'\bwanna\b', 'want to', 'Informal contraction'),
            (r'\bgotta\b', 'got to/have to', 'Informal contraction'),
            (r'\bkinda\b', 'kind of', 'Informal reduction'),
            (r'\bsorta\b', 'sort of', 'Informal reduction'),
            (r'\blemme\b', 'let me', 'Informal contraction'),
            (r'\bgimme\b', 'give me', 'Informal contraction'),
            (r"\bdunno\b", "don't know", 'Informal contraction'),
            (r'\bgotcha\b', 'got you', 'Coalescence'),
            (r'\bwouldja\b', 'would you', 'Coalescence'),
        ]
        
        for pattern, standard, desc in contraction_patterns:
            if re.search(pattern, text_lower):
                contractions.append({
                    'found': pattern.replace('\\b', ''),
                    'standard': standard,
                    'type': desc
                })
        
        # Calculate fluency indicators
        fluency_score = 100
        if word_timestamps and len(word_timestamps) > 1:
            # Check for appropriate pausing and smoother transitions
            gaps = []
            for i in range(len(word_timestamps) - 1):
                gap = word_timestamps[i+1].get('start', 0) - word_timestamps[i].get('end', 0)
                gaps.append(gap)
            
            avg_gap = sum(gaps) / len(gaps) if gaps else 0
            # Penalize very choppy speech
            if avg_gap > 0.5:
                fluency_score -= 20
            elif avg_gap > 0.3:
                fluency_score -= 10
        
        return {
            'linking_opportunities': linking_opportunities,
            'elision_potential': elision_potential,
            'contractions_found': contractions,
            'fluency_score': max(0, fluency_score),
            'connected_speech_score': self._calculate_connected_score(
                linking_opportunities, contractions, fluency_score
            ),
            'tips': self._generate_connected_speech_tips(
                linking_opportunities, elision_potential, contractions
            )
        }
    
    def _calculate_connected_score(self, linking: List, contractions: List, fluency: int) -> int:
        """Calculate overall connected speech score."""
        # Base score
        score = fluency
        
        # Natural contractions can be good or bad depending on context
        informal_count = len([c for c in contractions if 'Informal' in c.get('type', '')])
        if informal_count > 3:
            score -= 10  # Too informal
        
        return max(0, min(100, score))
    
    def _generate_connected_speech_tips(self, linking: List, elision: List, contractions: List) -> List[str]:
        """Generate tips for improving connected speech."""
        tips = []
        
        if linking:
            tips.append(
                "Practice linking words smoothly: connect final consonants to following vowels "
                "(e.g., 'an apple' → 'a napple')."
            )
        
        if any(e['type'] == 'h_dropping' for e in elision):
            tips.append(
                "In connected speech, function words like 'him', 'her', 'have' often reduce "
                "(give 'im, tell 'er). This is natural in fluent speech."
            )
        
        if contractions:
            tips.append(
                "Informal contractions are common in casual speech but may be inappropriate "
                "in formal contexts. Practice both formal and informal registers."
            )
        
        if not tips:
            tips.append("Your connected speech patterns are well-developed!")
        
        return tips
    
    def detect_l1_influence(self, text: str, transcribed_phonemes: List[str] = None,
                           suspected_l1: str = None) -> Dict:
        """
        Detect L1 (native language) influence patterns.
        
        Args:
            text: Transcribed text
            transcribed_phonemes: Detected phonemes (optional)
            suspected_l1: Suspected native language (optional)
            
        Returns:
            Dict with L1 influence analysis
        """
        text_lower = text.lower()
        detected_patterns = []
        l1_scores = {l1: 0 for l1 in self.l1_patterns.keys()}
        
        # Common error patterns to check in text
        error_checks = [
            # TH-fronting indicators
            (r'\b(f|s)ink\b', ['chinese', 'japanese', 'korean', 'french', 'russian'], '/θ/→/f/ or /s/', 'think'),
            (r'\b(d|z)is\b', ['chinese', 'hindi_urdu', 'french', 'russian'], '/ð/→/d/ or /z/', 'this'),
            # V/W confusion
            (r'\bwery\b', ['hindi_urdu'], '/v/→/w/', 'very'),
            (r'\bvater\b', ['russian'], '/w/→/v/', 'water'),
            # P/B confusion
            (r'\bbark\b.*\bcar\b', ['arabic'], '/p/→/b/', 'park'),
            # R/L confusion
            (r'\blight\b.*\bright\b|\bright\b.*\blight\b', ['chinese', 'japanese', 'korean'], '/r/↔/l/', 'right/light'),
            # F/P confusion
            (r'\bpish\b', ['korean'], '/f/→/p/', 'fish'),
            # Vowel insertion (epenthesis)
            (r'\be?school\b', ['spanish'], 'Vowel insertion before /s/', 'school'),
        ]
        
        for pattern, l1s, error_type, target_word in error_checks:
            if re.search(pattern, text_lower):
                for l1 in l1s:
                    detected_patterns.append({
                        'l1': l1,
                        'error_type': error_type,
                        'target_word': target_word,
                        'description': f"Possible {self.l1_patterns[l1]['name']} pattern"
                    })
                    l1_scores[l1] += 25
        
        # Determine most likely L1 if not specified
        if suspected_l1 and suspected_l1.lower() in self.l1_patterns:
            likely_l1 = suspected_l1.lower()
        elif any(l1_scores.values()):
            likely_l1 = max(l1_scores, key=l1_scores.get)
        else:
            likely_l1 = None
        
        # Get specific patterns for detected/suspected L1
        l1_specific = None
        if likely_l1:
            l1_specific = {
                'name': self.l1_patterns[likely_l1]['name'],
                'common_errors': self.l1_patterns[likely_l1]['common_errors'],
                'vowel_issues': self.l1_patterns[likely_l1].get('vowel_issues', []),
                'prosody_issues': self.l1_patterns[likely_l1].get('prosody_issues', []),
            }
        
        return {
            'detected_patterns': detected_patterns,
            'l1_scores': {k: v for k, v in l1_scores.items() if v > 0},
            'likely_l1': likely_l1,
            'l1_specific_info': l1_specific,
            'recommendations': self._generate_l1_recommendations(likely_l1, detected_patterns),
            'influence_score': self._calculate_l1_influence_score(detected_patterns)
        }
    
    def _calculate_l1_influence_score(self, patterns: List[Dict]) -> int:
        """Calculate how much L1 influence is affecting pronunciation (0-100, lower is more native-like)."""
        if not patterns:
            return 0  # No L1 influence detected
        return min(100, len(patterns) * 15)
    
    def _generate_l1_recommendations(self, l1: str, patterns: List[Dict]) -> List[str]:
        """Generate recommendations based on L1 influence."""
        recommendations = []
        
        if not l1 and not patterns:
            recommendations.append("No significant L1 transfer patterns detected. Keep practicing!")
            return recommendations
        
        if l1:
            l1_info = self.l1_patterns.get(l1, {})
            
            # Add specific recommendations based on common errors
            for error in l1_info.get('common_errors', [])[:3]:
                recommendations.append(
                    f"Practice: {error['pattern']} - {error['reason']}. "
                    f"Example: {error['example']}"
                )
        
        # Add pattern-specific recommendations
        error_types = set(p.get('error_type', '') for p in patterns)
        
        if '/θ/' in str(error_types) or '/ð/' in str(error_types):
            recommendations.append(
                "For 'th' sounds: Place your tongue between your teeth. "
                "Practice: 'think', 'this', 'that', 'three'."
            )
        
        if '/r/' in str(error_types) or '/l/' in str(error_types):
            recommendations.append(
                "For /r/ and /l/: /r/ - tongue curled back, doesn't touch roof. "
                "/l/ - tongue touches behind top teeth. Practice: 'right', 'light', 'really'."
            )
        
        return recommendations[:5]  # Limit to 5 recommendations


# Singleton instance
connected_speech_service = ConnectedSpeechService()
