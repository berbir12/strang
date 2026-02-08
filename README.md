# Strang – AI Avatar Video Generator

🎬 **Transform any text into professional AI avatar videos with Groq (FREE) + HeyGen**

Strang is a Chrome Extension that turns selected text into engaging avatar videos using:
- **Groq AI API** for intelligent script generation (100% FREE, 10-50x faster than alternatives)
- **HeyGen** for photorealistic AI avatar video rendering

## ✨ Features

✅ Select text on any webpage → Generate avatar video  
✅ Groq AI transforms your content into natural, engaging scripts (2-5 seconds!)  
✅ HeyGen renders professional AI avatar presentations  
✅ Real-time progress updates via WebSocket  
✅ Auto-selects first available avatar (no configuration needed)  
✅ Dark mode support  
✅ Simple, clean interface  
✅ No timeout limits - videos can take as long as needed

## 🏗️ Architecture

```
Chrome Extension → FastAPI Backend → Groq AI → Script (2-5s)
                                   → HeyGen → Avatar Video (2-5min)
                                   
WebSocket provides real-time progress updates
```

### How It Works

1. **User selects text** on any webpage
2. **Extension captures** the selection
3. **Groq AI** transforms text into a professional script (FREE, instant, high-quality)
4. **HeyGen** renders an AI avatar speaking the script
5. **Video is delivered** for preview and download

## 🚀 Quick Start

### 1. Get API Keys

