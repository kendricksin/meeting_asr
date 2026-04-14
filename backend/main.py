import os
import sys
import time
import uuid
import json
import base64
import asyncio
import struct
from datetime import datetime
from pathlib import Path
from typing import Optional, List

# Add backend directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import oss2
import requests
import dashscope
from dashscope.audio.qwen_asr import QwenTranscription
from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    BackgroundTasks,
    Query,
    Request,
    Header,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from moviepy import VideoFileClip, AudioFileClip
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

import config

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Allowed file extensions and magic bytes
ALLOWED_EXTENSIONS = {".mp4", ".mkv", ".mov", ".webm", ".mp3", ".mpeg"}
MAGIC_BYTES = {
    b"\x00\x00\x00\x00\x66\x74\x79\x70": "mp4",  # ftyp
    b"\x00\x00\x00\x1c\x66\x74\x79\x70": "mp4",  # ftyp (variant)
    b"\x00\x00\x00\x1a\x65\x78\x74\x72": "m4a",  # m4a
    b"\x49\x44\x33": "mp3",  # ID3
    b"\xff\xfb": "mp3",  # MP3 frame
    b"\xff\xfa": "mp3",  # MP3 frame
    b"\xff\xf3": "mp3",  # MP3 frame
    b"\xff\xf2": "mp3",  # MP3 frame
    b"\x1a\x45\xdf\xa3": "mkv",  # EBML
    b"\x00\x00\x00\x14": "webm",  # WebM
    b"\x00\x00\x00\x18": "webm",  # WebM
    b"RIFF": "wav",  # WAV
    b"MOOV": "mov",  # MOV
    b"\x00\x00\x00\x06\x6d\x6f\x6f\x76": "mov",  # mov
    b"ftyp": "mp4",  # mp4/m4a
    b"wide": "mp4",  # mp4
    b"mdat": "mp4",  # mp4
    b"free": "mp4",  # mp4
}

# Max tokens for summarization
MAX_SUMMARY_TOKENS = config.MAX_SUMMARY_TOKENS
MAX_AUDIO_DURATION_SECONDS = config.MAX_AUDIO_DURATION_MINUTES * 60


class SummaryRequest(BaseModel):
    context_text: Optional[str] = ""
    transcript: Optional[dict] = None
    speaker_count: Optional[int] = 3


class Sentence(BaseModel):
    id: int
    begin_time_ms: int
    end_time_ms: int
    text: str
    language: str
    emotion: str
    duration_ms: int
    words: list


class JobState(BaseModel):
    job_id: str
    filename: str
    status: str
    filepath: str
    audio_filepath: str
    oss_url: str
    is_audio: bool = False
    sentences: List[Sentence] = []
    summary_markdown: str = ""
    token_usage: dict = {}
    log: List[str] = []
    error: str = ""
    created_at: datetime
    ip_address: str = ""
    cost_usd: float = 0


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def sanitize_error(error: str) -> str:
    if not error:
        return "Unknown error"
    import re

    api_key_patterns = [
        r"sk-[a-zA-Z0-9]{20,}",
        r"[a-zA-Z0-9]{20,}==",
        r"Bearer [a-zA-Z0-9]+",
        r"oss[a-zA-Z0-9]+",
    ]
    sanitized = error
    for pattern in api_key_patterns:
        sanitized = re.sub(pattern, "[REDACTED]", sanitized)
    if len(sanitized) > 200:
        sanitized = sanitized[:200] + "..."
    return sanitized


def validate_file_magic(filepath: str) -> bool:
    with open(filepath, "rb") as f:
        header = f.read(16)

    for magic, fmt in MAGIC_BYTES.items():
        if header.startswith(magic):
            return True

    # Check for common video/audio signatures
    if len(header) >= 12:
        if header[4:8] in [
            b"ftyp",
            b"moov",
            b"mdat",
            b"wide",
            b"free",
            b"skip",
            b"wide",
        ]:
            return True
        if header[4:8] == b"uuid":
            return True

    # Check for WebM/MKV
    if header[0:4] == b"\x1a\x45\xdf\xa3":
        return True

    return False


