# EDD Video Generator

A Flask application that generates explainer videos for advanced math and science topics aimed at high school students.

Workflow:

1. Collect a topic in the web UI.
2. Use Claude Code headless mode once to create a structured 3 to 8 scene lesson plan and narration.
3. Use Deepgram TTS to generate narration audio scene by scene.
4. Build a deterministic Manim module from the storyboard using a library of animated scene templates and topic-aware visual choices.
5. Render scenes with Manim at higher quality and stitch them into a final MP4 with `ffmpeg`.

## Run

```bash
pyenv local edd
pip install -r requirements.txt
npm install -g @anthropic-ai/claude-code
python app.py
```

Open `http://127.0.0.1:5000`.

Default behavior:

- High-school student research audience
- About 3 minutes for the medium preset
- Usually 3 to 8 storyboard scenes based on complexity and runtime
- 1080p render quality by default
- `claude-sonnet-4-6`
- Max 2 Claude turns for planning
- Simplified Tailwind UI with live progress states

## Environment

The app reads `.env` automatically. Important variables:

- `DEEPGRAM_API_KEY`
- `DEEPGRAM_VOICE_MODEL`
- `CLAUDE_CODE_MODEL`
- `CLAUDE_QUESTION_MODEL`
- `CLAUDE_CODE_MAX_TURNS`
- `DEFAULT_RENDER_QUALITY`

## Notes

- `claude` CLI must already be installed and authenticated.
- The app uses the Claude Agent SDK and Claude Code CLI session on this machine.
- `ffmpeg` and LaTeX are required for Manim rendering.
- Generated jobs and media are stored under `instance/`.
