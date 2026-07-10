from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.manim_builder import build_manim_module
from app.services.media import render_scene
from app.services.template_registry import CONTENT_LAYOUTS


TEMPLATE_SCENES = [
    {
        "layout": "title_card",
        "slug": "title-card",
        "headline": "Understanding Feedback Loops",
        "hook": "Small changes can become large outcomes when a system responds to itself.",
        "narration": "This opening frame introduces feedback loops as a simple visual idea. A system creates an output, the output returns as an input, and the loop changes what happens next.",
        "visual_goal": "Show a strong opening title and one supporting line.",
        "key_points": [],
        "visual_items": ["Signal", "Response", "Adjustment"],
        "highlight_terms": ["feedback"],
        "equations": [],
        "takeaway": "",
    },
    {
        "layout": "summary",
        "slug": "summary",
        "headline": "Key takeaways",
        "hook": "",
        "narration": "The closing frame turns the lesson into three memorable takeaways. It should feel clear, calm, and useful after the animation has already explained the main idea.",
        "visual_goal": "Show one large takeaway and concise supporting points.",
        "key_points": ["Loops connect causes to effects", "Delays can hide the real driver", "A small correction can stabilize the system"],
        "visual_items": [],
        "highlight_terms": ["takeaway"],
        "equations": [],
        "takeaway": "A feedback loop is easiest to understand by tracking what returns to the system.",
    },
    {
        "layout": "thanks",
        "slug": "thanks",
        "headline": "Thanks for watching",
        "hook": "Made with lern",
        "narration": "Closing card. A short sign-off after the lesson is finished.",
        "visual_goal": "Show a simple thanks message and a sign-off.",
        "key_points": [],
        "visual_items": [],
        "highlight_terms": [],
        "equations": [],
        "takeaway": "",
    },
    {
        "layout": "statement",
        "slug": "statement",
        "headline": "The Loop Changes The System",
        "hook": "One memorable idea can anchor the rest of the explanation.",
        "narration": "This statement layout is for the core principle of a lesson. It gives the main insight enough scale to feel important, then adds supporting lines for context.",
        "visual_goal": "Show one bold centered insight with eyebrow label and supporting lines.",
        "key_points": ["The returned output becomes the next input", "Small changes compound over multiple cycles", "Understanding the loop helps predict the outcome"],
        "visual_items": [],
        "highlight_terms": ["core idea"],
        "equations": [],
        "takeaway": "Feedback matters because the system reacts to its own output.",
    },
    {
        "layout": "equation",
        "slug": "equation",
        "headline": "Rate Of Change",
        "hook": "The derivative turns motion into a local slope.",
        "narration": "This equation layout works best when one formula is the star of the scene. The chips underneath name the parts viewers should track while the narration explains the symbols.",
        "visual_goal": "Show one equation with annotation chips.",
        "key_points": [],
        "visual_items": [],
        "highlight_terms": ["slope", "input", "output"],
        "equations": ["\\frac{dy}{dx}=m"],
        "takeaway": "The derivative describes how fast the output changes at one point.",
    },
    {
        "layout": "step_derivation",
        "slug": "step-derivation",
        "headline": "Solving For The Unknown",
        "hook": "Each line keeps the equality true while isolating the variable.",
        "narration": "This derivation layout walks through a short calculation. It is useful when the explanation depends on seeing how one equation becomes the next.",
        "visual_goal": "Show a stacked sequence of equation transformations.",
        "key_points": [],
        "visual_items": ["Start", "Subtract", "Divide", "Result"],
        "highlight_terms": ["equivalent steps"],
        "equations": ["2x+6=18", "2x=12", "x=6"],
        "takeaway": "A derivation is a chain of small reversible moves.",
    },
    {
        "layout": "line_chart",
        "slug": "line-chart",
        "headline": "Trend Across Trials",
        "hook": "A line makes direction and rate visible across ordered observations.",
        "narration": "This line chart uses explicit data points when the storyboard has values. It works for trends, trajectories, and measured change over time.",
        "visual_goal": "Show a trend line with labeled observations.",
        "key_points": [],
        "visual_items": [],
        "highlight_terms": ["trial", "score"],
        "equations": [],
        "data_points": [
            {"label": "T1", "value": 42},
            {"label": "T2", "value": 55},
            {"label": "T3", "value": 63},
            {"label": "T4", "value": 71},
        ],
        "takeaway": "Ordered data reveals whether the process is improving.",
    },
    {
        "layout": "comparison",
        "slug": "comparison",
        "headline": "Two Ways To Estimate",
        "hook": "Side-by-side panels make tradeoffs easier to see.",
        "narration": "This comparison layout is for contrasting two methods, states, or explanations. It needs short labels because each panel has limited space.",
        "visual_goal": "Show two panels with a center versus marker.",
        "key_points": ["Fast to compute", "Sensitive to outliers", "Stable with more data"],
        "visual_items": ["Mean", "Median"],
        "highlight_terms": ["tradeoff"],
        "equations": [],
        "takeaway": "The better estimate depends on what kind of error matters most.",
    },
    {
        "layout": "before_after",
        "slug": "before-after",
        "headline": "Misconception To Model",
        "hook": "The correction changes what the viewer pays attention to.",
        "narration": "This before and after layout makes a conceptual correction visible. It is useful for misconceptions, transformations, and state changes.",
        "visual_goal": "Show two state cards connected by a transformation arrow.",
        "key_points": ["Track the hidden assumption", "Update the mental model"],
        "visual_items": ["Objects fall faster", "Acceleration is shared"],
        "highlight_terms": ["correction"],
        "equations": [],
        "takeaway": "The better model explains what stays the same.",
    },
    {
        "layout": "flow",
        "slug": "flow",
        "headline": "Pipeline Thinking",
        "hook": "Each stage transforms the output of the stage before it.",
        "narration": "This flow template shows boxes connected by arrows. Small packets move between stages to make the transformation feel active.",
        "visual_goal": "Show a left-to-right pipeline.",
        "key_points": [],
        "visual_items": ["Input", "Transform", "Check", "Output"],
        "highlight_terms": ["pipeline"],
        "equations": [],
        "takeaway": "A pipeline is easiest to debug one stage at a time.",
    },
    {
        "layout": "timeline",
        "slug": "timeline",
        "headline": "How The Idea Developed",
        "hook": "A timeline shows how discoveries built on each other.",
        "narration": "This timeline layout shows ordered milestones. It works for historical context, lifecycles, phases, and multi-stage scientific stories.",
        "visual_goal": "Show a horizontal sequence of milestones.",
        "key_points": [],
        "visual_items": ["Question", "Measurement", "Model", "Prediction", "Test"],
        "highlight_terms": ["sequence"],
        "equations": [],
        "takeaway": "The order matters because each step creates the next question.",
    },
    {
        "layout": "bar_chart",
        "slug": "bar-chart",
        "headline": "Comparing Magnitudes",
        "hook": "Bars make relative size visible immediately.",
        "narration": "This bar chart template grows bars from a baseline. It is useful for rankings, categories, shares, and simple magnitude comparisons.",
        "visual_goal": "Show a small animated bar chart.",
        "key_points": [],
        "visual_items": ["Option A", "Option B", "Option C", "Option D"],
        "highlight_terms": ["ranking"],
        "equations": [],
        "data_points": [
            {"label": "A", "value": 18},
            {"label": "B", "value": 42},
            {"label": "C", "value": 31},
            {"label": "D", "value": 25},
        ],
        "takeaway": "A chart should make the biggest difference obvious without extra explanation.",
    },
    {
        "layout": "proportional_chart",
        "slug": "proportional-chart",
        "headline": "Parts Of The Whole",
        "hook": "A proportion view shows how each category contributes to the total.",
        "narration": "This proportional chart uses concrete shares when available. It is useful for mixtures, ratios, percentages, and composition.",
        "visual_goal": "Show a stacked proportion bar with labels.",
        "key_points": [],
        "visual_items": [],
        "highlight_terms": ["share"],
        "equations": [],
        "data_points": [
            {"label": "Signal", "value": 55},
            {"label": "Noise", "value": 30},
            {"label": "Bias", "value": 15},
        ],
        "takeaway": "The largest part of a whole should be visible before reading the labels.",
    },
    {
        "layout": "cause_effect",
        "slug": "cause-effect",
        "headline": "One Driver, Many Effects",
        "hook": "Branching makes consequences easier to compare.",
        "narration": "This cause and effect layout puts the driver on one side and branches to several outcomes. It works well for mechanisms and consequences.",
        "visual_goal": "Show one cause branching into effects.",
        "key_points": [],
        "visual_items": ["Higher pressure", "Faster collisions", "More reactions"],
        "highlight_terms": ["temperature rise"],
        "equations": [],
        "takeaway": "A mechanism is clearer when each effect points back to the driver.",
    },
    {
        "layout": "network",
        "slug": "network",
        "headline": "Connected Variables",
        "hook": "A network shows relationships that a list hides.",
        "narration": "This network layout shows a small graph of related terms. It works for dependencies, interactions, systems, and connected concepts.",
        "visual_goal": "Show a compact relationship network.",
        "key_points": [],
        "visual_items": ["Input", "Hidden factor", "Output", "Feedback"],
        "highlight_terms": ["system"],
        "equations": [],
        "takeaway": "The structure of the connections can explain the behavior.",
    },
]


