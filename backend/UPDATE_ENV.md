# ⚠️ Update Your .env File

Your `.env` file needs to be updated for the new Groq-based system.

## Quick Fix

Open your `backend/.env` file and add this line at the top:

```env
# NEW: Groq API key (FREE - get from https://console.groq.com/keys)
GROQ_API_KEY=your_groq_key_here
```

## Steps:

1. **Get your FREE Groq API key:**
   - Go to: https://console.groq.com/keys
   - Sign up (free, no credit card!)
   - Click "Create API Key"
   - Copy your key (starts with `gsk_`)

2. **Add to your `.env` file:**
   - Open: `backend/.env`
   - Add this line at the top:
     ```env
     GROQ_API_KEY=gsk_your_actual_key_here
     ```

3. **Optional: Clean up old keys**
   You can remove these old lines (but it's not required):
   ```env
   HF_API_KEY=...
   HF_MODEL=...
   HF_FAST_MODEL=...
   HF_TIMEOUT_SECONDS=...
   HF_MAX_NEW_TOKENS=...
   ```

## Your .env should look like this:

```env
# NEW: Groq API (required)
GROQ_API_KEY=gsk_your_actual_key_here

# HeyGen (keep this)
HEYGEN_API_KEY=your_heygen_key_here

# Optional settings (defaults work fine)
HEYGEN_AVATAR_ID=Angela-inblackskirt-20220820
HEYGEN_VOICE_ID=1bd001e7e50f421d891986aad5158bc8

# Server settings
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Everything else can stay or be removed - the config now ignores old keys
```

## After updating:

```bash
python main.py
```

Should work! 🚀
