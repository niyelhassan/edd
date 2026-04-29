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
        "a single equation is the focus. Provide 1 compact LaTeX equation, 2-4 symbol/component labels in `highlight_terms`, and short definitions in `key_points` when useful.",
    ),
    TemplateDefinition(
        "step_derivation",
        "a formula, proof, or calculation unfolds over steps. Provide 2-6 compact LaTeX equations and short step labels in `visual_items`.",
    ),
    TemplateDefinition(
        "distribution",
        "probability, p-values, sampling, statistical significance, normal/Gaussian curves. Use `highlight_terms` for the x-axis and tail-area labels, and add an interpretation in `takeaway`.",
    ),
    TemplateDefinition(
        "axes_plot",
        "an x-y plot of a function such as growth, decay, log, parabola, or oscillation. Use `highlight_terms` for axis labels, `visual_items` for 1-3 named points, and `takeaway` for the reading of the curve.",
    ),
    TemplateDefinition(
        "line_chart",
        "a trend over ordered observations. Use only when `data_points` are meaningful; add `takeaway` and one `key_points` line to explain the trend.",
    ),
    TemplateDefinition(
        "bar_chart",
        "ranking, percentages, or magnitude comparison. Prefer `data_points`; also provide `takeaway` and one short `key_points` interpretation.",
    ),
    TemplateDefinition(
        "proportional_chart",
        "parts of a whole, ratios, mixture, composition, or percentage breakdown. Prefer `data_points` that sum to a meaningful whole.",
    ),
    TemplateDefinition(
        "comparison",
        "side-by-side contrast. Provide exactly two thing-names in `visual_items` and shared traits or tradeoffs in `key_points`.",
    ),
    TemplateDefinition(
        "before_after",
        "a misconception, transformation, or state change. Provide the before and after labels in `visual_items` and the changed properties in `key_points`.",
    ),
    TemplateDefinition(
        "flow",
        "pipelines, processes, ordered transformations, or numbered procedural steps. Provide 3-4 short stage names in `visual_items` and matching short descriptions in `key_points`.",
    ),
    TemplateDefinition(
        "timeline",
        "historical sequence, lifecycle, phases, milestones, or ordered discoveries. Provide 3-5 events in `visual_items` and an interpretation in `takeaway`.",
    ),
    TemplateDefinition(
        "cause_effect",
        "one driver branching into consequences. Put the cause first in `highlight_terms` and 2-4 effects in `visual_items`.",
    ),
    TemplateDefinition(
        "network",
        "a center concept connected to child ideas, relationships, dependencies, or graph structures. Put center title in `highlight_terms[0]`, child titles in `visual_items`, and matching child text in `key_points`.",
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
