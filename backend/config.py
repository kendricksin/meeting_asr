import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_REGION = os.getenv("DASHSCOPE_REGION", "singapore")

OSS_ACCESS_KEY_ID = os.getenv("OSS_ACCESS_KEY_ID", "")
OSS_ACCESS_KEY_SECRET = os.getenv("OSS_ACCESS_KEY_SECRET", "")
OSS_BUCKET_NAME = os.getenv("OSS_BUCKET_NAME", "")
OSS_ENDPOINT = os.getenv("OSS_ENDPOINT", "")

MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "500"))
MAX_AUDIO_DURATION_MINUTES = int(os.getenv("MAX_AUDIO_DURATION_MINUTES", "120"))
JOB_TTL_SECONDS = int(os.getenv("JOB_TTL_SECONDS", "3600"))
TEMP_DIR = os.getenv("TEMP_DIR", "/tmp/meetingmind")
TOKEN_PRICE_PER_1K = float(os.getenv("TOKEN_PRICE_PER_1K", "0.0002"))
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "15"))
MAX_SUMMARY_TOKENS = min(8000, max(1, int(os.getenv("MAX_SUMMARY_TOKENS", "8000"))))
RATE_LIMIT_UPLOADS_PER_MINUTE = int(os.getenv("RATE_LIMIT_UPLOADS_PER_MINUTE", "10"))
RATE_LIMIT_SUMMARIES_PER_MINUTE = int(os.getenv("RATE_LIMIT_SUMMARIES_PER_MINUTE", "5"))

REGIONAL_URLS = {
    "singapore": "https://dashscope-intl.aliyuncs.com/api/v1",
    "beijing": "https://dashscope.aliyuncs.com/api/v1",
    "us": "https://dashscope-us.aliyuncs.com/api/v1",
}
