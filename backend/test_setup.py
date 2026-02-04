"""
Quick test script to verify Strang v3.0 setup
Run this to check if everything is configured correctly
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

def test_environment():
    """Test if environment variables are set correctly"""
    print("=" * 60)
    print("Testing Strang v3.0 Configuration")
    print("=" * 60)
    print()
    
    issues = []
    
    # Check Groq API key
    groq_key = os.getenv("GROQ_API_KEY", "")
    if groq_key and groq_key != "your_groq_api_key_here":
        print("[OK] GROQ_API_KEY: Configured")
    else:
        print("[FAIL] GROQ_API_KEY: NOT configured")
        issues.append("Get your FREE Groq key: https://console.groq.com/keys")
    
    # Check HeyGen API key
    heygen_key = os.getenv("HEYGEN_API_KEY", "")
    if heygen_key and heygen_key != "your_heygen_api_key_here":
        print("[OK] HEYGEN_API_KEY: Configured")
    else:
        print("[FAIL] HEYGEN_API_KEY: NOT configured")
        issues.append("Get your HeyGen key: https://app.heygen.com/settings/api")
    
    print()
    
    # Check dependencies
    print("Checking dependencies...")
    try:
        import groq
        print("[OK] groq: Installed")
    except ImportError:
        print("[FAIL] groq: NOT installed")
        issues.append("Run: pip install -r requirements.txt")
    
    try:
        import fastapi
        print("[OK] fastapi: Installed")
    except ImportError:
        print("[FAIL] fastapi: NOT installed")
        issues.append("Run: pip install -r requirements.txt")
    
    try:
        import httpx
        print("[OK] httpx: Installed")
    except ImportError:
        print("[FAIL] httpx: NOT installed")
        issues.append("Run: pip install -r requirements.txt")
    
    print()
    
    # Test Groq connection
    if groq_key and groq_key != "your_groq_api_key_here":
        print("Testing Groq API connection...")
        try:
            from groq import Groq
            client = Groq(api_key=groq_key)
            
            # Quick test
            response = client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": "Say 'Hello from Groq!' in exactly those words."
                    }
                ],
                model="llama-3.3-70b-versatile",
                max_tokens=10
            )
            
            result = response.choices[0].message.content
            print(f"[OK] Groq API: Working! Response: '{result}'")
        except Exception as e:
            print(f"[FAIL] Groq API: Error - {e}")
            issues.append("Check your GROQ_API_KEY is valid")
    
    print()
    print("=" * 60)
    
    # Summary
    if not issues:
        print("SUCCESS! Your setup is ready!")
        print()
        print("Next steps:")
        print("1. Run: python main.py")
        print("2. Open: http://localhost:8000")
        print("3. Test the API endpoints")
    else:
        print("Issues found. Please fix:")
        print()
        for i, issue in enumerate(issues, 1):
            print(f"{i}. {issue}")
    
    print("=" * 60)


if __name__ == "__main__":
    test_environment()
