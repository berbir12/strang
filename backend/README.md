# Strang Backend - Hybrid Video Generation API

**Hybrid Manim + Mochi explainer video generation powered by Google Gemma 2.**

This backend service intelligently combines:
- **Gemma 2** (via Google Generative Language API) for script generation and scene classification
- **Manim** for text-heavy animated slides
- **Mochi** for photorealistic B-roll footage
- **FFmpeg** for video compositing
- **OpenAI TTS / ElevenLabs** for voiceover

---

## Architecture

```
Extension → POST /generate-video → Gemma 2 → Scene Classification
                                      ├─ "slide" → Manim → .mp4
                                      └─ "visual" → Mochi → .mp4
                                  → FFmpeg → Final video + SRT
```

---

## Requirements

### Minimum (Without Mochi)
- **CPU**: 4+ cores
- **RAM**: 8GB
- **Storage**: 10GB
- **Python**: 3.9+
- **FFmpeg**: Latest
- **LaTeX**: (for Manim formulas)

### Full Stack (With Mochi)
- **GPU**: NVIDIA H100 / A100 80GB (or multi-GPU setup)
- **VRAM**: 60GB+ (Mochi requirement)
- **RAM**: 32GB+
- **Storage**: 50GB+ (model weights ~10GB)

---

## Installation

### 1. Clone & Setup

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Install Manim

```bash
pip install manimgl

# Install LaTeX (optional but recommended)
# Windows: Download MiKTeX - https://miktex.org/download
# Linux: sudo apt install texlive-full
# Mac: brew install mactex
```

### 3. Install Mochi (Optional - Requires GPU)

```bash
cd ..
git clone https://github.com/genmoai/mochi
cd mochi

# Install Mochi dependencies
pip install uv
uv venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv pip install -e . --no-build-isolation

# Download weights (~10GB)
python3 ./scripts/download_weights.py ../backend/weights/
```

If you don't have a GPU, set `MOCHI_ENABLED=false` in your `.env` (placeholder videos will be used).

### 4. Configure Environment

```bash
cd backend
cp env.example .env
```

Edit `.env` and add your API keys:

```bash
GOOGLE_API_KEY=AIza-your-google-api-key-here
OPENAI_API_KEY=sk-your-openai-key  # For TTS
MOCHI_ENABLED=true  # Set false if no GPU
GEMMA_MODEL=gemma-2-9b-it
```

### 5. Install FFmpeg

**Windows:**
```bash
# Download from https://ffmpeg.org/download.html
# Or use chocolatey:
choco install ffmpeg
```

**Linux:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Mac:**
```bash
brew install ffmpeg
```

---

## Running the Server

### Development

```bash
cd backend
python main.py
```

Server runs at `http://localhost:8000`

### Production (with Gunicorn)

```bash
pip install gunicorn

gunicorn main:app \
  --workers 2 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 600
```

---

## API Endpoints

### 1. Generate Video

```http
POST /generate-video
Content-Type: application/json

{
  "text": "Explain quantum entanglement...",
  "style": "simple",
  "duration": 60,
  "voice_accent": "us",
  "include_mochi": true
}
```

**Response:**
```json
{
  "job_id": "uuid-here",
  "status": "queued",
  "message": "Video generation started...",
  "estimated_time_seconds": 90
}
```

### 2. Poll Progress

```http
GET /job/{job_id}/progress
```

**Response:**
```json
{
  "job_id": "...",
  "status": "rendering_slides",
  "progress_percent": 45,
  "current_step": "rendering_slides",
  "message": "Rendering slide 3/5: Key Concepts"
}
```

### 3. Get Result

```http
GET /job/{job_id}/result
```

**Response:**
```json
{
  "job_id": "...",
  "status": "completed",
  "video_url": "/outputs/uuid.mp4",
  "srt_content": "1\n00:00:00,000 --> 00:00:05,000\n...",
  "thumbnail_url": "/outputs/uuid_thumb.jpg",
  "duration": 60.0,
  "metadata": {
    "style": "simple",
    "num_scenes": 5,
    "scenes": [...]
  }
}
```

### 4. Download Files

```http
GET /job/{job_id}/video   # Download .mp4
GET /job/{job_id}/srt     # Download .srt
```

