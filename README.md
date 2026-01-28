# Strang – Hybrid AI Explainer Video Chrome Extension

🎬 **Transform any webpage text into professional explainer videos with AI**

Strang is a Chrome Extension that combines:
- **Claude AI** for intelligent script generation and scene planning
- **Manim** for beautiful animated slides (3Blue1Brown style)
- **Mochi AI** for photorealistic B-roll footage
- **Text-to-Speech** for natural voiceovers
- **Auto-compositing** with subtitles and smooth transitions

## 🎯 Features

✅ Highlight text → Right-click → Generate video  
✅ Multiple explanation styles (Simple, Academic, Child-friendly, Technical)  
✅ Hybrid rendering: Text slides (Manim) + Realistic visuals (Mochi)  
✅ AI-powered scene classification and timing  
✅ Professional voiceovers with TTS  
✅ SRT subtitle export  
✅ Dark mode support  
✅ Local fallback mode (works without backend)  

## 🏗️ Architecture

**Two Operation Modes:**

### Mode 1: Full Backend (Recommended)
```
Extension → Backend API → Claude → Scene Intelligence
                           ├─ Text Slides → Manim → .mp4
                           ├─ B-Roll → Mochi → .mp4
                           └─ TTS → Voiceover
                       → FFmpeg → Final Video + SRT
```

### Mode 2: Local Fallback
```
Extension → aiMock.js → Simple plan
         → videoRenderer.js → Canvas animation → WebM
```

## Project Structure

- `manifest.json` – MV3 manifest, background service worker, content script, permissions.
- `background.js` – Service worker:
  - Creates context menu (`Generate Explainer Video with Strang`).
  - Stores last text selection.
  - Exposes message handlers for:
    - `GET_LAST_SELECTION`
    - `REQUEST_ACTIVE_SELECTION`
    - `GENERATE_VIDEO_REQUEST`
  - Runs the mock AI pipeline (`aiMock.js`).
  - Broadcasts progress updates to the popup.
- `content.js` – Content script:
  - Tracks current text selection via `selectionchange`.
  - Responds to `GET_SELECTION` messages from the background.
- `popup.html` – Popup UI:
  - Editable text area.
  - Style selector (simple / academic / child-friendly / technical).
  - Video length selector (30 / 60 / 120 seconds).
  - Voice accent placeholder selector.
  - Dark mode toggle.
  - Generate button, loader, status text.
  - Video preview + playback speed.
  - Download buttons for `.webm` and `.srt`.
- `styles.css` – Minimal light/dark styling for the popup.
- `popup.js` – Popup logic:
  - Fetches last selection from background (or active selection from content script).
  - Sends `GENERATE_VIDEO_REQUEST` to background.
  - Receives `VIDEO_PROGRESS` events.
  - Calls `renderExplainerVideo` (`videoRenderer.js`) and shows preview.
  - Handles video + SRT downloads and dark mode.
- `aiMock.js` – Mock AI pipeline:
  - Step 1: builds `teachingScript`, `bulletBreakdown`, `keyConcepts`.
  - Step 2: generates `scenes` with timings and animation directives.
  - Step 3: builds a `voiceoverScript`.
- `videoRenderer.js` – Front-end video composer:
  - Uses `canvas` + `MediaRecorder` to output WebM.
  - Renders scenes with simple animations and subtitles.
  - Returns `{ blob, url, srt, timings }`.

## 🚀 Quick Start

### Option A: Local Mode Only (No Backend)

Perfect for testing the extension UI without deploying a backend.

1. **Load Extension**
   ```bash
   # Open Chrome → chrome://extensions/
   # Enable "Developer mode"
   # Click "Load unpacked" → Select this folder
   ```

2. **Configure Local Mode**
   - Edit `background.js`:
     ```javascript
     const USE_BACKEND = false;  // Line 18
     ```

3. **Test It**
   - Highlight text on any page
   - Right-click → "Generate Explainer Video with Strang"
   - Get a basic canvas-rendered video

