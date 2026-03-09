from backend.api.app import create_app
from backend.config.settings import FLASK_PORT

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=FLASK_PORT, debug=True)
