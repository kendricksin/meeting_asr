# Meeting Summary Generator

AI-powered meeting transcription and summarization using Qwen3 ASR.

## Features

- Upload video (MP4, MKV, MOV, WEBM) or audio (MP3) files
- Automatic audio extraction and transcription (up to 120 minutes)
- Interactive transcript with timestamps, language detection, and emotion tags
- Speaker prediction with configurable count (2-10 speakers)
- AI infers speaker names from conversation context
- Summary generation with up to 3 modifications
- Token usage tracking and cost estimation
- Dark theme UI with Inter font

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

## Local Development

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

5. Start the server:
```bash
uv run uvicorn backend.main:app --reload --port 8000
```

6. Open http://localhost:8000 in your browser.

## Deploy to Render

### Option 1: Using render.yaml (Recommended)

The `render.yaml` file automates the deployment. Connect your GitHub repo to Render and it will use this configuration automatically.

### Option 2: Manual Setup

1. Create a new **Web Service** on [Render](https://render.com)

2. Connect your GitHub repository

3. Configure the service:
   - **Root Directory**: (leave empty or set to `/`)
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

4. Add environment variables (Environment → Variables):
   ```
   DASHSCOPE_API_KEY=your_dashscope_api_key
   DASHSCOPE_REGION=singapore
   OSS_ACCESS_KEY_ID=your_oss_access_key
   OSS_ACCESS_KEY_SECRET=your_oss_secret
   OSS_BUCKET_NAME=your_bucket_name
   OSS_ENDPOINT=your_oss_endpoint
   ```

5. Add a **Disk** (Environment → Disks):
   - Name: `temp-storage`
   - Size: `1GB`
   - Mount Path: `/tmp/meetingmind`

6. Deploy the service

### Post-Deployment

- The app will be available at `https://your-service-name.onrender.com`
- Jobs expire after 1 hour of inactivity
- Rate limits: 2 uploads/minute, 2 summaries/minute per IP

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DASHSCOPE_API_KEY` | Yes | — | Alibaba DashScope API key |
| `DASHSCOPE_REGION` | No | `singapore` | Region: `singapore`, `beijing`, or `us` |
| `OSS_ACCESS_KEY_ID` | Yes | — | Alibaba Cloud OSS access key |
| `OSS_ACCESS_KEY_SECRET` | Yes | — | Alibaba Cloud OSS secret |
| `OSS_BUCKET_NAME` | Yes | — | OSS bucket name |
| `OSS_ENDPOINT` | Yes | — | OSS endpoint URL |
| `MAX_FILE_SIZE_MB` | No | `500` | Max upload size (MB) |
| `JOB_TTL_SECONDS` | No | `3600` | Job data TTL before cleanup |
| `TOKEN_PRICE_PER_1K` | No | `0.0002` | Estimated cost per 1K tokens |

## API Endpoints

| Method | Endpoint | Rate Limit | Description |
|--------|----------|-----------|-------------|
| POST | `/api/upload` | 2/min | Upload video/audio file |
| GET | `/api/status/{job_id}` | — | Get job status and progress |
| GET | `/api/transcript/{job_id}` | — | Get transcription results |
| POST | `/api/transcript/predict-speakers` | — | Predict speakers using AI |
| POST | `/api/summary/{job_id}` | 2/min | Generate summary |
| GET | `/api/download/{job_id}` | — | Download summary as Markdown |
| DELETE | `/api/job/{job_id}` | — | Delete job and cleanup files |
| GET | `/api/health` | — | Health check |

## App Flow

1. **Upload** — Drag & drop video (MP4, MKV, MOV, WEBM) or audio (MP3)
2. **Status** — View transcription progress with loading bar (0-96% over 5 min)
3. **Transcript** — View/edit speakers, search transcript, assign speakers to sentences
4. **Summary** — Generate summary with optional context, download as Markdown
