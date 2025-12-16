"""
Grammar and Language Checking Service
Provides comprehensive text analysis using:
- LanguageTool: Grammar, spelling, and basic style checks (UK English)
- FLAN-T5 Grammar Synthesis: Advanced grammar correction and rephrasing
- NLTK/WordNet/spaCy: Word alternatives and missing parts detection
"""
from typing import Dict, List, Optional
import re

# Configuration flags - set to True to enable heavy models
ENABLE_LANGUAGE_TOOL = True   # Self-hosted LanguageTool (UK English) - downloaded and ready!
ENABLE_T5_GRAMMAR = True      # T5 for advanced grammar correction (uses smaller model on CPU)
ENABLE_SPACY = False          # spaCy NLP (optional, uses fallback if False)


class GrammarService:
    """Service for grammar checking and language improvement"""
    
    def __init__(self):
        self.language_tool = None
        self.nlp = None
        self.t5_model = None
        self.t5_tokenizer = None
        self._lt_initialized = False
        self._spacy_initialized = False
        self._t5_initialized = False
        # Don't initialize tools here - lazy load on first use
        print("GrammarService ready (tools will load on first use)")
        if ENABLE_LANGUAGE_TOOL:
            print("  → LanguageTool (UK English) will be enabled")
        if ENABLE_T5_GRAMMAR:
            print("  → FLAN-T5 Grammar Synthesis will be enabled")
    
    def _ensure_language_tool(self):
        """Lazy initialize LanguageTool - Self-hosted UK English"""
        if self._lt_initialized:
            return
        self._lt_initialized = True
        
        if not ENABLE_LANGUAGE_TOOL:
            print("LanguageTool disabled - using fast fallback grammar check")
            return
            
        self._init_language_tool()
    
    def _ensure_spacy(self):
        """Lazy initialize spaCy"""
        if self._spacy_initialized:
            return
        self._spacy_initialized = True
        
        if not ENABLE_SPACY:
            print("spaCy disabled - using fast fallback NLP")
            return
            
        self._init_spacy()
    
    def _ensure_t5(self):
        """Lazy initialize FLAN-T5 Grammar Synthesis"""
        if self._t5_initialized:
            return
        self._t5_initialized = True
        
        if not ENABLE_T5_GRAMMAR:
            print("T5 disabled - using fast fallback")
            return
            
        self._init_t5()
    
    def _init_language_tool(self):
        """Initialize LanguageTool for grammar checking - UK English"""
        try:
            import language_tool_python
            # Use UK English (en-GB) for British English rules
            print("Initializing LanguageTool (UK English)... This may take a moment on first run.")
            self.language_tool = language_tool_python.LanguageTool('en-GB')
            print("✓ LanguageTool (UK English) initialized successfully")
        except ImportError:
            print("✗ language_tool_python not installed. Run: pip install language-tool-python")
        except Exception as e:
            print(f"✗ LanguageTool initialization error: {e}")
    
    def _init_spacy(self):
        """Initialize spaCy for NLP analysis"""
        try:
            import spacy
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                print("Downloading spaCy model...")
                import subprocess
                subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
                self.nlp = spacy.load("en_core_web_sm")
            print("✓ spaCy initialized successfully")
        except ImportError:
            print("✗ spaCy not installed. Run: pip install spacy")
        except Exception as e:
            print(f"✗ spaCy initialization error: {e}")
    
    def _init_t5(self):
        """Initialize T5 for advanced grammar correction and polishing"""
        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            import torch
            
            # Check if GPU is available
            use_gpu = torch.cuda.is_available()
            
            if use_gpu:
                # Use larger model on GPU for better quality
                model_name = "pszemraj/flan-t5-large-grammar-synthesis"
                print(f"GPU detected! Using {model_name} for high-quality grammar polishing...")
            else:
                # Use smaller, faster model on CPU
                model_name = "vennify/t5-base-grammar-correction"
                print(f"CPU mode. Using {model_name} for faster inference...")
            
            print(f"Initializing {model_name}... This may take a moment on first run.")
            
            self.t5_tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.t5_model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            
            # Store model name for reference
            self._t5_model_name = model_name
            
            if use_gpu:
                self.t5_model = self.t5_model.cuda()
                print(f"✓ T5 Grammar Model initialized (GPU)")
            else:
                print(f"✓ T5 Grammar Model initialized (CPU)")
                
        except ImportError:
            print("✗ transformers not installed. Run: pip install transformers torch")
        except Exception as e:
            print(f"✗ T5 initialization error: {e}")
    
    def check_grammar(self, text: str) -> Dict:
        """
        Comprehensive grammar check using LanguageTool + Fallback patterns
        Returns grammar errors, spelling errors, and style suggestions
        """
        # Lazy init LanguageTool
        self._ensure_language_tool()
        
        # Always get fallback results for ESL-specific patterns
        fallback_result = self._fallback_grammar_check(text)
        
        if not self.language_tool:
            return fallback_result
        
        try:
            matches = self.language_tool.check(text)
            
            errors = []
            for match in matches:
                error = {
                    "message": match.message,
                    "context": match.context,
                    "offset": match.offset,
                    "length": match.errorLength,
                    "replacements": match.replacements[:5] if match.replacements else [],
                    "rule_id": match.ruleId,
                    "category": match.category,
                    "type": self._categorize_error(match.ruleId, match.category)
                }
                errors.append(error)
            
            # Categorize LanguageTool errors
            lt_grammar_errors = [e for e in errors if e["type"] == "grammar"]
            lt_spelling_errors = [e for e in errors if e["type"] == "spelling"]
            lt_style_suggestions = [e for e in errors if e["type"] == "style"]
            
            # Merge with fallback results (fallback catches ESL patterns LanguageTool may miss)
            # Avoid duplicates by checking message content
            existing_messages = {e["message"].lower()[:30] for e in errors}
            
            for fb_error in fallback_result.get("grammar_errors", []):
                if fb_error.get("message", "").lower()[:30] not in existing_messages:
                    lt_grammar_errors.append(fb_error)
            
            # Use LanguageTool's correction as primary, but include fallback if different
            lt_corrected = self.language_tool.correct(text)
            fb_corrected = fallback_result.get("corrected_text", text)
            
            # Prefer the more different correction
            if lt_corrected.lower() != text.lower():
                corrected_text = lt_corrected
            elif fb_corrected.lower() != text.lower():
                corrected_text = fb_corrected
            else:
                corrected_text = lt_corrected
            
            total_errors = len(lt_grammar_errors) + len(lt_spelling_errors) + len(lt_style_suggestions)
            
            return {
                "total_errors": total_errors,
                "grammar_errors": lt_grammar_errors,
                "spelling_errors": lt_spelling_errors,
                "style_suggestions": lt_style_suggestions,
                "corrected_text": corrected_text,
                "score": max(0, 100 - total_errors * 10)
            }
            
        except Exception as e:
            print(f"Grammar check error: {e}")
            return fallback_result
    
    def _categorize_error(self, rule_id: str, category: str) -> str:
        """Categorize error type based on rule ID and category"""
        if "SPELL" in rule_id or "TYPO" in rule_id:
            return "spelling"
        elif "STYLE" in category or "REDUNDANCY" in rule_id:
            return "style"
        else:
            return "grammar"
    
    def _fallback_grammar_check(self, text: str) -> Dict:
        """Enhanced fallback grammar checking without LanguageTool"""
        errors = []
        corrected_text = text
        
        # === 0. Special pattern: Subject + incorrect verb + location ===
        location_nouns = ['gym', 'school', 'store', 'hospital', 'office', 'park', 'beach', 'mall', 
                          'restaurant', 'library', 'museum', 'cinema', 'theater', 'church', 'bank',
                          'market', 'supermarket', 'airport', 'station', 'hotel', 'home', 'work']
        
        for noun in location_nouns:
            # Pattern 1: "I does/do [noun]" -> "I go to the [noun]"
            pattern = rf'\bI\s+(does|do)\s+{noun}\b'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                errors.append({
                    "message": f"Incorrect phrase. 'I {match.group(1)} {noun}' should be 'I go to the {noun}'.",
                    "text": match.group(0),
                    "replacements": [f"I go to the {noun}"],
                    "suggestion": f"I go to the {noun}",
                    "type": "grammar"
                })
                corrected_text = re.sub(pattern, f"I go to the {noun}", corrected_text, flags=re.IGNORECASE)
                return {
                    "total_errors": 1,
                    "grammar_errors": errors,
                    "spelling_errors": [],
                    "style_suggestions": [],
                    "corrected_text": corrected_text,
                    "score": 85
                }
            
            # Pattern 2: "he/she/it go to [noun]" -> "he/she/it goes to the [noun]"
            pattern2 = rf'\b(he|she|it)\s+go\s+to\s+{noun}\b'
            match2 = re.search(pattern2, text, re.IGNORECASE)
            if match2:
                subject = match2.group(1)
                errors.append({
                    "message": f"Incorrect verb form. '{subject} go' should be '{subject} goes'.",
                    "text": match2.group(0),
                    "replacements": [f"{subject} goes to the {noun}"],
                    "suggestion": f"{subject} goes to the {noun}",
                    "type": "grammar"
                })
                corrected_text = re.sub(pattern2, f"{subject} goes to the {noun}", corrected_text, flags=re.IGNORECASE)
                return {
                    "total_errors": 1,
                    "grammar_errors": errors,
                    "spelling_errors": [],
                    "style_suggestions": [],
                    "corrected_text": corrected_text,
                    "score": 85
                }
            
            # Pattern 3: "he/she/it go [noun]" (missing 'to') -> "he/she/it goes to the [noun]"
            pattern3 = rf'\b(he|she|it)\s+go\s+{noun}\b'
            match3 = re.search(pattern3, text, re.IGNORECASE)
            if match3:
                subject = match3.group(1)
                errors.append({
                    "message": f"Incorrect phrase. '{subject} go {noun}' should be '{subject} goes to the {noun}'.",
                    "text": match3.group(0),
                    "replacements": [f"{subject} goes to the {noun}"],
                    "suggestion": f"{subject} goes to the {noun}",
                    "type": "grammar"
                })
                corrected_text = re.sub(pattern3, f"{subject} goes to the {noun}", corrected_text, flags=re.IGNORECASE)
                return {
                    "total_errors": 1,
                    "grammar_errors": errors,
                    "spelling_errors": [],
                    "style_suggestions": [],
                    "corrected_text": corrected_text,
                    "score": 85
                }
        
        # === 1. Subject-verb agreement checks ===
        subject_verb_errors = [
            # "I does" -> "I do" (and similar)
            (r'\bI\s+does\b', "Incorrect verb form for subject 'I'. Use 'do' instead of 'does'.", "I do"),
            (r'\bI\s+has\b(?!\s+to)', "Incorrect verb form for subject 'I'. Use 'have' instead of 'has'.", "I have"),
            (r'\bI\s+goes\b', "Incorrect verb form for subject 'I'. Use 'go' instead of 'goes'.", "I go"),
            (r'\bI\s+wants\b', "Incorrect verb form for subject 'I'. Use 'want' instead of 'wants'.", "I want"),
            (r'\bI\s+needs\b', "Incorrect verb form for subject 'I'. Use 'need' instead of 'needs'.", "I need"),
            (r'\bI\s+likes\b', "Incorrect verb form for subject 'I'. Use 'like' instead of 'likes'.", "I like"),
            (r'\bI\s+works\b', "Incorrect verb form for subject 'I'. Use 'work' instead of 'works'.", "I work"),
            (r'\bI\s+plays\b', "Incorrect verb form for subject 'I'. Use 'play' instead of 'plays'.", "I play"),
            (r'\bI\s+thinks\b', "Incorrect verb form for subject 'I'. Use 'think' instead of 'thinks'.", "I think"),
            (r'\bI\s+knows\b', "Incorrect verb form for subject 'I'. Use 'know' instead of 'knows'.", "I know"),
            (r'\bI\s+makes\b', "Incorrect verb form for subject 'I'. Use 'make' instead of 'makes'.", "I make"),
            (r'\bI\s+takes\b', "Incorrect verb form for subject 'I'. Use 'take' instead of 'takes'.", "I take"),
            (r'\bI\s+comes\b', "Incorrect verb form for subject 'I'. Use 'come' instead of 'comes'.", "I come"),
            (r'\bI\s+sees\b', "Incorrect verb form for subject 'I'. Use 'see' instead of 'sees'.", "I see"),
            (r'\bI\s+gets\b', "Incorrect verb form for subject 'I'. Use 'get' instead of 'gets'.", "I get"),
            (r'\bI\s+speaks\b', "Incorrect verb form for subject 'I'. Use 'speak' instead of 'speaks'.", "I speak"),
            
            # "He/She/It go" -> "He/She/It goes" (CRITICAL: missing -s/-es)
            (r'\b(He|She|It)\s+go\b(?!\s+to)', "Incorrect verb form. Use 'goes' with he/she/it.", "goes"),
            (r'\b(He|She|It)\s+do\b(?!\s+not)', "Incorrect verb form. Use 'does' with he/she/it.", "does"),
            (r'\b(He|She|It)\s+have\b(?!\s+to)', "Incorrect verb form. Use 'has' with he/she/it.", "has"),
            (r'\b(He|She|It)\s+want\b', "Incorrect verb form. Use 'wants' with he/she/it.", "wants"),
            (r'\b(He|She|It)\s+need\b', "Incorrect verb form. Use 'needs' with he/she/it.", "needs"),
            (r'\b(He|She|It)\s+like\b', "Incorrect verb form. Use 'likes' with he/she/it.", "likes"),
            (r'\b(He|She|It)\s+work\b', "Incorrect verb form. Use 'works' with he/she/it.", "works"),
            (r'\b(He|She|It)\s+play\b', "Incorrect verb form. Use 'plays' with he/she/it.", "plays"),
            (r'\b(He|She|It)\s+think\b', "Incorrect verb form. Use 'thinks' with he/she/it.", "thinks"),
            (r'\b(He|She|It)\s+know\b', "Incorrect verb form. Use 'knows' with he/she/it.", "knows"),
            (r'\b(He|She|It)\s+make\b', "Incorrect verb form. Use 'makes' with he/she/it.", "makes"),
            (r'\b(He|She|It)\s+take\b', "Incorrect verb form. Use 'takes' with he/she/it.", "takes"),
            (r'\b(He|She|It)\s+come\b', "Incorrect verb form. Use 'comes' with he/she/it.", "comes"),
            (r'\b(He|She|It)\s+see\b', "Incorrect verb form. Use 'sees' with he/she/it.", "sees"),
            (r'\b(He|She|It)\s+get\b', "Incorrect verb form. Use 'gets' with he/she/it.", "gets"),
            (r'\b(He|She|It)\s+speak\b', "Incorrect verb form. Use 'speaks' with he/she/it.", "speaks"),
            (r'\b(He|She|It)\s+run\b', "Incorrect verb form. Use 'runs' with he/she/it.", "runs"),
            (r'\b(He|She|It)\s+walk\b', "Incorrect verb form. Use 'walks' with he/she/it.", "walks"),
            (r'\b(He|She|It)\s+eat\b', "Incorrect verb form. Use 'eats' with he/she/it.", "eats"),
            (r'\b(He|She|It)\s+drink\b', "Incorrect verb form. Use 'drinks' with he/she/it.", "drinks"),
            (r'\b(He|She|It)\s+live\b', "Incorrect verb form. Use 'lives' with he/she/it.", "lives"),
            (r'\b(He|She|It)\s+love\b', "Incorrect verb form. Use 'loves' with he/she/it.", "loves"),
            
            # "They/We does" -> "They/We do"
            (r'\b(They|We|You)\s+does\b', "Incorrect verb form. Use 'do' with they/we/you.", "do"),
            (r'\b(They|We|You)\s+has\b(?!\s+to)', "Incorrect verb form. Use 'have' with they/we/you.", "have"),
            (r'\b(They|We|You)\s+goes\b', "Incorrect verb form. Use 'go' with they/we/you.", "go"),
            (r'\b(They|We|You)\s+wants\b', "Incorrect verb form. Use 'want' with they/we/you.", "want"),
            (r'\b(They|We|You)\s+needs\b', "Incorrect verb form. Use 'need' with they/we/you.", "need"),
            (r'\b(They|We|You)\s+likes\b', "Incorrect verb form. Use 'like' with they/we/you.", "like"),
            (r'\b(They|We|You)\s+speaks\b', "Incorrect verb form. Use 'speak' with they/we/you.", "speak"),
            
            # "is" / "are" / "am" agreement
            (r'\bI\s+is\b', "Incorrect verb form for 'I'. Use 'am' instead of 'is'.", "I am"),
            (r'\b(You|We|They)\s+is\b', "Incorrect verb form. Use 'are' instead of 'is'.", "are"),
            (r'\b(He|She|It)\s+are\b', "Incorrect verb form. Use 'is' instead of 'are'.", "is"),
            (r'\bI\s+are\b', "Incorrect verb form for 'I'. Use 'am' instead of 'are'.", "I am"),
            
            # "was" / "were" agreement
            (r'\b(You|We|They)\s+was\b', "Incorrect verb form. Use 'were' instead of 'was'.", "were"),
            (r'\b(He|She|It|I)\s+were\b(?!\s+to)', "Incorrect verb form. Use 'was' instead of 'were'.", "was"),
        ]
        
        for pattern, message, replacement in subject_verb_errors:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                error_info = {
                    "message": message,
                    "text": match.group(0),
                    "type": "grammar"
                }
                if replacement:
                    error_info["replacements"] = [replacement]
                    error_info["suggestion"] = replacement
                    corrected_text = re.sub(pattern, replacement, corrected_text, flags=re.IGNORECASE)
                errors.append(error_info)
        
        # === 2. Missing article detection ===
        # Common nouns that typically need articles
        nouns_needing_articles = [
            'gym', 'store', 'school', 'hospital', 'office', 'park', 'beach', 'mall', 
            'restaurant', 'library', 'museum', 'cinema', 'theater', 'church', 'bank',
            'market', 'supermarket', 'airport', 'station', 'hotel', 'house', 'home',
            'car', 'bus', 'train', 'movie', 'book', 'phone', 'computer', 'table',
            'chair', 'door', 'window', 'room', 'kitchen', 'bathroom', 'bedroom'
        ]
        
        words = text.lower().split()
        for i, word in enumerate(words):
            clean_word = re.sub(r'[^\w]', '', word)
            if clean_word in nouns_needing_articles:
                # Check if preceded by an article/determiner
                if i == 0 or words[i-1].lower() not in ['a', 'an', 'the', 'my', 'your', 'his', 'her', 'its', 'our', 'their', 'this', 'that', 'some', 'any', 'to']:
                    # Check context for better suggestion
                    prev_word = words[i-1] if i > 0 else ""
                    # Verbs that typically need "to the" before location nouns
                    location_verbs = ['go', 'goes', 'went', 'going', 'come', 'comes', 'came', 'coming', 
                                      'walk', 'walks', 'walked', 'run', 'runs', 'ran', 'drive', 'drives', 'drove']
                    
                    if prev_word in location_verbs or (i > 1 and words[i-2] in location_verbs):
                        suggestion = f"to the {clean_word}"
                    else:
                        suggestion = f"the {clean_word}"
                    
                    errors.append({
                        "message": f"Missing article or preposition before '{clean_word}'.",
                        "text": clean_word,
                        "word": clean_word,
                        "replacements": [f"the {clean_word}", f"a {clean_word}", f"to the {clean_word}"],
                        "suggestion": suggestion,
                        "type": "grammar"
                    })
                    # Apply correction
                    corrected_text = re.sub(
                        rf'\b{re.escape(clean_word)}\b', 
                        suggestion, 
                        corrected_text, 
                        count=1, 
                        flags=re.IGNORECASE
                    )
        
        # === 3. Common spelling/grammar mistakes ===
        common_mistakes = {
            r'(?<![A-Z])\bi\b(?!\')(?![A-Z])': ("'i' should be capitalized to 'I'", "I"),  # Only match lowercase 'i'
            r'\bdont\b': ("Missing apostrophe in 'don't'", "don't"),
            r'\bcant\b': ("Missing apostrophe in 'can't'", "can't"),
            r'\bwont\b': ("Missing apostrophe in 'won't'", "won't"),
            r'\bim\b': ("Missing apostrophe in 'I'm'", "I'm"),
            r'\bisnt\b': ("Missing apostrophe in 'isn't'", "isn't"),
            r'\barent\b': ("Missing apostrophe in 'aren't'", "aren't"),
            r'\bwasnt\b': ("Missing apostrophe in 'wasn't'", "wasn't"),
            r'\bwerent\b': ("Missing apostrophe in 'weren't'", "weren't"),
            r'\bhasnt\b': ("Missing apostrophe in 'hasn't'", "hasn't"),
            r'\bhavent\b': ("Missing apostrophe in 'haven't'", "haven't"),
            r'\bdoesnt\b': ("Missing apostrophe in 'doesn't'", "doesn't"),
            r'\bwouldnt\b': ("Missing apostrophe in 'wouldn't'", "wouldn't"),
            r'\bcouldnt\b': ("Missing apostrophe in 'couldn't'", "couldn't"),
            r'\bshouldnt\b': ("Missing apostrophe in 'shouldn't'", "shouldn't"),
            r'\bthats\b': ("Missing apostrophe in 'that's'", "that's"),
            r'\bwhats\b': ("Missing apostrophe in 'what's'", "what's"),
            r'\bheres\b': ("Missing apostrophe in 'here's'", "here's"),
            r'\btheres\b': ("Missing apostrophe in 'there's'", "there's"),
            r'\byoure\b': ("Missing apostrophe in 'you're'", "you're"),
            r'\btheyre\b': ("Missing apostrophe in 'they're'", "they're"),
            r'\bwere\b(?=\s+(not\s+)?going)': ("Use 'we're' for 'we are'", "we're"),
            r'\btheir\s+is\b': ("Wrong 'their/there' usage", "there is"),
            r'\btheir\s+are\b': ("Wrong 'their/there' usage", "there are"),
            r'\byour\s+welcome\b': ("Wrong 'your/you're' usage", "you're welcome"),
            r'\byour\s+(going|coming|doing|being)\b': ("Wrong 'your/you're' usage", "you're"),
            r'\bits\s+(a|an|the|going|coming)\b': ("Use 'it's' for 'it is'", "it's"),
            r'\balot\b': ("'A lot' is two words", "a lot"),
            r'\bshould\s+of\b': ("Use 'should have' not 'should of'", "should have"),
            r'\bcould\s+of\b': ("Use 'could have' not 'could of'", "could have"),
            r'\bwould\s+of\b': ("Use 'would have' not 'would of'", "would have"),
            r'\bthen\b(?=\s+\w+\s+then)': ("Possible confusion between 'then' and 'than'", "than"),
            
            # === Advanced grammar patterns ===
            # "goodly" -> "well"
            r'\bgoodly\b': ("'goodly' is not standard. Use 'well' instead.", "well"),
            r'\bfastly\b': ("'fastly' is not a word. Use 'fast' or 'quickly' instead.", "quickly"),
            r'\bslowly\b': ("Consider using 'slowly' correctly", "slowly"),  # valid but flagged for review
            
            # "have went" -> "went" or "have gone"
            r'\bhave\s+went\b': ("Incorrect tense. Use 'have gone' or 'went'.", "went"),
            r'\bhas\s+went\b': ("Incorrect tense. Use 'has gone' or 'went'.", "went"),
            r'\bhad\s+went\b': ("Incorrect tense. Use 'had gone'.", "had gone"),
            
            # "didn't knew" -> "didn't know"
            r"\bdidn't\s+knew\b": ("Use base form after 'didn't'. Should be 'didn't know'.", "didn't know"),
            r"\bdidn't\s+went\b": ("Use base form after 'didn't'. Should be 'didn't go'.", "didn't go"),
            r"\bdoesn't\s+knows\b": ("Use base form after 'doesn't'. Should be 'doesn't know'.", "doesn't know"),
            r"\bdon't\s+knows\b": ("Use base form after 'don't'. Should be 'don't know'.", "don't know"),
            
            # "want to crying" -> "want to cry"
            r'\bwant\s+to\s+crying\b': ("Use infinitive form: 'want to cry' not 'want to crying'.", "want to cry"),
            r'\bwants\s+to\s+crying\b': ("Use infinitive form: 'wants to cry' not 'wants to crying'.", "wants to cry"),
            r'\bwant\s+to\s+going\b': ("Use infinitive form: 'want to go' not 'want to going'.", "want to go"),
            r'\bwant\s+to\s+eating\b': ("Use infinitive form: 'want to eat' not 'want to eating'.", "want to eat"),
            r'\bwant\s+to\s+sleeping\b': ("Use infinitive form: 'want to sleep' not 'want to sleeping'.", "want to sleep"),
            r'\bneed\s+to\s+going\b': ("Use infinitive form: 'need to go' not 'need to going'.", "need to go"),
            r'\blike\s+to\s+going\b': ("Use infinitive form: 'like to go' not 'like to going'.", "like to go"),
            
            # "I am agree" -> "I agree"
            r'\bI\s+am\s+agree\b': ("Remove 'am'. Should be 'I agree' not 'I am agree'.", "I agree"),
            r'\bI\s+am\s+understand\b': ("Remove 'am'. Should be 'I understand'.", "I understand"),
            r'\bI\s+am\s+know\b': ("Remove 'am'. Should be 'I know'.", "I know"),
            r'\bI\s+am\s+like\b': ("Remove 'am'. Should be 'I like'.", "I like"),
            
            # "I no understand" -> "I don't understand"
            r'\bI\s+no\s+understand\b': ("Use 'I don't understand' not 'I no understand'.", "I don't understand"),
            r'\bI\s+no\s+know\b': ("Use 'I don't know' not 'I no know'.", "I don't know"),
            r'\bI\s+no\s+like\b': ("Use 'I don't like' not 'I no like'.", "I don't like"),
            r'\bI\s+no\s+have\b': ("Use 'I don't have' not 'I no have'.", "I don't have"),
            r'\bI\s+no\s+want\b': ("Use 'I don't want' not 'I no want'.", "I don't want"),
            
            # "can't able" -> "can't" or "unable"
            r"\bcan't\s+able\b": ("Redundant. Use 'can't' or 'am unable' instead.", "can't"),
            r"\bcant\s+able\b": ("Redundant. Use 'can't' or 'am unable' instead.", "can't"),
            r"\bcannot\s+able\b": ("Redundant. Use 'cannot' or 'am unable' instead.", "cannot"),
            
            # "very good" as style (not error, but "very" patterns)
            r'\bmore\s+better\b': ("'More better' is redundant. Use 'better'.", "better"),
            r'\bmore\s+worse\b': ("'More worse' is redundant. Use 'worse'.", "worse"),
            r'\bmost\s+best\b': ("'Most best' is redundant. Use 'best'.", "best"),
            r'\bmost\s+worst\b': ("'Most worst' is redundant. Use 'worst'.", "worst"),
            
            # "if he will finish" -> "if he finishes" (conditional)
            r'\bif\s+(he|she|it|I|we|they|you)\s+will\b': ("In conditional clauses, use present tense. Remove 'will'.", "if"),
            
            # "because...so" redundancy
            r'\bbecause\s+.+\s+so\s+': ("'Because' and 'so' are redundant together. Use one or the other.", ""),
            
            # "the boy which" -> "the boy who"
            r'\b(boy|girl|man|woman|person|people|child|children)\s+which\b': ("Use 'who' for people, not 'which'.", "who"),
            
            # Double negatives
            r"\bdon't\s+know\s+nothing\b": ("Double negative. Use 'don't know anything'.", "don't know anything"),
            r"\bcan't\s+do\s+nothing\b": ("Double negative. Use 'can't do anything'.", "can't do anything"),
            r"\bdidn't\s+see\s+nobody\b": ("Double negative. Use 'didn't see anybody'.", "didn't see anybody"),
            
            # Missing "is/are" in "X very Y" sentences
            r'\b(this|that|it)\s+(very|so|really|quite)\s+(good|bad|nice|great|beautiful|interesting|boring)\b': 
                ("Missing verb 'is'. Should be 'this is very good'.", "is"),
            r'\b(these|those|they)\s+(very|so|really|quite)\s+(good|bad|nice|great|beautiful|interesting|boring)\b': 
                ("Missing verb 'are'. Should be 'these are very good'.", "are"),
            
            # "[noun] very [adjective]" - missing is
            r'\b(movie|film|book|story|song|show|game)\s+(very|so|really)\s+(good|bad|nice|great|interesting|boring)\b':
                ("Missing verb 'is'. Should include 'is' before the adjective.", "is"),
            
            # Missing auxiliary in progressive: "I working" -> "I am working"
            r'\bI\s+(working|going|coming|running|eating|sleeping|reading|writing|playing|watching|walking|talking|doing)\b(?!\s+\w+ing)':
                ("Missing auxiliary verb. Use 'I am working' not 'I working'.", "I am"),
            r'\b(he|she|it)\s+(working|going|coming|running|eating|sleeping|reading|writing|playing|watching|walking|talking|doing)\b(?!\s+\w+ing)':
                ("Missing auxiliary verb. Use 'he/she is working' not 'he/she working'.", "is"),
            r'\b(they|we|you)\s+(working|going|coming|running|eating|sleeping|reading|writing|playing|watching|walking|talking|doing)\b(?!\s+\w+ing)':
                ("Missing auxiliary verb. Use 'they are working' not 'they working'.", "are"),
            
            # "interest" instead of "interesting"
            r'\bis\s+interest\b': ("Use 'interesting' as an adjective, not 'interest'.", "is interesting"),
            r'\bis\s+bore\b': ("Use 'boring' as an adjective, not 'bore'.", "is boring"),
            r'\bis\s+excite\b': ("Use 'exciting' as an adjective, not 'excite'.", "is exciting"),
            
            # "can goes" -> "can go"
            r'\bcan\s+goes\b': ("Use base form after 'can'. Should be 'can go'.", "can go"),
            r'\bcan\s+does\b': ("Use base form after 'can'. Should be 'can do'.", "can do"),
            r'\bcan\s+makes\b': ("Use base form after 'can'. Should be 'can make'.", "can make"),
            r'\bwill\s+goes\b': ("Use base form after 'will'. Should be 'will go'.", "will go"),
            r'\bwill\s+makes\b': ("Use base form after 'will'. Should be 'will make'.", "will make"),
        }
        
        for pattern, (message, replacement) in common_mistakes.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                errors.append({
                    "message": message,
                    "text": match.group(0),
                    "replacements": [replacement],
                    "suggestion": replacement,
                    "type": "grammar"
                })
                corrected_text = re.sub(pattern, replacement, corrected_text, flags=re.IGNORECASE)
        
        # === 4. Double word detection ===
        double_word_match = re.search(r'\b(\w+)\s+\1\b', text, re.IGNORECASE)
        if double_word_match:
            word = double_word_match.group(1)
            errors.append({
                "message": f"Repeated word: '{word}'",
                "text": f"{word} {word}",
                "replacements": [word],
                "suggestion": word,
                "type": "grammar"
            })
            corrected_text = re.sub(r'\b(\w+)\s+\1\b', r'\1', corrected_text, flags=re.IGNORECASE)
        
        # Calculate score
        score = max(0, 100 - len(errors) * 15)
        
        return {
            "total_errors": len(errors),
            "grammar_errors": [e for e in errors if e.get("type") == "grammar"],
            "spelling_errors": [e for e in errors if e.get("type") == "spelling"],
            "style_suggestions": [e for e in errors if e.get("type") == "style"],
            "corrected_text": corrected_text,
            "score": score
        }
    
    def correct_with_t5(self, text: str) -> Dict:
        """
        Advanced grammar correction using T5
        Provides better phrasing and natural corrections for whole paragraphs
        """
        # Lazy init T5
        self._ensure_t5()
        
        if not self.t5_model or not self.t5_tokenizer:
            return {
                "original": text,
                "corrected": text,
                "improved_phrasing": text,
                "available": False
            }
        
        try:
            import torch
            
            # Format input based on model type
            model_name = getattr(self, '_t5_model_name', '')
            if 'vennify' in model_name or 't5-base' in model_name:
                # vennify/t5-base-grammar-correction needs "grammar: " prefix
                input_text = f"grammar: {text}"
            else:
                # flan-t5 works with direct input
                input_text = text
            
            # Tokenize input
            inputs = self.t5_tokenizer(
                input_text, 
                return_tensors="pt", 
                max_length=512, 
                truncation=True,
                padding=True
            )
            
            # Move to GPU if model is on GPU
            if torch.cuda.is_available() and next(self.t5_model.parameters()).is_cuda:
                inputs = {k: v.cuda() for k, v in inputs.items()}
            
            # Generate correction with beam search for better quality
            with torch.no_grad():
                outputs = self.t5_model.generate(
                    **inputs,
                    max_length=512,
                    num_beams=5,
                    num_return_sequences=1,
                    early_stopping=True,
                    do_sample=False,
                    temperature=1.0,
                )
            
            corrected = self.t5_tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Check if correction is different
            is_different = corrected.lower().strip() != text.lower().strip()
            
            return {
                "original": text,
                "corrected": corrected,
                "improved_phrasing": corrected if is_different else text,
                "has_improvements": is_different,
                "available": True,
                "model": "flan-t5-large-grammar-synthesis"
            }
            
        except Exception as e:
            print(f"T5 correction error: {e}")
            return {
                "original": text,
                "corrected": text,
                "improved_phrasing": text,
                "available": False,
                "error": str(e)
            }
    
    def analyze_with_nlp(self, text: str) -> Dict:
        """
        Analyze text using NLTK/spaCy for:
        - Missing parts (articles, verbs, etc.)
        - Word alternatives (synonyms)
        - Sentence structure analysis
        """
        # Lazy init spaCy
        self._ensure_spacy()
        
        if not self.nlp:
            return self._fallback_nlp_analysis(text)
        
        try:
            doc = self.nlp(text)
            
            # Extract parts of speech
            pos_tags = []
            for token in doc:
                pos_tags.append({
                    "word": token.text,
                    "pos": token.pos_,
                    "tag": token.tag_,
                    "dep": token.dep_
                })
            
            # Detect missing parts
            missing_parts = self._detect_missing_parts(doc)
            
            # Get word alternatives using WordNet
            word_alternatives = self._get_word_alternatives(doc)
            
            # Sentence complexity analysis
            complexity = self._analyze_complexity(doc)
            
            # Entity recognition
            entities = [{"text": ent.text, "label": ent.label_} for ent in doc.ents]
            
            return {
                "pos_tags": pos_tags,
                "missing_parts": missing_parts,
                "word_alternatives": word_alternatives,
                "complexity": complexity,
                "entities": entities,
                "sentence_count": len(list(doc.sents)),
                "word_count": len([t for t in doc if not t.is_punct])
            }
            
        except Exception as e:
            print(f"NLP analysis error: {e}")
            return self._fallback_nlp_analysis(text)
    
    def _detect_missing_parts(self, doc) -> List[Dict]:
        """Detect potential missing parts in sentences"""
        missing = []
        
        for sent in doc.sents:
            tokens = list(sent)
            
            # Check for missing articles before nouns
            for i, token in enumerate(tokens):
                if token.pos_ == "NOUN" and token.dep_ in ["nsubj", "dobj", "pobj"]:
                    # Check if preceded by determiner
                    if i == 0 or tokens[i-1].pos_ not in ["DET", "PRON", "PROPN", "NUM"]:
                        # Check if it's a countable singular noun
                        if token.tag_ == "NN":
                            missing.append({
                                "type": "article",
                                "position": token.idx,
                                "word": token.text,
                                "suggestion": f"Consider adding 'a', 'an', or 'the' before '{token.text}'",
                                "examples": [f"a {token.text}", f"the {token.text}"]
                            })
            
            # Check for missing subject
            has_subject = any(t.dep_ in ["nsubj", "nsubjpass"] for t in tokens)
            has_verb = any(t.pos_ == "VERB" for t in tokens)
            
            if has_verb and not has_subject and len(tokens) > 2:
                missing.append({
                    "type": "subject",
                    "suggestion": "Sentence may be missing a subject",
                    "sentence": sent.text
                })
        
        return missing
    
    def _get_word_alternatives(self, doc) -> List[Dict]:
        """Get synonyms/alternatives for key words using WordNet"""
        alternatives = []
        
        try:
            from nltk.corpus import wordnet
            import nltk
            try:
                wordnet.synsets('test')
            except LookupError:
                nltk.download('wordnet')
                nltk.download('omw-1.4')
            
            # Get alternatives for adjectives, verbs, and nouns
            for token in doc:
                if token.pos_ in ["ADJ", "VERB", "NOUN"] and len(token.text) > 3:
                    synsets = wordnet.synsets(token.text)
                    synonyms = set()
                    
                    for syn in synsets[:3]:
                        for lemma in syn.lemmas()[:3]:
                            if lemma.name() != token.text and "_" not in lemma.name():
                                synonyms.add(lemma.name())
                    
                    if synonyms:
                        alternatives.append({
                            "word": token.text,
                            "pos": token.pos_,
                            "alternatives": list(synonyms)[:5]
                        })
                        
        except Exception as e:
            print(f"WordNet error: {e}")
        
        return alternatives
    
    def _analyze_complexity(self, doc) -> Dict:
        """Analyze sentence complexity"""
        sentences = list(doc.sents)
        
        if not sentences:
            return {"level": "unknown", "score": 0}
        
        avg_length = sum(len(list(s)) for s in sentences) / len(sentences)
        
        # Count subordinate clauses
        subordinate_clauses = sum(1 for t in doc if t.dep_ in ["advcl", "ccomp", "xcomp", "relcl"])
        
        if avg_length > 20 or subordinate_clauses > 2:
            level = "complex"
            score = 80
        elif avg_length > 12 or subordinate_clauses > 0:
            level = "moderate"
            score = 60
        else:
            level = "simple"
            score = 40
        
        return {
            "level": level,
            "score": score,
            "avg_sentence_length": round(avg_length, 1),
            "subordinate_clauses": subordinate_clauses
        }
    
    def _fallback_nlp_analysis(self, text: str) -> Dict:
        """Enhanced fallback NLP analysis without spaCy"""
        words = text.split()
        
        # === Simple POS tagging based on patterns ===
        pos_tags = []
        # Common word -> POS mappings
        pronouns = ['i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their']
        verbs = ['is', 'are', 'am', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 
                 'go', 'goes', 'went', 'going', 'come', 'comes', 'came', 'coming', 'get', 'gets', 'got',
                 'make', 'makes', 'made', 'take', 'takes', 'took', 'see', 'sees', 'saw', 'know', 'knows', 'knew',
                 'think', 'thinks', 'thought', 'want', 'wants', 'wanted', 'like', 'likes', 'liked', 'need', 'needs', 'needed',
                 'work', 'works', 'worked', 'play', 'plays', 'played', 'run', 'runs', 'ran', 'walk', 'walks', 'walked']
        articles = ['a', 'an', 'the']
        prepositions = ['to', 'in', 'on', 'at', 'for', 'with', 'by', 'from', 'of', 'about', 'into', 'through', 'during', 'before', 'after']
        nouns = ['gym', 'school', 'work', 'home', 'house', 'office', 'store', 'park', 'car', 'bus', 'train', 
                 'book', 'phone', 'computer', 'table', 'chair', 'door', 'window', 'room', 'time', 'day', 'year', 'way', 'man', 'woman', 'child']
        
        for word in words:
            clean_word = re.sub(r'[^\w]', '', word).lower()
            if clean_word in pronouns:
                pos = "PRON"
            elif clean_word in verbs:
                pos = "VERB"
            elif clean_word in articles:
                pos = "DET"
            elif clean_word in prepositions:
                pos = "ADP"
            elif clean_word in nouns:
                pos = "NOUN"
            elif clean_word.endswith('ly'):
                pos = "ADV"
            elif clean_word.endswith(('ing', 'ed')):
                pos = "VERB"
            elif clean_word.endswith(('tion', 'ness', 'ment', 'ity')):
                pos = "NOUN"
            else:
                pos = "NOUN"  # Default to noun for unknown words
            
            pos_tags.append({"word": word, "pos": pos})
        
        # === Missing parts detection ===
        missing_parts = []
        nouns_needing_articles = ['gym', 'store', 'school', 'hospital', 'office', 'park', 'beach', 'mall', 
                                   'restaurant', 'library', 'museum', 'cinema', 'theater', 'church', 'bank']
        
        for i, word in enumerate(words):
            clean_word = re.sub(r'[^\w]', '', word).lower()
            if clean_word in nouns_needing_articles:
                # Check if preceded by an article
                if i == 0 or words[i-1].lower() not in ['a', 'an', 'the', 'my', 'your', 'his', 'her', 'its', 'our', 'their', 'to']:
                    missing_parts.append({
                        "type": "article",
                        "word": clean_word,
                        "suggestion": f"Add 'the' or 'a' before '{clean_word}'."
                    })
        
        # === Word alternatives using a simple thesaurus ===
        simple_thesaurus = {
            'gym': ['fitness center', 'workout place', 'health club'],
            'go': ['proceed', 'move', 'travel', 'head'],
            'good': ['great', 'excellent', 'fine', 'wonderful'],
            'bad': ['poor', 'terrible', 'awful', 'unpleasant'],
            'big': ['large', 'huge', 'enormous', 'massive'],
            'small': ['tiny', 'little', 'compact', 'miniature'],
            'happy': ['joyful', 'pleased', 'delighted', 'cheerful'],
            'sad': ['unhappy', 'sorrowful', 'gloomy', 'depressed'],
            'fast': ['quick', 'rapid', 'swift', 'speedy'],
            'slow': ['sluggish', 'unhurried', 'leisurely', 'gradual'],
            'work': ['labor', 'employment', 'job', 'occupation'],
            'like': ['enjoy', 'love', 'prefer', 'appreciate'],
            'want': ['desire', 'wish', 'need', 'require'],
            'make': ['create', 'produce', 'build', 'construct'],
            'get': ['obtain', 'acquire', 'receive', 'gain'],
            'think': ['believe', 'consider', 'suppose', 'assume'],
            'know': ['understand', 'realize', 'recognize', 'comprehend'],
            'see': ['observe', 'notice', 'view', 'watch'],
        }
        
        word_alternatives = []
        for word in words:
            clean_word = re.sub(r'[^\w]', '', word).lower()
            if clean_word in simple_thesaurus:
                # Find POS for this word
                word_pos = "NOUN"
                for tag in pos_tags:
                    if tag["word"].lower() == clean_word:
                        word_pos = tag["pos"]
                        break
                word_alternatives.append({
                    "word": clean_word,
                    "pos": word_pos,
                    "alternatives": simple_thesaurus[clean_word]
                })
        
        # === Complexity analysis ===
        word_count = len(words)
        sentence_count = text.count('.') + text.count('!') + text.count('?') or 1
        avg_sentence_length = word_count / sentence_count
        
        if avg_sentence_length > 20:
            level = "complex"
            complexity_score = 80
        elif avg_sentence_length > 12:
            level = "moderate"
            complexity_score = 60
        else:
            level = "simple"
            complexity_score = 40
        
        return {
            "pos_tags": pos_tags,
            "missing_parts": missing_parts,
            "word_alternatives": word_alternatives,
            "complexity": {
                "level": level, 
                "score": complexity_score,
                "avg_sentence_length": round(avg_sentence_length, 1),
                "subordinate_clauses": 0
            },
            "entities": [],
            "sentence_count": sentence_count,
            "word_count": word_count
        }
    
    def full_analysis(self, text: str) -> Dict:
        """
        Perform comprehensive analysis combining all tools
        """
        # Grammar check with LanguageTool
        grammar_result = self.check_grammar(text)
        
        # Advanced correction with T5
        t5_result = self.correct_with_t5(text)
        
        # NLP analysis with spaCy/NLTK
        nlp_result = self.analyze_with_nlp(text)
        
        # Calculate overall score
        grammar_score = grammar_result.get("score", 50)
        complexity_score = nlp_result.get("complexity", {}).get("score", 50)
        
        overall_score = (grammar_score * 0.6 + complexity_score * 0.4)
        
        # Generate feedback summary
        feedback = self._generate_feedback(grammar_result, t5_result, nlp_result)
        
        return {
            "original_text": text,
            "grammar": grammar_result,
            "advanced_correction": t5_result,
            "nlp_analysis": nlp_result,
            "overall_score": round(overall_score, 1),
            "feedback": feedback
        }
    
    def _generate_feedback(self, grammar: Dict, t5: Dict, nlp: Dict) -> List[str]:
        """Generate user-friendly feedback"""
        feedback = []
        
        # Grammar feedback
        if grammar.get("grammar_errors"):
            feedback.append(f"Found {len(grammar['grammar_errors'])} grammar issue(s) to fix.")
        
        if grammar.get("spelling_errors"):
            feedback.append(f"Found {len(grammar['spelling_errors'])} spelling error(s).")
        
        if grammar.get("style_suggestions"):
            feedback.append(f"{len(grammar['style_suggestions'])} style improvement(s) suggested.")
        
        # T5 feedback
        if t5.get("has_improvements"):
            feedback.append("A more natural phrasing is available.")
        
        # NLP feedback
        if nlp.get("missing_parts"):
            feedback.append(f"Consider adding {len(nlp['missing_parts'])} missing part(s).")
        
        if nlp.get("word_alternatives"):
            feedback.append(f"{len(nlp['word_alternatives'])} word(s) have alternative suggestions.")
        
        if not feedback:
            feedback.append("Great job! Your text looks good.")
        
        return feedback


# Singleton instance
grammar_service = GrammarService()
