import traceback

from flask import Blueprint, jsonify, request

from backend.research.analyzer import (
    discover_niches, generate_video_ideas, analyze_niche_with_data, quick_niche_scan,
    analyze_scan_results,
)
from backend.research.deep_scanner import deep_scan, check_spanish_gap
from backend.research.youtube_api import YOUTUBE_API_KEY
from backend.pipeline.tasks import executor
from backend.pipeline.event_bus import event_bus
from backend.storage.database import get_db
from backend.storage.models import Project

bp = Blueprint("research", __name__, url_prefix="/api/research")

# In-memory store for async research results
_research_results = {}
_research_status = {}


@bp.route("/status-check", methods=["GET"])
def api_status_check():
    """Check which data sources are available."""
    has_youtube = bool(YOUTUBE_API_KEY)
    try:
        from backend.research.trends import HAS_TRENDS
        has_trends = True
    except Exception:
        has_trends = False

    return jsonify({
        "youtube_api": has_youtube,
        "google_trends": has_trends,
        "openai": True,  # Required, always assumed available
        "message": (
            "Datos reales disponibles" if has_youtube else
            "Sin YouTube API key — el análisis usará estimaciones de IA. "
            "Para datos reales, configura YOUTUBE_API_KEY en .env"
        ),
    })


@bp.route("/discover", methods=["POST"])
def api_discover_niches():
    """Discover best niches. Uses real YouTube data when API key is available."""
    data = request.get_json() or {}
    preferences = data.get("preferences", {})

    research_id = "latest"
    _research_status[research_id] = "running"

    def _run():
        try:
            event_bus.emit("research:start", {"status": "discovering_niches"})
            result = discover_niches(preferences)
            _research_results[research_id] = result
            _research_status[research_id] = "completed"
            event_bus.emit("research:complete", {
                "status": "niches_ready",
                "count": len(result.get("niches", [])),
            })
        except Exception as e:
            _research_status[research_id] = "error"
            _research_results[research_id] = {"error": str(e)}
            event_bus.emit("research:error", {"error": str(e)})
            traceback.print_exc()

    executor.submit(_run)
    return jsonify({"status": "started", "research_id": research_id})


@bp.route("/deep-analyze", methods=["POST"])
def api_deep_analyze():
    """Deep analysis of a specific niche with ALL real data sources."""
    data = request.get_json() or {}
    niche = data.get("niche", "")
    language = data.get("language", "es")

    if not niche:
        return jsonify({"error": "niche is required"}), 400

    research_id = f"deep_{niche}"
    _research_status[research_id] = "running"

    def _run():
        try:
            event_bus.emit("research:start", {"status": "deep_analysis", "niche": niche})
            result = analyze_niche_with_data(niche, language)
            _research_results[research_id] = result
            _research_status[research_id] = "completed"
            event_bus.emit("research:complete", {"status": "deep_ready", "niche": niche})
        except Exception as e:
            _research_status[research_id] = "error"
            _research_results[research_id] = {"error": str(e)}
            event_bus.emit("research:error", {"error": str(e)})
            traceback.print_exc()

    executor.submit(_run)
    return jsonify({"status": "started", "research_id": research_id})


@bp.route("/ideas", methods=["POST"])
def api_generate_ideas():
    """Generate video ideas backed by real data."""
    data = request.get_json() or {}
    niche = data.get("niche", "")
    count = data.get("count", 15)

    if not niche:
        return jsonify({"error": "niche is required"}), 400

    research_id = f"ideas_{niche}"
    _research_status[research_id] = "running"

    def _run():
        try:
            event_bus.emit("research:start", {"status": "generating_ideas", "niche": niche})
            result = generate_video_ideas(niche, count)
            _research_results[research_id] = result
            _research_status[research_id] = "completed"
            event_bus.emit("research:complete", {
                "status": "ideas_ready",
                "niche": niche,
                "count": len(result.get("ideas", [])),
            })
        except Exception as e:
            _research_status[research_id] = "error"
            _research_results[research_id] = {"error": str(e)}
            event_bus.emit("research:error", {"error": str(e)})
            traceback.print_exc()

    executor.submit(_run)
    return jsonify({"status": "started", "research_id": research_id})


