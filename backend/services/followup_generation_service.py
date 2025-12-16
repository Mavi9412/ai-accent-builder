"""
Follow-Up Question Generation Service
Context-aware practice question generation based on pronunciation errors

Hybrid Architecture:
1. Gemini API (online, first priority) - Best quality responses
2. FLAN-T5-base (offline fallback) - Works on CPU
3. Rule-based detection: LanguageTool, spaCy, CMU Dict, Vosk → detect errors

Generates:
- Phoneme-specific drills
- Stress pattern corrections
- Intonation practice sentences
- Grammar correction exercises
- Minimal pair practices
"""

import os
import random
import re
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path

# Gemini API Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyCVirLvxF53dqT0Kvh_toLEzO29pgmdFUw")
GEMINI_AVAILABLE = False

try:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    GEMINI_AVAILABLE = True
    print(f"[FollowUpGeneration] Gemini API configured successfully")
except ImportError:
    print("[FollowUpGeneration] google-generativeai not installed. Run: pip install google-generativeai")
except Exception as e:
    print(f"[FollowUpGeneration] Gemini API configuration failed: {e}")

# Phoneme dictionary for pronunciation practice
try:
    import nltk
    from nltk.corpus import cmudict
    try:
        CMU_DICT = cmudict.dict()
    except LookupError:
        nltk.download('cmudict', quiet=True)
        CMU_DICT = cmudict.dict()
    CMU_AVAILABLE = True
except ImportError:
    CMU_DICT = {}
    CMU_AVAILABLE = False
    print("[FollowUpGeneration] NLTK/CMUDict not available")

# T5 for natural language generation (fallback)
T5_AVAILABLE = False
T5_MODEL = None
T5_TOKENIZER = None

try:
    from transformers import AutoTokenizer, T5ForConditionalGeneration
    try:
        from optimum.onnxruntime import ORModelForSeq2SeqLM
        ONNX_AVAILABLE = True
    except ImportError:
        ONNX_AVAILABLE = False
        print("[FollowUpGeneration] optimum.onnxruntime not available - falling back to PyTorch")
        
    T5_AVAILABLE = True
except ImportError:
    print("[FollowUpGeneration] transformers not available - T5 disabled")
    ONNX_AVAILABLE = False


@dataclass
class PronunciationError:
    """Represents a detected pronunciation error."""
    word: str
    word_index: int
    error_type: str  # 'phoneme', 'stress', 'intonation', 'rhythm', 'grammar'
    expected: str
    actual: str
    phoneme: Optional[str] = None
    score: float = 0.0
    severity: str = "medium"  # 'low', 'medium', 'high'