def validate_file(filename: str, filepath: str) -> tuple[bool, str]:
    ext = Path(filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        return False, f"File extension {ext} not allowed"

    if not validate_file_magic(filepath):
        return False, "File content does not match its extension"

    return True, ""


BASE_DIR = Path(__file__).parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
TEMP_DIR = config.TEMP_DIR

os.makedirs(TEMP_DIR, exist_ok=True)

app.mount("/pages", StaticFiles(directory=str(FRONTEND_DIR / "pages")), name="pages")
app.mount("/styles", StaticFiles(directory=str(FRONTEND_DIR / "styles")), name="styles")
app.mount("/static/api", StaticFiles(directory=str(FRONTEND_DIR / "api")), name="api")

jobs: dict = {}

dashscope.base_http_api_url = config.REGIONAL_URLS.get(
    config.DASHSCOPE_REGION, config.REGIONAL_URLS["singapore"]
)
dashscope.api_key = config.DASHSCOPE_API_KEY


def log_job(job_id: str, message: str):
    if job_id in jobs:
        jobs[job_id].log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")


def cleanup_job(job_id: str):
    if job_id in jobs:
        job = jobs[job_id]
        for path_key in ["filepath", "audio_filepath"]:
            filepath = getattr(job, path_key, None)
            if filepath and os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    pass
        del jobs[job_id]


def extract_audio(video_path: str, audio_path: str) -> float:
    with VideoFileClip(video_path) as clip:
        duration = clip.audio.duration if clip.audio else 0
        if clip.audio:
            clip.audio.write_audiofile(audio_path, logger=None)
    return duration


def get_audio_duration(audio_path: str) -> float:
    with AudioFileClip(audio_path) as clip:
        return clip.duration


def upload_to_oss(local_path: str) -> str:
    auth = oss2.Auth(config.OSS_ACCESS_KEY_ID, config.OSS_ACCESS_KEY_SECRET)
    bucket = oss2.Bucket(auth, config.OSS_ENDPOINT, config.OSS_BUCKET_NAME)
    object_name = f"meetingmind/{uuid.uuid4()}_{Path(local_path).name}"
    result = bucket.put_object_from_file(object_name, local_path)
    if result.status == 200:
        return bucket.sign_url("GET", object_name, 3600, slash_safe=True)
    raise Exception(f"OSS upload failed: {result.status}")


def transcribe(job_id: str, file_url: str) -> tuple[List[dict], float]:
    log_job(job_id, "Transcription task submitted")
    task_response = QwenTranscription.async_call(
        model="qwen3-asr-flash-filetrans",
        file_url=file_url,
        language="th",
        enable_itn=True,
        enable_words=True,
        enable_disfluencies=False,
    )
    task_id = task_response.output.task_id
    log_job(job_id, f"Task ID: {task_id}")

    while True:
        task_result = QwenTranscription.fetch(task=task_id)
        status = task_result.output.task_status
        log_job(job_id, f"Polling... status: {status}")
        if status == "SUCCEEDED":
            break
        if status in ("FAILED", "CANCELED"):
            raise RuntimeError(f"Transcription {status}: {task_result.output}")
        time.sleep(config.POLL_INTERVAL_SECONDS)

    transcription_url = task_result.output.result["transcription_url"]
    data = requests.get(transcription_url).json()
    transcripts = data.get("transcripts", [])

    sentences = []
    sentence_id = 0
    audio_duration = 0

    for transcript in transcripts:
        for sent in transcript.get("sentences", []):
            begin = sent.get("begin_time", 0)
            end = sent.get("end_time", 0)
            audio_duration = max(audio_duration, end / 1000.0)

            words = []
            for w in sent.get("words", []):
                words.append(
                    {
                        "begin_time_ms": w.get("begin_time", 0),
                        "end_time_ms": w.get("end_time", 0),
                        "text": w.get("text", ""),
                        "punctuated_text": w.get("punctuated_text", ""),
                    }
                )

            sentences.append(
                {
                    "id": sentence_id,
                    "begin_time_ms": begin,
                    "end_time_ms": end,
                    "text": sent.get("text", ""),
                    "language": sent.get("language", ""),
                    "emotion": sent.get("emotion", "neutral"),
                    "duration_ms": end - begin,
                    "words": words,
                }
            )
            sentence_id += 1

    return sentences, audio_duration


def summarize(
    transcript: str, context_text: str, images: List[bytes]
) -> tuple[str, dict, float]:
    from openai import OpenAI

    base_url = config.REGIONAL_URLS.get(
        config.DASHSCOPE_REGION, config.REGIONAL_URLS["singapore"]
    ).replace("/api/v1", "/compatible-mode/v1")

    client = OpenAI(
        api_key=config.DASHSCOPE_API_KEY,
        base_url=base_url,
    )

    content = []

    if context_text:
        content.append({"type": "text", "text": f"Additional context: {context_text}"})

    content.append({"type": "text", "text": f"Transcript:\n{transcript}"})

    for img_bytes in images:
        base64_img = base64.b64encode(img_bytes).decode("utf-8")
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"},
            }
        )

    system_prompt = """You are a meeting summary assistant. Generate a well-structured Markdown meeting summary with the following sections:
# Meeting Summary — [Date]

## Overview
[Brief summary of the meeting]

## Discussion
[Key discussion points]

## Action Items
[Any action items identified]

## Decisions
[Any decisions made]

Be concise and professional. Use appropriate language if the transcript is in a different language or multiple language such as thai chinese or english."""

    response = client.chat.completions.create(
        model="qwen3.6-plus",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
        max_tokens=min(MAX_SUMMARY_TOKENS, 8000, 65536),
    )

    summary = response.choices[0].message.content
    usage = response.usage

    token_usage = {
        "summary_input_tokens": usage.prompt_tokens,
        "summary_output_tokens": usage.completion_tokens,
        "summary_total_tokens": usage.total_tokens,
    }

    cost = (usage.total_tokens / 1000) * config.TOKEN_PRICE_PER_1K

    return summary, token_usage, cost