### Option B: Full Backend (Recommended)

For production-quality videos with Claude + Manim + Mochi.

1. **Setup Backend** (see `backend/README.md`)
   ```bash
   cd backend
   pip install -r requirements.txt
   # Configure .env with API keys
   python main.py
   ```

2. **Load Extension**
   ```bash
   # Open Chrome → chrome://extensions/
   # Enable "Developer mode"
   # Click "Load unpacked" → Select project root folder
   ```

3. **Configure Backend Mode**
   - Edit `background.js`:
     ```javascript
     const BACKEND_URL = 'http://localhost:8000';  // Line 17
     const USE_BACKEND = true;  // Line 18
     ```

4. **Test It**
   - Highlight text on any page
   - Right-click → "Generate Explainer Video with Strang"
   - Wait for backend processing (progress updates in popup)
   - Get professional video with slides + B-roll + voiceover

---

## 📖 Detailed Setup

### Extension Installation

1. Clone repository:
   ```bash
   git clone <your-repo>
   cd strang
   ```

2. Load in Chrome:
   - Navigate to `chrome://extensions/`
   - Enable **Developer mode** (top-right)
   - Click **Load unpacked**
   - Select the `strang` folder (root, not `backend`)

3. Pin extension to toolbar

### Backend Installation

See detailed guide: **[backend/README.md](backend/README.md)**

**Quick version:**
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp env.example .env
# Edit .env and add ANTHROPIC_API_KEY

# Run server
python main.py
```

**Requirements:**
- Python 3.9+
- FFmpeg
- Anthropic API key (Claude)
- Optional: GPU for Mochi (60GB VRAM)

---

## 🎯 Usage Guide

### Basic Flow

1. **Select Text**
   - Highlight any text on a webpage
   - Right-click → **"Generate Explainer Video with Strang"**
   - OR click extension icon → **"Use current page selection"**

2. **Configure Settings**
   - **Explanation Style**: Simple / Academic / Child-friendly / Technical
   - **Video Length**: 30s / 60s / 120s
   - **Voice Accent**: US / UK / AU / Neutral

3. **Generate**
   - Click **"Generate explainer video"**
   - Watch progress updates
   - Wait for completion (30s-2min depending on mode)

4. **Preview & Download**
   - Play video in popup
   - Adjust playback speed
   - Download:
     - **Video** (.mp4 or .webm)
     - **Subtitles** (.srt)

### Dark Mode

Toggle dark mode in popup for comfortable viewing.

---

## 📁 Project Structure

```
strang/
├── manifest.json          # Chrome MV3 manifest
├── background.js          # Service worker (API calls, context menu)
├── content.js            # Selection tracking
├── popup.html            # UI layout
├── popup.js              # UI logic + backend polling
├── styles.css            # Dark/light theme
├── aiMock.js             # Local fallback pipeline
├── videoRenderer.js      # Local canvas renderer
├── README.md             # This file
└── backend/              # Python FastAPI backend
    ├── main.py           # API server
    ├── config.py         # Configuration
    ├── models.py         # Pydantic models
    ├── requirements.txt  # Python dependencies
    ├── services/
    │   ├── claude_service.py      # Claude integration
    │   ├── manim_generator.py     # Manim slides
    │   ├── mochi_service.py       # Mochi B-roll
    │   ├── tts_service.py         # Text-to-speech
    │   └── compositor.py          # FFmpeg video assembly
    ├── utils/
    │   └── job_manager.py         # Async job queue
    └── README.md                  # Backend setup guide
