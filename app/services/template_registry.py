from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TemplateDefinition:
    name: str
    prompt: str


SPECIAL_LAYOUTS = ("title_card", "summary", "thanks")

CONTENT_TEMPLATES = (
    TemplateDefinition(
        "statement",
        "one powerful insight, principle, or definition stated boldly. Put the statement in `takeaway` (or `hook`). Add 1–2 supporting clauses in `key_points`. Use `highlight_terms` for the eyebrow label. No equations or data needed.",
    ),
    TemplateDefinition(
        "equation",
        "a single equation is the visual centerpiece. Provide 1–2 compact LaTeX equations in `equations`. Put each symbol name (e.g. 'E', 'm', 'c') in `highlight_terms` and the matching definition ('Energy', 'Mass', 'Speed of light') in the corresponding `key_points` entry — one per symbol. The renderer builds a clean variable-definitions table from these pairs.",
    ),
    TemplateDefinition(
        "step_derivation",
        "a formula, proof, or multi-step calculation that unfolds line by line. Provide 2–8 compact LaTeX strings in `equations` (each a single step or transformation). Add short step labels in `visual_items` (e.g. 'Given', 'Expand', 'Simplify'). No data or chips needed.",
    ),
    TemplateDefinition(
        "distribution",
        "probability, p-values, sampling, statistical significance, normal/Gaussian curves. Use `highlight_terms` for the x-axis label and tail-area label. Put a concise interpretation in `takeaway` and additional context in `key_points[0]`.",
    ),
    TemplateDefinition(
        "axes_plot",
        "an x-y plot of a function such as growth, decay, log, parabola, sine, or oscillation. Use `highlight_terms[0]` for the x-axis label and `highlight_terms[1]` for the y-axis label. Provide 1–3 named points in `visual_items`. Put the reading of the curve in `takeaway`.",
    ),
    TemplateDefinition(
        "line_chart",
        "a trend over ordered observations. Provide `data_points` with concrete labels and numeric values. Add `takeaway` for the main trend and one `key_points` line for the interpretation.",
    ),
    TemplateDefinition(
        "bar_chart",
        "ranking, percentages, or magnitude comparison. Provide `data_points` with concrete labels and values (up to 5). Put the main insight in `takeaway` and one supporting detail in `key_points[0]`.",
    ),
    TemplateDefinition(
        "proportional_chart",
        "parts of a whole, ratios, mixture, composition, or percentage breakdown. Provide `data_points` (up to 5) that sum to a meaningful whole. Each slice is labeled with its name and percentage. Add `takeaway` for the headline insight.",
    ),
    TemplateDefinition(
        "comparison",
        "side-by-side contrast of two things. Provide exactly two thing-names in `visual_items[0]` and `visual_items[1]`. Provide 3–4 shared traits or tradeoffs in `key_points` — the renderer splits them evenly across the two panels.",
    ),
    TemplateDefinition(
        "before_after",
        "a misconception, transformation, or state change. Provide before/after labels in `visual_items` and the changed properties in `key_points`.",
    ),
    TemplateDefinition(
        "flow",
        "pipelines, processes, ordered transformations, or numbered procedural steps. Provide 3–4 short stage names (2–5 words each) in `visual_items`. Provide a matching description sentence for each stage in `key_points` — these appear inside the stage cards.",
    ),
    TemplateDefinition(
        "timeline",
        "historical sequence, lifecycle, phases, milestones, or ordered discoveries. Provide 3–5 event/milestone names in `visual_items`. Provide a matching brief description for each milestone in `key_points`. Add a summary in `takeaway`.",
    ),
    TemplateDefinition(
        "cause_effect",
        "one driver branching into 2–4 consequences. Put the cause in `highlight_terms[0]`. Put each effect label in `visual_items` and the corresponding explanation in `key_points`.",
    ),
    TemplateDefinition(
        "network",
        "a center concept connected to child nodes showing relationships or dependencies. Put the center title in `highlight_terms[0]`, child titles (2–5) in `visual_items`, and matching child descriptions in `key_points`.",
    ),
    TemplateDefinition(
        "bullets",
        "only when no visual layout fits. Use sparingly as an emergency fallback.",
    ),
)

CONTENT_LAYOUTS = tuple(template.name for template in CONTENT_TEMPLATES)
VALID_LAYOUTS = ("auto",) + SPECIAL_LAYOUTS + CONTENT_LAYOUTS


def content_layout_prompt() -> str:
    return "\n".join(f"- `{template.name}`: {template.prompt}" for template in CONTENT_TEMPLATES)