async def process_job(job_id: str):
    job = jobs[job_id]

    try:
        if job.is_audio:
            log_job(job_id, "Processing audio file directly...")
            audio_path = job.filepath
            job.audio_filepath = audio_path

            duration = await asyncio.to_thread(get_audio_duration, audio_path)
            if duration > MAX_AUDIO_DURATION_SECONDS:
                raise ValueError(f"Audio duration exceeds 120 minutes limit")
            log_job(
                job_id, f"Audio duration: {duration:.1f}s ({duration / 60:.1f} min)"
            )
        else:
            log_job(job_id, "Starting audio extraction...")
            audio_path = job.filepath + ".audio.mp3"
            job.audio_filepath = audio_path

            duration = await asyncio.to_thread(extract_audio, job.filepath, audio_path)
            if duration > MAX_AUDIO_DURATION_SECONDS:
                raise ValueError(f"Audio duration exceeds 120 minutes limit")
            log_job(
                job_id,
                f"Audio extracted: {duration:.1f}s ({os.path.getsize(audio_path) / 1024 / 1024:.1f} MB)",
            )

        log_job(job_id, "Uploading to OSS...")
        job.oss_url = await asyncio.to_thread(upload_to_oss, audio_path)
        log_job(job_id, "Audio uploaded to OSS")

        log_job(job_id, "Starting ASR transcription...")
        job.status = "transcribing"
        sentences, audio_duration = await asyncio.to_thread(
            transcribe, job_id, job.oss_url
        )
        job.sentences = [Sentence(**s) for s in sentences]
        job.token_usage["transcription_proxy_tokens"] = int(audio_duration * 8)
        log_job(job_id, f"Transcription complete: {len(sentences)} sentences")

        job.status = "complete"
        log_job(job_id, "Processing complete!")

    except Exception as e:
        job.status = "error"
        job.error = sanitize_error(str(e))
        log_job(job_id, f"Error: {sanitize_error(str(e))}")


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again later."},
    )


@app.get("/")
async def root():
    return FileResponse(str(FRONTEND_DIR / "pages" / "index.html"))


