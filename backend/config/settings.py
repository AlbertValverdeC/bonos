import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
AUDIO_DIR = DATA_DIR / "audio"
FOOTAGE_DIR = DATA_DIR / "footage"
THUMBNAILS_DIR = DATA_DIR / "thumbnails"
OUTPUT_DIR = DATA_DIR / "output"

for d in [DATA_DIR, AUDIO_DIR, FOOTAGE_DIR, THUMBNAILS_DIR, OUTPUT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'bonos.db'}")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SCRIPTWRITER_MODEL = os.getenv("SCRIPTWRITER_MODEL", "gpt-4o")
SCRIPTWRITER_TEMPERATURE = float(os.getenv("SCRIPTWRITER_TEMPERATURE", "0.7"))

# ElevenLabs (legacy)
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")
ELEVENLABS_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")

# Fish Audio (preferred TTS)
FISH_AUDIO_API_KEY = os.getenv("FISH_AUDIO_API_KEY", "")
FISH_AUDIO_VOICE_ID = os.getenv("FISH_AUDIO_VOICE_ID", "")
FISH_AUDIO_MODEL = os.getenv("FISH_AUDIO_MODEL", "speech-1.6")

# Pexels
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

# YouTube
YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID", "")
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET", "")
YOUTUBE_REFRESH_TOKEN = os.getenv("YOUTUBE_REFRESH_TOKEN", "")

# Server
FLASK_PORT = int(os.getenv("FLASK_PORT", "8001"))
VITE_PORT = int(os.getenv("VITE_PORT", "5177"))
