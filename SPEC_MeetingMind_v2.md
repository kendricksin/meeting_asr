# MeetingMind — Video Meeting Analyzer

**Spec Version:** 2.0  
**Last Updated:** 2026-04-11  
**Status:** Draft / For Engineering Review  
**Supersedes:** v1.0 (which used Whisper + OpenAI)

---

## 1. Overview

### Project Name
**MeetingMind** — Async Video Meeting Analyzer

### Core Functionality
A single-page web tool that allows users to upload a video recording of a meeting (MP4, MKV, MOV, WEBM), automatically transcribes the audio using **Qwen3 ASR**, generates a structured meeting summary with action items in Markdown, and provides both in-page rendering and a downloadable Markdown file. Token consumption is tracked and displayed for both the transcription and summarization stages. An optional "Add Context + Generate Summary" flow allows uploading up to 5 images plus free text to feed Qwen3.6-multimodal for a richer summary.

### Target Users
- Business professionals who conduct remote video meetings
- Teams that want to archive and extract actionable insights from meeting recordings
- Freelancers or consultants who need quick post-meeting documentation

### Target Platform
**Render** — Auto-scaled on-demand Web Service

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────────────┐  │
│  │  Upload UI   │──▶│  Status/Log  │──▶│  Results Panel     │  │
│  │              │   │              │   │  - Transcript      │  │
│  │  [Tab:        │   │              │   │  - Summary         │  │
│  │   Transcript]│   │              │   │  - Token Count     │  │
│  │  [Tab:        │   │              │   │  - Download .md    │  │
│  │   Summary]    │   │              │   └────────────────────┘  │
│  └──────────────┘   └──────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Render Backend (FastAPI)                     │
│                                                                 │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────────────┐  │
│  │  File Upload │──▶│  Qwen3 ASR   │──▶│  Qwen3.6 Multimodal │  │
│  │  Handler     │   │  (via OSS)   │   │  Summarizer         │  │
│  └──────────────┘   └──────────────┘   └────────────────────┘  │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Token Tracker | Markdown Generator | File Cleanup         │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Vanilla HTML/CSS/JS (no framework — keeps it light) |
| Backend | Python FastAPI on Render |
| Transcription | **Qwen3-ASR** via DashScope (`qwen3-asr-flash-filetrans`) — audio uploaded to Alibaba Cloud OSS |
| Summarization | **Qwen3.6-multimodal** via DashScope (handles text + images) |
| Object Storage | Alibaba Cloud OSS (for audio files sent to Qwen3-ASR) |
| Hosting | Render (Auto-scaled, pay-per-use Web Service) |
| File Storage | Temporary disk storage on Render instance — cleared after processing |

---

## 3. Data Flow

```
[1] User uploads video (MP4/MKV/MOV/WEBM, max 500 MB)
         │
         ▼
[2] Extract audio → MP3/WAV
         │
         ▼
[3] Upload audio to Alibaba Cloud OSS → get pre-signed URL
         │
         ▼
[4] Qwen3-ASR async call → submit task, poll until SUCCEEDED
         │
    Returns: raw JSON with sentences[], each sentence has:
      - begin_time (ms), end_time (ms)
      - text
      - language (th/en/etc.)
      - emotion (neutral/happy/sad/etc.)
      - words[] (word-level timestamps)
         │
         ▼
[5] Display interactive transcript from JSON
         │
    Optional: "Generate Summary with Context"
         │
         ▼
[6a] User uploads up to 5 images + optional text
         │
[6b] Call Qwen3.6-multimodal with transcript + images + text
         │
         ▼
[7] Return summary Markdown → render + downloadable
```

---

## 4. Qwen3-ASR Output Format (Canonical JSON)

This is the **standard format** that the frontend renders. The backend must normalize/transform Qwen3-ASR's raw output into this structure before sending to the frontend.

### 4.1 Model Constraints

