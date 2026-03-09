import json
import subprocess
from pathlib import Path

from backend.config.settings import AUDIO_DIR, FOOTAGE_DIR, OUTPUT_DIR
from backend.storage.models import Project, ScriptSection, FootageClip


def assemble_video(db, project_id: int):
    """Assemble final video from audio + selected footage clips using ffmpeg."""
    project = db.query(Project).get(project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")

    project.status = "assembling"
    db.commit()

    audio_path = AUDIO_DIR / project.audio_filename
    if not audio_path.exists():
        raise ValueError(f"Audio file not found: {audio_path}")

    # Get selected clips in section order
    sections = (
        db.query(ScriptSection)
        .filter_by(project_id=project_id)
        .order_by(ScriptSection.position)
        .all()
    )

    selected_clips = []
    for section in sections:
        clip = (
            db.query(FootageClip)
            .filter_by(project_id=project_id, section_id=section.id, selected=1)
            .first()
        )
        if clip and clip.local_filename:
            clip_path = FOOTAGE_DIR / clip.local_filename
            if clip_path.exists():
                selected_clips.append({
                    "path": str(clip_path),
                    "duration": section.duration_estimate or clip.duration or 10,
                })

    if not selected_clips:
        raise ValueError("No footage clips selected. Search for footage first.")

    # Get audio duration using ffprobe
    audio_duration = _get_duration(str(audio_path))

    # Create concat file for ffmpeg
    output_path = OUTPUT_DIR / f"project_{project_id}.mp4"
    concat_file = OUTPUT_DIR / f"project_{project_id}_concat.txt"

    # Build clip list that covers the full audio duration
    clip_entries = []
    total_video_duration = 0
    clip_idx = 0

    while total_video_duration < audio_duration:
        clip = selected_clips[clip_idx % len(selected_clips)]
        clip_entries.append(f"file '{clip['path']}'")
        clip_duration = _get_duration(clip["path"])
        total_video_duration += clip_duration
        clip_idx += 1

    concat_file.write_text("\n".join(clip_entries))

    # Assemble with ffmpeg: concat clips + overlay audio
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-i", str(audio_path),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        "-map", "0:v:0", "-map", "1:a:0",
        "-shortest",
        "-movflags", "+faststart",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr[-500:]}")

    # Cleanup concat file
    concat_file.unlink(missing_ok=True)

    project.video_filename = f"project_{project_id}.mp4"
    project.status = "thumbnail"
    project.current_step = 6
    db.commit()

    return {"filename": project.video_filename, "duration": audio_duration}


def _get_duration(filepath: str) -> float:
    """Get media duration in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        filepath,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    try:
        return float(result.stdout.strip())
    except (ValueError, AttributeError):
        return 0.0