@app.post("/api/upload")
@limiter.limit(f"{config.RATE_LIMIT_UPLOADS_PER_MINUTE}/minute")
async def upload(
    request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...)
):
    client_ip = get_client_ip(request)

    if file.size and file.size > config.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            400, f"File too large. Max size: {config.MAX_FILE_SIZE_MB} MB"
        )

    job_id = str(uuid.uuid4())
    filepath = os.path.join(TEMP_DIR, f"{job_id}_{file.filename}")

    with open(filepath, "wb") as f:
        content = await file.read()
        f.write(content)

    valid, error_msg = validate_file(file.filename, filepath)
    if not valid:
        os.remove(filepath)
        raise HTTPException(400, error_msg)

    filename_lower = file.filename.lower()
    is_audio = filename_lower.endswith(".mp3") or filename_lower.endswith(".mpeg")

    job = JobState(
        job_id=job_id,
        filename=file.filename,
        status="queued",
        filepath=filepath,
        audio_filepath=filepath if is_audio else "",
        oss_url="",
        is_audio=is_audio,
        created_at=datetime.now(),
        ip_address=client_ip,
    )
    jobs[job_id] = job

    log_job(job_id, f"Upload received: {file.filename}")
    log_job(job_id, f"Client IP: {client_ip}")

    background_tasks.add_task(process_job, job_id)

    return {
        "job_id": job_id,
        "filename": file.filename,
        "status": "queued",
        "file_size_mb": round(file.size / (1024 * 1024), 1) if file.size else 0,
        "is_audio": is_audio,
    }


@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    job = jobs[job_id]
    return {
        "job_id": job_id,
        "status": job.status,
        "progress_percent": 100
        if job.status == "complete"
        else 50
        if job.status == "transcribing"
        else 10,
        "log": job.log,
        "error_message": sanitize_error(job.error) if job.status == "error" else None,
    }


@app.get("/api/transcript/{job_id}")
async def get_transcript(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    job = jobs[job_id]
    if job.status != "complete":
        raise HTTPException(400, "Transcription not ready")

    from collections import Counter

    audio_duration = max(
        (job.sentences[-1].end_time_ms / 1000) if job.sentences else 0,
        sum(s.duration_ms for s in job.sentences) / 2000 if job.sentences else 0,
    )

    lang_counter = Counter(s.language for s in job.sentences)
    dominant_lang = lang_counter.most_common(1)[0][0] if lang_counter else "th"

    return {
        "job_id": job_id,
        "audio_duration_seconds": audio_duration,
        "language": dominant_lang,
        "sentences": [s.model_dump() for s in job.sentences],
        "token_usage": job.token_usage,
    }


@app.post("/api/transcript/predict-speakers")
@limiter.limit("5/minute")
async def predict_speakers(request: Request, request_data: SummaryRequest = None):
    if not request_data or not request_data.transcript:
        raise HTTPException(400, "Transcript data required")

    sentences = request_data.transcript.get("sentences", [])
    if not sentences:
        raise HTTPException(400, "No sentences in transcript")

    speaker_count = request_data.speaker_count or 3

    transcript_for_llm = "\n".join(
        [
            f"[{s['begin_time_ms'] // 60000:02d}:{(s['begin_time_ms'] % 60000) // 1000:02d}] {s['text']}"
            for s in sentences
        ]
    )

    try:
        speakers = await predict_speakers_llm(
            transcript_for_llm, len(sentences), speaker_count
        )
        return {"speakers": speakers}
    except Exception as e:
        raise HTTPException(500, sanitize_error(str(e)))


async def predict_speakers_llm(
    transcript_text: str, num_sentences: int, speaker_count: int = 3
) -> list:
    from openai import OpenAI

    base_url = config.REGIONAL_URLS.get(
        config.DASHSCOPE_REGION, config.REGIONAL_URLS["singapore"]
    ).replace("/api/v1", "/compatible-mode/v1")

    client = OpenAI(
        api_key=config.DASHSCOPE_API_KEY,
        base_url=base_url,
    )

    speaker_labels = ", ".join([f"Speaker {chr(65 + i)}" for i in range(speaker_count)])

    system_prompt = f"""You are a meeting analyst. Analyze the transcript and assign speaker labels to each sentence.
Group sentences by speaker based on:
1. Time proximity (sentences close together are likely same speaker)
2. Content context (who is addressing whom, names mentioned)
3. Speaking patterns and language used

If names are mentioned in the transcript (e.g., someone says "I'm John" or addresses someone), use those names as speaker labels.
Otherwise, use labels like "Person A", "Person B", etc. up to {speaker_count} speakers.
Keep speaker labels short (max 15 characters).

Return ONLY a JSON array of speaker labels, one per sentence in order.
Example output: ["John", "John", "Sarah", "John", "Mike"]

Respond with ONLY the JSON array, no explanation."""

    response = client.chat.completions.create(
        model="qwen3.6-plus",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Transcript:\n{transcript_text[:8000]}"},
        ],
        max_tokens=min(1024, num_sentences * 20),
    )

    result_text = response.choices[0].message.content.strip()

    import json
    import re

    json_match = re.search(r"\[.*\]", result_text, re.DOTALL)
    if json_match:
        try:
            speakers = json.loads(json_match.group())
            if isinstance(speakers, list) and len(speakers) == num_sentences:
                return speakers
        except:
            pass

    return [f"Person {chr(65 + (i % speaker_count))}" for i in range(num_sentences)]


