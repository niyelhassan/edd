from pathlib import Path
import os

from flask import Flask

from .config import Config, load_local_env
from .db import init_app as init_db
from .routes import bp as routes_bp
from .services.job_manager import JobManager


def create_app() -> Flask:
    base_dir = Path(__file__).resolve().parent.parent
    load_local_env(base_dir)

    claude_max_turns_raw = os.getenv("CLAUDE_CODE_MAX_TURNS", "")
    secret_key = os.getenv("SECRET_KEY", "").strip()
    if not secret_key:
        raise RuntimeError(
            "SECRET_KEY is required. Copy .env.example to .env and set a long, "
            "random value before starting the app."
        )

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    app.config.update(
        SECRET_KEY=secret_key,
        CLAUDE_CODE_MODEL=os.getenv("CLAUDE_CODE_MODEL", app.config["CLAUDE_CODE_MODEL"]),
        CLAUDE_CODE_MAX_TURNS=int(claude_max_turns_raw) if claude_max_turns_raw.strip() else None,
        DEEPGRAM_API_KEY=os.getenv("DEEPGRAM_API_KEY", app.config["DEEPGRAM_API_KEY"]),
        DEEPGRAM_VOICE_MODEL=os.getenv("DEEPGRAM_VOICE_MODEL", app.config["DEEPGRAM_VOICE_MODEL"]),
        GOOGLE_RESULTS_SPREADSHEET_ID=os.getenv("GOOGLE_RESULTS_SPREADSHEET_ID", app.config["GOOGLE_RESULTS_SPREADSHEET_ID"]),
        GOOGLE_RESULTS_WORKSHEET_NAME=os.getenv("GOOGLE_RESULTS_WORKSHEET_NAME", app.config["GOOGLE_RESULTS_WORKSHEET_NAME"]),
        GOOGLE_SERVICE_ACCOUNT_FILE=os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", app.config["GOOGLE_SERVICE_ACCOUNT_FILE"]),
        GOOGLE_SERVICE_ACCOUNT_JSON=os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", app.config["GOOGLE_SERVICE_ACCOUNT_JSON"]),
        POLL_INTERVAL_MS=int(os.getenv("POLL_INTERVAL_MS", str(app.config["POLL_INTERVAL_MS"]))),
    )
    app.config["BASE_DIR"] = str(base_dir)
    app.config["DATABASE"] = str(Path(app.instance_path) / "edd.sqlite3")
    app.config["JOBS_DIR"] = str(Path(app.instance_path) / "jobs")
    app.config["OUTPUT_DIR"] = str(Path(app.instance_path) / "output")

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["JOBS_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["OUTPUT_DIR"]).mkdir(parents=True, exist_ok=True)

    init_db(app)
    app.register_blueprint(routes_bp)
    app.extensions["job_manager"] = JobManager(app)

    @app.context_processor
    def inject_globals() -> dict:
        return {"poll_interval_ms": app.config["POLL_INTERVAL_MS"]}

    return app