- **Groq (FREE)**: Get your API key at [console.groq.com/keys](https://console.groq.com/keys) (100% free, no credit card!)
- **HeyGen**: Get your API key at [app.heygen.com/settings/api](https://app.heygen.com/settings/api)

### 2. Setup Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt

# Configure environment
cp env.example .env
# Edit .env and add your API keys:
# GROQ_API_KEY=gsk_your_groq_key_here
# HEYGEN_API_KEY=your_heygen_key_here

# Run server
python main.py
```

Server runs at `http://localhost:8000`

### 3. Load Chrome Extension

1. Open Chrome → `chrome://extensions/`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked**
4. Select this project folder

### 4. Use It!

1. **Highlight text** on any webpage
2. **Right-click** → "Generate Avatar Video with Strang"  
   OR click the extension icon
3. Click **"Generate Avatar Video"**
4. Watch real-time progress
5. Preview and download your video!

## 📁 Project Structure

```
strang/
├── manifest.json          # Chrome MV3 manifest
├── background.js          # Service worker (API, WebSocket)
├── content.js             # Text selection capture
├── popup.html             # Extension UI
├── popup.js               # UI logic
├── styles.css             # Styling
│
└── backend/               # FastAPI server
    ├── main.py            # API endpoints
    ├── config.py          # Configuration
    ├── models.py          # Pydantic models
    ├── requirements.txt   # Python dependencies
    ├── services/
    │   ├── groq_service.py      # Groq AI integration (FREE!)
    │   └── heygen_service.py    # HeyGen integration
    └── utils/
        └── job_manager.py     # Async job queue
```

## 🔧 Configuration

### Backend (.env)

```bash
# Required
GROQ_API_KEY=gsk_your_groq_key_here
HEYGEN_API_KEY=your_heygen_api_key

# Groq Settings (optional - defaults work great)
GROQ_MODEL=llama-3.3-70b-versatile  # Best quality, still FREE
GROQ_MAX_TOKENS=1024
GROQ_TEMPERATURE=0.7

# HeyGen Settings (optional - auto-selects if not set)
HEYGEN_AVATAR_ID=  # Leave empty to auto-select first available
HEYGEN_VOICE_ID=1bd001e7e50f421d891986aad5158bc8

# Video Settings
DEFAULT_VIDEO_WIDTH=1280   # 720p (free tier compatible)
DEFAULT_VIDEO_HEIGHT=720

# Server
HOST=0.0.0.0
PORT=8000
```

### Extension (background.js)

```javascript
const BACKEND_URL = 'http://localhost:8000';
const BACKEND_WS_URL = 'ws://localhost:8000';
```

## 📡 API Endpoints

### Generate Video
```http
POST /api/process-video
Content-Type: application/json

{
  "text": "Your content here...",
  "style": "professional",
  "avatar_id": "optional_avatar_id",
  "voice_id": "optional_voice_id"
}
```

### Generate Script Only
```http
POST /api/generate-script
Content-Type: application/json

{
  "text": "Your content here...",
  "style": "professional",
  "duration_hint": 60
}
```

### Check Progress
```http
GET /job/{job_id}/progress
```

### Get Result
```http
GET /job/{job_id}/result
```

### WebSocket Updates
```
ws://localhost:8000/ws/job/{job_id}
```

### List Avatars/Voices
```http
GET /api/avatars
GET /api/voices
```

## 💰 Cost Estimates

| Service | Cost per Video |
|---------|----------------|
| Groq AI | **100% FREE** ✨ (generous limits) |
| HeyGen | ~$0.10-0.50 per minute |
| **Total** | **~$0.10-0.50** |

**Note:** Groq is completely free with generous rate limits. You only pay for HeyGen video generation!

## 🎨 Script Styles

- **Professional**: Business-ready, clear and authoritative
- **Casual**: Conversational, relaxed tone
- **Educational**: Structured for learning, clear explanations
- **Friendly**: Warm, approachable, personable

## 🛠️ Tech Stack

**Extension:**
- Chrome Manifest V3
- Vanilla JavaScript
- Chrome Storage API
- WebSocket for real-time updates

**Backend:**
- FastAPI (Python)
- Groq API (FREE AI script generation)
- httpx (async HTTP for HeyGen)
- WebSockets

**AI Services:**
- Groq API (Llama 3.3 70B) - Script generation (FREE, 2-5 seconds)
- HeyGen - Avatar video rendering (2-5 minutes)

## ⚡ Why Groq API?

- **100% FREE** - No credit card required, generous free tier
- **BLAZINGLY FAST** - 10-50x faster than HuggingFace (2-5 seconds vs 15-30 seconds)
- **HIGH QUALITY** - Access to Llama 3.3 70B, one of the best open models
- **NO COLD STARTS** - Instant responses, always ready
- **HIGHLY RELIABLE** - Professional infrastructure, 99.9% uptime
- **GENEROUS LIMITS** - Thousands of requests per day on free tier

## 🐛 Troubleshooting

### "GROQ_API_KEY not configured"
- Copy `backend/env.example` to `backend/.env`
- Add your Groq API key from [console.groq.com/keys](https://console.groq.com/keys)
- It's 100% free - just sign up!

### "HEYGEN_API_KEY not configured"  
- Add your HeyGen API key to `.env`
- Get it from [app.heygen.com/settings/api](https://app.heygen.com/settings/api)

### "Failed to connect to backend"
- Ensure backend is running: `python main.py`
- Check URL in `background.js`
- Verify server is accessible: `curl http://localhost:8000`

### Groq rate limit errors
- Groq free tier has generous limits (thousands per day)
- Wait a few seconds if you hit the limit
- Limits reset quickly (per minute, not per day)

### "Avatar not found" errors
- System auto-selects first available avatar
- Or use `/api/avatars` endpoint to see available avatars
- Update `HEYGEN_AVATAR_ID` in `.env` with a valid ID

### Video takes too long
- HeyGen rendering typically takes 2-5 minutes
- Progress updates appear in real-time via WebSocket
- No timeout - videos can take as long as needed

### Script generation is slow
- Groq is extremely fast (2-5 seconds)
- If slow, check your internet connection
- Verify Groq API key is correct

## 📊 Performance

**Script Generation:**
- Groq: **2-5 seconds** ⚡ (10-50x faster than alternatives)

**Total Pipeline:**
- Script: 2-5 seconds (Groq)
- Video: 2-5 minutes (HeyGen)
- **Total: ~2-5 minutes** (much faster than old setup!)

## 📚 Documentation

- **Backend README**: `backend/README.md` - Complete backend documentation
- **Setup Guide**: `backend/SETUP_GUIDE.md` - Quick setup instructions
- **Migration Guide**: `backend/MIGRATION_SUMMARY.md` - Technical changes
- **Roadmap**: `ROADMAP.md` - Future development plans

## 📜 License

MIT License - See LICENSE file

---

**Built with ❤️ using Groq (FREE) + HeyGen**

**Version:** 3.0.0  
**Status:** ✅ Production Ready
