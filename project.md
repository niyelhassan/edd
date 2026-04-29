# Project overview

EDD Video Generator is a web app that creates short STEM explainer videos for students and measures learning outcomes with pre/post quizzes and a feedback survey.

## Core capabilities

- Topic intake with required research area, length presets, and color theme selection.
- Automated storyboard creation and lesson structuring into title, content, summary, and closing scenes.
- Template-driven visual layouts (equations, charts, comparisons, flows, timelines, networks, and more).
- Narrated video production with captions and a thumbnail preview.
- Five-question pre-quiz and post-quiz with score delta and results view.
- Feedback survey and CSV export of study results.
- Library of completed lessons, rerun support, and a debug view with logs and artifacts.
- Live progress updates while the video renders.

## User experience flow

1. First visit shows onboarding, then the home library.
2. Student enters a topic, research area, length, and color theme.
3. Pre-quiz appears once questions are ready; progress is visible while the video renders.
4. Watch page shows the video or a live progress state until the video is ready.
5. Post-quiz, results, and feedback survey conclude the flow.

## Content and media generation

- Storyboards include a title card, distinct content scenes, a summary, and a fixed closing thanks card.
- Each content scene uses a single layout type to keep the lesson visually varied.
- Supported layout families include statement, equation, derivation, charts, comparisons, before/after, flow, timeline, cause/effect, network, and bullets.
- Length presets target short, medium, or long lessons.
- Color themes apply consistent styling across all scenes in a lesson.

## Video outputs and artifacts

- Final MP4 video output.
- WebVTT captions generated from narration.
- Thumbnail extracted from the final video.
- Per-scene renders, audio files, and intermediate clips are stored with each job.
- The watch page provides in-browser playback and a download link when the video is ready.

## Learning measurement and feedback

- The pre-quiz establishes baseline knowledge for the lesson.
- The post-quiz uses the same questions to measure learning gain.
- Results show pre score, post score, and the change.
- A survey captures student feedback on quality, length, usefulness, and suggested improvements.
- Quiz and survey results are stored in a CSV file for analysis.

## Job management and observability

- Jobs are queued and processed in the background with a small worker pool.
- Pending jobs resume automatically on startup.
- Progress is computed from job logs and surfaced in the UI.
- A debug page shows storyboard data, logs, and model usage.
- API endpoints provide job status and quiz readiness for polling.

## Storage and data

- SQLite database stores job metadata, status, and logs.
- Job artifacts are stored under per-job directories in the instance folder.
- Survey and quiz results are aggregated in a project-level CSV file.

## Configuration surface

- Models, voice, worker count, and polling interval are configurable.
- The library view can be limited to completed jobs or expanded to all jobs.
