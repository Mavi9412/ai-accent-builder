import requests

# All test sentences from user
all_sentences = [
    # Basic
    "he go to gym",
    "i does my homework",
    "she dont like apple",
    "we is happy today",
    "they has a car",
    # Medium
    "my friend go school every day",
    "i cant able to come today",
    "this movie very good",
    "she want to crying",
    "i no understand what you say",
    # Advanced
    "because it was raining so we stayed home",
    "the boy which is running are my brother",
    "i have went to the market yesterday",
    "he speak english goodly",
    "i am agree with your opinion",
    # Bonus Hard
    "this book is interest but the character dont develop good",
    "he didn't knew that she was already leave the city",
    "the dog chase the cat and run fastly down the street",
    "if he will finish his work he can goes with us",
    "i am tired because i working whole night",
]

print("=" * 80)
print("COMPREHENSIVE GRAMMAR CHECKER TEST - ALL SENTENCES")
print("=" * 80)

passed = 0
failed = 0

for text in all_sentences:
    try:
        response = requests.post(
            "http://localhost:8000/api/grammar/check",
            json={"text": text},
            timeout=10
        )
        result = response.json()
        corrected = result.get("grammar", {}).get("corrected_text", text)
        errors = result.get("grammar", {}).get("total_errors", 0)
        grammar_errors = result.get("grammar", {}).get("grammar_errors", [])
        
        # Check if any correction was made
        is_corrected = corrected.lower().strip() != text.lower().strip()
        status = "PASS" if is_corrected else "FAIL"
        symbol = "✅" if is_corrected else "❌"
        
        if is_corrected:
            passed += 1
        else:
            failed += 1
        
        print(f"\n{symbol} [{status}]")
        print(f"   INPUT:     {text}")
        print(f"   CORRECTED: {corrected}")
        print(f"   ERRORS:    {errors}")
        if grammar_errors and len(grammar_errors) > 0:
            for err in grammar_errors[:2]:  # Show first 2 errors
                print(f"   - {err.get('message', '')[:60]}")
        
    except Exception as e:
        failed += 1
        print(f"\n❌ [ERROR] {text}")
        print(f"   Exception: {e}")

print("\n" + "=" * 80)
print(f"SUMMARY: {passed} passed, {failed} failed out of {len(all_sentences)} total")
print("=" * 80)
