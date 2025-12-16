"""
Grammar Router - API endpoints for grammar and language checking
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/grammar", tags=["Grammar"])


class TextInput(BaseModel):
    text: str
    check_type: Optional[str] = "full"  # "full", "grammar", "correction", "nlp"


@router.post("/check")
async def check_grammar(input_data: TextInput):
    """
    Check grammar and get corrections for the input text.
    Uses LanguageTool, T5, and spaCy/NLTK.
    """
    try:
        from services.grammar_service import grammar_service
        
        text = input_data.text.strip()
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")
        
        check_type = input_data.check_type
        
        if check_type == "grammar":
            result = grammar_service.check_grammar(text)
        elif check_type == "correction":
            result = grammar_service.correct_with_t5(text)
        elif check_type == "nlp":
            result = grammar_service.analyze_with_nlp(text)
        else:
            # Full analysis
            result = grammar_service.full_analysis(text)
        
        return result
        
    except Exception as e:
        print(f"Grammar check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick-check")
async def quick_grammar_check(input_data: TextInput):
    """
    Quick grammar check - returns only essential errors and corrections.
    Optimized for real-time checking.
    """
    try:
        from services.grammar_service import grammar_service
        
        text = input_data.text.strip()
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")
        
        # Quick check with LanguageTool only
        grammar_result = grammar_service.check_grammar(text)
        
        # Simplify response for quick use
        return {
            "has_errors": grammar_result["total_errors"] > 0,
            "error_count": grammar_result["total_errors"],
            "corrected_text": grammar_result["corrected_text"],
            "score": grammar_result["score"],
            "errors": [
                {
                    "message": e["message"],
                    "replacements": e["replacements"][:3],
                    "type": e["type"]
                }
                for e in (
                    grammar_result["grammar_errors"] + 
                    grammar_result["spelling_errors"]
                )[:5]
            ]
        }
        
    except Exception as e:
        print(f"Quick check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alternatives")
async def get_word_alternatives(input_data: TextInput):
    """
    Get word alternatives and synonyms for the input text.
    Uses NLTK/WordNet.
    """
    try:
        from services.grammar_service import grammar_service
        
        text = input_data.text.strip()
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")
        
        nlp_result = grammar_service.analyze_with_nlp(text)
        
        return {
            "word_alternatives": nlp_result.get("word_alternatives", []),
            "word_count": nlp_result.get("word_count", 0)
        }
        
    except Exception as e:
        print(f"Alternatives error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
