from flask import Blueprint, jsonify, request, send_from_directory

from backend.config import settings
from backend.tts.fish_audio_tts import list_voices

bp = Blueprint("settings", __name__, url_prefix="/api/settings")


def _mask_key(key: str) -> str:
    if not key or len(key) < 8:
        return "***" if key else ""
    return key[:4] + "..." + key[-4:]


@bp.route("/keys", methods=["GET"])
def get_keys():
    return jsonify({
        "openai": _mask_key(settings.OPENAI_API_KEY),
        "fish_audio": _mask_key(settings.FISH_AUDIO_API_KEY),
        "elevenlabs": _mask_key(settings.ELEVENLABS_API_KEY),
        "pexels": _mask_key(settings.PEXELS_API_KEY),
        "youtube_client_id": _mask_key(settings.YOUTUBE_CLIENT_ID),
        "fish_audio_voice_id": settings.FISH_AUDIO_VOICE_ID or "",
        "elevenlabs_voice_id": settings.ELEVENLABS_VOICE_ID or "",
        "elevenlabs_model": settings.ELEVENLABS_MODEL,
        "scriptwriter_model": settings.SCRIPTWRITER_MODEL,
    })


@bp.route("/keys/test", methods=["POST"])
def test_keys():
    """Test API connectivity."""
    results = {}

    # Test OpenAI
    if settings.OPENAI_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            client.models.list()
            results["openai"] = {"ok": True}
        except Exception as e:
            results["openai"] = {"ok": False, "error": str(e)}
    else:
        results["openai"] = {"ok": False, "error": "No API key"}

    # Test Fish Audio
    if settings.FISH_AUDIO_API_KEY:
        try:
            voices = list_voices()
            results["fish_audio"] = {"ok": True, "voices": len(voices)}
        except Exception as e:
            results["fish_audio"] = {"ok": False, "error": str(e)}
    else:
        results["fish_audio"] = {"ok": False, "error": "No API key"}

    # Test Pexels
    if settings.PEXELS_API_KEY:
        try:
            import requests as req
            resp = req.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": settings.PEXELS_API_KEY},
                params={"query": "test", "per_page": 1},
                timeout=10,
            )
            resp.raise_for_status()
            results["pexels"] = {"ok": True}
        except Exception as e:
            results["pexels"] = {"ok": False, "error": str(e)}
    else:
        results["pexels"] = {"ok": False, "error": "No API key"}

    return jsonify(results)


@bp.route("/voices", methods=["GET"])
def get_voices():
    """List available Fish Audio voices."""
    try:
        voices = list_voices()
        return jsonify({"voices": voices})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- Static file serving for media ---

@bp.route("/media/audio/<path:filename>", methods=["GET"])
def serve_audio(filename):
    return send_from_directory(str(settings.AUDIO_DIR), filename)


@bp.route("/media/thumbnails/<path:filename>", methods=["GET"])
def serve_thumbnail(filename):
    return send_from_directory(str(settings.THUMBNAILS_DIR), filename)


@bp.route("/media/output/<path:filename>", methods=["GET"])
def serve_video(filename):
    return send_from_directory(str(settings.OUTPUT_DIR), filename)
