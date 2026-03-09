from flask import Blueprint, jsonify, request

from backend.storage.database import get_db
from backend.storage.models import Channel

bp = Blueprint("channels", __name__, url_prefix="/api/channels")


@bp.route("", methods=["GET"])
def list_channels():
    db = get_db()
    try:
        channels = db.query(Channel).order_by(Channel.created_at.desc()).all()
        return jsonify([c.to_dict() for c in channels])
    finally:
        db.close()


@bp.route("", methods=["POST"])
def create_channel():
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "name is required"}), 400

    db = get_db()
    try:
        channel = Channel(
            name=data["name"],
            niche=data.get("niche", ""),
            language=data.get("language", "es"),
            voice_id=data.get("voice_id", ""),
            style_prompt=data.get("style_prompt", ""),
            thumbnail_style=data.get("thumbnail_style", ""),
        )
        db.add(channel)
        db.commit()
        db.refresh(channel)
        return jsonify(channel.to_dict()), 201
    finally:
        db.close()


@bp.route("/<int:channel_id>", methods=["PUT"])
def update_channel(channel_id):
    data = request.get_json()
    db = get_db()
    try:
        channel = db.query(Channel).get(channel_id)
        if not channel:
            return jsonify({"error": "Channel not found"}), 404

        for field in ["name", "niche", "language", "youtube_channel_id",
                      "voice_id", "style_prompt", "thumbnail_style"]:
            if field in data:
                setattr(channel, field, data[field])

        db.commit()
        return jsonify(channel.to_dict())
    finally:
        db.close()


@bp.route("/<int:channel_id>", methods=["DELETE"])
def delete_channel(channel_id):
    db = get_db()
    try:
        channel = db.query(Channel).get(channel_id)
        if not channel:
            return jsonify({"error": "Channel not found"}), 404

        db.delete(channel)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()