@bp.route("/deep-scan", methods=["POST"])
def api_deep_scan():
    """Deep scan: search hundreds of keywords to find real outliers.

    This is the DATA FIRST approach — scans YouTube for actual outlier videos
    from small channels, then has AI analyze the results.
    """
    data = request.get_json() or {}
    categories = data.get("categories")  # None = scan ALL categories

    research_id = "deep_scan"
    _research_status[research_id] = "running"
    _research_results[research_id] = {"progress": "starting..."}

    def _run():
        try:
            def progress(msg, pct):
                _research_results[research_id] = {"progress": msg, "pct": pct}
                event_bus.emit("research:progress", {"message": msg, "pct": pct})

            event_bus.emit("research:start", {"status": "deep_scanning"})

            # Phase 1: Massive scan
            scan_data = deep_scan(
                categories=categories,
                progress_callback=progress,
            )

            # Phase 2: Check Spanish gap for top outliers
            progress("Analizando gap EN→ES...", 85)
            spanish_gap = check_spanish_gap(scan_data["outliers"], top_n=10)
            scan_data["spanish_gap"] = spanish_gap

            # Phase 3: AI interprets all the real data
            progress("IA interpretando datos reales...", 90)
            ai_analysis = analyze_scan_results(scan_data)
            scan_data["ai_analysis"] = ai_analysis

            _research_results[research_id] = scan_data
            _research_status[research_id] = "completed"
            event_bus.emit("research:complete", {
                "status": "deep_scan_ready",
                "outliers": len(scan_data["outliers"]),
                "categories": len(scan_data["categories_ranked"]),
            })
        except Exception as e:
            _research_status[research_id] = "error"
            _research_results[research_id] = {"error": str(e)}
            event_bus.emit("research:error", {"error": str(e)})
            traceback.print_exc()

    executor.submit(_run)
    return jsonify({"status": "started", "research_id": research_id})


@bp.route("/quick-scan", methods=["POST"])
def api_quick_scan():
    """Quick comparison of multiple niches with real data."""
    data = request.get_json() or {}
    niches = data.get("niches", [])

    if not niches:
        return jsonify({"error": "niches list is required"}), 400

    research_id = "quick_scan"
    _research_status[research_id] = "running"

    def _run():
        try:
            result = quick_niche_scan(niches)
            _research_results[research_id] = result
            _research_status[research_id] = "completed"
        except Exception as e:
            _research_status[research_id] = "error"
            _research_results[research_id] = {"error": str(e)}
            traceback.print_exc()

    executor.submit(_run)
    return jsonify({"status": "started", "research_id": research_id})


@bp.route("/status/<path:research_id>", methods=["GET"])
def api_research_status(research_id):
    status = _research_status.get(research_id, "not_found")
    return jsonify({"research_id": research_id, "status": status})


@bp.route("/results/<path:research_id>", methods=["GET"])
def api_research_results(research_id):
    status = _research_status.get(research_id, "not_found")
    results = _research_results.get(research_id)

    if status == "not_found":
        return jsonify({"error": "Research not found"}), 404

    return jsonify({
        "research_id": research_id,
        "status": status,
        "data": results,
    })


@bp.route("/idea-to-project", methods=["POST"])
def api_idea_to_project():
    """Convert a research idea into a pipeline project."""
    data = request.get_json() or {}
    title = data.get("title", "")
    topic = data.get("topic", title)
    channel_id = data.get("channel_id")

    if not topic:
        return jsonify({"error": "title or topic is required"}), 400

    db = get_db()
    try:
        project = Project(
            topic=topic,
            title=title,
            channel_id=channel_id,
            status="idea",
            current_step=0,
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return jsonify(project.to_dict()), 201
    finally:
        db.close()
