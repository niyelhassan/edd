# EDD Video Generator

A Flask app that turns a STEM topic into a short narrated lesson video with pre/post quizzes and feedback capture.

## What it does

- Collects a topic, research area, length, and color theme.
- Generates a storyboard, narration, and a Manim scene plan.
- Renders an MP4 with captions and a thumbnail.
- Runs a 5-question pre-quiz and post-quiz with results and score delta.
- Captures survey feedback and stores results in CSV.
- Stores jobs, logs, and artifacts locally, and lets you rerun jobs.

## User flow

1. Hello walkthrough (first visit only) -> Home (completed library + new lesson).
2. Create lesson plan + quiz -> Pre-quiz.
3. Watch video (live progress while rendering).
4. Post-quiz -> Results -> Feedback survey -> Thanks.

## Generation pipeline (local background renderer)

- Queue job and log state changes.
- Plan a storyboard (Claude Agent SDK).
- Include a 5-question quiz in the storyboard response.
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

- `claude` CLI installed and authenticated.
- Claude Agent SDK available in the Python environment.
- `ffmpeg` and `ffprobe` available on PATH.
- LaTeX (required by Manim).
- A Deepgram API key for narration.

## Environment

The app reads `.env` automatically. Common variables:

- `SECRET_KEY`
- `CLAUDE_CODE_MODEL`
- `CLAUDE_CODE_MAX_TURNS`
- `DEEPGRAM_API_KEY`
- `DEEPGRAM_VOICE_MODEL`
- `GOOGLE_RESULTS_SPREADSHEET_ID`
- `GOOGLE_RESULTS_WORKSHEET_NAME`
- `GOOGLE_SERVICE_ACCOUNT_FILE`
- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `POLL_INTERVAL_MS`

### Google Sheets results sync

`results.csv` can be mirrored into a Google Sheet whenever quiz or survey results are saved.

1. Create a Google Cloud service account and enable the Google Sheets API for its project.
2. Download the service account key JSON.
3. Share the target Google Sheet with the service account email from the JSON file, using Editor access.
4. Add these values to `.env`:

```bash
GOOGLE_RESULTS_SPREADSHEET_ID=your_sheet_id_from_the_url
GOOGLE_RESULTS_WORKSHEET_NAME=results
GOOGLE_SERVICE_ACCOUNT_FILE=/absolute/path/to/service-account.json
```

Instead of `GOOGLE_SERVICE_ACCOUNT_FILE`, you can set `GOOGLE_SERVICE_ACCOUNT_JSON` to the full JSON object if your deployment stores secrets as environment variables.

## Outputs

- SQLite DB: `instance/edd.sqlite3`
- Job artifacts: `instance/jobs/<job_id>/`
- Survey + quiz results: `results.csv`

## Docs

- `project.md` for a full capability overview.
- `flowchart.md` for the updated system flow.
