from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


class MediaError(RuntimeError):
    pass


MANIM_RESOLUTION = "1920,1080"
MANIM_FPS = "30"


def render_scene(*, module_path: Path, class_name: str, media_dir: Path) -> Path:
    media_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "manim",
        "-r",
        MANIM_RESOLUTION,
        "--fps",
        MANIM_FPS,
        str(module_path),
        class_name,
        "--media_dir",
        str(media_dir),
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise MediaError(completed.stderr.strip() or completed.stdout.strip() or "Manim render failed.")

    matches = sorted(media_dir.rglob(f"{class_name}.mp4"))
    if not matches:
        raise MediaError(f"Manim did not produce an MP4 for {class_name}.")
    return matches[-1]


def probe_duration(media_path: Path) -> float:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(media_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise MediaError(completed.stderr.strip() or completed.stdout.strip() or "ffprobe failed.")
    payload = json.loads(completed.stdout)
    return float(payload["format"]["duration"])


def mux_video_with_audio(*, video_path: Path, audio_path: Path, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    video_duration = probe_duration(video_path)
    audio_duration = probe_duration(audio_path)
    pad_duration = max(audio_duration - video_duration + 0.25, 0)
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(audio_path),
        "-filter_complex",
        f"[0:v]tpad=stop_mode=clone:stop_duration={pad_duration:.2f}[v]",
        "-map",
        "[v]",
        "-map",
        "1:a:0",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-shortest",
        str(output_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise MediaError(completed.stderr.strip() or completed.stdout.strip() or "ffmpeg mux failed.")
    return output_path


def extract_thumbnail(
    *,
    video_path: Path,
    output_path: Path,
    timestamp: float | None = None,
    title_duration: float | None = None,
    width: int = 720,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if timestamp is None:
        if title_duration and title_duration > 1.25:
            timestamp = title_duration - 1.0
        else:
            duration = probe_duration(video_path)
            timestamp = min(max(duration - 0.5, 0.1), 2.0)
    command = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{timestamp:.2f}",
        "-i",
        str(video_path),
        "-frames:v",
        "1",
        "-vf",
        f"scale={width}:-2",
        "-q:v",
        "3",
        str(output_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise MediaError(completed.stderr.strip() or completed.stdout.strip() or "ffmpeg thumbnail failed.")
    return output_path


def concat_clips(*, clip_paths: list[Path], output_path: Path, workdir: Path) -> Path:
    if not clip_paths:
        raise MediaError("No clips provided for concatenation.")

    concat_file = workdir / "concat.txt"
    concat_file.write_text(
        "\n".join(f"file '{path.resolve()}'" for path in clip_paths),
        encoding="utf-8",
    )
    command = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-pix_fmt",
        "yuv420p",
        str(output_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise MediaError(completed.stderr.strip() or completed.stdout.strip() or "ffmpeg concat failed.")
    return output_path