| Parameter | qwen3-asr-flash-filetrans (Async) | qwen3-asr-flash (Sync) |
|-----------|-----------------------------------|------------------------|
| **Max audio file size** | 2 GB | 10 MB |
| **Max audio duration** | 12 hours | 5 minutes |
| **Use case** | Long meeting transcription | Short audio / voice messages |

> **Note:** This tool uses **`qwen3-asr-flash-filetrans`** (async) for meeting-length recordings. It supports multilingual recognition, noise rejection, singing voice transcription, and emotion recognition.

### 4.2 Qwen3-ASR Parameters

The following parameters are passed to the Qwen3-ASR API call:

| Parameter | Value | Notes |
|-----------|-------|-------|
| `model` | `qwen3-asr-flash-filetrans` | Stable model |
| `language` | `"th"` | Thai primary; also handles EN code-switching. Auto-detect is supported but forcing TH improves accuracy for Thai meetings. |
| `enable_itn` | `true` | Inverse Text Normalization: converts numbers/dates/times to readable text (e.g. "1 มกรา" → "1 มกราคม") |
| `enable_words` | `true` | Word-level timestamps for granular transcript display |
| `enable_disfluencies` | `false` | Filter out filler words (uh/um). Set `true` to include them. |
| `channel_id` | `[0]` | Audio channel. Use `[0]` for mono or single-channel files. Set `[0, 1]` for stereo (each channel processed separately). |

### 4.3 Emotion Recognition

Qwen3-ASR-Flash-Filetrans recognizes the following emotional states per sentence:

| Tag | Description |
|-----|-------------|
| `surprise` | Surprised tone |
| `calm` | Calm / neutral tone |
| `happy` | Happy / positive tone |
| `sad` | Sad tone |
| `disgust` | Disgusted tone |
| `angry` | Angry tone |
| `fear` | Fearful tone |
| `neutral` | Default when no emotion detected |

### 4.4 Regional Endpoints & API Keys

> **Critical:** API keys are **region-specific**. Using a Singapore-region key with a Beijing endpoint (or vice versa) will fail. Obtain keys from the appropriate regional console.

| Region | Base URL | Model Suffix | Notes |
|--------|----------|--------------|-------|
| **Singapore (International)** | `https://dashscope-intl.aliyuncs.com/api/v1` | None | Primary deployment |
| **Beijing (Chinese Mainland)** | `https://dashscope.aliyuncs.com/api/v1` | None | For mainland China deployment |
| **US** | `https://dashscope-us.aliyuncs.com/api/v1` | `-us` suffix on model name | Qwen3-ASR-Flash only (not Filetrans) |

API key console links:
- Singapore: https://modelstudio.console.alibabacloud.com/?tab=dashboard#/api-key
- US: https://modelstudio.console.alibabacloud.com/us-east-1?tab=dashboard#/api-key
- Beijing: https://bailian.console.aliyuncs.com/?tab=model#/api-key

### 4.5 Task Lifecycle

The Qwen3-ASR async workflow follows a 3-step pattern:

```
[1] POST /transcription → { task_id, task_status: "PENDING" }
         │
         ▼
[2] GET /tasks/{task_id} → poll until task_status == "SUCCEEDED" | "FAILED" | "CANCELED"
         │
    Poll interval: 30 seconds recommended (DOC: 2s minimum, our impl: 30s to avoid rate limits)
         │
         ▼
[3] On SUCCEEDED:
    - Fetch transcription_url from task_result.output.result["transcription_url"]
    - GET transcription_url → raw JSON with sentences[]
```

**Important:** The task result contains a **`transcription_url`** — a separate URL that must be fetched to retrieve the actual transcript JSON. The transcription URL is valid for at least 1 hour after task completion.

### 4.6 Response Schema

