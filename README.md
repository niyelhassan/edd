# EDD Video Generator

A Flask application that generates explainer videos for advanced math and science topics aimed at high school students.

Workflow:

1. Collect a topic in the web UI.
2. Use `codex exec` once to create a structured 3-scene lesson plan and narration.
3. Use Deepgram TTS to generate narration audio scene by scene.
4. Build a deterministic Manim module from the storyboard so layout, text wrapping, and timing stay stable.
5. Render scenes with Manim and stitch them into a final MP4 with `ffmpeg`.

## Run

```bash
pyenv local edd
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

Default behavior:

- High-school audience
- About 72 seconds
- 3 scenes
- Fast generation mode
- Simplified Tailwind UI with live progress states

## Environment

The app reads `.env` automatically. Important variables:

- `DEEPGRAM_API_KEY`
- `DEEPGRAM_VOICE_MODEL`
- `CODEX_MODEL`
- `CODEX_REASONING_EFFORT`
- `DEFAULT_RENDER_QUALITY`

## Notes

- `codex` CLI must already be installed and authenticated.
- `ffmpeg` and LaTeX are required for Manim rendering.
- Generated jobs and media are stored under `instance/`.