@app.post("/api/summary/{job_id}")
@limiter.limit("5/minute")
async def create_summary(
    request: Request, job_id: str, request_data: SummaryRequest = None
):
    transcript_text = None
    job = None

    if request_data and request_data.transcript:
        sentences = request_data.transcript.get("sentences", [])
        transcript_text = "\n".join(
            [
                f"[{s['begin_time_ms'] // 60000:02d}:{(s['begin_time_ms'] % 60000) // 1000:02d}] {s['text']}"
                for s in sentences
            ]
        )
    elif job_id in jobs:
        job = jobs[job_id]
        if len(job.sentences) == 0:
            raise HTTPException(400, "No transcript available")
        transcript_text = "\n".join(
            [
                f"[{s.begin_time_ms // 60000:02d}:{(s.begin_time_ms % 60000) // 1000:02d}] {s.text}"
                for s in job.sentences
            ]
        )
    else:
        raise HTTPException(404, "Job not found and no transcript provided")

    if job:
        job.status = "summarizing"
        log_job(job_id, "Generating summary...")

    try:
        context_text = request_data.context_text if request_data else ""
        summary, token_usage, cost = summarize(transcript_text, context_text or "", [])

        if job:
            job.summary_markdown = summary
            job.token_usage.update(token_usage)
            job.cost_usd = cost
            job.status = "complete"
            log_job(job_id, f"Summary generated! Cost: ${cost:.4f}")

        return {
            "job_id": job_id,
            "summary_markdown": summary,
            "token_usage": token_usage,
            "cost_usd": cost,
        }
    except Exception as e:
        import traceback

        error_detail = sanitize_error(str(e))
        if job:
            log_job(job_id, f"Summary error: {error_detail}")
            log_job(job_id, f"Trace: {traceback.format_exc()}")
            job.status = "error"
            job.error = error_detail
        raise HTTPException(500, error_detail)


@app.get("/api/download/{job_id}")
async def download_summary(job_id: str, include_transcript: bool = Query(False)):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    job = jobs[job_id]

    content = job.summary_markdown

    if include_transcript and job.sentences:
        content += "\n\n---\n\n## Full Transcript\n\n"
        for s in job.sentences:
            mins = s.begin_time_ms // 60000
            secs = (s.begin_time_ms % 60000) // 1000
            content += f"[{mins:02d}:{secs:02d}] {s.text}\n"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"meeting_summary_{timestamp}.md"

    return StreamingResponse(
        io.BytesIO(content.encode()),
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.delete("/api/job/{job_id}")
async def delete_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    cleanup_job(job_id)
    return {"deleted": True}


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "asr_model": "qwen3-asr-flash-filetrans",
        "llm_model": "qwen3.6-plus",
    }


@app.on_event("startup")
async def startup():
    os.makedirs(TEMP_DIR, exist_ok=True)


import io