```json
{
  "job_id": "uuid-string",
  "filename": "meeting.mp4",
  "audio_duration_seconds": 2843.5,
  "language": "th",
  "transcription_status": "SUCCEEDED",
  "sentences": [
    {
      "id": 0,
      "begin_time_ms": 2092,
      "end_time_ms": 3372,
      "text": "พี่ครับ ครับ",
      "language": "th",
      "emotion": "happy",
      "duration_ms": 1280,
      "words": [
        {
          "begin_time_ms": 2092,
          "end_time_ms": 2172,
          "text": "พ",
          "punctuated_text": "ี่"
        },
        {
          "begin_time_ms": 2252,
          "end_time_ms": 2252,
          "text": "คร",
          "punctuated_text": "ั"
        }
      ]
    },
    {
      "id": 1,
      "begin_time_ms": 17452,
      "end_time_ms": 18172,
      "text": "ได้ยินไหมครับ",
      "language": "th",
      "emotion": "neutral",
      "duration_ms": 720,
      "words": []
    }
  ],
  "token_usage": {
    "transcription_proxy_tokens": 12400
  }
}
```

### 4.7 Field Specifications

| Field | Type | Description |
|-------|------|-------------|
| `sentences[].id` | int | Auto-incrementing index per sentence |
| `sentences[].begin_time_ms` | int | Start time in milliseconds |
| `sentences[].end_time_ms` | int | End time in milliseconds |
| `sentences[].duration_ms` | int | `end_time_ms - begin_time_ms` |
| `sentences[].text` | string | Raw text (with punctuation via ITN) |
| `sentences[].language` | string | Language code: `"th"`, `"en"`, etc. |
| `sentences[].emotion` | string | Emotion tag from the 8 supported emotions |
| `sentences[].words` | array | Word-level timestamps (when `enable_words=True`) |
| `sentences[].words[].begin_time_ms` | int | Word start |
| `sentences[].words[].end_time_ms` | int | Word end |
| `sentences[].words[].text` | string | Word text without punctuation |
| `sentences[].words[].punctuated_text` | string | Punctuation attached to word |

### 4.8 Speaker Diarization — Explicit Limitation

> **The Qwen3-ASR Flash-Filetrans model does NOT support speaker diarization.** This is explicitly documented: *"No sensitive words filter or speaker diarization."*

The tool MUST NOT promise or imply speaker identification. The frontend heuristic clustering (time gaps + language switching) is a best-effort workaround only.

### 4.9 Token Proxy for Transcription

Qwen3-ASR does not expose standard token counts. Use as proxy:
```
transcription_proxy_tokens = audio_duration_seconds * 8
```
(Roughly: 450 chars/min spoken at ~150 wpm × ~1.3 Thai char overhead, divided by 4 tokens/char ≈ 8 tokens/sec)

---

## 5. Frontend Specification

### 5.1 Page Structure

