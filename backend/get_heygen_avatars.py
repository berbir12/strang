"""
Quick script to list available HeyGen avatars and voices
Run this to find valid avatar/voice IDs for your account
"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

from services.heygen_service import HeyGenService


async def main():
    """List available avatars and voices"""
    
    if not os.getenv("HEYGEN_API_KEY"):
        print("ERROR: HEYGEN_API_KEY not found in .env file")
        print("Please add your HeyGen API key to backend/.env")
        return
    
    print("=" * 60)
    print("HeyGen Available Avatars & Voices")
    print("=" * 60)
    print()
    
    try:
        service = HeyGenService()
        
        # Get avatars
        print("Available Avatars:")
        print("-" * 60)
        avatars = await service.list_avatars()
        
        if not avatars:
            print("[ERROR] No avatars found. Check your HEYGEN_API_KEY.")
        else:
            for i, avatar in enumerate(avatars, 1):
                avatar_id = avatar.get("avatar_id", "N/A")
                avatar_name = avatar.get("avatar_name", "Unknown")
                print(f"{i}. {avatar_name}")
                print(f"   ID: {avatar_id}")
                if i == 1:
                    print(f"   [USE THIS] Add to .env: HEYGEN_AVATAR_ID={avatar_id}")
                print()
        
        # Get voices
        print("Available Voices:")
        print("-" * 60)
        voices = await service.list_voices()
        
        if not voices:
            print("[ERROR] No voices found.")
        else:
            for i, voice in enumerate(voices[:10], 1):  # Show first 10
                voice_id = voice.get("voice_id", "N/A")
                voice_name = voice.get("name", "Unknown")
                language = voice.get("language", "N/A")
                gender = voice.get("gender", "N/A")
                print(f"{i}. {voice_name} ({language}, {gender})")
                print(f"   ID: {voice_id}")
                if i == 1:
                    print(f"   [USE THIS] Add to .env: HEYGEN_VOICE_ID={voice_id}")
                print()
        
        print("=" * 60)
        print("[SUCCESS] To update your .env file:")
        print("   1. Open backend/.env")
        print("   2. Update HEYGEN_AVATAR_ID with one of the IDs above")
        print("   3. Update HEYGEN_VOICE_ID with one of the IDs above")
        print("=" * 60)
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        print()
        print("Make sure:")
        print("1. HEYGEN_API_KEY is set in backend/.env")
        print("2. Your HeyGen API key is valid")
        print("3. You have access to avatars in your HeyGen account")


if __name__ == "__main__":
    asyncio.run(main())
