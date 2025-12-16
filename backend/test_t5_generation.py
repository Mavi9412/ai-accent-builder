import time
import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.followup_generation_service import FollowUpGenerationService, T5_AVAILABLE, ONNX_AVAILABLE

def test_t5_generation():
    print("\n=== Testing T5-Small Generation ===")
    
    # Initialize service (forces model load)
    start_load = time.time()
    service = FollowUpGenerationService(use_t5=True, t5_model_name="google/flan-t5-base")
    
    # Force initialization
    service._init_t5()
    
    load_time = time.time() - start_load
    print(f"Model Load Time: {load_time:.2f}s")
    
    if not service.t5_model:
        print("❌ Failed to load T5 model")
        return
        
    loading_method = "ONNX" if ONNX_AVAILABLE and "ORModel" in str(type(service.t5_model)) else "PyTorch"
    print(f"✅ Model Loaded via: {loading_method}")
    print(f"Model Type: {type(service.t5_model)}")
    
    start_gen = time.time()
    result = service._generate_llm_context_followup({
        'transcribed_text': 'I go to store yesterday',
        'overall_score': 65,
        'word_analyses': [
            {'word': 'store', 'score': 40, 'expected_phonemes': 'S T AO R', 'actual_phonemes': 'S T O', 'is_correct': False}
        ]
    })
    gen_time = time.time() - start_gen
    
    if result:
        import json
        print(f"Generated Question (Enhanced):\n{json.dumps(result, indent=2)}")
        print(f"Generation Time: {gen_time:.2f}s")
    else:
        print("❌ Generation returned None")

    # Test Rephrasing
    print("\n--- Rephrasing Test ---")
    text = "Please say the word again correctly."
    start_rephrase = time.time()
    rephrased = service._rephrase_with_t5(text)
    rephrase_time = time.time() - start_rephrase
    
    print(f"Original: {text}")
    print(f"Rephrased: {rephrased}")
    print(f"Time: {rephrase_time:.2f}s")

if __name__ == "__main__":
    test_t5_generation()