```
┌──────────────────────────────────────────────────────────────────┐
│  Header: Logo + "MeetingMind" + tagline                        │
├──────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  DRAG & DROP ZONE / FILE PICKER                           │   │
│  │  supports: MP4, MKV, MOV, WEBM (max 500 MB)              │   │
│  │  [Browse Files]                                           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Step Indicator: [1 Upload] → [2 Transcribe] →           │   │
│  │                   [3 Summarize] → [4 Complete]            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Live Log Console (collapsible, auto-scroll)             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌────────────[Transcript]────────[Summary]─────────────────┐  │
│  │  [Tab: Transcript]  [Tab: Summary + Actions]              │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │                                                          │  │
│  │  ┌─────────────────────────────────────────────────────┐ │  │
│  │  │  Interactive Transcript Panel                       │ │  │
│  │  │  [🔍 Search] [⏱ Filter by time]                     │ │  │
│  │  │  ─────────────────────────────────────────────────  │ │  │
│  │  │  [00:01] [TH][happy]  พี่ครับ ครับ                  │ │  │
│  │  │  [00:21] [TH][neutral] โอ้ ว้าว นั่นน่าประทับใจ...   │ │  │
│  │  │  ─────────────────────────────────────────────────  │ │  │
│  │  │  [Speaker A]  [Speaker B]  [Speaker C] (legend)    │ │  │
│  │  └─────────────────────────────────────────────────────┘ │  │
│  │                                                          │  │
│  │  ┌─────────────────────────────────────────────────────┐ │  │
│  │  │  Summary Panel                                       │ │  │
│  │  │  [📎 Add Context + Images] → opens modal            │ │  │
│  │  │  Rendered Markdown:                                  │ │  │
│  │  │  # Meeting Summary — [Date]                          │ │  │
│  │  │  ## Overview | ## Discussion | ## Actions | ## Decisions│ │ │
│  │  │  [Download .md] [Copy Markdown]                      │ │  │
│  │  └─────────────────────────────────────────────────────┘ │  │
│  │                                                          │  │
│  │  ┌─────────────────────────────────────────────────────┐ │  │
│  │  │  Token & Cost Panel                                   │ │  │
│  │  │  Transcription: ~12,400 tokens (proxy)              │ │  │
│  │  │  Summary: 8,234 tokens | Est. cost: $0.023 USD       │ │  │
│  │  └─────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Footer: Powered by Qwen3-ASR + Qwen3.6 | Render                │
└──────────────────────────────────────────────────────────────────┘
```

### 5.2 Transcript Panel Features

| Feature | Description |
|---------|-------------|
| **Timestamp display** | Each sentence shows `[MM:SS]` timestamp |
| **Speech duration** | Each sentence shows duration badge (e.g. `+1.2s`) on hover |
| **Language badge** | `[TH]`, `[EN]`, `[mixed]` — color coded |
| **Emotion tag** | `[neutral]`, `[happy]`, `[sad]` — color coded |
| **Speaker color coding** | Sentences are auto-colored by inferred speaker cluster (not provided by Qwen3-ASR natively, so cluster by time gaps + language patterns) |
| **Search** | Full-text search with highlight matches |
| **Click to seek** | Click a timestamp → scrolls to that position (if video player present, seeks video) |
| **Copy sentence** | Click copy icon on any sentence to copy text |
| **Auto-scroll follow** | Toggle to auto-scroll as transcript plays |

### 5.3 Speaker Color Coding Logic

> **Limitation:** Qwen3-ASR Flash-Filetrans does NOT provide speaker diarization. The speaker colors below are **heuristic only** and should be clearly labeled as "Auto-clustered (inferred)" in the UI rather than named speakers.

Implementation approach:

1. **Time gap heuristic**: If gap between consecutive sentences > 2 seconds, treat as a potential new speaker turn
2. **Language switch**: If language code switches between consecutive sentences (e.g., `th` → `en` → `th`), treat as a separate speaker cluster
3. **Assign colors**: Cycle through 6 preset colors: `#3B82F6` (blue), `#10B981` (green), `#F59E0B` (amber), `#EF4444` (red), `#8B5CF6` (purple), `#EC4899` (pink)
4. **User override**: Allow user to manually rename each speaker cluster (e.g., "Speaker A" → "John") and reassign colors. These overrides should persist for the session (not persisted to backend).
5. **Legend**: Always display a speaker legend below the transcript showing which color maps to which cluster label.

### 5.4 Summary Panel Features

| Feature | Description |
|---------|-------------|
| **Markdown rendering** | `marked.js` in-browser, properly styled |
| **"Add Context + Images" modal** | Opens a modal to upload up to 5 images + free-text context field |
| **Image preview** | Thumbnails of uploaded images with remove button |
| **"Generate Summary" button** | Triggers Qwen3.6-multimodal call with transcript + images + text |
| **Loading state** | Shows spinner + "Generating summary..." during LLM call |
| **Download .md** | Downloads `meeting_summary_[timestamp].md` |
| **Copy Markdown** | One-click copy to clipboard |

