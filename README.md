# MeetingMind — Video Meeting Analyzer

A multi-page web tool that transcribes video meetings using Qwen3 ASR and generates structured summaries with Qwen3.6 Multimodal.

## Features

- Upload video (MP4, MKV, MOV, WEBM) or audio (MP3) files
- Automatic audio extraction and transcription
- Maximum 120 minutes audio duration
- Interactive transcript with timestamps, language badges, and emotion tags
- Speaker clustering (auto-inferred, clearly labeled)
- Summary generation with up to 3 modifications
- Token usage tracking and cost estimation
- Downloadable Markdown summaries and transcript JSON

## Security & Rate Limits

- **Rate limiting**: 10 uploads/minute, 5 summaries/minute per IP
- **File validation**: Magic bytes verification to prevent extension spoofing
- **IP tracking**: All jobs track uploader IP address
- **Cost caps**: Summary tokens capped at 8000
- **Auto cleanup**: Jobs expire after 1 hour

## Tech Stack

- **Backend**: Python FastAPI
- **Frontend**: Vanilla HTML/CSS/JS (served by FastAPI)
- **Transcription**: Qwen3-ASR (qwen3-asr-flash-filetrans)
- **Summarization**: Qwen3.6 Plus via DashScope
- **Storage**: Alibaba Cloud OSS
- **Hosting**: Render

## Project Structure

```
meeting_asr/
├── backend/
│   ├── main.py           # FastAPI application
│   ├── config.py         # Configuration
│   └── requirements.txt  # Python dependencies
├── frontend/
│   ├── pages/
│   │   ├── index.html       # Upload page
│   │   ├── status.html      # Transcription progress
│   │   ├── transcript.html  # View transcript
│   │   └── summary.html     # Generate/view summary
│   ├── styles/
│   │   └── main.css     # All styles
│   └── api/
│       └── client.js    # API client
├── .env.example
├── README.md
└── render.yaml
```

## Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager
- Alibaba Cloud account with DashScope API key
- Alibaba Cloud OSS bucket

## Installation

1. Clone the repository:
```bash
git clone <repo-url>
cd meeting_asr
```

2. Install dependencies:
```bash
uv sync
```

3. Copy the environment template:
```bash
cp .env.example .env
```

4. Edit `.env` with your credentials:
```env
DASHSCOPE_API_KEY=your_api_key_here
DASHSCOPE_REGION=singapore
OSS_ACCESS_KEY_ID=your_access_key_id
OSS_ACCESS_KEY_SECRET=your_access_key_secret
OSS_BUCKET_NAME=your_bucket_name
OSS_ENDPOINT=https://oss-ap-southeast-1.aliyuncs.com
```

## Running Locally

Start the server:
```bash
uv run uvicorn backend.main:app --reload --port 8000
```

Open http://localhost:8000 in your browser.

**App Flow:**
1. Upload a video or audio file on the home page
2. Wait for transcription (progress shown on status page)
3. View transcript with speaker clustering
4. Generate summary with optional context (up to 3 modifications)

## Deployment on Render

1. Create a new Web Service on [Render](https://render.com)
2. Connect your GitHub repository
3. Use the `render.yaml` configuration (or set up manually):
   - Build Command: `pip install -r backend/requirements.txt`
   - Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables from `.env.example`
5. Enable a 1GB disk for temporary file storage

## API Endpoints

| Method | Endpoint | Rate Limit | Description |
|--------|----------|-----------|-------------|
| POST | `/api/upload` | 10/min | Upload video/audio file |
| GET | `/api/status/{job_id}` | — | Get job status and logs |
| GET | `/api/transcript/{job_id}` | — | Get transcription results |
| POST | `/api/summary/{job_id}` | 5/min | Generate summary |
| GET | `/api/download/{job_id}` | — | Download summary as Markdown |
| DELETE | `/api/job/{job_id}` | — | Delete job and cleanup files |
| GET | `/api/health` | — | Health check |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DASHSCOPE_API_KEY` | required | Alibaba DashScope API key |
| `DASHSCOPE_REGION` | `singapore` | Region: `singapore`, `beijing`, or `us` |
| `OSS_ACCESS_KEY_ID` | required | Alibaba Cloud OSS access key |
| `OSS_ACCESS_KEY_SECRET` | required | Alibaba Cloud OSS secret |
| `OSS_BUCKET_NAME` | required | OSS bucket name |
| `OSS_ENDPOINT` | required | OSS endpoint URL |
| `MAX_FILE_SIZE_MB` | `500` | Max upload size |
| `JOB_TTL_SECONDS` | `3600` | Job data TTL before cleanup |
| `POLL_INTERVAL_SECONDS` | `15` | ASR task poll interval |
| `TOKEN_PRICE_PER_1K` | `0.0002` | Estimated cost per 1K tokens |

## Pages

1. **Upload** (`/`) - Drag & drop video (MP4, MKV, MOV, WEBM) or audio (MP3)
2. **Status** (`/pages/status.html`) - View transcription progress with live logs
3. **Transcript** (`/pages/transcript.html`) - Interactive transcript with search, speaker clusters, download JSON
4. **Summary** (`/pages/summary.html`) - Generate summary with up to 3 modifications, download MD
