from __future__ import annotations

import json
from pathlib import Path


MODULE_TEMPLATE = '''from manim import *
import math

try:
    from manimpango import list_fonts as _list_fonts
except Exception:
    def _list_fonts():
        return []


STORY = __STORY_JSON__
SCENES = STORY["scenes"]

THEMES = {
    "blueprint": {"background": "#F6F8FB", "ink": "#0F172A", "muted": "#64748B", "accent": "#1D4ED8", "accent_2": "#0EA5E9", "panel": "#CBD5E1", "card": "#FFFFFF"},
    "chalk": {"background": "#F8F7F2", "ink": "#1F2937", "muted": "#6B7280", "accent": "#0F766E", "accent_2": "#14B8A6", "panel": "#D6D3D1", "card": "#FFFCF7"},
    "lab": {"background": "#F5FAFA", "ink": "#0F172A", "muted": "#4B5563", "accent": "#0891B2", "accent_2": "#14B8A6", "panel": "#CFE8EA", "card": "#FFFFFF"},
    "signal": {"background": "#FFF8F2", "ink": "#1F2937", "muted": "#57534E", "accent": "#F97316", "accent_2": "#FB923C", "panel": "#F1D5BF", "card": "#FFFFFF"},
    "midnight": {"background": "#0B1220", "ink": "#E5E7EB", "muted": "#94A3B8", "accent": "#60A5FA", "accent_2": "#22D3EE", "panel": "#1E293B", "card": "#111827"},
    "sunset": {"background": "#FFF5EE", "ink": "#431407", "muted": "#9A3412", "accent": "#EA580C", "accent_2": "#F59E0B", "panel": "#FED7AA", "card": "#FFFFFF"},
}

TEMPLATE_ORDER = [
    "hero_reveal",
    "concept_network",
    "equation_build",
    "graph_discovery",
    "before_after",
    "process_flow",
    "timeline_story",
    "orbit_system",
    "lab_experiment",
    "probability_grid",
    "distribution_curve",
    "geometry_proof",
    "vector_field",
    "feedback_loop",
    "research_bridge",
]

LEGACY_VARIANTS = {
    "basic": "hero_reveal",
    "hero": "hero_reveal",
    "split": "before_after",
    "spotlight": "hero_reveal",
    "compare": "before_after",
    "grid": "probability_grid",
    "stage": "research_bridge",
    "orbit": "orbit_system",
    "magazine": "research_bridge",
}

LAYOUT_TO_TEMPLATE = {
    "concept_map": "concept_network",
    "equation": "equation_build",
    "comparison": "before_after",
    "axes": "graph_discovery",
    "timeline": "timeline_story",
    "flow": "process_flow",
    "orbit": "orbit_system",
    "matrix": "probability_grid",
    "distribution": "distribution_curve",
    "geometry": "geometry_proof",
    "vector": "vector_field",
    "bridge": "research_bridge",
    "feedback": "feedback_loop",
    "lab": "lab_experiment",
}


def colors():
    return THEMES.get(STORY.get("visual_theme", "blueprint"), THEMES["blueprint"])


def pick_font():
    preferred = ["Avenir Next", "SF Pro Display", "Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"]
    available = set(_list_fonts() or [])
    if not available:
        return preferred[-1]
    for name in preferred:
        if name in available:
            return name
    return preferred[-1]


FONT_FAMILY = pick_font()


def clean_text(value):
    return " ".join(str(value or "").replace("\\n", " ").split()).strip()


def truncate_text(text, max_chars):
    text = clean_text(text)
    if len(text) <= max_chars:
        return text
    clipped = text[:max_chars].rsplit(" ", 1)[0].strip()
    return clipped or text[:max_chars]


def wrap_text(text, max_chars=28, max_lines=3):
    words = clean_text(text).split()
    if not words:
        return ""
    lines = []
    current = ""
    index = 0
    while index < len(words):
        word = words[index]
        candidate = f"{current} {word}".strip()
        if not current or len(candidate) <= max_chars:
            current = candidate
            index += 1
            continue
        lines.append(current)
        current = ""
        if len(lines) >= max_lines - 1:
            break
    remaining = words[index:]
    if current:
        lines.append(current)
    elif remaining:
        lines.append(remaining.pop(0))
    if remaining:
        tail = truncate_text(" ".join([lines[-1], *remaining]), max_chars - 1)
        lines[-1] = tail.rstrip(" .,;:") + "..."
    return "\\n".join(lines[:max_lines])


def fit_box(mobject, width, height=None):
    if mobject.width > width:
        mobject.scale_to_fit_width(width)
    if height and mobject.height > height:
        mobject.scale_to_fit_height(height)
    return mobject


def safe_text(
    text,
    *,
    font_size,
    color,
    weight=NORMAL,
    width=None,
    height=None,
    max_chars=28,
    max_lines=3,
):
    wrapped = wrap_text(text, max_chars=max_chars, max_lines=max_lines)
    obj = Text(wrapped or " ", font=FONT_FAMILY, font_size=font_size, color=color, weight=weight)
    if width or height:
        fit_box(obj, width or obj.width, height)
    return obj


def safe_math(expr, palette):
    text = clean_text(expr)
    if not text:
        return None
    try:
        obj = MathTex(text, color=palette["ink"], font_size=52)
    except Exception:
        obj = safe_text(text, font_size=28, color=palette["ink"], weight=SEMIBOLD, max_chars=24, max_lines=2)
    return fit_box(obj, 5.7, 1.5)


def scene_terms(scene, limit=4):
    values = []
    for key in ("highlight_terms", "visual_items", "key_points"):
        for item in scene.get(key, []):
            text = clean_text(item)
            if text and text not in values:
                values.append(text)
            if len(values) >= limit:
                return values
    headline = clean_text(scene.get("headline"))
    return [headline or "Concept"]


def scene_points(scene, limit=3):
    values = []
    for key in ("key_points", "visual_items", "highlight_terms"):
        for item in scene.get(key, []):
            text = clean_text(item)
            if text and text not in values:
                values.append(text)
            if len(values) >= limit:
                return values
    return values


def card_fill(palette):
    return palette["card"]


def place_on_stage(mobject, frame, pad=0.45):
    fit_box(mobject, frame.width - pad, frame.height - pad)
    mobject.move_to(frame.get_center())
    return mobject


def build_info_column(scene, palette):
    title = safe_text(scene.get("headline", "Scene"), font_size=36, color=palette["ink"], weight=BOLD, width=5.1, height=1.3, max_chars=24, max_lines=2)
    title.to_edge(UP, buff=0.55).to_edge(LEFT, buff=0.62)

    hook = safe_text(scene.get("hook") or scene.get("takeaway") or "", font_size=22, color=palette["accent"], weight=SEMIBOLD, width=5.0, height=1.0, max_chars=30, max_lines=2)
    hook.next_to(title, DOWN, buff=0.25, aligned_edge=LEFT)

    rows = []
    for item in scene_points(scene, limit=3):
        dot = Dot(radius=0.05, color=palette["accent"])
        text = safe_text(item, font_size=20, color=palette["ink"], width=4.5, height=0.7, max_chars=34, max_lines=2)
        rows.append(VGroup(dot, text).arrange(RIGHT, buff=0.18, aligned_edge=UP))
    bullets = VGroup(*rows).arrange(DOWN, buff=0.24, aligned_edge=LEFT) if rows else VGroup()
    if len(bullets):
        bullets.next_to(hook, DOWN, buff=0.34, aligned_edge=LEFT)

    return VGroup(title, hook, bullets)


def hero_reveal_visual(scene, palette):
    terms = scene_terms(scene, limit=4)
    ring_a = Circle(radius=1.25, color=palette["accent"], stroke_width=4).set_fill(palette["accent"], opacity=0.07)
    ring_b = Circle(radius=1.8, color=palette["panel"], stroke_width=3)
    center = safe_text(terms[0], font_size=48, color=palette["ink"], weight=BOLD, max_chars=16, max_lines=2)
    nodes = []
    for idx, term in enumerate(terms[1:4]):
        card = RoundedRectangle(corner_radius=0.18, width=2.0, height=0.78, stroke_color=palette["panel"], fill_color=card_fill(palette), fill_opacity=0.95)
        label = safe_text(term, font_size=17, color=palette["ink"], width=1.5, height=0.45, max_chars=16, max_lines=1)
        angle = math.radians([20, 150, 270][idx])
        nodes.append(VGroup(card, label).move_to(np.array([2.15 * math.cos(angle), 1.95 * math.sin(angle), 0])))
    return VGroup(ring_a, ring_b, center, *nodes)


def concept_network_visual(scene, palette):
    terms = scene_terms(scene, limit=5)
    center = Circle(radius=0.84, color=palette["accent"], stroke_width=4).set_fill(palette["accent"], opacity=0.1)
    center_label = safe_text(terms[0], font_size=22, color=palette["ink"], weight=BOLD, width=1.6, height=0.7, max_chars=14)
    center_group = VGroup(center, center_label)
    positions = [UP * 2.0 + RIGHT * 1.6, RIGHT * 2.35 + DOWN * 0.2, LEFT * 2.15 + DOWN * 1.35, LEFT * 2.25 + UP * 0.9]
    nodes = []
    links = []
    for idx, term in enumerate(terms[1:5]):
        card = RoundedRectangle(corner_radius=0.16, width=2.05, height=0.76, stroke_color=palette["panel"], fill_color=card_fill(palette), fill_opacity=0.95)
        label = safe_text(term, font_size=16, color=palette["ink"], width=1.6, height=0.45, max_chars=16, max_lines=1)
        node = VGroup(card, label).move_to(positions[idx])
        nodes.append(node)
        links.append(Line(center_group.get_center(), node.get_center(), color=palette["panel"], stroke_width=3))
    return VGroup(center_group, *links, *nodes)


def equation_build_visual(scene, palette):
    eq = safe_math((scene.get("equations") or [""])[0], palette)
    if eq is None:
        eq = safe_text(scene.get("headline", "Equation"), font_size=40, color=palette["ink"], weight=BOLD, max_chars=20, max_lines=2)
    halo = RoundedRectangle(corner_radius=0.2, width=max(2.6, eq.width + 0.7), height=max(1.2, eq.height + 0.45), stroke_color=palette["panel"], fill_color=card_fill(palette), fill_opacity=0.95)
    chips = []
    for idx, term in enumerate(scene_terms(scene, limit=3)):
        chip = RoundedRectangle(corner_radius=0.14, width=1.7, height=0.62, stroke_color=palette["panel"], fill_color=card_fill(palette), fill_opacity=0.95)
        text = safe_text(term, font_size=15, color=palette["ink"], max_chars=14, max_lines=1)
        chips.append(VGroup(chip, text).move_to(DOWN * 1.35 + RIGHT * (idx - 1) * 2.05))
    return VGroup(halo, eq, *chips)


def graph_discovery_visual(scene, palette):
    axes = Axes(x_range=[-3.2, 3.2, 1], y_range=[-2.6, 2.6, 1], x_length=5.4, y_length=4.3, axis_config={"color": palette["muted"], "stroke_width": 3}, tips=False)
    blob = " ".join([clean_text(scene.get("narration")), clean_text(scene.get("visual_goal"))]).lower()
    if any(term in blob for term in ("growth", "increase", "accumulate")):
        func = lambda x: 1.8 / (1 + math.exp(-1.2 * x)) - 0.9
    elif any(term in blob for term in ("decay", "drop", "decrease")):
        func = lambda x: 2.1 * math.exp(-0.8 * (x + 2.6)) - 1.65
    else:
        func = lambda x: 0.75 * math.sin(x) + 0.2 * x
    curve = axes.plot(func, x_range=[-3, 3], color=palette["accent"])
    labels = scene_terms(scene, limit=2)
    x_label = safe_text(labels[0] if labels else "Input", font_size=18, color=palette["muted"], max_chars=12, max_lines=1).next_to(axes.x_axis, RIGHT, buff=0.08)
    y_label = safe_text(labels[1] if len(labels) > 1 else "Output", font_size=18, color=palette["muted"], max_chars=12, max_lines=1).next_to(axes.y_axis, UP, buff=0.08)
    points = []
    for idx, item in enumerate(scene_points(scene, limit=3)):
        x_coord = [-2.0, 0.2, 2.15][idx]
        y_coord = func(x_coord)
        dot = Dot(axes.c2p(x_coord, y_coord), radius=0.08, color=palette["accent_2"])
        tag = safe_text(item, font_size=15, color=palette["ink"], width=1.6, height=0.45, max_chars=14, max_lines=1).next_to(dot, UR, buff=0.06)
        points.extend([dot, tag])
    return VGroup(axes, curve, x_label, y_label, *points)


def before_after_visual(scene, palette):
    terms = scene_terms(scene, limit=2)
    left = RoundedRectangle(corner_radius=0.22, width=2.45, height=3.3, stroke_color=palette["panel"], fill_color=card_fill(palette), fill_opacity=0.95).shift(LEFT * 1.9)
    right = left.copy().shift(RIGHT * 3.8)
    left_label = safe_text(terms[0] if terms else "Before", font_size=22, color=palette["ink"], weight=SEMIBOLD, width=1.9, height=0.8, max_chars=14).move_to(left)
    right_label = safe_text(terms[1] if len(terms) > 1 else "After", font_size=22, color=palette["ink"], weight=SEMIBOLD, width=1.9, height=0.8, max_chars=14).move_to(right)
    arrow = Arrow(left.get_right(), right.get_left(), color=palette["accent"], stroke_width=4, buff=0.18, tip_length=0.16)
    return VGroup(left, right, left_label, right_label, arrow)


def process_flow_visual(scene, palette):
    entries = scene_points(scene, limit=4) or ["Input", "Transform", "Output"]
    nodes = []
    arrows = []
    for idx, item in enumerate(entries):
        box = RoundedRectangle(corner_radius=0.18, width=1.8, height=0.82, stroke_width=0, fill_color=palette["accent"] if idx % 2 == 0 else palette["accent_2"], fill_opacity=0.95)
        label = safe_text(item, font_size=16, color=WHITE, width=1.45, height=0.5, max_chars=14, max_lines=2)
        node = VGroup(box, label).move_to(LEFT * (len(entries) - 1) + RIGHT * (idx * 2.0))
        nodes.append(node)
        if idx > 0:
            arrows.append(Arrow(nodes[idx - 1].get_right(), node.get_left(), color=palette["panel"], stroke_width=4, buff=0.15, tip_length=0.12))
    return VGroup(*nodes, *arrows)


def timeline_story_visual(scene, palette):
    base = Line(LEFT * 3.0, RIGHT * 3.0, color=palette["panel"], stroke_width=5)
    milestones = scene_points(scene, limit=4) or ["Start", "Build", "Interpret"]
    offsets = np.linspace(-2.5, 2.5, len(milestones))
    parts = [base]
    for idx, item in enumerate(milestones):
        dot = Dot(radius=0.12, color=palette["accent"] if idx % 2 == 0 else palette["accent_2"]).move_to(base.get_center() + RIGHT * float(offsets[idx]))
        label = safe_text(item, font_size=15, color=palette["ink"], width=1.8, height=0.7, max_chars=15, max_lines=2)
        label.next_to(dot, UP if idx % 2 == 0 else DOWN, buff=0.24)
        parts.extend([dot, label])
    return VGroup(*parts)


def orbit_system_visual(scene, palette):
    terms = scene_terms(scene, limit=3)
    center = Circle(radius=0.42, color=palette["accent"], stroke_width=3).set_fill(palette["accent"], opacity=0.25)
    center_label = safe_text(terms[0], font_size=18, color=palette["ink"], weight=BOLD, max_chars=12, max_lines=1)
    orbit_a = Circle(radius=1.35, color=palette["panel"], stroke_width=2)
    orbit_b = Circle(radius=2.0, color=palette["panel"], stroke_width=2)
    sat_a = Dot(point=RIGHT * 1.35, radius=0.1, color=palette["accent"])
    sat_b = Dot(point=LEFT * 2.0, radius=0.1, color=palette["accent_2"])
    label_a = safe_text(terms[1] if len(terms) > 1 else "Body A", font_size=14, color=palette["ink"], max_chars=10, max_lines=1).next_to(sat_a, UR, buff=0.05)
    label_b = safe_text(terms[2] if len(terms) > 2 else "Body B", font_size=14, color=palette["ink"], max_chars=10, max_lines=1).next_to(sat_b, UR, buff=0.05)
    return VGroup(center, center_label, orbit_a, orbit_b, sat_a, sat_b, label_a, label_b)


def lab_experiment_visual(scene, palette):
    left = RoundedRectangle(corner_radius=0.18, width=1.7, height=2.8, stroke_color=palette["panel"], fill_color=card_fill(palette), fill_opacity=0.94).shift(LEFT * 1.8)
    right = left.copy().shift(RIGHT * 3.6)
    liquid_left = Rectangle(width=1.3, height=1.1, stroke_width=0, fill_color=palette["accent"], fill_opacity=0.32).move_to(left.get_bottom() + UP * 0.75)
    liquid_right = Rectangle(width=1.3, height=0.8, stroke_width=0, fill_color=palette["accent_2"], fill_opacity=0.28).move_to(right.get_bottom() + UP * 0.6)
    particles = []
    for row in range(2):
        for col in range(3):
            particles.append(Dot(radius=0.045, color=palette["accent"]).move_to(left.get_center() + LEFT * 0.45 + RIGHT * col * 0.38 + DOWN * 0.35 + UP * row * 0.28))
    return VGroup(left, right, liquid_left, liquid_right, *particles)


def probability_grid_visual(scene, palette):
    cells = [Square(side_length=0.38, stroke_color=palette["panel"], stroke_width=1.8, fill_color=card_fill(palette), fill_opacity=0.95) for _ in range(25)]
    grid = VGroup(*cells).arrange_in_grid(rows=5, cols=5, buff=0.06)
    count = min(20, max(6, len(scene_terms(scene, limit=5)) * 3 + 2))
    for idx in range(count):
        cells[idx].set_fill(palette["accent"], opacity=0.82).set_stroke(palette["accent"], width=2.1)
    ratio = safe_text(f"{count}/25", font_size=30, color=palette["ink"], weight=BOLD, max_chars=10, max_lines=1).next_to(grid, DOWN, buff=0.3)
    return VGroup(grid, ratio)


def distribution_curve_visual(scene, palette):
    axes = Axes(x_range=[-3.5, 3.5, 1], y_range=[0, 3.4, 0.5], x_length=5.5, y_length=4.0, axis_config={"color": palette["muted"], "stroke_width": 3}, tips=False)
    curve = axes.plot(lambda x: 2.8 * math.exp(-(x**2) / 2), x_range=[-3.2, 3.2], color=palette["accent"])
    area = axes.get_area(curve, x_range=[-1.0, 1.0], color=palette["accent_2"], opacity=0.35)
    mean_line = DashedLine(axes.c2p(0, 0), axes.c2p(0, 2.8), color=palette["panel"], stroke_width=3)
    return VGroup(axes, curve, area, mean_line)


def geometry_proof_visual(scene, palette):
    a = np.array([-2.2, -1.25, 0])
    b = np.array([2.0, -1.25, 0])
    c = np.array([0.4, 1.7, 0])
    triangle = Polygon(a, b, c, color=palette["accent"], stroke_width=4)
    fill = triangle.copy().set_stroke(width=0).set_fill(palette["accent"], opacity=0.11)
    side_ab = Line(a, b)
    side_bc = Line(b, c)
    side_ca = Line(c, a)
    angle_a = Angle(side_ca, side_ab, radius=0.42, color=palette["accent_2"])
    angle_b = Angle(side_ab, side_bc, radius=0.36, color=palette["accent_2"])
    eq = safe_text((scene.get("equations") or ["angles sum to 180"])[0], font_size=20, color=palette["ink"], max_chars=26, max_lines=2).next_to(triangle, DOWN, buff=0.3)
    return VGroup(fill, triangle, angle_a, angle_b, eq)


def vector_field_visual(scene, palette):
    arrows = []
    for x in [-2, -1, 0, 1, 2]:
        for y in [-2, -1, 0, 1, 2]:
            direction = np.array([-float(y), float(x), 0.0])
            norm = np.linalg.norm(direction[:2]) or 1.0
            direction = direction / norm * 0.42
            center = np.array([x * 0.9, y * 0.7, 0.0])
            start = center - direction * 0.5
            end = center + direction * 0.5
            color = palette["accent"] if (x + y) % 2 == 0 else palette["accent_2"]
            arrows.append(Arrow(start, end, buff=0, color=color, stroke_width=3, max_tip_length_to_length_ratio=0.33))
    label = safe_text("Direction field", font_size=18, color=palette["ink"], max_chars=16, max_lines=1).next_to(VGroup(*arrows), DOWN, buff=0.22)
    return VGroup(*arrows, label)


def feedback_loop_visual(scene, palette):
    labels = scene_terms(scene, limit=4)
    while len(labels) < 4:
        labels.append(f"Step {len(labels) + 1}")
    positions = [UP * 1.9, RIGHT * 2.2, DOWN * 1.9, LEFT * 2.2]
    nodes = []
    arrows = []
    for idx, text in enumerate(labels[:4]):
        circle = Circle(radius=0.58, color=palette["panel"], stroke_width=3).set_fill(card_fill(palette), opacity=0.95)
        label = safe_text(text, font_size=14, color=palette["ink"], width=1.0, height=0.5, max_chars=10, max_lines=2)
        nodes.append(VGroup(circle, label).move_to(positions[idx]))
    for idx in range(4):
        arrows.append(Arrow(nodes[idx].get_center(), nodes[(idx + 1) % 4].get_center(), color=palette["accent"], stroke_width=3, path_arc=PI / 3, buff=0.78, tip_length=0.13))
    return VGroup(*nodes, *arrows)


def research_bridge_visual(scene, palette):
    terms = scene_terms(scene, limit=2)
    left = RoundedRectangle(corner_radius=0.2, width=2.45, height=2.4, stroke_color=palette["panel"], fill_color=card_fill(palette), fill_opacity=0.96).shift(LEFT * 2.2)
    right = left.copy().shift(RIGHT * 4.4)
    left_text = safe_text(terms[0] if terms else "Question", font_size=20, color=palette["ink"], width=1.9, height=0.95, max_chars=16, max_lines=2).move_to(left)
    right_text = safe_text(terms[1] if len(terms) > 1 else "Evidence", font_size=20, color=palette["ink"], width=1.9, height=0.95, max_chars=16, max_lines=2).move_to(right)
    bridge = ArcBetweenPoints(left.get_right() + RIGHT * 0.1, right.get_left() + LEFT * 0.1, angle=-PI / 3, color=palette["accent"], stroke_width=6)
    runner = Dot(radius=0.09, color=palette["accent_2"]).move_to(bridge.get_start())
    return VGroup(left, right, left_text, right_text, bridge, runner)


TEMPLATE_RENDERERS = {
    "hero_reveal": hero_reveal_visual,
    "concept_network": concept_network_visual,
    "equation_build": equation_build_visual,
    "graph_discovery": graph_discovery_visual,
    "before_after": before_after_visual,
    "process_flow": process_flow_visual,
    "timeline_story": timeline_story_visual,
    "orbit_system": orbit_system_visual,
    "lab_experiment": lab_experiment_visual,
    "probability_grid": probability_grid_visual,
    "distribution_curve": distribution_curve_visual,
    "geometry_proof": geometry_proof_visual,
    "vector_field": vector_field_visual,
    "feedback_loop": feedback_loop_visual,
    "research_bridge": research_bridge_visual,
}


def template_for_scene(scene, scene_index):
    variant = clean_text(scene.get("scene_variant", "")).lower().replace("-", "_").replace(" ", "_")
    variant = LEGACY_VARIANTS.get(variant, variant)
    if variant in TEMPLATE_ORDER:
        return variant

    layout = clean_text(scene.get("layout", "auto")).lower()
    if layout in LAYOUT_TO_TEMPLATE:
        return LAYOUT_TO_TEMPLATE[layout]

    blob = " ".join([
        clean_text(scene.get("headline")),
        clean_text(scene.get("narration")),
        clean_text(scene.get("visual_goal")),
        " ".join(scene.get("highlight_terms", [])),
        " ".join(scene.get("visual_items", [])),
    ]).lower()
    keyword_templates = [
        ("probability_grid", ("probability", "bayes", "odds", "chance")),
        ("distribution_curve", ("distribution", "variance", "gaussian", "normal")),
        ("vector_field", ("vector", "gradient", "field", "flux")),
        ("geometry_proof", ("geometry", "triangle", "theorem", "proof")),
        ("lab_experiment", ("experiment", "molecule", "chemical", "cell", "enzyme")),
        ("orbit_system", ("orbit", "planet", "electron", "rotation")),
        ("feedback_loop", ("feedback", "loop", "cycle", "regulation")),
        ("research_bridge", ("research", "hypothesis", "evidence", "result")),
        ("graph_discovery", ("graph", "plot", "trend", "slope")),
        ("process_flow", ("process", "pipeline", "algorithm", "method")),
    ]
    for template, terms in keyword_templates:
        if any(term in blob for term in terms):
            return template

    return TEMPLATE_ORDER[(max(1, int(scene_index)) - 1) % len(TEMPLATE_ORDER)]


def animate_visual(scene_obj, visual, total):
    if isinstance(visual, VGroup):
        animations = []
        for item in visual:
            if isinstance(item, (Line, Arrow, CurvedArrow, DashedLine, Axes, Arc)):
                animations.append(Create(item))
            elif isinstance(item, (Circle, Dot, Square, Rectangle, RoundedRectangle, Polygon)):
                animations.append(GrowFromCenter(item))
            else:
                animations.append(FadeIn(item, shift=UP * 0.06))
        run_time = min(1.7, total * 0.24)
        scene_obj.play(LaggedStart(*animations, lag_ratio=0.06), run_time=run_time)
        return run_time

    run_time = min(1.4, total * 0.2)
    scene_obj.play(FadeIn(visual, shift=UP * 0.08), run_time=run_time)
    return run_time


def apply_template_motion(scene_obj, template, visual, total):
    if template in {"orbit_system", "feedback_loop"}:
        run_time = min(1.0, total * 0.14)
        scene_obj.play(visual.animate.rotate(PI / 12), run_time=run_time)
        return run_time
    if template in {"vector_field", "graph_discovery"}:
        run_time = min(0.9, total * 0.12)
        scene_obj.play(visual.animate.scale(1.03), run_time=run_time)
        return run_time
    if template in {"process_flow", "timeline_story", "research_bridge"}:
        run_time = min(0.8, total * 0.11)
        scene_obj.play(visual.animate.shift(RIGHT * 0.12), run_time=run_time)
        return run_time
    return 0.0


def build_visual(scene, palette, scene_index):
    template = template_for_scene(scene, scene_index)
    builder = TEMPLATE_RENDERERS.get(template, concept_network_visual)
    return builder(scene, palette), template


def render_scene_page(scene_obj, scene_data, scene_index):
    palette = colors()
    scene_obj.camera.background_color = palette["background"]

    top_band = Rectangle(height=0.8, width=14.5, stroke_width=0, fill_color=palette["panel"], fill_opacity=0.38).to_edge(UP, buff=0)
    accent_bar = Rectangle(height=7.2, width=0.15, stroke_width=0, fill_color=palette["accent"], fill_opacity=1).to_edge(LEFT, buff=0)
    scene_obj.add(top_band, accent_bar)

    info = build_info_column(scene_data, palette)
    stage = RoundedRectangle(corner_radius=0.26, width=6.8, height=5.7, stroke_color=palette["panel"], fill_color=card_fill(palette), fill_opacity=0.93)
    stage.to_edge(RIGHT, buff=0.58).shift(DOWN * 0.15)

    scene_obj.play(FadeIn(stage, scale=0.98), run_time=0.45)
    scene_obj.play(FadeIn(info[0], shift=UP * 0.18), run_time=0.35)
    if len(info) > 1:
        scene_obj.play(FadeIn(info[1], shift=RIGHT * 0.1), run_time=0.25)
    if len(info) > 2 and len(info[2]):
        for row in info[2]:
            scene_obj.play(FadeIn(row, shift=UP * 0.08), run_time=0.2)

    total = max(6.0, float(scene_data.get("target_duration_seconds", 10.0)) + 0.2)
    spent = 1.25

    visual, template = build_visual(scene_data, palette, scene_index)
    visual = place_on_stage(visual, stage)
    spent += animate_visual(scene_obj, visual, total)
    spent += apply_template_motion(scene_obj, template, visual, total)

    tag = safe_text(template.replace("_", " "), font_size=14, color=palette["muted"], max_chars=24, max_lines=1).next_to(stage, DOWN, buff=0.16)
    scene_obj.play(FadeIn(tag), run_time=0.2)
    spent += 0.2

    scene_obj.wait(max(0.35, total - spent))


__SCENE_CLASSES__
'''


def _scene_class_block(class_name: str, index: int) -> str:
    return f'''
class {class_name}(Scene):
    def construct(self):
        render_scene_page(self, SCENES[{index}], {index + 1})
'''


def build_manim_module(*, storyboard: dict, output_path: Path) -> Path:
    scenes = storyboard["scenes"]
    scene_classes = "\n".join(_scene_class_block(scene["class_name"], index) for index, scene in enumerate(scenes))
    module = (
        MODULE_TEMPLATE.replace("__STORY_JSON__", json.dumps(storyboard, indent=2))
        .replace("__SCENE_CLASSES__", scene_classes)
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(module, encoding="utf-8")
    return output_path