### 5.5 "Add Context + Generate Summary" Modal

```
┌────────────────────────────────────────────────────────┐
│  Generate Rich Summary                            [X] │
├────────────────────────────────────────────────────────┤
│                                                        │
│  Additional Context (optional):                        │
│  ┌──────────────────────────────────────────────────┐ │
│  │  e.g., "Meeting with potential hire, discussing   │ │
│  │  AI sales role at GSaS.Thai language."            │ │
│  └──────────────────────────────────────────────────┘ │
│                                                        │
│  Upload Images (up to 5, optional):                    │
│  ┌──────────────────────────────────────────────────┐ │
│  │  [Drag & drop images here] or [Browse]            │ │
│  │  JPG, PNG, WEBP — max 10 MB each                  │ │
│  └──────────────────────────────────────────────────┘ │
│  [img1_thumb.jpg ×] [img2.png ×] [img3.png ×]        │
│                                                        │
│  [Cancel]                    [Generate Summary ▶]    │
└────────────────────────────────────────────────────────┘
```

---

## 6. Backend Specification

### 6.1 API Endpoints

**`POST /upload`**
```
Content-Type: multipart/form-data
Body: file (video file)

Response 200:
{
  "job_id": "uuid-string",
  "filename": "meeting.mp4",
  "status": "queued",
  "file_size_mb": 142.3
}
```

**`GET /status/{job_id}`**
```
Response 200:
{
  "job_id": "uuid-string",
  "status": "queued|transcribing|summarizing|complete|error",
  "progress_percent": 45,
  "log": ["[12:01:03] Upload received", "[12:01:15] Starting ASR..."],
  "error_message": null
}
```

**`GET /transcript/{job_id}`**
```
Response 200:
{
  "job_id": "uuid-string",
  "audio_duration_seconds": 2843.5,
  "language": "th",
  "sentences": [ /* normalized sentence array */ ],
  "token_usage": {
    "transcription_proxy_tokens": 12400
  }
}
```

**`POST /summary/{job_id}`**
```
Content-Type: multipart/form-data (optional files + text)

Body (all fields optional):
  - context_text: string
  - images: up to 5 image files

Response 200:
{
  "job_id": "uuid-string",
  "summary_markdown": "...",
  "token_usage": {
    "summary_input_tokens": 6234,
    "summary_output_tokens": 2100,
    "summary_total_tokens": 8334
  },
  "cost_usd": 0.008
}
```

**`GET /download/{job_id}`**
```
Query params:
  - include_transcript: bool (default false)

Response: Markdown file as attachment
Content-Disposition: attachment; filename="meeting_summary_20260411_214523.md"
```

**`DELETE /job/{job_id}`**
```
Response 200:
{ "deleted": true }
```

**`GET /health`**
```
Response 200:
{ "status": "ok", "asr_model": "qwen3-asr-flash-filetrans", "llm_model": "qwen3.6-multimodal" }
```

### 6.2 Job State Store (In-Memory)

```python
class JobState(BaseModel):
    job_id: str
    filename: str
    status: str
    filepath: str           # temp video file
    audio_filepath: str     # extracted audio path
    oss_url: str            # pre-signed OSS URL
    sentences: List[Sentence] = []
    summary_markdown: str = ""
    token_usage: dict = {}
    log: List[str] = []
    error: str = ""
    created_at: datetime
```

- Jobs expire after `JOB_TTL_SECONDS = 3600` (1 hour)
- Background cleanup task sweeps stale files every 10 minutes

### 6.3 Key Processing Functions

#### 3a. Audio Extraction
```python
def extract_audio(video_path: str, audio_path: str) -> None:
    with VideoFileClip(video_path) as clip:
        clip.audio.write_audiofile(audio_path, logger=None)
```

