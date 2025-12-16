"""
Test Gemini API with UPDATED MASTER PROMPT
Tests: sentence WITHOUT errors should still get vocab + accent tips
"""
import google.generativeai as genai

# Configure API
GEMINI_API_KEY = "AIzaSyCVirLvxF53dqT0Kvh_toLEzO29pgmdFUw"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')  # Updated model

# Test sentence WITHOUT errors (to test if vocab/tip still appear)
transcribed = "I hope you are doing very well today"
error_summary = "No significant errors detected"
topic = "greeting"
pronunciation_score = 95

# UPDATED MASTER PROMPT (ALWAYS provides vocabulary and tips)
prompt = f'''You are a friendly British English speaking tutor.

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

print("=" * 60)
print("INPUT SENTENCE:", transcribed)
print("ERRORS:", error_summary)
print("=" * 60)
print("\nSENDING TO GEMINI API...\n")

try:
    response = model.generate_content(prompt)
    print("=" * 60)
    print("GEMINI RESPONSE (ALL FIELDS SHOULD BE PRESENT):")
    print("=" * 60)
    print(response.text)
except Exception as e:
    print(f"ERROR: {e}")
