from __future__ import annotations

import re
from pathlib import Path


_SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'\(])")
_MAX_CUE_CHARS = 90
_MIN_CUE_DURATION = 0.9


def _format_timestamp(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    total_ms = int(round(seconds * 1000))
    hours, remainder_ms = divmod(total_ms, 3600 * 1000)
    minutes, remainder_ms = divmod(remainder_ms, 60 * 1000)
    secs, ms = divmod(remainder_ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"


def _split_sentences(text: str) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    return [chunk.strip() for chunk in _SENTENCE_END_RE.split(text) if chunk.strip()]


def _chunk_sentence(sentence: str, max_chars: int = _MAX_CUE_CHARS) -> list[str]:
    """Break a long sentence into cue-sized fragments at clause boundaries."""
    if len(sentence) <= max_chars:
        return [sentence]

    parts = re.split(r"(?<=[,;:—])\s+", sentence)
    chunks: list[str] = []
    buffer = ""
    for part in parts:
        candidate = (buffer + " " + part).strip() if buffer else part
        if len(candidate) > max_chars and buffer:
            chunks.append(buffer)
            buffer = part
        else:
            buffer = candidate
    if buffer:
        chunks.append(buffer)

    out: list[str] = []
    for chunk in chunks:
        if len(chunk) <= max_chars:
            out.append(chunk)
            continue
        words = chunk.split()
        line = ""
        for word in words:
            candidate = (line + " " + word).strip() if line else word
            if len(candidate) > max_chars and line:
                out.append(line)
                line = word
            else:
                line = candidate
        if line:
            out.append(line)
    return out


def _split_narration(narration: str) -> list[str]:
    cues: list[str] = []
    for sentence in _split_sentences(narration):
        cues.extend(_chunk_sentence(sentence))
    return [cue for cue in cues if cue]


def build_vtt(scenes: list[dict], scene_durations: list[float] | None = None) -> str:
    """Build a WebVTT string from scene narrations + per-scene durations."""
    durations: list[float] = []
    for index, scene in enumerate(scenes):
        if scene_durations and index < len(scene_durations) and scene_durations[index] > 0:
            durations.append(float(scene_durations[index]))
        else:
            durations.append(float(scene.get("target_duration_seconds") or 0) or 6.0)

    lines: list[str] = ["WEBVTT", ""]
    cursor = 0.0
    for scene, duration in zip(scenes, durations):
        narration = (scene.get("narration") or "").strip()
        cues = _split_narration(narration) or [scene.get("headline") or ""]
        if not any(cues):
            cursor += duration
            continue

        weights = [max(len(cue), 1) for cue in cues]
        total_weight = sum(weights)
        scene_end = cursor + duration

        cue_start = cursor
        for index, (cue, weight) in enumerate(zip(cues, weights)):
            slice_seconds = duration * (weight / total_weight)
            if slice_seconds < _MIN_CUE_DURATION and index < len(cues) - 1:
                slice_seconds = _MIN_CUE_DURATION
            cue_end = min(cue_start + slice_seconds, scene_end)
            if index == len(cues) - 1:
                cue_end = scene_end
            if cue_end <= cue_start:
                cue_end = cue_start + 0.5

            lines.append(f"{_format_timestamp(cue_start)} --> {_format_timestamp(cue_end)}")
            lines.append(cue)
            lines.append("")
            cue_start = cue_end

        cursor = scene_end

    return "\n".join(lines).rstrip() + "\n"


def write_captions(*, scenes: list[dict], output_path: Path, scene_durations: list[float] | None = None) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    vtt = build_vtt(scenes, scene_durations)
    output_path.write_text(vtt, encoding="utf-8")
    return output_path
