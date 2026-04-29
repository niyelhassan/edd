# EDD Video Generator

A Flask app that turns a STEM topic into a short narrated lesson video with pre/post quizzes and feedback capture.

## What it does

- Collects a topic, context, length, and color theme.
- Generates a storyboard, narration, and a Manim scene plan.
- Renders an MP4 with captions and a thumbnail.
- Runs a 5-question pre-quiz and post-quiz with results and score delta.
- Captures survey feedback and stores results in CSV.
- Stores jobs, logs, and artifacts locally, and lets you rerun jobs.

## User flow

1. Onboarding (first visit only) -> Home (completed library + new lesson).
2. Create lesson -> Pre-quiz (wait if questions are still generating).
3. Watch video (live progress while rendering).
4. Post-quiz -> Results -> Feedback survey -> Thanks.

## Generation pipeline (background workers)

- Queue job and log state changes.
- Plan a storyboard (Claude Agent SDK).
- Generate a 5-question quiz (Claude CLI).
- Synthesize narration (Deepgram TTS).
- Build a Manim module, render scenes, mux audio, and concatenate.
- Produce captions (VTT) and a thumbnail image.
- Save final artifacts under `instance/jobs/<job_id>/`.

## Video templates

Production videos are assembled from storyboard scenes. Each scene uses one layout from the template registry:

- Structure: `title_card`, `summary`, `thanks`
- Statement: `statement`
- Math/data: `equation`, `step_derivation`, `distribution`, `axes_plot`, `line_chart`, `bar_chart`, `proportional_chart`
- Explanation: `comparison`, `before_after`, `flow`, `timeline`, `cause_effect`, `network`, `bullets`

Chart templates can use optional `data_points` objects shaped like `{"label": "A", "value": 42}` so generated videos can use real user-provided quantities instead of generic seeded values.

## Run

```bash
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

## Requirements

- `claude` CLI installed and authenticated (quiz generation).
- Claude Agent SDK available in the Python environment (storyboard generation).
- `ffmpeg` and `ffprobe` available on PATH.
- LaTeX (required by Manim).
- A Deepgram API key for narration.

## Environment

The app reads `.env` automatically. Common variables:

- `SECRET_KEY`
- `CLAUDE_CODE_MODEL`
- `CLAUDE_QUESTION_MODEL`
- `CLAUDE_CODE_MAX_TURNS`
- `DEEPGRAM_API_KEY`
- `DEEPGRAM_VOICE_MODEL`
- `MAX_WORKERS`
- `POLL_INTERVAL_MS`

## Outputs

- SQLite DB: `instance/edd.sqlite3`
- Job artifacts: `instance/jobs/<job_id>/`
- Survey + quiz results: `survey_results.csv`

## Docs

- `project.md` for a full capability overview.
- `flowchart.md` for the updated system flow.
