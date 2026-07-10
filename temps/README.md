# Template Preview Videos

This folder is for local, silent Manim previews of the current video templates. It does not call Claude, Deepgram, or the Flask job workflow.

## Generate Previews

From the repo root:

```bash
python temps/make_template_videos.py --clean
```

Outputs:

- `temps/videos/<template>.mp4`: one video per populated template.
- `temps/template_storyboard.json`: the sample data used to populate each template.
- `temps/_generated_template_scenes.py`: the generated Manim scene module.
- `temps/_media/`: Manim render cache and intermediate files.

To render only a few templates:

```bash
python temps/make_template_videos.py --only equation flow timeline
```

## Current Video Templates

Every production video is a storyboard made of scenes. Each scene has a `layout` value, and `app/services/manim_builder.py` dispatches that layout to a renderer. A normal job renders each scene as a silent Manim clip, muxes it with the scene narration MP3, then concatenates all clips into the final MP4.

The shared structure is:

- Top chrome: lesson eyebrow, scene headline, blue underline, progress dots, and `lern` mark.
- Body area: one layout-specific visual centered below the headline.
- Timing: each renderer animates in for a few seconds, then waits until the narration duration is covered.
- Theme: selectable accent themes with monochrome surfaces.

Template descriptions:

- `title_card`: Opening scene. Large lesson title, optional non-duplicative subtitle, soft accent circle.
- `summary`: Closing scene. Large takeaway plus up to three checkmark-style points.
- `bullets`: Fallback scene. Hook line plus up to three numbered text points.
- `statement`: Bold insight scene. One large principle or definition with a small eyebrow label and support line.
- `concept_map`: Hub-and-spoke map. One central term connected to three supporting concepts.
- `equation`: One primary equation, optional secondary equation, and up to three annotation chips.
- `step_derivation`: Stacked equation transformations with short step labels.
- `distribution`: Bell curve with shaded tail area, threshold line, and axis/tail labels.
- `axes_plot`: Generic x-y axes, a generated curve, and up to three labeled markers.
- `line_chart`: Ordered trend line using concrete `data_points` when available.
- `comparison`: Two side-by-side panels with a central `vs` marker.
- `before_after`: Two state cards connected by a transformation arrow.
- `flow`: Left-to-right pipeline nodes with arrows.
- `timeline`: Horizontal milestone line with alternating labels.
- `bar_chart`: Small category bar chart using concrete `data_points` when available.
- `proportional_chart`: Stacked part-of-whole bar using concrete `data_points` when available.
- `cause_effect`: One driver branching into multiple effects.
- `network`: Compact node graph for relationships and dependencies.

## How To Improve The Videos

The current templates are reliable, but they still look template-like because most of them use generic geometry, generic motion, and generic data. The biggest improvements should happen in this order:

- Add visual specificity per concept. For example, a genetics video should not use the same generic network as a neural-network video. Add domain-specific shapes, labels, and examples.
- Replace random or fake values. `bar_chart`, `line_chart`, and `proportional_chart` can use `data_points`; real values and explicit curve types make scenes feel intentional.
- Make motion explain the idea. Several templates animate entrance only, then wait. Use motion to reveal cause, comparison, dependency, or change over time.
- Reduce repeated chrome. The top bar is consistent, but it consumes space and makes every middle scene feel similar. Consider a lighter chrome mode for highly visual layouts.
- Add variants. `scene_variant` is currently normalized to `basic`, so the system cannot yet pick hero, split, dense, sparse, or diagram-first versions.
- Improve typography hierarchy. Current text is crisp, but all templates share the same sans-serif voice and similar scale. Add stronger headline/body contrast and template-specific label styles.
- Use stronger composition. Many bodies are centered and symmetric. Add diagonal layouts, asymmetry, image-like framing, and larger focal objects where the concept allows it.
