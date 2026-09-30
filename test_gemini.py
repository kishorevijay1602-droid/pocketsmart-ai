import os
from google import genai

API_KEY = os.getenv("GEMINI_API_KEY")

print("API key found:", bool(API_KEY))

if not API_KEY:
    raise ValueError("GEMINI_API_KEY is not set.")

client = genai.Client(api_key=API_KEY)

print("Testing Gemini API...")

try:
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents="Say hello in one short sentence."
    )

    print("\nGemini response:")
    print(response.text)

except Exception as e:
    print("\nGemini ERROR:")
    print(type(e).__name__)
    print(str(e))