def _storyboard_for_templates(scenes: list[dict]) -> dict:
    prepared = []
    for index, scene in enumerate(scenes, start=1):
        item = dict(scene)
        item["class_name"] = f"Template{index:02d}{''.join(part.capitalize() for part in item['slug'].split('-'))}"
        item["scene_variant"] = "basic"
        item["target_duration_seconds"] = 6.0
        prepared.append(item)
    return {
        "title": "Template Preview Reel",
        "summary": "Silent preview scenes for every populated video template.",
        "learning_objective": "Compare the structure and visual behavior of each Manim template.",
        "closing_takeaway": "Use these previews to improve template layout, pacing, and visual specificity.",
        "color_theme": "blue",
        "scenes": prepared,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Render one silent MP4 preview for each populated video template.")
    parser.add_argument("--only", nargs="*", help="Optional layout names to render, such as equation flow timeline.")
    parser.add_argument("--clean", action="store_true", help="Delete previous generated preview files first.")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    videos_dir = base_dir / "videos"
    media_dir = base_dir / "_media"
    module_path = base_dir / "_generated_template_scenes.py"
    storyboard_path = base_dir / "template_storyboard.json"

    if args.clean:
        shutil.rmtree(videos_dir, ignore_errors=True)
        shutil.rmtree(media_dir, ignore_errors=True)
        module_path.unlink(missing_ok=True)
        storyboard_path.unlink(missing_ok=True)

    selected = TEMPLATE_SCENES
    if args.only:
        wanted = {name.strip().lower() for name in args.only}
        selected = [scene for scene in TEMPLATE_SCENES if scene["layout"] in wanted]
        missing = sorted(wanted - {scene["layout"] for scene in selected})
        if missing:
            raise SystemExit(f"Unknown template(s): {', '.join(missing)}")
    else:
        missing_from_previews = sorted(set(CONTENT_LAYOUTS) - {scene["layout"] for scene in TEMPLATE_SCENES})
        if missing_from_previews:
            raise SystemExit(f"Missing preview scene(s): {', '.join(missing_from_previews)}")

    videos_dir.mkdir(parents=True, exist_ok=True)
    media_dir.mkdir(parents=True, exist_ok=True)

    storyboard = _storyboard_for_templates(selected)
    storyboard_path.write_text(json.dumps(storyboard, indent=2), encoding="utf-8")
    build_manim_module(storyboard=storyboard, output_path=module_path)

    print(f"Rendering {len(storyboard['scenes'])} template preview(s) into {videos_dir}")
    for scene in storyboard["scenes"]:
        rendered = render_scene(
            module_path=module_path,
            class_name=scene["class_name"],
            media_dir=media_dir / scene["slug"],
        )
        output_path = videos_dir / f"{scene['layout']}.mp4"
        shutil.copy2(rendered, output_path)
        print(f"- {scene['layout']}: {output_path.relative_to(ROOT)}")

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
