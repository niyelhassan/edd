from __future__ import annotations

from pathlib import Path

import requests
from pydub import AudioSegment


class DeepgramError(RuntimeError):
    pass


class DeepgramTTSClient:
    def __init__(self, api_key: str):
        if not api_key:
            raise DeepgramError("DEEPGRAM_API_KEY is not configured.")
        self.api_key = api_key

    def synthesize(self, *, text: str, output_path: Path, model: str) -> float:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://api.deepgram.com/v1/speak?model={model}&encoding=mp3&bit_rate=32000"
        response = requests.post(
            url,
            headers={
                "Authorization": f"Token {self.api_key}",
                "Content-Type": "application/json",
            },
            json={"text": text},
            stream=True,
            timeout=(10, 180),
        )
        if response.status_code >= 400:
            raise DeepgramError(f"Deepgram TTS failed: {response.status_code} {response.text.strip()}")

        with output_path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    handle.write(chunk)

        duration = AudioSegment.from_file(output_path).duration_seconds
        return round(duration, 2)
