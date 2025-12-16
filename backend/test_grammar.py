import requests
import json

# All test sentences
test_cases = [
    # Basic
    ("he go to gym", "He goes to the gym"),
    ("i does my homework", "I do my homework"),
    ("she dont like apple", "She doesn't like apple"),
    ("we is happy today", "We are happy today"),
    ("they has a car", "They have a car"),
    # Medium
    ("my friend go school every day", "My friend goes to school every day"),
    ("i cant able to come today", "I can't come today"),
    ("she want to crying", "She wants to cry"),
    ("i no understand what you say", "I don't understand what you say"),
    # Advanced
    ("he speak english goodly", "He speaks English well"),
    ("i have went to the market yesterday", "I went to the market yesterday"),
    ("i am agree with your opinion", "I agree with your opinion"),
    # Bonus Hard
    ("the boy which is running are my brother", "The boy who is running is my brother"),
    ("he didn't knew that she was already leave", "He didn't know..."),
]

print("=" * 80)
print("GRAMMAR CHECKER TEST RESULTS")
print("=" * 80)

passed = 0
failed = 0

for text, expected in test_cases:
    try:
        response = requests.post(
            "http://localhost:8000/api/grammar/check",
            json={"text": text},
            timeout=10
        )
        result = response.json()
        corrected = result.get("grammar", {}).get("corrected_text", text)
        errors = result.get("grammar", {}).get("total_errors", 0)
        
        # Check if any correction was made
        is_corrected = corrected.lower().strip() != text.lower().strip()
        status = "PASS" if is_corrected else "FAIL"
        symbol = "✅" if is_corrected else "❌"
        
        if is_corrected:
            passed += 1
        else:
            failed += 1
        
        print(f"\n{symbol} [{status}] {text}")
        print(f"   → Corrected: {corrected}")
        print(f"   → Expected:  {expected}")
        print(f"   → Errors detected: {errors}")
        
    except Exception as e:
        failed += 1
        print(f"\n❌ [ERROR] {text}")
        print(f"   → Exception: {e}")

print("\n" + "=" * 80)
print(f"SUMMARY: {passed} passed, {failed} failed out of {len(test_cases)} tests")
print("=" * 80)
