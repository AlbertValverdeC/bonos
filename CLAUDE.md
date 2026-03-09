# YouTube Faceless Pipeline - "Bonos"

## Project Overview
Automated pipeline for faceless YouTube channel production using AI.
Pipeline: Idea → Script (AI) → Review (human) → Voiceover (TTS) → Stock Footage → Video Assembly → Thumbnail → YouTube Upload

## Tech Stack
- **Backend**: Python 3.12, Flask on port 8001
- **Frontend**: React 19 + TypeScript + Vite on port 5177, Tailwind CSS
- **Database**: SQLite at data/bonos.db
- **APIs**: OpenAI (scripts/thumbnails), ElevenLabs (TTS), Pexels (footage), YouTube Data API v3

## Commands
- `make dev` — run backend + frontend concurrently
- `make backend` — run Flask backend only
- `make frontend` — run Vite frontend only
- `make install` — install all dependencies
- `make lint` — lint backend (ruff) + frontend (eslint)
- `make format` — format backend (ruff)

## Architecture
- Backend uses Flask blueprints, SQLAlchemy models, background ThreadPoolExecutor
- Frontend proxies /api to backend via Vite config
- Pipeline progress streamed via SSE (Server-Sent Events)
- Human-in-the-loop: script must be approved before pipeline continues
- All media files stored in data/ (gitignored)

## Ports
- Flask backend: 8001
- Vite frontend: 5177

## Language
- UI and conversations in Spanish (castellano)
- Code comments and variable names in English