---

## Configuration

All settings are in `config.py` and can be overridden via environment variables.

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | - | **Required**: Claude API key |
| `OPENAI_API_KEY` | - | For OpenAI TTS |
| `MOCHI_ENABLED` | true | Enable/disable Mochi (GPU required) |
| `MOCHI_WEIGHTS_PATH` | ./weights | Path to Mochi model weights |
| `TTS_PROVIDER` | openai | `openai`, `elevenlabs`, or `none` |
| `DEFAULT_VIDEO_WIDTH` | 1280 | Output video width |
| `DEFAULT_VIDEO_HEIGHT` | 720 | Output video height |
| `MAX_TEXT_LENGTH` | 3000 | Max input characters |

---

## Deployment

### Option 1: GPU Cloud (Recommended for Full Stack)

**Providers:**
- **RunPod**: $1.50/hr for H100 80GB
- **Lambda Labs**: $1.99/hr for A100 80GB
- **Vast.ai**: Variable pricing

**Setup:**
```bash
# SSH into GPU instance
git clone <your-repo>
cd backend

# Follow installation steps above
python main.py
```

Expose port 8000 via reverse proxy (nginx + HTTPS).

### Option 2: CPU-Only (Without Mochi)

If you don't need Mochi's photorealistic B-roll:

```bash
# In .env
MOCHI_ENABLED=false
TTS_PROVIDER=none  # Optional: disable TTS too
```

Deploy on any VPS:
- **DigitalOcean**: $24/mo (4 vCPU, 8GB RAM)
- **Linode**: Similar pricing
- **Railway / Render**: Easy deployment

### Option 3: Docker

```dockerfile
# Dockerfile (example)
FROM python:3.10

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

RUN apt-get update && apt-get install -y ffmpeg

COPY . .

CMD ["python", "main.py"]
```

Build & run:
```bash
docker build -t strang-backend .
docker run -p 8000:8000 --env-file .env strang-backend
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'genmo'"

Mochi isn't installed or not in PATH. Either:
1. Install Mochi (see Installation step 3)
2. Set `MOCHI_ENABLED=false` in `.env`

### "Manim rendering failed"

- Ensure `manimgl` is installed: `pip install manimgl`
- Check LaTeX is installed (optional but helps)
- Fallback renderer will be used automatically

### "Backend error: 500"

Check logs:
```bash
python main.py
```

Common issues:
- Missing `ANTHROPIC_API_KEY`
- FFmpeg not installed
- Permissions on `outputs/` directory

### Videos have no audio

- Ensure `TTS_PROVIDER` is set to `openai` or `elevenlabs`
- Verify API keys are correct
- Check `OPENAI_API_KEY` or `ELEVENLABS_API_KEY` in `.env`

---

## Performance Tips

1. **Reduce Mochi steps**: Lower `MOCHI_NUM_INFERENCE_STEPS` (default 64) to 32 for 2x speed
2. **Lower resolution**: Set `DEFAULT_VIDEO_WIDTH=854` and `HEIGHT=480` for faster encoding
3. **Disable TTS**: Set `TTS_PROVIDER=none` if voiceover isn't critical
4. **Use CPU offload**: Keep `MOCHI_CPU_OFFLOAD=true` to save VRAM

---

## Extension Configuration

Update `background.js` in the Chrome extension:

```javascript
const BACKEND_URL = 'http://localhost:8000';  // or your deployed URL
const USE_BACKEND = true;
```

If deploying remotely, use HTTPS and update CORS in `main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["chrome-extension://your-extension-id"],
    ...
)
```

---

## Cost Estimates (per 60s video)

| Component | Cost |
|-----------|------|
| Claude API (Sonnet 4) | ~$0.02 |
| OpenAI TTS | ~$0.10 |
| Mochi (H100 rental 2min) | ~$0.05 |
| **Total** | **~$0.17/video** |

Without Mochi (CPU-only):
- **~$0.12/video** (Claude + TTS only)

---

## License

MIT - See main repository LICENSE

---

## Support

For issues:
1. Check logs: `python main.py`
2. Verify `.env` configuration
3. Test endpoints: `curl http://localhost:8000/`

Happy video generating! 🎬
