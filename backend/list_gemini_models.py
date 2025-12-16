"""
List available Gemini models for this API key
"""
import google.generativeai as genai

# Configure API
GEMINI_API_KEY = "AIzaSyAfHfWYjq1l2MDUJg23_EKBb_F0V9Ga8mU"
genai.configure(api_key=GEMINI_API_KEY)

print("=" * 60)
print("AVAILABLE GEMINI MODELS:")
print("=" * 60)

for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f"  - {m.name}")
