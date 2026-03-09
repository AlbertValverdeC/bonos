from flask import Flask
from flask_cors import CORS

from backend.storage.database import init_db
from backend.api.routes import projects, pipeline, channels, settings, research


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    # Initialize database
    init_db()

    # Register blueprints
    app.register_blueprint(projects.bp)
    app.register_blueprint(pipeline.bp)
    app.register_blueprint(channels.bp)
    app.register_blueprint(settings.bp)
    app.register_blueprint(research.bp)

    @app.route("/api/health")
    def health():
        return {"status": "ok"}

    return app