```

---

## 🔧 Configuration

### Extension Config (`background.js`)

```javascript
const BACKEND_URL = 'http://localhost:8000';  // Your backend URL
const USE_BACKEND = true;  // true = backend mode, false = local mock
```

### Backend Config (`backend/.env`)

```bash
ANTHROPIC_API_KEY=sk-ant-xxxxx       # Required: Claude API
OPENAI_API_KEY=sk-xxxxx              # Optional: TTS
MOCHI_ENABLED=true                   # Requires GPU
TTS_PROVIDER=openai                  # openai / elevenlabs / none
```

See `backend/env.example` for all options.

---

## 💰 Cost Estimates

**Per 60-second video with full backend:**

| Component | Cost |
|-----------|------|
| Claude API (script generation) | $0.02 |
| OpenAI TTS (voiceover) | $0.10 |
| Mochi (GPU rental 2min) | $0.05 |
| **Total** | **~$0.17** |

**Without Mochi (CPU-only):** ~$0.12/video

**Local mode:** Free (but lower quality)

---

## 🐛 Troubleshooting

### Extension Issues

**"No text selected"**
- Ensure text is highlighted
- Try refreshing the page
- Check content script loaded (inspect console)

**"Failed to connect to backend"**
- Verify backend is running: `curl http://localhost:8000`
- Check `BACKEND_URL` in `background.js`
- Check CORS settings in `backend/main.py`

### Backend Issues

**"ANTHROPIC_API_KEY not configured"**
- Copy `backend/env.example` to `backend/.env`
- Add your Claude API key

**"Mochi generation failed"**
- Check GPU available: `nvidia-smi`
- Or disable Mochi: `MOCHI_ENABLED=false` in `.env`

**"Manim rendering failed"**
- Install LaTeX (optional but helps)
- Fallback PIL renderer will be used automatically

See detailed troubleshooting: **[backend/README.md](backend/README.md)**

---

## 🚢 Deployment

### Extension
- Load unpacked in Chrome (development)
- Or publish to Chrome Web Store (production)

### Backend

**Options:**
1. **GPU Cloud** (for Mochi):
   - RunPod: $1.50/hr H100
   - Lambda Labs: $1.99/hr A100
   
2. **CPU VPS** (without Mochi):
   - DigitalOcean: $24/mo (4 vCPU)
   - Railway / Render: Easy deploys

3. **Docker**:
   ```bash
   cd backend
   docker build -t strang-backend .
   docker run -p 8000:8000 --env-file .env strang-backend
   ```

See deployment guide: **[backend/README.md](backend/README.md)**

---

## 📊 Performance

**Local Mode:**
- Generation time: 5-10 seconds
- Video quality: Basic canvas animations
- Cost: Free

**Backend Mode (CPU-only):**
- Generation time: 30-60 seconds
- Video quality: Professional Manim slides
- Cost: ~$0.12/video

**Backend Mode (Full with Mochi):**
- Generation time: 60-120 seconds
- Video quality: Hybrid slides + photorealistic B-roll
- Cost: ~$0.17/video

---

## 🛠️ Tech Stack

**Extension:**
- Manifest V3
- Vanilla JavaScript (ES6+)
- Chrome APIs (storage, tabs, contextMenus)
- Canvas API + MediaRecorder

**Backend:**
- FastAPI (Python)
- Claude Sonnet 4 (Anthropic)
- Manim (3Blue1Brown animation engine)
- Mochi AI (Genmo video generation)
- FFmpeg (video compositing)
- OpenAI TTS / ElevenLabs (voiceover)

---

## 📝 Notes

- Text limit: 3000 characters (configurable)
- Supported video formats: MP4 (backend), WebM (local)
- Subtitle format: SRT (SubRip)
- Browser support: Chrome/Edge (Manifest V3)

---

## 📜 License

MIT License - see LICENSE file

---

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Additional TTS providers
- More animation styles in Manim
- Video quality optimizations
- UI/UX enhancements

---

## 🎓 Learn More

- **Manim**: [3b1b/manim](https://github.com/3b1b/manim)
- **Mochi**: [genmoai/mochi](https://github.com/genmoai/mochi)
- **Claude API**: [docs.anthropic.com](https://docs.anthropic.com)

---

**Built with ❤️ for educators, creators, and knowledge sharers**

# DR.strang
