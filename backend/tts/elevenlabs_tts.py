import json
from pathlib import Path

import requests

from backend.config.settings import (
    ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL, AUDIO_DIR,
)
from backend.storage.models import Project, ScriptSection, ApiUsageLog


BASE_URL = "https://api.elevenlabs.io/v1"


def generate_voiceover(db, project_id: int, voice_id: str = ""):
    """Generate TTS audio for all script sections."""
    project = db.query(Project).get(project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")

    if not project.script_approved:
        raise ValueError("Script must be approved before generating voiceover")

    project.status = "voiceover"
    db.commit()

    vid = voice_id or ELEVENLABS_VOICE_ID
    if project.channel and project.channel.voice_id:
        vid = project.channel.voice_id

    if not vid:
        raise ValueError("No voice ID configured. Set ELEVENLABS_VOICE_ID or configure the channel.")

    # Concatenate all narration text
    sections = db.query(ScriptSection).filter_by(project_id=project_id).order_by(ScriptSection.position).all()
    if not sections:
        # Fallback: use raw script text
        script_data = json.loads(project.script) if project.script.startswith("{") else {}
        full_text = "\n\n".join(
            s.get("narration", "") for s in script_data.get("sections", [])
        ) or project.script
    else:
        full_text = "\n\n".join(s.narration_text for s in sections if s.narration_text)

    if not full_text.strip():
        raise ValueError("No narration text found in script sections")

    total_chars = len(full_text)

    # Generate audio via ElevenLabs API
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "text": full_text,
        "model_id": ELEVENLABS_MODEL,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.3,
        },
    }

    resp = requests.post(
        f"{BASE_URL}/text-to-speech/{vid}",
        headers=headers,
        json=payload,
        timeout=300,
    )
    resp.raise_for_status()

    # Save audio file
    filename = f"project_{project_id}.mp3"
    filepath = AUDIO_DIR / filename
    filepath.write_bytes(resp.content)

    # Estimate duration (~150 words per minute in Spanish, ~5 chars per word)
    estimated_duration = (total_chars / 5) / 150 * 60

    # Log API usage
    # ElevenLabs Creator: $22/100min ≈ $0.0037/sec ≈ $0.22/min
    estimated_cost = (estimated_duration / 60) * 0.22
    log = ApiUsageLog(
        service="elevenlabs",
        endpoint=f"tts/{vid}",
        characters=total_chars,
        estimated_cost=round(estimated_cost, 4),
        project_id=project_id,
    )
    db.add(log)

    # Update project
    project.audio_filename = filename
    project.audio_duration = estimated_duration
    project.status = "footage"
    project.current_step = 4
    db.commit()

    return {"filename": filename, "duration": estimated_duration, "characters": total_chars}


def list_voices() -> list[dict]:
    """List available ElevenLabs voices."""
    headers = {"xi-api-key": ELEVENLABS_API_KEY}
    resp = requests.get(f"{BASE_URL}/voices", headers=headers, timeout=30)
    resp.raise_for_status()
    voices = resp.json().get("voices", [])
    return [
        {
            "voice_id": v["voice_id"],
            "name": v["name"],
            "category": v.get("category", ""),
            "labels": v.get("labels", {}),
        }
        for v in voices
    ]
