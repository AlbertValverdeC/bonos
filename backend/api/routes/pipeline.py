import json

from flask import Blueprint, Response, jsonify, request

from backend.pipeline.event_bus import event_bus
from backend.pipeline.tasks import run_pipeline_step
from backend.scriptwriter.generator import generate_script, suggest_ideas
from backend.tts.fish_audio_tts import generate_voiceover
from backend.footage.pexels import search_footage
from backend.video.assembler import assemble_video
from backend.video.thumbnail import generate_thumbnail
from backend.youtube.uploader import upload_to_youtube
from backend.storage.database import get_db
from backend.storage.models import Project, ScriptSection

bp = Blueprint("pipeline", __name__, url_prefix="/api")


# --- Script generation ---

@bp.route("/projects/<int:project_id>/generate-script", methods=["POST"])
def api_generate_script(project_id):
    data = request.get_json() or {}
    duration = data.get("duration_minutes", 15)
    extra = data.get("extra_instructions", "")

    run_pipeline_step(
        project_id, "generate_script", generate_script,
        duration_minutes=duration, extra_instructions=extra,
    )
    return jsonify({"status": "started", "step": "generate_script"})


@bp.route("/projects/<int:project_id>/approve-script", methods=["PUT"])
def api_approve_script(project_id):
    db = get_db()
    try:
        project = db.query(Project).get(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        project.script_approved = 1
        project.status = "script_review"
        project.current_step = 3
        db.commit()
        return jsonify({"ok": True, "status": project.status})
    finally:
        db.close()


@bp.route("/projects/<int:project_id>/script", methods=["PUT"])
def api_update_script(project_id):
    """Manually edit the script."""
    data = request.get_json()
    db = get_db()
    try:
        project = db.query(Project).get(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        if "sections" in data:
            # Update individual sections
            db.query(ScriptSection).filter_by(project_id=project_id).delete()
            for i, s in enumerate(data["sections"]):
                section = ScriptSection(
                    project_id=project_id,
                    position=i,
                    section_type=s.get("section_type", "body"),
                    narration_text=s.get("narration_text", ""),
                    visual_instructions=s.get("visual_instructions", ""),
                    duration_estimate=s.get("duration_estimate", 0),
                )
                db.add(section)

        if "title" in data:
            project.title = data["title"]

        if "metadata_json" in data:
            project.metadata_json = data["metadata_json"]

        # Reset approval when script is edited
        project.script_approved = 0
        db.commit()
        return jsonify(project.to_dict(include_sections=True))
    finally:
        db.close()


@bp.route("/projects/<int:project_id>/suggest-ideas", methods=["GET"])
def api_suggest_ideas(project_id):
    db = get_db()
    try:
        project = db.query(Project).get(project_id)
        niche = ""
        if project and project.channel:
            niche = project.channel.niche
        if not niche:
            niche = request.args.get("niche", "general")

        ideas = suggest_ideas(niche)
        return jsonify({"ideas": ideas})
    finally:
        db.close()


# --- Voiceover ---

@bp.route("/projects/<int:project_id>/generate-voiceover", methods=["POST"])
def api_generate_voiceover(project_id):
    data = request.get_json() or {}
    run_pipeline_step(
        project_id, "generate_voiceover", generate_voiceover,
        voice_id=data.get("voice_id", ""),
    )
    return jsonify({"status": "started", "step": "generate_voiceover"})


# --- Footage ---

@bp.route("/projects/<int:project_id>/search-footage", methods=["POST"])
def api_search_footage(project_id):
    run_pipeline_step(project_id, "search_footage", search_footage)
    return jsonify({"status": "started", "step": "search_footage"})


# --- Video assembly ---

@bp.route("/projects/<int:project_id>/assemble-video", methods=["POST"])
def api_assemble_video(project_id):
    run_pipeline_step(project_id, "assemble_video", assemble_video)
    return jsonify({"status": "started", "step": "assemble_video"})


# --- Thumbnail ---

@bp.route("/projects/<int:project_id>/generate-thumbnail", methods=["POST"])
def api_generate_thumbnail(project_id):
    run_pipeline_step(project_id, "generate_thumbnail", generate_thumbnail)
    return jsonify({"status": "started", "step": "generate_thumbnail"})


# --- YouTube upload ---

@bp.route("/projects/<int:project_id>/upload-youtube", methods=["POST"])
def api_upload_youtube(project_id):
    data = request.get_json() or {}
    privacy = data.get("privacy", "private")
    run_pipeline_step(
        project_id, "upload_youtube", upload_to_youtube,
        privacy=privacy,
    )
    return jsonify({"status": "started", "step": "upload_youtube"})


# --- Auto-pipeline (run all steps after script approval) ---

@bp.route("/projects/<int:project_id>/run-pipeline", methods=["POST"])
def api_run_pipeline(project_id):
    """Run the full pipeline from current status onward."""
    db = get_db()
    try:
        project = db.query(Project).get(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        status = project.status

        if status == "idea":
            data = request.get_json() or {}
            run_pipeline_step(
                project_id, "generate_script", generate_script,
                duration_minutes=data.get("duration_minutes", 15),
            )
            return jsonify({"status": "started", "from_step": "generate_script"})

        if status == "script_review" and project.script_approved:
            # Chain: voiceover → footage → assembly → thumbnail
            run_pipeline_step(project_id, "auto_pipeline", _auto_pipeline_after_approval)
            return jsonify({"status": "started", "from_step": "voiceover"})

        return jsonify({"error": f"Cannot auto-run from status: {status}"}), 400
    finally:
        db.close()


def _auto_pipeline_after_approval(db, project_id: int):
    """Run voiceover → footage → assembly → thumbnail sequentially."""
    generate_voiceover(db, project_id)
    search_footage(db, project_id)
    assemble_video(db, project_id)
    generate_thumbnail(db, project_id)
    return {"completed": "full_pipeline"}


# --- SSE Events ---

@bp.route("/pipeline/events", methods=["GET"])
def api_pipeline_events():
    q = event_bus.subscribe()
    return Response(
        event_bus.stream(q),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@bp.route("/pipeline/events/history", methods=["GET"])
def api_pipeline_events_history():
    limit = request.args.get("limit", 50, type=int)
    return jsonify(event_bus.get_history(limit))
