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
        "one powerful insight, principle, or definition stated boldly and centered. Put the statement in `takeaway` (or `hook`). Add 1–3 supporting clauses in `key_points` — each appears as a centered line below the main statement. Use `highlight_terms` for the eyebrow label. No equations or data needed. This is also the default layout when no other visual template fits.",
    ),
    TemplateDefinition(
        "equation",
        "a single equation is the visual centerpiece. Provide 1–2 compact LaTeX equations in `equations`. Put each symbol name (e.g. 'E', 'm', 'c') in `highlight_terms` and the matching definition ('Energy', 'Mass', 'Speed of light') in the corresponding `key_points` entry — one per symbol. Add a `takeaway` sentence explaining the significance of the equation.",
    ),
    TemplateDefinition(
        "step_derivation",
        "a formula, proof, or multi-step calculation that unfolds line by line. Provide 2–8 compact LaTeX strings in `equations` (each a single step or transformation). Add short step labels in `visual_items` (e.g. 'Given', 'Expand', 'Simplify'). Add a `takeaway` summarizing the result.",
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
        "parts of a whole, ratios, mixture, composition, or percentage breakdown. Provide `data_points` (up to 5) that sum to a meaningful whole. Add `takeaway` for the headline insight and one `key_points` line for context.",
    ),
    TemplateDefinition(
        "comparison",
        "side-by-side contrast of two things. Provide exactly two thing-names in `visual_items[0]` and `visual_items[1]`. Provide 3–4 shared traits or tradeoffs in `key_points` — the renderer splits them evenly across the two panels. Add a `takeaway` summarizing which is preferred or why the distinction matters.",
    ),
    TemplateDefinition(
        "before_after",
        "a misconception, transformation, or state change. Provide before/after labels in `visual_items` and 2–3 changed properties in `key_points`. Add a `takeaway` explaining the significance of the change.",
    ),
    TemplateDefinition(
        "flow",
        "pipelines, processes, ordered transformations, or numbered procedural steps. Provide 3–4 short stage names (2–5 words each) in `visual_items`. Provide a matching description sentence for each stage in `key_points` — these appear inside the stage cards. Add a `takeaway` for the overall process.",
    ),
    TemplateDefinition(
        "timeline",
        "historical sequence, lifecycle, phases, milestones, or ordered discoveries. Provide 3–5 event/milestone names in `visual_items`. Provide a matching brief description for each milestone in `key_points`. Add a summary in `takeaway`.",
    ),
    TemplateDefinition(
        "cause_effect",
        "one driver branching into 2–4 consequences. Put the cause in `highlight_terms[0]`. Put each effect label in `visual_items` and the corresponding explanation in `key_points`. Add a `takeaway` with the key implication.",
    ),
    TemplateDefinition(
        "network",
        "a center concept connected to child nodes showing relationships or dependencies. Put the center title in `highlight_terms[0]`, child titles (2–5) in `visual_items`, and matching child descriptions in `key_points`.",
    ),
)

CONTENT_LAYOUTS = tuple(template.name for template in CONTENT_TEMPLATES)
VALID_LAYOUTS = ("auto",) + SPECIAL_LAYOUTS + CONTENT_LAYOUTS


def content_layout_prompt() -> str:
    return "\n".join(f"- `{template.name}`: {template.prompt}" for template in CONTENT_TEMPLATES)