class FollowUpGenerationService:
    """
    Service for generating context-aware follow-up practice questions.
    Uses hybrid approach: Gemini API (primary) → T5 (fallback) → Rule-based.
    """
    
    def __init__(self, use_t5: bool = True, use_llm: bool = False, 
                 t5_model_name: str = "google/flan-t5-base",
                 use_gemini: bool = True):
        """
        Initialize follow-up generation service.
        
        Args:
            use_t5: Whether to use T5 for natural question phrasing
            use_llm: Whether to use LLaMA/TinyLLaMA (requires more resources)
            t5_model_name: T5 model variant to use
            use_gemini: Whether to use Gemini API (online, priority)
        """
        self.use_gemini = use_gemini and GEMINI_AVAILABLE
        self.use_t5 = use_t5 and T5_AVAILABLE
        self.use_llm = use_llm
        self.t5_model_name = t5_model_name
        self.t5_model = None
        self.t5_tokenizer = None
        self.gemini_model = None
        
        # Initialize Gemini if available
        if self.use_gemini:
            try:
                self.gemini_model = genai.GenerativeModel('gemini-2.5-flash')
                print("[FollowUpGeneration] Gemini model initialized (gemini-2.5-flash)")
            except Exception as e:
                print(f"[FollowUpGeneration] Failed to initialize Gemini model: {e}")
                self.use_gemini = False
        
        # Load templates
        self.templates = self._load_templates()
        self.minimal_pairs = self._load_minimal_pairs()
        self.phoneme_drills = self._load_phoneme_drills()
        
        print(f"[FollowUpGeneration] Initialized. Gemini={self.use_gemini}, T5={self.use_t5}, CMU={CMU_AVAILABLE}")
    
    def _init_t5(self):
        """Lazily initialize T5 model with ONNX/CPU optimization."""
        global T5_MODEL, T5_TOKENIZER
        
        if self.t5_model is not None:
            return
        
        if T5_MODEL is not None:
            self.t5_model = T5_MODEL
            self.t5_tokenizer = T5_TOKENIZER
            return
        
        if not T5_AVAILABLE:
            return
        
        try:
            print(f"[FollowUpGeneration] Loading T5 model: {self.t5_model_name}")
            # Use google/flan-t5-small if default t5-small is set, as it's better for instructions
            model_name = "google/flan-t5-small" if self.t5_model_name == "t5-small" else self.t5_model_name
            
            self.t5_tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            # Try ONNX first (faster on CPU)
            if ONNX_AVAILABLE:
                try:
                    print(f"[FollowUpGeneration] Attempting ONNX load for {model_name}...")
                    self.t5_model = ORModelForSeq2SeqLM.from_pretrained(model_name, export=True)
                    print("[FollowUpGeneration] ONNX model loaded successfully!")
                except Exception as e:
                    print(f"[FollowUpGeneration] ONNX load failed ({e}), falling back to PyTorch")
                    self.t5_model = None

            # Fallback to PyTorch
            if self.t5_model is None:
                self.t5_model = T5ForConditionalGeneration.from_pretrained(model_name)
                # Optimize for CPU if possible
                try:
                    import torch
                    if hasattr(torch, 'compile'):
                        print("[FollowUpGeneration] Compiling PyTorch model...")
                        self.t5_model = torch.compile(self.t5_model)
                except:
                    pass
            
            # Cache globally
            T5_MODEL = self.t5_model
            T5_TOKENIZER = self.t5_tokenizer
            
            print("[FollowUpGeneration] T5 model ready")
        except Exception as e:
            print(f"[FollowUpGeneration] T5 loading failed: {e}")
            self.use_t5 = False
    
    def generate_followup(self, analysis_result: Dict) -> Dict:
        """
        Generate follow-up practice question based on analysis results.
        Uses LLM for context-aware generation if available.
        
        Args:
            analysis_result: Dict containing word_analyses, scores, etc.
            
        Returns:
            Dict with:
                - question: The follow-up question/instruction
                - target_word: Word to practice
                - target_phoneme: Specific phoneme if applicable
                - practice_words: Additional words for drill
                - error_type: Type of error being addressed
                - difficulty: Estimated difficulty level
        """
        # SPEED OPTIMIZATION: Skip T5 LLM for faster response
        # Use template-based generation for speed (T5 loading takes 10+ seconds first time)
        # LLM still available via: _generate_llm_context_followup() if explicitly needed
        
        # Fallback to rule-based generation (FAST)
        
        # Fallback to rule-based generation
        # Extract errors from analysis
        errors = self._extract_errors(analysis_result)
        
        if not errors:
            return self._generate_success_followup(analysis_result)
        
        # Sort by severity and select most important error
        errors.sort(key=lambda e: (
            {'high': 0, 'medium': 1, 'low': 2}[e.severity],
            -e.score  # Lower score = more severe
        ))
        
        primary_error = errors[0]
        
        # Generate question based on error type
        if primary_error.error_type == 'phoneme':
            return self._generate_phoneme_followup(primary_error, analysis_result)
        elif primary_error.error_type == 'stress':
            return self._generate_stress_followup(primary_error, analysis_result)
        elif primary_error.error_type == 'intonation':
            return self._generate_intonation_followup(primary_error, analysis_result)
        elif primary_error.error_type == 'rhythm':
            return self._generate_rhythm_followup(primary_error, analysis_result)
        elif primary_error.error_type == 'grammar':
            return self._generate_grammar_followup(primary_error, analysis_result)
        else:
            return self._generate_general_followup(primary_error, analysis_result)
    
    def _generate_llm_context_followup(self, analysis_result: Dict) -> Optional[Dict]:
        """
        Generate context-aware follow-up using LLM.
        Priority: Gemini API (online) → T5 (offline fallback)
        Uses the MASTER PROMPT for British English tutor responses.
        """
        # Try Gemini first (online, best quality)
        if self.use_gemini and self.gemini_model:
            result = self._generate_with_gemini(analysis_result)
            if result:
                return result
            print("[FollowUp-LLM] Gemini failed, falling back to T5...")
        
        # Fallback to T5 (offline)
        if not self.use_t5:
            return None
        
        self._init_t5()
        
        if self.t5_model is None:
            return None
        
        try:
            # Build context from analysis
            transcribed = analysis_result.get('transcribed_text', '')
            overall_score = analysis_result.get('overall_score', 0)
            word_analyses = analysis_result.get('word_analyses', [])
            pronunciation_score = analysis_result.get('scores', {}).get('pronunciation', overall_score)
            
            # Find problem words
            problem_words = [
                w for w in word_analyses 
                if not w.get('is_correct', True) or w.get('score', 100) < 80
            ]
            
            # Build error summary with underlined words
            if problem_words:
                error_words = [f"__{w.get('word', '')}__" for w in problem_words[:3]]
                error_summary = f"Issues with: {', '.join(error_words)}"
                has_mistakes = True
            else:
                error_summary = "No significant errors detected"
                has_mistakes = False
            
            # Detect topic from sentence
            topic = self._detect_topic(transcribed)
            
            # ==========================================
            # MASTER PROMPT (SAFE FOR T5-small & Gemini)
            # ==========================================
            master_prompt = f'''You are a friendly British English speaking tutor.

STRICT RULES (DO NOT BREAK):

1. If there is ANY grammar mistake:
   - Underline ONLY the incorrect words using __double underscores__
   - Explain the mistake in ONE simple sentence
   - Give the corrected British English sentence

2. If NO grammar mistakes exist:
   - Write "Well done! No corrections needed."
   - Still provide vocabulary alternatives

3. Vocabulary improvement (ALWAYS PROVIDE THESE):
   - Give ONE Formal alternative of the sentence
   - Give ONE Informal/casual alternative
   - Give ONE British expression or slang version
   - Label each clearly

4. Accent Tip (ALWAYS PROVIDE):
   - Give ONE short British pronunciation tip
   - Focus on any word from the sentence
   - No phonetic symbols unless necessary

5. Conversation flow (VERY IMPORTANT):
   - Ask ONLY ONE follow-up question
   - Question MUST be related to what the user talked about
   - Question must sound natural, like real conversation
   - DO NOT ask about scores or percentages

6. Tone:
   - Friendly
   - Supportive
   - Natural British English
   - Short sentences

INPUT:
Sentence: "{transcribed}"
Detected Errors: {error_summary}
Topic: {topic}
Pronunciation Score: {pronunciation_score}

OUTPUT FORMAT (MANDATORY - ALWAYS fill in ALL sections):

Mistake Analysis:
- (your analysis here, or "No mistakes found - well done!")

Correction:
- (corrected sentence, or "No correction needed")

Vocabulary Upgrade:
- Formal: (formal version of the sentence)
- Informal: (casual version)
- British: (British slang/expression version)

Accent Tip:
- (ONE British pronunciation tip for any word in the sentence)

Next Question:
- (ONE conversational follow-up question)
'''
            
            # Generate response using T5
            inputs = self.t5_tokenizer.encode(
                master_prompt, 
                return_tensors="pt", 
                max_length=512, 
                truncation=True
            )
            
            outputs = self.t5_model.generate(
                inputs,
                max_new_tokens=200,
                num_beams=2,
                do_sample=True,
                temperature=0.7,
                top_p=0.9
            )
            
            raw_output = self.t5_tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
            print(f"[FollowUp-LLM] Raw output: {raw_output}")
            
            # Parse the structured output
            result = self._parse_master_prompt_output(raw_output, has_mistakes, topic, transcribed)
            
            # Add metadata
            result['generated_by'] = f"llm_{self.t5_model_name}"
            result['topic'] = topic
            result['error_type'] = "phoneme" if has_mistakes else "success"
            result['difficulty'] = "adaptive"
            
            # Add target word info for practice
            if problem_words:
                result['target_word'] = problem_words[0].get('word', '')
                target_phoneme = self._find_problem_phoneme(
                    problem_words[0].get('expected_phonemes', ''),
                    problem_words[0].get('actual_phonemes', '')
                )
                result['target_phoneme'] = target_phoneme
                result['practice_words'] = self._get_minimal_pairs_for_phoneme(target_phoneme) if target_phoneme else []
            else:
                result['target_word'] = None
                result['target_phoneme'] = None
                result['practice_words'] = []
            
            return result
            
        except Exception as e:
            print(f"[FollowUp-LLM] Error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_master_prompt_output(self, raw_output: str, has_mistakes: bool, topic: str, transcribed: str) -> Dict:
        """
        Parse the structured output from the MASTER PROMPT.
        Handles Gemini's format: '- Label: content' and section headers.
        """
        result = {
            'question': '',
            'followup': '',
            'mistakes_underlined': '',
            'correction': '',
            'accent_tip': '',
            'vocabulary_tip': '',
            'vocab_formal': '',
            'vocab_informal': '',
            'vocab_british': '',
            'next_practice_sentence': '',
            'practice_sentence': ''
        }
        
        lines = raw_output.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove leading dash if present
            if line.startswith('-'):
                line = line[1:].strip()
            
            line_lower = line.lower()
            
            # Check for section headers
            if 'mistake analysis' in line_lower:
                current_section = 'mistake'
                continue
            elif line_lower.startswith('correction') and ':' not in line_lower[11:]:
                current_section = 'correction'
                continue
            elif 'vocabulary upgrade' in line_lower:
                current_section = 'vocab'
                continue
            elif 'accent tip' in line_lower and ':' not in line_lower[10:]:
                current_section = 'accent'
                continue
            elif 'next question' in line_lower and ':' not in line_lower[13:]:
                current_section = 'question'
                continue
            
            # Parse inline content (e.g., "Formal: I trust you...")
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if value:  # Only set if there's actual content
                    if 'formal' in key and 'informal' not in key:
                        result['vocab_formal'] = value
                    elif 'informal' in key:
                        result['vocab_informal'] = value
                    elif 'british' in key:
                        result['vocab_british'] = value
                    elif 'correction' in key:
                        result['correction'] = value
                    elif 'accent' in key or 'tip' in key:
                        result['accent_tip'] = value
                    elif 'question' in key:
                        result['question'] = value
                        result['followup'] = value
                    elif 'mistake' in key or 'analysis' in key:
                        result['mistakes_underlined'] = value
            else:
                # Plain content for current section
                if current_section == 'mistake' and not result['mistakes_underlined']:
                    result['mistakes_underlined'] = line
                elif current_section == 'correction' and not result['correction']:
                    result['correction'] = line
                elif current_section == 'accent' and not result['accent_tip']:
                    result['accent_tip'] = line
                elif current_section == 'question' and not result['question']:
                    result['question'] = line
                    result['followup'] = line
        
        # Build combined vocabulary tip
        vocab_parts = []
        if result['vocab_formal']:
            vocab_parts.append(f"Formal: {result['vocab_formal']}")
        if result['vocab_informal']:
            vocab_parts.append(f"Informal: {result['vocab_informal']}")
        if result['vocab_british']:
            vocab_parts.append(f"British: {result['vocab_british']}")
        result['vocabulary_tip'] = ' | '.join(vocab_parts)
        
        # Fallback: If no question was parsed, generate a simple one
        if not result['question']:
            if has_mistakes:
                result['question'] = f"Would you like to try saying that again?"
            else:
                result['question'] = f"That was brilliant! Would you like to continue talking about {topic}?"
            result['followup'] = result['question']
        
        # Fallback for practice sentence
        if not result['next_practice_sentence']:
            result['next_practice_sentence'] = transcribed
            result['practice_sentence'] = transcribed
        
        return result
    
    def _generate_with_gemini(self, analysis_result: Dict) -> Optional[Dict]:
        """
        Generate follow-up using Gemini API (online, fast, best quality).
        Uses the same MASTER PROMPT format for consistency.
        """
        try:
            # Build context from analysis
            transcribed = analysis_result.get('transcribed_text', '')
            overall_score = analysis_result.get('overall_score', 0)
            word_analyses = analysis_result.get('word_analyses', [])
            pronunciation_score = analysis_result.get('scores', {}).get('pronunciation', overall_score)
            
            # Find problem words
            problem_words = [
                w for w in word_analyses 
                if not w.get('is_correct', True) or w.get('score', 100) < 80
            ]
            
            # Build error summary with underlined words
            if problem_words:
                error_words = [f"__{w.get('word', '')}__" for w in problem_words[:3]]
                error_summary = f"Issues with: {', '.join(error_words)}"
                has_mistakes = True
            else:
                error_summary = "No significant errors detected"
                has_mistakes = False
            
            # Detect topic
            topic = self._detect_topic(transcribed)
            
            # Build MASTER PROMPT for Gemini
            master_prompt = f'''You are a friendly British English speaking tutor.

STRICT RULES (DO NOT BREAK):

1. If there is ANY grammar mistake:
   - Underline ONLY the incorrect words using __double underscores__
   - Explain the mistake in ONE simple sentence
   - Give the corrected British English sentence

2. If NO grammar mistakes exist:
   - Write "Well done! No corrections needed."
   - Still provide vocabulary alternatives

3. Vocabulary improvement (ALWAYS PROVIDE THESE):
   - Give ONE Formal alternative of the sentence
   - Give ONE Informal/casual alternative
   - Give ONE British expression or slang version
   - Label each clearly

4. Accent Tip (ALWAYS PROVIDE):
   - Give ONE short British pronunciation tip
   - Focus on any word from the sentence
   - No phonetic symbols unless necessary

5. Conversation flow (VERY IMPORTANT):
   - Ask ONLY ONE follow-up question
   - Question MUST be related to what the user talked about
   - Question must sound natural, like real conversation
   - DO NOT ask about scores or percentages

6. Tone:
   - Friendly
   - Supportive
   - Natural British English
   - Short sentences

INPUT:
Sentence: "{transcribed}"
Detected Errors: {error_summary}
Topic: {topic}
Pronunciation Score: {pronunciation_score}

OUTPUT FORMAT (MANDATORY - ALWAYS fill in ALL sections):

Mistake Analysis:
- (your analysis here, or "No mistakes found - well done!")

Correction:
- (corrected sentence, or "No correction needed")

Vocabulary Upgrade:
- Formal: (formal version of the sentence)
- Informal: (casual version)
- British: (British slang/expression version)

Accent Tip:
- (ONE British pronunciation tip for any word in the sentence)

Next Question:
- (ONE conversational follow-up question)
'''
            
            # Call Gemini API
            response = self.gemini_model.generate_content(
                master_prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=500,  # Increased for full response
                )
            )
            
            raw_output = response.text.strip()
            print(f"[FollowUp-Gemini] Response received ({len(raw_output)} chars)")
            print(f"[FollowUp-Gemini] RAW OUTPUT:\n{raw_output[:500]}...")  # Debug: show raw output
            
            # Parse the structured output (reuse the same parser)
            result = self._parse_master_prompt_output(raw_output, has_mistakes, topic, transcribed)
            
            # Debug: Show what was parsed
            print(f"[FollowUp-Gemini] PARSED: correction={result.get('correction', 'NONE')[:30] if result.get('correction') else 'NONE'}...")
            print(f"[FollowUp-Gemini] PARSED: vocab_formal={result.get('vocab_formal', 'NONE')[:30] if result.get('vocab_formal') else 'NONE'}...")
            print(f"[FollowUp-Gemini] PARSED: accent_tip={result.get('accent_tip', 'NONE')[:30] if result.get('accent_tip') else 'NONE'}...")
            print(f"[FollowUp-Gemini] PARSED: question={result.get('question', 'NONE')[:30] if result.get('question') else 'NONE'}...")
            
            # Add metadata
            result['generated_by'] = "gemini-2.5-flash"
            result['topic'] = topic
            result['error_type'] = "phoneme" if has_mistakes else "success"
            result['difficulty'] = "adaptive"
            
            # Add target word info for practice
            if problem_words:
                result['target_word'] = problem_words[0].get('word', '')
                target_phoneme = self._find_problem_phoneme(
                    problem_words[0].get('expected_phonemes', ''),
                    problem_words[0].get('actual_phonemes', '')
                )
                result['target_phoneme'] = target_phoneme
                result['practice_words'] = self._get_minimal_pairs_for_phoneme(target_phoneme) if target_phoneme else []
            else:
                result['target_word'] = None
                result['target_phoneme'] = None
                result['practice_words'] = []
            
            return result
            
        except Exception as e:
            print(f"[FollowUp-Gemini] Error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _detect_topic(self, text: str) -> str:
        """Detect the topic from the user's sentence."""
        text_lower = text.lower()
        
        # Topic detection keywords
        topics = {
            'greeting': ['hello', 'hi', 'good morning', 'good afternoon', 'how are you'],
            'weather': ['weather', 'rain', 'sunny', 'cold', 'hot', 'cloudy'],
            'food': ['eat', 'food', 'lunch', 'dinner', 'breakfast', 'hungry', 'restaurant'],
            'travel': ['travel', 'trip', 'holiday', 'vacation', 'airport', 'flight'],
            'work': ['work', 'job', 'office', 'meeting', 'boss', 'colleague'],
            'shopping': ['shop', 'buy', 'store', 'price', 'money'],
            'family': ['family', 'mother', 'father', 'sister', 'brother', 'parents'],
            'hobbies': ['hobby', 'sport', 'music', 'read', 'play', 'watch'],
            'daily life': ['morning', 'evening', 'today', 'yesterday', 'tomorrow'],
        }
        
        for topic, keywords in topics.items():
            if any(kw in text_lower for kw in keywords):
                return topic
        
        return "general conversation"
    
    def _extract_errors(self, analysis_result: Dict) -> List[PronunciationError]:
        """Extract pronunciation errors from analysis result."""
        errors = []
        
        word_analyses = analysis_result.get('word_analyses', [])
        word_feedback = analysis_result.get('word_feedback', [])
        
        # Combine both sources
        words_to_check = word_analyses if word_analyses else word_feedback
        
        for word_data in words_to_check:
            # Check if word is correct
            is_correct = word_data.get('is_correct', True)
            score = word_data.get('score', word_data.get('pronunciation_score', 100))
            
            if is_correct and score >= 80:
                continue
            
            word = word_data.get('word', '')
            word_index = word_data.get('word_index', 0)
            
            # Determine error type
            expected = word_data.get('expected_phonemes', '')
            actual = word_data.get('actual_phonemes', '')
            
            # Phoneme error
            if expected and actual and expected != actual:
                severity = 'high' if score < 50 else ('medium' if score < 70 else 'low')
                errors.append(PronunciationError(
                    word=word,
                    word_index=word_index,
                    error_type='phoneme',
                    expected=expected,
                    actual=actual,
                    phoneme=self._find_problem_phoneme(expected, actual),
                    score=score,
                    severity=severity
                ))
            
            # Stress error (from feedback)
            feedback = word_data.get('feedback', '')
            if 'stress' in feedback.lower():
                errors.append(PronunciationError(
                    word=word,
                    word_index=word_index,
                    error_type='stress',
                    expected='correct stress',
                    actual='incorrect stress',
                    score=score,
                    severity='medium'
                ))
            
            # General pronunciation error
            if not errors or errors[-1].word != word:
                if score < 70:
                    errors.append(PronunciationError(
                        word=word,
                        word_index=word_index,
                        error_type='phoneme',
                        expected=expected or word,
                        actual=actual or 'unclear',
                        score=score,
                        severity='high' if score < 50 else 'medium'
                    ))
        
        return errors
    
    def _find_problem_phoneme(self, expected: str, actual: str) -> Optional[str]:
        """Find the specific phoneme that differs between expected and actual."""
        exp_phonemes = expected.split() if expected else []
        act_phonemes = actual.split() if actual else []
        
        for exp, act in zip(exp_phonemes, act_phonemes):
            if exp != act:
                return exp
        
        return exp_phonemes[0] if exp_phonemes else None
    
    def _generate_phoneme_followup(self, error: PronunciationError, 
                                    analysis: Dict) -> Dict:
        """Generate follow-up for phoneme errors."""
        word = error.word
        phoneme = error.phoneme
        
        # Get minimal pairs for this phoneme
        practice_words = self._get_minimal_pairs_for_phoneme(phoneme) if phoneme else []
        
        # Get phoneme description
        phoneme_desc = self._get_phoneme_description(phoneme) if phoneme else ""
        
        # Select template
        templates = self.templates.get('phoneme', [])
        template = random.choice(templates) if templates else (
            "Please repeat the word '{word}' focusing on the correct pronunciation."
        )
        
        # Format question
        question = template.format(
            word=word,
            phoneme=phoneme or 'sound',
            phoneme_ipa=f"/{phoneme}/" if phoneme else '',
            description=phoneme_desc
        )
        
        # Optionally rephrase with T5 for more natural language
        if self.use_t5:
            question = self._rephrase_with_t5(question)
        
        return {
            "question": question,
            "target_word": word,
            "target_phoneme": phoneme,
            "practice_words": practice_words[:5],
            "error_type": "phoneme",
            "phoneme_description": phoneme_desc,
            "difficulty": self._calculate_difficulty(error),
            "drill_sentence": self._get_drill_sentence(word, phoneme)
        }
    
    def _generate_stress_followup(self, error: PronunciationError,
                                   analysis: Dict) -> Dict:
        """Generate follow-up for stress pattern errors."""
        word = error.word
        
        templates = self.templates.get('stress', [])
        template = random.choice(templates) if templates else (
            "Pay attention to the stress pattern in '{word}'. "
            "Try saying it with emphasis on the correct syllable."
        )
        
        question = template.format(word=word)
        
        if self.use_t5:
            question = self._rephrase_with_t5(question)
        
        return {
            "question": question,
            "target_word": word,
            "target_phoneme": None,
            "practice_words": self._get_similar_stress_words(word),
            "error_type": "stress",
            "difficulty": self._calculate_difficulty(error),
            "drill_sentence": f"Repeat emphasizing: {word.upper()}"
        }
    
    def _generate_intonation_followup(self, error: PronunciationError,
                                       analysis: Dict) -> Dict:
        """Generate follow-up for intonation errors."""
        sentence = analysis.get('transcribed_text', '')
        
        templates = self.templates.get('intonation', [])
        template = random.choice(templates) if templates else (
            "Try the sentence again, paying attention to the rising and falling "
            "tones throughout the phrase."
        )
        
        question = template.format(sentence=sentence)
        
        if self.use_t5:
            question = self._rephrase_with_t5(question)
        
        return {
            "question": question,
            "target_word": None,
            "target_phoneme": None,
            "practice_words": [],
            "error_type": "intonation",
            "difficulty": "medium",
            "drill_sentence": sentence
        }
    
    def _generate_rhythm_followup(self, error: PronunciationError,
                                   analysis: Dict) -> Dict:
        """Generate follow-up for rhythm/timing errors."""
        sentence = analysis.get('transcribed_text', '')
        
        templates = self.templates.get('rhythm', [])
        template = random.choice(templates) if templates else (
            "Let's work on the rhythm. Try to match the natural flow of English "
            "by spacing your words evenly."
        )
        
        question = template
        
        if self.use_t5:
            question = self._rephrase_with_t5(question)
        
        return {
            "question": question,
            "target_word": None,
            "target_phoneme": None,
            "practice_words": [],
            "error_type": "rhythm",
            "difficulty": "medium",
            "drill_sentence": sentence
        }
    
    def _generate_grammar_followup(self, error: PronunciationError,
                                    analysis: Dict) -> Dict:
        """Generate follow-up for grammar errors."""
        word = error.word
        
        templates = self.templates.get('grammar', [])
        template = random.choice(templates) if templates else (
            "There seems to be a grammar issue. Please try the sentence again "
            "with correct grammar structure."
        )
        
        question = template.format(word=word)
        
        if self.use_t5:
            question = self._rephrase_with_t5(question)
        
        return {
            "question": question,
            "target_word": word,
            "target_phoneme": None,
            "practice_words": [],
            "error_type": "grammar",
            "difficulty": "medium",
            "drill_sentence": error.expected if error.expected != word else None
        }
    
    def _generate_general_followup(self, error: PronunciationError,
                                    analysis: Dict) -> Dict:
        """Generate general follow-up when error type is unclear."""
        word = error.word
        sentence = analysis.get('transcribed_text', '')
        
        question = (
            f"Let's practice the word '{word}' again. "
            f"Listen to the reference audio and try to match the pronunciation."
        )
        
        if self.use_t5:
            question = self._rephrase_with_t5(question)
        
        return {
            "question": question,
            "target_word": word,
            "target_phoneme": None,
            "practice_words": [],
            "error_type": "general",
            "difficulty": self._calculate_difficulty(error),
            "drill_sentence": sentence
        }
    
    def _generate_success_followup(self, analysis: Dict) -> Dict:
        """Generate context-aware follow-up for successful pronunciation."""
        sentence = analysis.get('transcribed_text', '')
        score = analysis.get('overall_score', analysis.get('pronunciation_score', 0))
        
        # Context-aware questions based on what was said
        words = sentence.lower().split() if sentence else []
        topics_detected = []
        
        # Detect topics/themes
        topic_keywords = {
            'greeting': ['hello', 'hi', 'hey', 'good morning', 'how are you'],
            'introduction': ['my name', 'i am', "i'm", 'nice to meet'],
            'weather': ['weather', 'rain', 'sunny', 'cold', 'warm'],
            'food': ['eat', 'food', 'breakfast', 'lunch', 'dinner', 'hungry'],
            'travel': ['travel', 'trip', 'holiday', 'vacation', 'visit'],
            'work': ['work', 'job', 'office', 'meeting', 'project'],
        }
        
        for topic, keywords in topic_keywords.items():
            if any(kw in sentence.lower() for kw in keywords):
                topics_detected.append(topic)
        
        # Generate contextual question based on detected topic
        if score >= 90:
            if 'greeting' in topics_detected:
                questions = [
                    f"Brilliant! You said '{sentence}' perfectly. Now try: 'Lovely to meet you, how do you do?'",
                    f"Excellent greeting! Try this British phrase: 'Cheerio, hope to see you soon!'",
                    f"Perfect! Can you say: 'I'm absolutely delighted to make your acquaintance.'",
                ]
            elif 'weather' in topics_detected:
                questions = [
                    f"Wonderful pronunciation! Try: 'The weather in Britain is rather unpredictable, isn't it?'",
                    f"Great job! Now say: 'I do hope we'll have some sunshine this afternoon.'",
                ]
            elif 'food' in topics_detected:
                questions = [
                    f"Excellent! Try this: 'Would you fancy a cup of tea with your biscuits?'",
                    f"Perfect! Now say: 'I'm rather peckish, shall we grab something to eat?'",
                ]
            else:
                # Generic but related to their sentence
                questions = [
                    f"Excellent! You scored {score}%. Now try a longer sentence with similar words.",
                    f"Brilliant pronunciation of '{sentence[:30]}...'! Ready for something harder?",
                    f"Perfect! Try expanding: '{sentence}' into a more complex thought.",
                ]
        else:
            # Good but not perfect
            questions = [
                f"Good job on '{sentence}'! Try saying it once more with more emphasis on stressed syllables.",
                f"Nice work! You scored {score}%. Let's practice again to reach 90%+.",
                f"Well done! Focus on the rhythm and try: '{sentence}' one more time.",
            ]
        
        question = random.choice(questions)
        next_sentence = self._get_contextual_next_sentence(sentence, topics_detected)
        
        return {
            "question": question,
            "target_word": None,
            "target_phoneme": None,
            "practice_words": [],
            "error_type": "success",
            "difficulty": "next_level" if score >= 90 else "reinforce",
            "drill_sentence": None,
            "next_sentence": next_sentence,
            "context": topics_detected[0] if topics_detected else "general"
        }
    
    def _get_contextual_next_sentence(self, current: str, topics: list) -> str:
        """Get next practice sentence based on context."""
        sentences_by_topic = {
            'greeting': [
                "How do you do? Pleased to make your acquaintance.",
                "Good afternoon, isn't it a lovely day?",
                "Do come in, make yourself at home.",
            ],
            'weather': [
                "The forecast says it shall be frightfully cold tomorrow.",
                "One can never quite trust British weather, can one?",
                "I rather think we're in for some rain this evening.",
            ],
            'food': [
                "Shall we have afternoon tea at half past three?",
                "I'm absolutely famished, let's find a proper meal.",
                "Would you care for some scones with clotted cream?",
            ],
            'travel': [
                "I'm absolutely thrilled about our trip to Scotland.",
                "Have you ever visited the Lake District?",
                "The journey was rather long but quite enjoyable.",
            ],
            'work': [
                "I have a rather important meeting this afternoon.",
                "The project deadline is approaching rapidly.",
                "Let's schedule a conference call for tomorrow.",
            ],
        }
        
        for topic in topics:
            if topic in sentences_by_topic:
                return random.choice(sentences_by_topic[topic])
        
        # Default British sentences
        return random.choice([
            "The cathedral is absolutely breathtaking, wouldn't you agree?",
            "I thought we might pop round to the shops later.",
            "Environmental sustainability is crucially important these days.",
        ])
    
    def _rephrase_with_t5(self, text: str) -> str:
        """Use T5 to rephrase text more naturally."""
        if not self.use_t5:
            return text
        
        self._init_t5()
        
        if self.t5_model is None:
            return text
        
        try:
            # T5 prompt for paraphrasing
            input_text = f"paraphrase: {text}"
            
            inputs = self.t5_tokenizer.encode(input_text, return_tensors="pt", 
                                              max_length=256, truncation=True)
            
            outputs = self.t5_model.generate(
                inputs,
                max_new_tokens=60,  # CPU optimized: keep it short
                num_beams=2,        # CPU optimized: reduced from 4
                early_stopping=True,
                do_sample=True,
                temperature=0.7
            )
            
            rephrased = self.t5_tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Only use if it's reasonable length and not too different
            if len(rephrased) > 10 and len(rephrased) < len(text) * 2:
                return rephrased
            
            return text
            
        except Exception as e:
            print(f"[FollowUpGeneration] T5 rephrasing failed: {e}")
            return text
    
    def _get_minimal_pairs_for_phoneme(self, phoneme: str) -> List[str]:
        """Get minimal pair words for practicing a specific phoneme."""
        pair_data = self.minimal_pairs.get(phoneme, {})
        if isinstance(pair_data, dict):
            return pair_data.get('words', [])
        return pair_data if isinstance(pair_data, list) else []
    
    def _get_phoneme_description(self, phoneme: str) -> str:
        """Get articulation description for a phoneme."""
        descriptions = {
            'TH': "Place tongue between teeth, let air flow through",
            'DH': "Like 'TH' but with voice vibration",
            'R': "Curl tongue back, don't touch the roof of mouth",
            'L': "Touch tongue tip to ridge behind upper teeth",
            'W': "Round lips and push air through",
            'V': "Touch upper teeth to lower lip with voice",
            'F': "Touch upper teeth to lower lip without voice",
            'S': "Teeth close together, tongue forward, hiss",
            'Z': "Like 'S' but with voice vibration",
            'SH': "Lips slightly rounded, tongue pulled back",
            'ZH': "Like 'SH' but with voice vibration",
            'CH': "Start with 'T' sound, release into 'SH'",
            'JH': "Like 'CH' but with voice vibration",
            'NG': "Back of tongue touches soft palate",
            'AE': "Mouth open, tongue low and forward (like 'cat')",
            'AH': "Mouth open, tongue relaxed (like 'cut')",
            'IH': "Tongue high and forward, lips relaxed (like 'bit')",
            'IY': "Tongue very high and forward (like 'beat')",
            'UH': "Tongue high and back, lips rounded (like 'put')",
            'UW': "Lips very rounded, tongue high and back (like 'boot')",
            'EH': "Tongue mid-height and forward (like 'bed')",
            'AO': "Lips rounded, tongue mid-height back (like 'thought')",
        }
        return descriptions.get(phoneme, f"Focus on the '{phoneme}' sound")
    
    def _get_similar_stress_words(self, word: str) -> List[str]:
        """Get words with similar stress patterns for practice."""
        # Simple list of common stress pattern words
        stress_words = {
            2: ["about", "begin", "decide", "enjoy", "forget"],
            3: ["important", "tomorrow", "computer", "together", "remember"]
        }
        
        syllable_count = self._count_syllables(word)
        return stress_words.get(syllable_count, [word])
    
    def _count_syllables(self, word: str) -> int:
        """Estimate syllable count for a word."""
        word = word.lower()
        vowels = "aeiouy"
        count = 0
        prev_was_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_was_vowel:
                count += 1
            prev_was_vowel = is_vowel
        
        # Handle silent e
        if word.endswith('e') and count > 1:
            count -= 1
        
        return max(1, count)
    
    def _get_drill_sentence(self, word: str, phoneme: str = None) -> str:
        """Get a practice sentence containing the target word/phoneme."""
        if phoneme and phoneme in self.phoneme_drills:
            return random.choice(self.phoneme_drills[phoneme])
        
        return f"Please practice: The word '{word}' should be pronounced clearly."
    
    def _get_next_practice_sentence(self, analysis: Dict) -> str:
        """Get next practice sentence based on current performance."""
        # This could be expanded to select from a progression system
        next_sentences = [
            "The weather in Britain is rather variable.",
            "I thought you said you were going to the theatre.",
            "Would you like a cup of tea with your breakfast?",
            "The cathedral is absolutely breathtaking.",
            "Environmental sustainability is crucially important."
        ]
        return random.choice(next_sentences)
    
    def _calculate_difficulty(self, error: PronunciationError) -> str:
        """Calculate difficulty based on error characteristics."""
        if error.score < 40:
            return "challenging"
        elif error.score < 60:
            return "moderate"
        elif error.score < 80:
            return "achievable"
        else:
            return "easy"
    
    def _load_templates(self) -> Dict[str, List[str]]:
        """Load question templates by error type."""
        return {
            'phoneme': [
                "Let's practice the '{word}' sound. Focus on {phoneme_ipa}: {description}.",
                "Try saying '{word}' again. Pay special attention to how you form the {phoneme_ipa} sound.",
                "The sound in '{word}' needs work. Here's how to make {phoneme_ipa}: {description}.",
                "Repeat '{word}' focusing on {phoneme_ipa}. {description}.",
            ],
            'stress': [
                "Pay attention to word stress in '{word}'. Which syllable should be emphasized?",
                "Let's work on stress patterns. Try saying '{word}' with proper emphasis.",
                "The stress in '{word}' was off. Listen to the reference and match the rhythm.",
            ],
            'intonation': [
                "Your intonation needs adjustment. Try matching the melody of the reference.",
                "Focus on the rise and fall of your voice. The sentence should flow naturally.",
                "Let's work on sentence melody. Listen and repeat with similar pitch patterns.",
            ],
            'rhythm': [
                "English has a stress-timed rhythm. Try to keep the beat steady between stressed syllables.",
                "Work on your timing. The words should flow smoothly, not choppy.",
                "Let's practice the natural rhythm. Listen to how the words connect together.",
            ],
            'grammar': [
                "There was a grammar issue with '{word}'. Please try the correct form.",
                "Let's fix the grammar. Try the sentence again with proper structure.",
            ]
        }
    
    def _load_minimal_pairs(self) -> Dict[str, List[str]]:
        """Load minimal pair words for phoneme practice - TRUE MINIMAL PAIRS."""
        return {
            # Voiceless TH vs S/F
            'TH': {
                'contrast': [('think', 'sink'), ('thick', 'sick'), ('three', 'free'), 
                            ('thumb', 'some'), ('path', 'pass'), ('math', 'mass')],
                'words': ['think', 'thing', 'thought', 'through', 'thank', 'bath', 'path', 'teeth'],
            },
            # Voiced TH vs D/Z
            'DH': {
                'contrast': [('this', 'dis'), ('those', 'doze'), ('then', 'den'),
                            ('they', 'day'), ('breathe', 'breed'), ('father', 'fodder')],
                'words': ['this', 'that', 'these', 'those', 'there', 'mother', 'weather'],
            },
            # R vs L
            'R': {
                'contrast': [('right', 'light'), ('read', 'lead'), ('rock', 'lock'),
                            ('rice', 'lice'), ('rip', 'lip'), ('pray', 'play'), ('fry', 'fly')],
                'words': ['red', 'right', 'run', 'road', 'rain', 'ripe', 'rate'],
            },
            'L': {
                'contrast': [('light', 'right'), ('lead', 'read'), ('lock', 'rock'),
                            ('lip', 'rip'), ('play', 'pray'), ('fly', 'fry'), ('glass', 'grass')],
                'words': ['light', 'love', 'lead', 'long', 'look', 'live', 'late'],
            },
            # V vs W
            'V': {
                'contrast': [('vest', 'west'), ('vine', 'wine'), ('veil', 'whale'),
                            ('vet', 'wet'), ('vow', 'wow'), ('very', 'wary')],
                'words': ['very', 'voice', 'view', 'vest', 'vine', 'vote', 'value'],
            },
            'W': {
                'contrast': [('west', 'vest'), ('wine', 'vine'), ('wet', 'vet'),
                            ('whale', 'veil'), ('wow', 'vow'), ('wary', 'vary')],
                'words': ['water', 'wait', 'want', 'walk', 'week', 'west', 'wine'],
            },
            # S vs SH vs CH
            'S': {
                'contrast': [('see', 'she'), ('sock', 'shock'), ('sip', 'ship'),
                            ('sue', 'shoe'), ('mass', 'mash'), ('mess', 'mesh')],
                'words': ['see', 'sit', 'sun', 'say', 'soon', 'sell', 'same'],
            },
            'SH': {
                'contrast': [('she', 'see'), ('ship', 'sip'), ('shoe', 'sue'),
                            ('shop', 'chop'), ('wash', 'watch'), ('mash', 'match')],
                'words': ['she', 'ship', 'shop', 'show', 'should', 'shine', 'shell'],
            },
            'CH': {
                'contrast': [('chop', 'shop'), ('chip', 'ship'), ('catch', 'cash'),
                            ('watch', 'wash'), ('much', 'mush'), ('chin', 'shin')],
                'words': ['church', 'chance', 'child', 'check', 'choose', 'chain', 'cheese'],
            },
            # B vs P (voiced vs voiceless)
            'B': {
                'contrast': [('bat', 'pat'), ('buy', 'pie'), ('bin', 'pin'),
                            ('bet', 'pet'), ('big', 'pig'), ('cab', 'cap')],
                'words': ['bat', 'bet', 'bit', 'but', 'boat', 'book', 'back'],
            },
            'P': {
                'contrast': [('pat', 'bat'), ('pie', 'buy'), ('pin', 'bin'),
                            ('pet', 'bet'), ('pig', 'big'), ('cap', 'cab')],
                'words': ['pat', 'pet', 'pit', 'put', 'pot', 'park', 'path'],
            },
            # Short A vs Long A
            'AE': {
                'contrast': [('cat', 'cut'), ('bat', 'but'), ('hat', 'hut'),
                            ('mat', 'met'), ('sat', 'set'), ('pan', 'pen')],
                'words': ['cat', 'hat', 'bat', 'map', 'sat', 'apple', 'back'],
            },
            # Long E vs Short I
            'IY': {
                'contrast': [('beat', 'bit'), ('seat', 'sit'), ('feet', 'fit'),
                            ('heat', 'hit'), ('sleep', 'slip'), ('sheep', 'ship')],
                'words': ['see', 'meet', 'beat', 'feet', 'lead', 'beach', 'peace'],
            },
            'IH': {
                'contrast': [('bit', 'beat'), ('sit', 'seat'), ('fit', 'feet'),
                            ('hit', 'heat'), ('slip', 'sleep'), ('ship', 'sheep')],
                'words': ['bit', 'sit', 'fit', 'hit', 'ship', 'chip', 'trip'],
            },
        }
    
    def _load_phoneme_drills(self) -> Dict[str, List[str]]:
        """Load drill sentences for specific phonemes."""
        return {
            'TH': [
                "I think this is the thing they thought about.",
                "Thank you for thinking through the theory.",
                "The three thieves thought they were through.",
                "Thunder and lightning are thrilling phenomena.",
                "Thirty-three thousand feathers on a thrush's throat.",
            ],
            'DH': [
                "This is the one that they wanted.",
                "These are those things over there.",
                "The weather is rather rainy today.",
                "My father and mother are together.",
                "They breathe with ease in the breeze.",
            ],
            'R': [
                "The rabbit ran really rather rapidly.",
                "Roberto reads the red book regularly.",
                "Right around the river, roses grow.",
                "Rare red rabbits ran round the rocks.",
                "Remember to reserve the restaurant for Friday.",
            ],
            'L': [
                "Love and laughter lead to a lovely life.",
                "Look at the little light on the left.",
                "Lilly likes to listen to lullabies late.",
                "Lovely lilacs line the long lane lazily.",
                "The lion lay leisurely on the lawn.",
            ],
            'V': [
                "Very few have investigated the vast village.",
                "Victor viewed the vivid violet violets.",
                "Vera's voice was extremely vivacious.",
                "Vegetables and vitamins are very valuable.",
                "Vivian values various vintage vases.",
            ],
            'W': [
                "The wise woman watched the wild waves.",
                "We would welcome warm winter weather.",
                "Will you wait while I wash the windows?",
                "Willy went west wearing a woolen waistcoat.",
                "Waves washed over the wooden wharf.",
            ],
            'SH': [
                "She should share the shiny shells.",
                "Shirley showed Sharon her new shoes.",
                "The chef made a delicious fish dish.",
                "I wish I could finish washing the dishes.",
                "Shall we share some champagne?",
            ],
            'CH': [
                "Charlie chose to chew chocolate cheerfully.",
                "The church choir sang a cheerful chant.",
                "I watched the children catch butterflies.",
                "Choose to change your challenging choices.",
                "Richard reached for a rich chocolate cake.",
            ],
        }
    
    def _load_stress_drills(self) -> Dict[str, Dict]:
        """Load stress pattern practice drills."""
        return {
            # Pattern: o = unstressed, O = stressed
            'oO': {  # 2 syllables, stress on 2nd
                'words': ['about', 'begin', 'decide', 'enjoy', 'forget', 'prepare', 'receive'],
                'sentence': "About what you begin, decide to enjoy and don't forget!",
                'tip': "In these words, the second syllable is louder and longer.",
            },
            'Oo': {  # 2 syllables, stress on 1st
                'words': ['table', 'city', 'letter', 'happy', 'study', 'mother', 'water'],
                'sentence': "Happy mothers study letters at the water table in the city.",
                'tip': "The first syllable is stressed - make it louder and clearer.",
            },
            'oOo': {  # 3 syllables, stress on 2nd
                'words': ['important', 'tomorrow', 'computer', 'together', 'remember', 'banana'],
                'sentence': "Remember, tomorrow is important - bring your computer together!",
                'tip': "The middle syllable carries the stress - emphasize it!",
            },
            'Ooo': {  # 3 syllables, stress on 1st
                'words': ['beautiful', 'difficult', 'hospital', 'family', 'library', 'separately'],
                'sentence': "The beautiful family visited the hospital library separately.",
                'tip': "The first syllable is prominent - the rest are softer.",
            },
            'ooO': {  # 3 syllables, stress on 3rd
                'words': ['understand', 'introduce', 'recommend', 'guarantee', 'disagree'],
                'sentence': "I understand: you recommend and guarantee but disagree.",
                'tip': "The final syllable is stressed - build up to it!",
            },
            'oOoo': {  # 4 syllables, stress on 2nd
                'words': ['communication', 'pronunciation', 'imagination', 'examination'],
                'sentence': "Good pronunciation requires imagination during examination.",
                'tip': "The second syllable is longest and loudest in these -tion words.",
            },
        }
    
    def _load_intonation_drills(self) -> Dict[str, List[Dict]]:
        """Load intonation practice sentences with patterns."""
        return {
            'rising': {  # Yes/No questions - voice goes UP
                'sentences': [
                    {"text": "Are you coming?", "pattern": "↗", "tip": "Voice rises at 'coming'"},
                    {"text": "Did you enjoy it?", "pattern": "↗", "tip": "Rise at 'enjoy it'"},
                    {"text": "Is this your book?", "pattern": "↗", "tip": "Rise at 'book'"},
                    {"text": "Would you like some tea?", "pattern": "↗", "tip": "Rise at 'tea'"},
                    {"text": "Have you been to London?", "pattern": "↗", "tip": "Rise at 'London'"},
                ],
                'explanation': "Yes/No questions typically end with rising intonation.",
            },
            'falling': {  # Statements and WH-questions - voice goes DOWN
                'sentences': [
                    {"text": "I live in London.", "pattern": "↘", "tip": "Voice falls at 'London'"},
                    {"text": "Where do you work?", "pattern": "↘", "tip": "Fall at 'work'"},
                    {"text": "What time is it?", "pattern": "↘", "tip": "Fall at 'it'"},
                    {"text": "That was delicious.", "pattern": "↘", "tip": "Fall at 'delicious'"},
                    {"text": "How interesting!", "pattern": "↘", "tip": "Fall at 'interesting'"},
                ],
                'explanation': "Statements and WH-questions end with falling intonation.",
            },
            'fall_rise': {  # Polite uncertainty, not finished speaking
                'sentences': [
                    {"text": "Well...", "pattern": "↘↗", "tip": "Fall then slight rise - shows hesitation"},
                    {"text": "I'm not sure, but...", "pattern": "↘↗", "tip": "Indicates more to come"},
                    {"text": "It's alright, I suppose.", "pattern": "↘↗", "tip": "Shows reservation"},
                    {"text": "If you like...", "pattern": "↘↗", "tip": "Polite uncertainty"},
                ],
                'explanation': "Fall-rise shows politeness, uncertainty, or that you're not finished.",
            },
            'list': {  # Listing items - rise on each, fall on last
                'sentences': [
                    {"text": "I bought apples, oranges, and bananas.", "pattern": "↗↗↘", 
                     "tip": "Rise on 'apples', rise on 'oranges', fall on 'bananas'"},
                    {"text": "We visited Paris, Rome, and Madrid.", "pattern": "↗↗↘",
                     "tip": "Rise, rise, then fall on the last item"},
                ],
                'explanation': "In lists, items rise except the final one which falls.",
            },
        }
    
    def _load_grammar_corrections(self) -> Dict[str, List[Dict]]:
        """Load grammar correction exercises for British English."""
        return {
            'articles': [
                {"wrong": "I go to university.", "correct": "I go to university.", "note": "British: no article needed"},
                {"wrong": "I went to hospital.", "correct": "I went to hospital.", "note": "British: no article when you're a patient"},
                {"wrong": "At the weekend", "correct": "At the weekend", "note": "British uses 'at', American uses 'on'"},
            ],
            'verb_forms': [
                {"wrong": "I have gotten better.", "correct": "I have got better.", "note": "British uses 'got', not 'gotten'"},
                {"wrong": "Did you eat yet?", "correct": "Have you eaten yet?", "note": "British prefers present perfect for recent past"},
                {"wrong": "I just ate lunch.", "correct": "I've just eaten lunch.", "note": "British uses present perfect with 'just'"},
            ],
            'vocabulary': [
                {"wrong": "I'm taking a vacation.", "correct": "I'm going on holiday.", "note": "British: holiday, not vacation"},
                {"wrong": "The apartment is nice.", "correct": "The flat is lovely.", "note": "British: flat, not apartment"},
                {"wrong": "Let's take the elevator.", "correct": "Let's take the lift.", "note": "British: lift, not elevator"},
                {"wrong": "Line up here.", "correct": "Queue here.", "note": "British: queue, not line up"},
            ],
            'prepositions': [
                {"wrong": "I'll meet you Monday.", "correct": "I'll meet you on Monday.", "note": "British requires 'on' with days"},
                {"wrong": "Different than", "correct": "Different from", "note": "British: different from (or to)"},
                {"wrong": "Write me soon.", "correct": "Write to me soon.", "note": "British requires 'to'"},
            ],
        }
    
    def get_minimal_pair_practice(self, phoneme: str) -> Dict:
        """Get a complete minimal pair practice exercise for frontend display."""
        pair_data = self.minimal_pairs.get(phoneme, {})
        
        if isinstance(pair_data, dict):
            contrasts = pair_data.get('contrast', [])
            words = pair_data.get('words', [])
        else:
            # Legacy format compatibility
            contrasts = []
            words = pair_data if isinstance(pair_data, list) else []
        
        if contrasts:
            selected_pair = random.choice(contrasts)
            return {
                'phoneme': phoneme,
                'type': 'minimal_pair',
                'word1': selected_pair[0],
                'word2': selected_pair[1],
                'instruction': f"Listen and repeat: '{selected_pair[0]}' vs '{selected_pair[1]}'",
                'practice_words': words[:5],
                'tip': self._get_phoneme_description(phoneme),
            }
        else:
            return {
                'phoneme': phoneme,
                'type': 'word_list',
                'practice_words': words[:5],
                'tip': self._get_phoneme_description(phoneme),
            }
    
    def get_stress_practice(self, syllable_count: int = None) -> Dict:
        """Get a stress pattern practice exercise."""
        stress_drills = self._load_stress_drills()
        
        if syllable_count == 2:
            patterns = ['oO', 'Oo']
        elif syllable_count == 3:
            patterns = ['oOo', 'Ooo', 'ooO']
        elif syllable_count == 4:
            patterns = ['oOoo']
        else:
            patterns = list(stress_drills.keys())
        
        pattern = random.choice(patterns)
        drill = stress_drills.get(pattern, {})
        
        return {
            'type': 'stress_pattern',
            'pattern': pattern,
            'pattern_visual': pattern.replace('O', '●').replace('o', '○'),
            'words': drill.get('words', []),
            'sentence': drill.get('sentence', ''),
            'tip': drill.get('tip', ''),
        }
    
    def get_intonation_practice(self, pattern_type: str = None) -> Dict:
        """Get an intonation practice exercise."""
        intonation_drills = self._load_intonation_drills()
        
        if pattern_type and pattern_type in intonation_drills:
            drill = intonation_drills[pattern_type]
        else:
            pattern_type = random.choice(list(intonation_drills.keys()))
            drill = intonation_drills[pattern_type]
        
        sentence = random.choice(drill.get('sentences', [{}]))
        
        return {
            'type': 'intonation',
            'pattern_type': pattern_type,
            'sentence': sentence.get('text', ''),
            'pattern': sentence.get('pattern', ''),
            'tip': sentence.get('tip', ''),
            'explanation': drill.get('explanation', ''),
        }
    
    def get_grammar_practice(self, category: str = None) -> Dict:
        """Get a grammar correction exercise."""
        grammar = self._load_grammar_corrections()
        
        if category and category in grammar:
            corrections = grammar[category]
        else:
            category = random.choice(list(grammar.keys()))
            corrections = grammar[category]
        
        correction = random.choice(corrections)
        
        return {
            'type': 'grammar',
            'category': category,
            'incorrect': correction.get('wrong', ''),
            'correct': correction.get('correct', ''),
            'note': correction.get('note', ''),
        }


    def _parse_t5_output(self, text: str) -> Dict[str, str]:
        """Parse structured T5 output with labels."""
        result = {}
        patterns = {
            'Mistakes': r'Mistakes?:?\s*(.*?)(?=\n[A-Z][a-z]+:|$)',
            'Correction': r'Correction:?\s*(.*?)(?=\n[A-Z][a-z]+:|$)',
            'Accent': r'Accent:?\s*(.*?)(?=\n[A-Z][a-z]+:|$)',
            'Vocabulary': r'Vocabulary:?\s*(.*?)(?=\n[A-Z][a-z]+:|$)',
            'Dialogue': r'Dialogue:?\s*(.*?)(?=\n[A-Z][a-z]+:|$)',
            'Practice': r'Practice:?\s*(.*?)(?=\n[A-Z][a-z]+:|$)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                result[key] = match.group(1).strip()
            else:
                result[key] = ""
        
        # Fallback if parsing fails totally (model just chatted)
        if not result.get('Dialogue') and not result.get('Correction'):
            result['Dialogue'] = text
            
        return result


# Singleton instance
followup_generation_service = FollowUpGenerationService(use_t5=True)
