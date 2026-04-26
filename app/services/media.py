from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path


class MediaError(RuntimeError):
    pass


MANIM_QUALITY_FLAGS = {
    "480p": "-ql",
    "720p": "-qm",
    "1080p": "-qh",
    "1440p": "-qp",
    "4k": "-qk",
}


def _manim_quality_flag(render_quality: str | None) -> str:
    key = str(render_quality or "").strip().lower()
    return MANIM_QUALITY_FLAGS.get(key, MANIM_QUALITY_FLAGS["1080p"])


def extract_scene_class_names(module_path: Path) -> list[str]:
    module = ast.parse(module_path.read_text(encoding="utf-8"))

    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "SCENE_CLASS_NAMES":
                    value = ast.literal_eval(node.value)
                    if isinstance(value, list):
                        return [str(item) for item in value]

    names = []
    for node in module.body:
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == "Scene":
                    names.append(node.name)
    return names


def render_scene(*, module_path: Path, class_name: str, media_dir: Path, render_quality: str | None = None) -> Path:
    media_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "manim",
        _manim_quality_flag(render_quality),
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
    filter_graph = (
        f"[0:v]tpad=stop_mode=clone:stop_duration={pad_duration:.2f}[v];"
        "[1:a]loudnorm=I=-16:LRA=11:TP=-1.5[a]"
    )
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(audio_path),
        "-filter_complex",
        filter_graph,
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-c:v",
        "libx264",
        "-preset",
        "slow",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        "48000",
        "-movflags",
        "+faststart",
        "-shortest",
        str(output_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise MediaError(completed.stderr.strip() or completed.stdout.strip() or "ffmpeg mux failed.")
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
        "-preset",
        "slow",
        "-crf",
        "18",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        "48000",
        "-movflags",
        "+faststart",
        "-pix_fmt",
        "yuv420p",
        str(output_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise MediaError(completed.stderr.strip() or completed.stdout.strip() or "ffmpeg concat failed.")
    return output_path
