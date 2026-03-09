import json
from pathlib import Path

import requests
from openai import OpenAI

from backend.config.settings import PEXELS_API_KEY, OPENAI_API_KEY, FOOTAGE_DIR
from backend.storage.models import Project, ScriptSection, FootageClip, ApiUsageLog


PEXELS_BASE = "https://api.pexels.com"


def search_footage(db, project_id: int):
    """Search and download stock footage for each script section."""
    project = db.query(Project).get(project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")

    project.status = "footage"
    db.commit()

    sections = db.query(ScriptSection).filter_by(project_id=project_id).order_by(ScriptSection.position).all()
    if not sections:
        raise ValueError("No script sections found. Generate a script first.")

    # Extract search queries from visual instructions using AI
    queries = _extract_search_queries(sections)

    total_clips = 0
    project_dir = FOOTAGE_DIR / f"project_{project_id}"
    project_dir.mkdir(exist_ok=True)

    for section, query in zip(sections, queries):
        if not query:
            continue

        clips = _search_pexels_videos(query, per_page=3)
        for clip_data in clips:
            # Download the clip
            video_files = clip_data.get("video_files", [])
            # Prefer HD quality
            best = _pick_best_quality(video_files)
            if not best:
                continue

            filename = f"section_{section.position}_{clip_data['id']}.mp4"
            filepath = project_dir / filename

            if not filepath.exists():
                _download_file(best["link"], filepath)

            clip = FootageClip(
                project_id=project_id,
                section_id=section.id,
                source="pexels",
                source_id=str(clip_data["id"]),
                source_url=clip_data.get("url", ""),
                local_filename=str(filepath.relative_to(FOOTAGE_DIR)),
                duration=clip_data.get("duration", 0),
                width=best.get("width", 0),
                height=best.get("height", 0),
                search_query=query,
                selected=0,
            )
            db.add(clip)
            total_clips += 1

    # Auto-select first clip per section
    db.commit()
    for section in sections:
        first_clip = (
            db.query(FootageClip)
            .filter_by(project_id=project_id, section_id=section.id)
            .first()
        )
        if first_clip:
            first_clip.selected = 1

    project.status = "assembling"
    project.current_step = 5
    db.commit()

    return {"total_clips": total_clips}


def _extract_search_queries(sections: list[ScriptSection]) -> list[str]:
    """Use AI to extract English search queries from visual instructions."""
    client = OpenAI(api_key=OPENAI_API_KEY)

    visuals = [
        f"Section {s.position} ({s.section_type}): {s.visual_instructions}"
        for s in sections
        if s.visual_instructions
    ]

    if not visuals:
        # Fallback: extract from narration
        visuals = [
            f"Section {s.position}: {s.narration_text[:200]}"
            for s in sections
        ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.3,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": """Extract 1 short English search query for stock video footage for each section.
Return JSON: {"queries": ["query1", "query2", ...]}
Queries should be simple, concrete, visual terms (e.g. "city skyline night", "person typing laptop", "stock market graph").
One query per section, in the same order.""",
            },
            {"role": "user", "content": "\n".join(visuals)},
        ],
    )

    data = json.loads(response.choices[0].message.content)
    queries = data.get("queries", [])

    # Pad to match sections count
    while len(queries) < len(sections):
        queries.append("")

    return queries


def _search_pexels_videos(query: str, per_page: int = 3) -> list[dict]:
    """Search Pexels for videos."""
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": per_page, "orientation": "landscape"}

    resp = requests.get(f"{PEXELS_BASE}/videos/search", headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("videos", [])


def _pick_best_quality(video_files: list[dict]) -> dict | None:
    """Pick the best HD quality file (prefer 1920x1080)."""
    sorted_files = sorted(video_files, key=lambda f: abs(f.get("height", 0) - 1080))
    for f in sorted_files:
        if f.get("height", 0) >= 720:
            return f
    return sorted_files[0] if sorted_files else None


def _download_file(url: str, filepath: Path):
    """Download a file from URL to local path."""
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    with open(filepath, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
