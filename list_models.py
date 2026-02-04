"""List available Google Generative AI models"""
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv("backend/.env")

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("ERROR: GOOGLE_API_KEY not found in backend/.env")
    exit(1)

genai.configure(api_key=api_key)

print("=" * 60)
print("Available Google Generative AI Models:")
print("=" * 60)

for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f"\n✓ {m.name}")
        print(f"  Display Name: {m.display_name}")
        print(f"  Methods: {', '.join(m.supported_generation_methods)}")
