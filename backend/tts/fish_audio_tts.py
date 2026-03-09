import json
from pathlib import Path

import requests

from backend.config.settings import (
    FISH_AUDIO_API_KEY, FISH_AUDIO_VOICE_ID, FISH_AUDIO_MODEL, AUDIO_DIR,
)
from backend.storage.models import Project, ScriptSection, ApiUsageLog


BASE_URL = "https://api.fish.audio"


def generate_voiceover(db, project_id: int, voice_id: str = ""):
    """Generate TTS audio for all script sections using Fish Audio."""
    project = db.query(Project).get(project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")

    if not project.script_approved:
        raise ValueError("Script must be approved before generating voiceover")

    if not FISH_AUDIO_API_KEY:
        raise ValueError("FISH_AUDIO_API_KEY not configured in .env")

    project.status = "voiceover"
    db.commit()

    vid = voice_id or FISH_AUDIO_VOICE_ID
    if project.channel and project.channel.voice_id:
        vid = project.channel.voice_id

    # Concatenate all narration text
    sections = (
        db.query(ScriptSection)
        .filter_by(project_id=project_id)
        .order_by(ScriptSection.position)
        .all()
    )
    if not sections:
        script_data = json.loads(project.script) if project.script.startswith("{") else {}
        full_text = "\n\n".join(
            s.get("narration", "") for s in script_data.get("sections", [])
        ) or project.script
    else:
        full_text = "\n\n".join(s.narration_text for s in sections if s.narration_text)

    if not full_text.strip():
        raise ValueError("No narration text found in script sections")

    total_chars = len(full_text)

    # Generate audio via Fish Audio API
    headers = {
        "Authorization": f"Bearer {FISH_AUDIO_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "text": full_text,
        "format": "mp3",
        "mp3_bitrate": 128,
    }

    if vid:
        payload["reference_id"] = vid

    resp = requests.post(
        f"{BASE_URL}/v1/tts",
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
    # Fish Audio: ~$0.015 per 1000 chars
    estimated_cost = (total_chars / 1000) * 0.015
    log = ApiUsageLog(
        service="fish_audio",
        endpoint="v1/tts",
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
    """List available Fish Audio voices (public models)."""
    headers = {"Authorization": f"Bearer {FISH_AUDIO_API_KEY}"}
    resp = requests.get(
        f"{BASE_URL}/model",
        headers=headers,
        params={"page_size": 20, "sort_by": "task_count"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    items = data.get("items", data) if isinstance(data, dict) else data
    return [
        {
            "voice_id": v.get("_id", v.get("id", "")),
            "name": v.get("title", v.get("name", "")),
            "category": v.get("type", ""),
            "labels": {"language": v.get("languages", [])},
        }
        for v in (items if isinstance(items, list) else [])
    ]
