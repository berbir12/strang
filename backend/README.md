# Strang Backend - Groq (FREE) + HeyGen API

**AI Avatar Video Generation powered by Groq and HeyGen**

## Overview

This backend transforms text into professional AI avatar videos using a powerful and efficient pipeline:

1. **Groq AI API** - FREE, lightning-fast script generation using Llama 3.3 70B
2. **HeyGen** - Renders photorealistic AI avatar videos

### Why Groq?

- **100% FREE** - No credit card required, generous free tier
- **BLAZINGLY FAST** - 10-50x faster than other free AI APIs
- **HIGH QUALITY** - Access to Llama 3.3 70B, one of the best open models
- **NO COLD STARTS** - Instant responses, no waiting

## Requirements

- Python 3.9+
- Groq API key (free!)
- HeyGen API key

## Installation

```bash
cd backend
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

```bash
cp env.example .env
```

Edit `.env` and add your API keys:

```env
GROQ_API_KEY=your_groq_api_key_here
HEYGEN_API_KEY=your_heygen_api_key_here
```

### Getting Your API Keys

**Groq (FREE):**
1. Go to [console.groq.com](https://console.groq.com/keys)
2. Sign up (free, no credit card required!)
3. Click "Create API Key"
4. Copy your key

**HeyGen:**
1. Go to [app.heygen.com](https://app.heygen.com)
2. Navigate to Settings → API
3. Create a new API key
4. Copy your key

### Finding Your HeyGen Avatar/Voice IDs

1. Go to [app.heygen.com](https://app.heygen.com)
2. Create a video manually and note the avatar/voice IDs
3. Or use the `/api/avatars` and `/api/voices` endpoints to list available options

## Running the Server

### Development

```bash
python main.py
```

Server runs at `http://localhost:8000`

### Production

```bash
pip install gunicorn

gunicorn main:app \
  --workers 2 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 600
```

## API Endpoints

### POST /api/process-video

Start video generation job.

**Request:**
```json
{
  "text": "Your content here...",
  "style": "professional",
  "avatar_id": "optional_avatar_id",
  "voice_id": "optional_voice_id"
}
```

**Response:**
```json
{
  "job_id": "uuid",
  "status": "queued",
  "message": "Video generation started...",
  "estimated_time_seconds": 150
}
```

### POST /api/generate-script

Generate script only (without video).

**Request:**
```json
{
  "text": "Your content here...",
  "style": "professional",
  "duration_hint": 60
}
```

**Response:**
```json
{
  "original_text": "...",
  "script": "Enhanced script...",
  "style": "professional",
  "word_count": 150,
  "estimated_duration_seconds": 60
}
```

### GET /job/{job_id}/progress

Get job progress.

**Response:**
```json
{
  "job_id": "uuid",
  "status": "rendering",
  "progress_percent": 65,
  "current_step": "rendering",
  "message": "HeyGen is rendering your avatar video..."
}
```

### GET /job/{job_id}/result

Get final result.

**Response:**
```json
{
  "job_id": "uuid",
  "status": "completed",
  "video_url": "https://...",
  "thumbnail_url": "https://...",
  "duration": 45.5,
  "script": "The generated script..."
}
```

### WebSocket /ws/job/{job_id}

Real-time progress updates.

**Messages:**
```json
{"type": "progress", "status": "scripting", "progress_percent": 20, "message": "Groq is writing..."}
{"type": "progress", "status": "rendering", "progress_percent": 50, "message": "HeyGen is rendering..."}
{"type": "complete", "status": "completed", "video_url": "..."}
```

### GET /api/avatars

List available HeyGen avatars.

### GET /api/voices

List available HeyGen voices.

## Script Styles

| Style | Description |
|-------|-------------|
| professional | Business-ready, clear and authoritative |
| casual | Conversational, relaxed tone |
| educational | Structured for learning |
| friendly | Warm, approachable |

## Generation Pipeline

```
┌─────────────────────────────────────────────┐
│  Stage 1: Script Generation (0-30%)         │
│  • Groq AI transforms input script          │
│  • ⚡ EXTREMELY FAST (~2-5 seconds)        │
│  • Uses Llama 3.3 70B for quality           │
│  • 100% FREE, no cold starts                │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Stage 2: Video Rendering (30-100%)         │
│  • HeyGen generates avatar video            │
│  • Polls for completion (5s intervals)      │
│  • Typically takes 2-5 minutes              │
│  • Returns video URL when done              │
└─────────────────────────────────────────────┘
```

## Groq Models

Available FREE models (configure in `.env`):

| Model | Speed | Quality | Use Case |
|-------|-------|---------|----------|
| `llama-3.3-70b-versatile` | Very Fast | Excellent | **Recommended default** |
| `llama-3.1-70b-versatile` | Very Fast | Excellent | Alternative option |
| `mixtral-8x7b-32768` | Ultra Fast | Very Good | When speed is critical |
| `gemma2-9b-it` | Ultra Fast | Good | Lightweight option |

All models are **100% FREE** with generous rate limits!

## Cost Estimates

| Service | Cost |
|---------|------|
| Groq AI | **100% FREE** ✨ |
| HeyGen | ~$0.10-0.50 per minute |

**Total cost:** Only pay for HeyGen video generation!

## Advantages Over Previous Setup

### Old: HuggingFace Free Inference
- ❌ Slow cold starts (10-30 seconds)
- ❌ Rate limited
- ❌ Unreliable availability
- ❌ Inconsistent quality

### New: Groq API
- ✅ **10-50x faster** (~2-5 seconds)
- ✅ **100% FREE** (generous limits)
- ✅ **No cold starts** (instant response)
- ✅ **Highly reliable**
- ✅ **Better quality** (Llama 3.3 70B)

## Troubleshooting

### "GROQ_API_KEY is not configured"
- Ensure `.env` file exists with `GROQ_API_KEY=...`
- Get your free key from [console.groq.com/keys](https://console.groq.com/keys)

### "HEYGEN_API_KEY is not configured"
- Ensure `.env` file exists with `HEYGEN_API_KEY=...`
- Get your key from HeyGen settings

### Groq rate limit errors
- Groq free tier has generous limits (thousands of requests per day)
- Wait a few seconds if you hit the limit
- Rate limits reset quickly (per minute, not per day)

### HeyGen returns 401
- Check your API key is valid
- Ensure you have credits in your HeyGen account

### Video generation times out
- HeyGen can take 2-5 minutes for videos
- Increase `HEYGEN_MAX_WAIT_TIME` in `.env` if needed

## Project Structure

```
backend/
├── main.py                     # FastAPI application
├── config.py                   # Settings & env vars
├── models.py                   # Pydantic models
├── requirements.txt            # Dependencies
├── env.example                 # Example environment
├── services/
│   ├── groq_service.py        # Groq AI integration (NEW!)
│   └── heygen_service.py      # HeyGen integration
└── utils/
    └── job_manager.py         # Async job queue
```

## Performance Benchmarks

**Script Generation (500-word input):**
- Old (HuggingFace Free): ~15-30 seconds (with cold start)
- **New (Groq)**: ~2-5 seconds ⚡

**Total Pipeline Time:**
- Old: ~3-6 minutes
- **New: ~2-4 minutes** (30-40% faster!)

## License

MIT License