#### 3b. OSS Upload
```python
def upload_to_oss(local_path: str) -> str:
    # Upload to Alibaba Cloud OSS
    # Return pre-signed URL valid for 1 hour
```

#### 3c. Qwen3-ASR Transcription
```python
def transcribe(file_url: str, region: str = "singapore") -> list[Sentence]:
    # Set regional base URL
    base_urls = {
        "singapore": "https://dashscope-intl.aliyuncs.com/api/v1",
        "beijing":   "https://dashscope.aliyuncs.com/api/v1",
        "us":        "https://dashscope-us.aliyuncs.com/api/v1",
    }
    dashscope.base_http_api_url = base_urls[region]

    # Submit async task
    task_response = QwenTranscription.async_call(
        model="qwen3-asr-flash-filetrans",
        file_url=file_url,
        language="th",
        enable_itn=True,
        enable_words=True,
        enable_disfluencies=False,
    )
    task_id = task_response.output.task_id

    # Poll until SUCCEEDED (30s interval recommended)
    while True:
        task_result = QwenTranscription.fetch(task=task_id)
        status = task_result.output.task_status
        if status == "SUCCEEDED":
            break
        if status in ("FAILED", "CANCELED"):
            raise RuntimeError(f"Transcription {status}: {task_result.output}")
        time.sleep(POLL_INTERVAL_SECONDS)

    # Fetch transcript JSON from transcription_url
    transcription_url = task_result.output.result["transcription_url"]
    data = requests.get(transcription_url).json()

    # Normalize to Sentence[] schema
    sentences = normalize_sentences(data.get("transcripts", []))
    return sentences
```

> **Important:** The raw Qwen3-ASR response groups sentences under a `transcripts[]` array. Each transcript object contains a `sentences[]` array. The backend must flatten/normalize this into the canonical `Sentence` schema before sending to the frontend.

> **Transcription URL validity:** The `transcription_url` returned in the result is valid for at least 1 hour after task completion. Do not assume indefinite validity — fetch and process promptly.

#### 3d. Qwen3.6 Multimodal Summarization
```python
def summarize(transcript: str, context_text: str, images: list[bytes]) -> tuple[str, int]:
    # Build multimodal prompt:
    # - First text: SUMMARY_SYSTEM_PROMPT
    # - Then transcript text
    # - Then context_text if provided
    # - Then images if provided (as image URLs or base64)
    # Call Qwen3.6-multimodal
    # Return (markdown_summary, total_tokens)
```

---

## 7. Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `DASHSCOPE_API_KEY` | env var | Alibaba DashScope API key (region-specific — SG vs Beijing vs US) |
| `DASHSCOPE_REGION` | `"singapore"` | Region selection: `"singapore"` \| `"beijing"` \| `"us"` — determines base URL |
| `OSS_ACCESS_KEY_ID` | env var | Alibaba Cloud OSS access key |
| `OSS_ACCESS_KEY_SECRET` | env var | Alibaba Cloud OSS secret |
| `OSS_BUCKET_NAME` | env var | OSS bucket name |
| `OSS_ENDPOINT` | env var | OSS endpoint (e.g. `https://oss-ap-southeast-1.aliyuncs.com` for Singapore) |
| `QVLLM_ENDPOINT` | env var | vLLM endpoint for Qwen3.6-multimodal (if self-hosted) |
| `MAX_FILE_SIZE_MB` | `500` | Max video upload size |
| `JOB_TTL_SECONDS` | `3600` | Job data TTL before cleanup |
| `TEMP_DIR` | `/tmp/meetingmind` | Temp file storage |
| `TOKEN_PRICE_PER_1K` | `0.0002` | Estimated cost per 1K tokens (Qwen3.6) |
| `POLL_INTERVAL_SECONDS` | `30` | Interval between Qwen3-ASR task status polls |

### 7.1 Regional Base URL Mapping

