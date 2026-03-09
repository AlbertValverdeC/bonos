from flask import Blueprint, jsonify, request

from backend.storage.database import get_db
from backend.storage.models import Project, Channel

bp = Blueprint("projects", __name__, url_prefix="/api/projects")


@bp.route("", methods=["GET"])
def list_projects():
    db = get_db()
    try:
        query = db.query(Project).order_by(Project.created_at.desc())

        status = request.args.get("status")
        if status:
            query = query.filter_by(status=status)

        channel_id = request.args.get("channel_id")
        if channel_id:
            query = query.filter_by(channel_id=int(channel_id))

        projects = query.all()
        return jsonify([p.to_dict() for p in projects])
    finally:
        db.close()


@bp.route("", methods=["POST"])
def create_project():
    data = request.get_json()
    if not data or not data.get("topic"):
        return jsonify({"error": "topic is required"}), 400

    db = get_db()
    try:
        project = Project(
            topic=data["topic"],
            title=data.get("title", data["topic"]),
            channel_id=data.get("channel_id"),
            status="idea",
            current_step=0,
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return jsonify(project.to_dict()), 201
    finally:
        db.close()


@bp.route("/<int:project_id>", methods=["GET"])
def get_project(project_id):
    db = get_db()
    try:
        project = db.query(Project).get(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404
        return jsonify(project.to_dict(include_sections=True, include_footage=True))
    finally:
        db.close()


@bp.route("/<int:project_id>", methods=["PUT"])
def update_project(project_id):
    data = request.get_json()
    db = get_db()
    try:
        project = db.query(Project).get(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        for field in ["title", "topic", "channel_id", "status", "metadata_json"]:
            if field in data:
                setattr(project, field, data[field])

        db.commit()
        return jsonify(project.to_dict())
    finally:
        db.close()


@bp.route("/<int:project_id>", methods=["DELETE"])
def delete_project(project_id):
    db = get_db()
    try:
        project = db.query(Project).get(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        db.delete(project)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()
