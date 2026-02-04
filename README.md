# Strang – AI Avatar Video Generator

🎬 **Transform any text into professional AI avatar videos with HuggingFace + HeyGen**

Strang is a Chrome Extension that turns selected text into engaging avatar videos using:
- **HuggingFace Inference API** for intelligent script generation (Mistral-7B-Instruct-v0.2)
- **HeyGen** for photorealistic AI avatar video rendering

## ✨ Features

✅ Select text on any webpage → Generate avatar video  
✅ HuggingFace transforms your content into natural, engaging scripts  
✅ HeyGen renders professional AI avatar presentations  
✅ Real-time progress updates via WebSocket  
✅ Dark mode support  
✅ Simple, clean interface  

## 🏗️ Architecture

```
Chrome Extension → FastAPI Backend → HuggingFace → Script
                                   → HeyGen → Avatar Video
                                   
WebSocket provides real-time progress updates
```

### How It Works

1. **User selects text** on any webpage
2. **Extension captures** the selection
3. **HuggingFace** transforms text into a professional script with natural pauses
4. **HeyGen** renders an AI avatar speaking the script
5. **Video is delivered** for preview and download

## 🚀 Quick Start

### 1. Get API Keys

- **HuggingFace**: Get your API token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) (free tier available!)
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
# HF_API_KEY=your_huggingface_token
# HEYGEN_API_KEY=your_heygen_key

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
    │   ├── huggingface_service.py  # HuggingFace integration
    │   └── heygen_service.py       # HeyGen integration
    └── utils/
        └── job_manager.py     # Async job queue
```

## 🔧 Configuration

### Backend (.env)

```bash
# Required
HF_API_KEY=your_huggingface_token
HEYGEN_API_KEY=your_heygen_api_key

# HuggingFace Settings
HF_MODEL=mistralai/Mistral-7B-Instruct-v0.2

# HeyGen Settings  
HEYGEN_AVATAR_ID=Angela-inblackskirt-20220820
HEYGEN_VOICE_ID=1bd001e7e50f421d891986aad5158bc8

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
  "fast_scripting": true
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
| HuggingFace Inference API | **FREE** (free tier available!) |
| HeyGen | ~$0.10-0.50 (depends on plan) |
| **Total** | **~$0.10-0.50** |

**Note:** HuggingFace free tier may have rate limits and cold start delays. For production use, consider upgrading or using serverless inference endpoints.

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

**Backend:**
- FastAPI (Python)
- huggingface-hub (HuggingFace Inference API)
- httpx (async HTTP)
- WebSockets

**AI Services:**
- HuggingFace Inference API (Mistral-7B-Instruct-v0.2) - Script generation
- HeyGen - Avatar video rendering

## ⚡ Why HuggingFace Inference API?

- **Free tier** - No hosting costs with free API quota
- **Official models** - Access to high-quality open-source models
- **No setup** - Direct API calls, no infrastructure needed
- **Flexible** - Easy to switch between different models

## 🐛 Troubleshooting

### "HF_API_KEY not configured"
- Copy `backend/env.example` to `backend/.env`
- Add your HuggingFace API token from [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

### "HEYGEN_API_KEY not configured"  
- Add your HeyGen API key to `.env`

### "Failed to connect to backend"
- Ensure backend is running: `python main.py`
- Check URL in `background.js`

### "Model is loading" or cold start delays
- HuggingFace Inference API may have cold starts (10-30 seconds)
- The service automatically retries with backoff
- Consider using popular models that are kept warm

### Script generation is slow
- Free tier models may be slower than paid services
- Try switching to a lighter model in `.env` (e.g., `google/flan-t5-xxl`)
- Rate limits may apply - wait a bit between requests

### Video takes too long
- HeyGen rendering typically takes 1-5 minutes
- Progress updates appear in real-time

## 📜 License

MIT License - See LICENSE file

---

**Built with ❤️ using HuggingFace + HeyGen**
