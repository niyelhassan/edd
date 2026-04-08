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

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", app.config["SECRET_KEY"]),
        CODEX_MODEL=os.getenv("CODEX_MODEL", app.config["CODEX_MODEL"]),
        CODEX_REASONING_EFFORT=os.getenv("CODEX_REASONING_EFFORT", app.config["CODEX_REASONING_EFFORT"]),
        DEEPGRAM_API_KEY=os.getenv("DEEPGRAM_API_KEY", app.config["DEEPGRAM_API_KEY"]),
        DEEPGRAM_VOICE_MODEL=os.getenv("DEEPGRAM_VOICE_MODEL", app.config["DEEPGRAM_VOICE_MODEL"]),
        MAX_WORKERS=int(os.getenv("MAX_WORKERS", str(app.config["MAX_WORKERS"]))),
        DEFAULT_RENDER_QUALITY=os.getenv("DEFAULT_RENDER_QUALITY", app.config["DEFAULT_RENDER_QUALITY"]),
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