```python
REGIONAL_URLS = {
    "singapore": "https://dashscope-intl.aliyuncs.com/api/v1",
    "beijing":   "https://dashscope.aliyuncs.com/api/v1",
    "us":        "https://dashscope-us.aliyuncs.com/api/v1",
}
```

> **Critical:** The `DASHSCOPE_REGION` must match the region of the `DASHSCOPE_API_KEY`. Mismatched region + key will result in authentication failures.

---

## 8. Deployment on Render

### 8.1 render.yaml

```yaml
services:
  - type: web
    name: meetingmind
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    plan: starter
    disk:
      name: temp-storage
      sizeGb: 1
    envVars:
      - key: DASHSCOPE_API_KEY
        sync: false
      - key: OSS_ACCESS_KEY_ID
        sync: false
      - key: OSS_ACCESS_KEY_SECRET
        sync: false
      - key: OSS_BUCKET_NAME
        sync: false
      - key: OSS_ENDPOINT
        sync: false
```

### 8.2 Resource Notes

- Audio extraction (moviepy) and OSS upload are the slowest steps (~30-60s for a 45-min meeting)
- Qwen3-ASR async poll typically resolves within 2-3 minutes
- Render disk is needed to store temp video + audio during processing
- No persistent database — all state is in-memory job store

---

## 9. Security Considerations

- **File validation**: Check MIME type + extension server-side before processing
- **No persistent storage**: Video and audio files deleted after job completion or cleanup
- **API keys**: Stored as Render env vars, never in code or logs
- **Upload limits**: Enforced server-side (500 MB max)
- **Image upload**: Max 5 images × 10 MB each = 50 MB max for context images
- **No user auth (v1)**: Open tool. Rate limiting per IP can be added if abuse occurs

---

## 10. Open Questions / TODOs

1. **Image encoding for Qwen3.6**: Base64 is simpler but inflates token usage significantly. Option A: Base64-encode images client-side before upload. Option B: Upload images to OSS first, pass OSS URLs to Qwen3.6. Decide before implementation.
2. **Language hint**: Allow user to set a language hint (TH/EN/mixed) vs auto-detect? Auto-detect may be wrong for code-switching meetings.
3. **Video player in-page**: Should we embed the video player alongside the transcript for seek-by-click functionality?
4. **Download transcript separately**: Should transcript be downloadable as `.txt` or `.json` in addition to the Markdown summary?
5. **Rate limiting**: How to prevent abuse on free Render tier? Per-IP limit on uploads per hour?
6. **Audio channel handling**: If stereo audio is uploaded, `channel_id: [0, 1]` processes each channel separately — how should the frontend merge or present two channel transcripts?

---

## 11. Success Criteria (v1)

- [ ] Video upload works for MP4, MKV, MOV, WEBM up to 500 MB
- [ ] Transcript renders with `[MM:SS]` timestamps, language badges, and emotion tags per sentence
- [ ] Word-level timestamps rendered when `enable_words=True` (hover to reveal)
- [ ] Transcript is searchable (full-text with match highlighting)
- [ ] Sentences are color-coded by auto-clustered speaker groups (clearly labeled as "inferred")
- [ ] Speech duration shown per sentence (inline badge or hover tooltip)
- [ ] "Add Context + Images" modal accepts up to 5 images (JPG/PNG/WEBP, max 10 MB each) + optional text
- [ ] Summary generation with images calls Qwen3.6-multimodal successfully
- [ ] Markdown summary renders correctly in-page (`marked.js`) and downloads as `.md`
- [ ] Token count displayed for both transcription (proxy: `duration_s × 8`) and summarization (actual LLM tokens)
- [ ] Full pipeline completes within 5 minutes for a 45-min meeting video
- [ ] Job cleanup removes all temp files after job completion or TTL expiry
- [ ] Regional endpoint correctly selected based on `DASHSCOPE_REGION` env var

---

*Spec prepared for engineering handoff. Questions or clarifications should be routed back to the product owner.*
