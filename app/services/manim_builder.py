from __future__ import annotations

import json
from pathlib import Path


MODULE_TEMPLATE = '''from manim import *
import textwrap
import math

STORY = __STORY_JSON__
SCENES = STORY["scenes"]
SCENE_CLASS_NAMES = __SCENE_CLASS_NAMES__

THEMES = {
    "blueprint": {
        "background": "#F8FAFC",
        "ink": "#0F172A",
        "muted": "#475569",
        "accent": "#2563EB",
        "accent_2": "#0EA5E9",
        "accent_3": "#F97316",
        "panel": "#E2E8F0",
        "good": "#16A34A",
    },
    "chalk": {
        "background": "#F7F3E9",
        "ink": "#1F2937",
        "muted": "#6B7280",
        "accent": "#0F766E",
        "accent_2": "#14B8A6",
        "accent_3": "#F59E0B",
        "panel": "#D6D3D1",
        "good": "#15803D",
    },
    "lab": {
        "background": "#F8FAFC",
        "ink": "#111827",
        "muted": "#4B5563",
        "accent": "#7C3AED",
        "accent_2": "#EC4899",
        "accent_3": "#06B6D4",
        "panel": "#E5E7EB",
        "good": "#22C55E",
    },
    "signal": {
        "background": "#FFF7ED",
        "ink": "#1C1917",
        "muted": "#57534E",
        "accent": "#DC2626",
        "accent_2": "#EA580C",
        "accent_3": "#2563EB",
        "panel": "#E7E5E4",
        "good": "#16A34A",
    },
    "midnight": {
        "background": "#0B1020",
        "ink": "#E2E8F0",
        "muted": "#94A3B8",
        "accent": "#60A5FA",
        "accent_2": "#A78BFA",
        "accent_3": "#22D3EE",
        "panel": "#1E293B",
        "good": "#34D399",
    },
    "sunset": {
        "background": "#FFF6ED",
        "ink": "#431407",
        "muted": "#9A3412",
        "accent": "#EA580C",
        "accent_2": "#F97316",
        "accent_3": "#DB2777",
        "panel": "#FED7AA",
        "good": "#16A34A",
    },
}


def palette():
    return THEMES.get(STORY.get("visual_theme", "blueprint"), THEMES["blueprint"])


def fit_box(mobject, max_width, max_height=None):
    if mobject.width > max_width:
        mobject.scale_to_fit_width(max_width)
    if max_height and mobject.height > max_height:
        mobject.scale_to_fit_height(max_height)
    return mobject


def wrapped_lines(text, width):
    lines = textwrap.wrap(text or "", width=width)
    return lines or [text or ""]


def paragraph_block(text, width=5.0, font_size=30, color="#111827", weight=MEDIUM, line_width=28, max_height=None):
    block = Paragraph(*wrapped_lines(text, line_width), alignment="left", line_spacing=0.76)
    for line in block:
        line.set_color(color)
        line.set_font_size(font_size)
        line.set_weight(weight)
    return fit_box(block, width, max_height)


def title_block(text, colors, width=7.0):
    return paragraph_block(text, width=width, font_size=40, color=colors["ink"], weight=BOLD, line_width=22, max_height=1.9)


def label_chip(text, colors, width=2.15, fill=None):
    fill_color = fill or colors["accent"]
    box = RoundedRectangle(
        corner_radius=0.16,
        height=0.52,
        width=width,
        stroke_width=0,
        fill_color=fill_color,
        fill_opacity=1,
    )
    txt = Text(text, font_size=21, color=WHITE, weight=SEMIBOLD)
    fit_box(txt, width - 0.3, 0.32)
    return VGroup(box, txt).move_to(box)


def chip_row(items, colors, width=6.0):
    chips = []
    fills = [colors["accent"], colors["accent_2"], colors["accent_3"]]
    for index, item in enumerate(items[:3]):
        chips.append(label_chip(item, colors, width=2.0, fill=fills[index % len(fills)]).scale(0.88))
    if not chips:
        chips = [label_chip("core idea", colors, width=2.1).scale(0.88)]
    row = VGroup(*chips).arrange(RIGHT, buff=0.16)
    return fit_box(row, width, 0.75)


def bullet_group(items, colors, width=5.0, font_size=24):
    rows = []
    for item in items[:3]:
        dot = Dot(radius=0.055, color=colors["accent"])
        text = paragraph_block(item, width=width - 0.4, font_size=font_size, color=colors["ink"], line_width=28, max_height=0.95)
        rows.append(VGroup(dot, text).arrange(RIGHT, buff=0.16, aligned_edge=UP))
    if not rows:
        rows = [VGroup(Dot(radius=0.055, color=colors["accent"]), Text("key idea", font_size=24, color=colors["ink"])).arrange(RIGHT, buff=0.16)]
    group = VGroup(*rows).arrange(DOWN, buff=0.22, aligned_edge=LEFT)
    return fit_box(group, width, 3.1)


def safe_equation(expr, colors, width=4.8):
    if not expr:
        return None
    try:
        eq = MathTex(expr, color=colors["ink"], font_size=54)
    except Exception:
        eq = Text(expr, font_size=32, color=colors["ink"], weight=SEMIBOLD)
    return fit_box(eq, width, 1.25)


def panel(width, height, colors, fill_opacity=0.9):
    fill_color = WHITE if colors["background"] != "#0B1020" else colors["panel"]
    return RoundedRectangle(
        corner_radius=0.22,
        width=width,
        height=height,
        stroke_color=colors["panel"],
        stroke_width=2,
        fill_color=fill_color,
        fill_opacity=fill_opacity,
    )


def ambient_background(colors):
    blob_a = Circle(radius=2.2, stroke_width=0, fill_color=colors["accent"], fill_opacity=0.08).move_to(LEFT * 4.1 + UP * 2.6)
    blob_b = Circle(radius=1.7, stroke_width=0, fill_color=colors["accent_2"], fill_opacity=0.08).move_to(RIGHT * 4.8 + DOWN * 2.1)
    blob_c = Circle(radius=1.1, stroke_width=0, fill_color=colors["accent_3"], fill_opacity=0.08).move_to(RIGHT * 2.4 + UP * 3.0)
    line_a = Line(LEFT * 7, RIGHT * 7, color=colors["panel"], stroke_width=1).shift(UP * 2.2).set_opacity(0.35)
    line_b = Line(LEFT * 7, RIGHT * 7, color=colors["panel"], stroke_width=1).shift(DOWN * 2.4).set_opacity(0.25)
    return VGroup(blob_a, blob_b, blob_c, line_a, line_b)


def concept_map_visual(scene, colors):
    core = Circle(radius=0.92, color=colors["accent"], stroke_width=4).set_fill(colors["accent"], opacity=0.08)
    core_text = Text(scene["highlight_terms"][0], font_size=30, color=colors["ink"], weight=BOLD)
    core_group = VGroup(core, core_text)
    positions = [UP * 2.25, RIGHT * 2.85, DOWN * 2.25, LEFT * 2.85]
    nodes = []
    connectors = []
    for index, term in enumerate(scene["visual_items"][:4]):
        node_panel = panel(2.3, 0.9, colors)
        node_text = Text(term, font_size=22, color=colors["ink"], weight=MEDIUM)
        fit_box(node_text, 1.9, 0.42)
        node = VGroup(node_panel, node_text).move_to(positions[index])
        nodes.append(node)
        connectors.append(Line(core_group.get_center(), node.get_center(), color=colors["panel"], stroke_width=3))
    return fit_box(VGroup(*connectors, core_group, *nodes), 6.8, 5.5)


def equation_visual(scene, colors):
    eq = safe_equation(scene["equations"][0] if scene["equations"] else "", colors, width=4.6)
    orbit = Circle(radius=1.8, color=colors["accent"], stroke_width=4).set_fill(colors["accent"], opacity=0.04)
    markers = []
    positions = [UP * 2.2 + RIGHT * 1.6, RIGHT * 2.5, DOWN * 2.0 + RIGHT * 1.25, LEFT * 2.25]
    fills = [colors["accent"], colors["accent_2"], colors["accent_3"], colors["accent"]]
    for index, term in enumerate(scene["highlight_terms"][:4]):
        markers.append(label_chip(term, colors, width=1.9, fill=fills[index]).scale(0.8).move_to(positions[index]))
    pieces = [orbit]
    if eq:
        pieces.append(eq)
    return fit_box(VGroup(*pieces, *markers), 6.5, 5.4)


def comparison_visual(scene, colors):
    left = panel(2.75, 3.6, colors).shift(LEFT * 1.95)
    right = panel(2.75, 3.6, colors).shift(RIGHT * 1.95)
    left_title = Text(scene["visual_items"][0], font_size=26, color=colors["ink"], weight=SEMIBOLD).next_to(left.get_top(), DOWN, buff=0.24)
    right_term = scene["visual_items"][1] if len(scene["visual_items"]) > 1 else scene["highlight_terms"][-1]
    right_title = Text(right_term, font_size=26, color=colors["ink"], weight=SEMIBOLD).next_to(right.get_top(), DOWN, buff=0.24)
    divider = Line(UP * 2.1, DOWN * 2.1, color=colors["panel"], stroke_width=3)
    return fit_box(VGroup(left, right, left_title, right_title, divider), 6.8, 5.4)


def axes_visual(scene, colors):
    axes = Axes(
        x_range=[-3, 3, 1],
        y_range=[-3, 3, 1],
        x_length=5.8,
        y_length=5.3,
        axis_config={"color": colors["muted"], "stroke_width": 3},
        tips=False,
    )
    x_text = scene["highlight_terms"][0] if scene["highlight_terms"] else "horizontal"
    y_text = scene["highlight_terms"][1] if len(scene["highlight_terms"]) > 1 else "vertical"
    x_label = Text(x_text, font_size=21, color=colors["muted"]).next_to(axes.x_axis, RIGHT, buff=0.12)
    y_label = Text(y_text, font_size=21, color=colors["muted"]).next_to(axes.y_axis, UP, buff=0.12)
    coords = [(2, 0), (0, 2), (-2, 0), (1.4, 1.2)]
    markers = []
    for index, item in enumerate(scene["visual_items"][:4]):
        point = Dot(axes.c2p(*coords[index]), radius=0.08, color=colors["accent"] if index % 2 == 0 else colors["accent_3"])
        label = Text(item, font_size=18, color=colors["ink"]).next_to(point, UR, buff=0.08)
        markers.extend([point, label])
    return fit_box(VGroup(axes, x_label, y_label, *markers), 6.8, 5.5)


def timeline_visual(scene, colors):
    base = Line(LEFT * 3.0, RIGHT * 3.0, color=colors["panel"], stroke_width=5)
    points = []
    labels = []
    steps = scene["visual_items"][:4] or scene["highlight_terms"][:4]
    offsets = [-2.6, -0.9, 0.9, 2.6]
    fills = [colors["accent"], colors["accent_2"], colors["accent_3"], colors["accent"]]
    for index, label in enumerate(steps[:4]):
        dot = Dot(radius=0.12, color=fills[index]).move_to(base.get_center() + RIGHT * offsets[index])
        card = panel(1.75, 0.9, colors)
        text = paragraph_block(label, width=1.35, font_size=18, color=colors["ink"], weight=MEDIUM, line_width=12, max_height=0.5)
        item = VGroup(card, text).next_to(dot, UP if index % 2 == 0 else DOWN, buff=0.32)
        points.append(dot)
        labels.append(item)
    return fit_box(VGroup(base, *points, *labels), 6.9, 5.4)


def flow_visual(scene, colors):
    terms = scene["visual_items"][:4] or scene["highlight_terms"][:4]
    nodes = []
    arrows = []
    fills = [colors["accent"], colors["accent_2"], colors["accent_3"], colors["accent"]]
    positions = [LEFT * 3.0 + UP * 1.2, LEFT * 1.0 + DOWN * 0.5, RIGHT * 1.0 + UP * 0.5, RIGHT * 3.0 + DOWN * 1.2]
    for index, term in enumerate(terms[:4]):
        blob = RoundedRectangle(corner_radius=0.24, width=2.0, height=0.95, stroke_width=0, fill_color=fills[index], fill_opacity=0.95)
        text = Text(term, font_size=21, color=WHITE, weight=SEMIBOLD)
        fit_box(text, 1.55, 0.42)
        node = VGroup(blob, text).move_to(positions[index])
        nodes.append(node)
        if index > 0:
            arrows.append(Arrow(nodes[index - 1].get_center(), node.get_center(), color=colors["panel"], stroke_width=5, buff=0.48, tip_length=0.14))
    return fit_box(VGroup(*arrows, *nodes), 6.9, 5.5)


def orbit_visual(scene, colors):
    center = Circle(radius=0.78, color=colors["accent"], stroke_width=4).set_fill(colors["accent"], opacity=0.12)
    center_text = Text(scene["highlight_terms"][0], font_size=26, color=colors["ink"], weight=BOLD)
    orbits = [
        Circle(radius=1.55, color=colors["panel"], stroke_width=2),
        Circle(radius=2.35, color=colors["panel"], stroke_width=2),
    ]
    angles = [25, 140, 245, 320]
    nodes = []
    fills = [colors["accent"], colors["accent_2"], colors["accent_3"], colors["accent"]]
    labels = scene["visual_items"][:4] or scene["highlight_terms"][:4]
    for index, label in enumerate(labels[:4]):
        radius = 1.55 if index < 2 else 2.35
        point = Dot(radius=0.1, color=fills[index]).move_to(radius * RIGHT).rotate(math.radians(angles[index]))
        text = Text(label, font_size=18, color=colors["ink"], weight=MEDIUM).next_to(point, UR, buff=0.06)
        nodes.extend([point, text])
    return fit_box(VGroup(*orbits, center, center_text, *nodes), 6.8, 5.4)


def raw_visual(scene, colors):
    layout = scene.get("layout", "concept_map")
    if layout == "equation":
        return equation_visual(scene, colors)
    if layout == "comparison":
        return comparison_visual(scene, colors)
    if layout == "axes":
        return axes_visual(scene, colors)
    if layout == "timeline":
        return timeline_visual(scene, colors)
    if layout == "flow":
        return flow_visual(scene, colors)
    if layout == "orbit":
        return orbit_visual(scene, colors)
    return concept_map_visual(scene, colors)


def hero_composition(scene, colors):
    title = title_block(scene["headline"], colors, width=9.8).to_edge(UP, buff=0.42)
    hook = paragraph_block(scene.get("hook", ""), width=7.3, font_size=26, color=colors["accent"], weight=SEMIBOLD, line_width=22, max_height=1.05).next_to(title, DOWN, buff=0.18)
    visual = raw_visual(scene, colors).scale(0.98).move_to(DOWN * 0.15)
    support = chip_row(scene.get("highlight_terms", []), colors, width=8.5).to_edge(DOWN, buff=0.72)
    footer = paragraph_block(scene.get("takeaway", ""), width=10.0, font_size=22, color=colors["muted"], line_width=38, max_height=0.9).to_edge(DOWN, buff=0.24)
    return {"title": title, "hook": hook, "visual": visual, "support": support, "footer": footer}


def split_composition(scene, colors):
    title = title_block(scene["headline"], colors, width=5.2)
    hook = paragraph_block(scene.get("hook", ""), width=5.0, font_size=23, color=colors["accent"], weight=SEMIBOLD, line_width=18, max_height=1.0)
    support = bullet_group(scene.get("key_points", []), colors, width=4.9, font_size=23)
    eq = safe_equation(scene["equations"][0] if scene.get("equations") else "", colors, width=4.5)
    left_items = [title, hook, support]
    if eq:
        left_items.append(eq)
    left = VGroup(*left_items).arrange(DOWN, buff=0.3, aligned_edge=LEFT)
    fit_box(left, 5.4, 5.8)
    left.to_edge(LEFT, buff=0.55).shift(UP * 0.18)
    visual = raw_visual(scene, colors).to_edge(RIGHT, buff=0.38)
    footer = paragraph_block(scene.get("takeaway", ""), width=11.5, font_size=22, color=colors["muted"], line_width=38, max_height=0.9).to_edge(DOWN, buff=0.24)
    return {"title": left[0], "hook": left[1], "visual": visual, "support": left[2:], "footer": footer}


def spotlight_composition(scene, colors):
    title = title_block(scene["headline"], colors, width=6.3).to_corner(UL, buff=0.44)
    hook = paragraph_block(scene.get("hook", ""), width=4.3, font_size=22, color=colors["accent"], weight=SEMIBOLD, line_width=17, max_height=1.0).next_to(title, DOWN, buff=0.18, aligned_edge=LEFT)
    glow = Circle(radius=2.4, stroke_width=0, fill_color=colors["accent"], fill_opacity=0.06)
    visual = VGroup(glow, raw_visual(scene, colors).scale(0.9)).move_to(RIGHT * 1.65 + DOWN * 0.12)
    support = VGroup(*[label_chip(item, colors, width=2.1).scale(0.8) for item in scene.get("visual_items", [])[:3]]).arrange(DOWN, buff=0.18)
    if len(support) == 0:
        support = VGroup(label_chip("focus", colors, width=2.0).scale(0.8))
    support.to_edge(LEFT, buff=0.65).shift(DOWN * 1.65)
    footer = paragraph_block(scene.get("takeaway", ""), width=8.0, font_size=22, color=colors["muted"], line_width=32, max_height=0.95).to_edge(DOWN, buff=0.24)
    return {"title": title, "hook": hook, "visual": visual, "support": support, "footer": footer}


def compare_composition(scene, colors):
    title = title_block(scene["headline"], colors, width=9.2).to_edge(UP, buff=0.42)
    hook = paragraph_block(scene.get("hook", ""), width=6.8, font_size=23, color=colors["accent"], weight=SEMIBOLD, line_width=22, max_height=1.0).next_to(title, DOWN, buff=0.14)
    visual = comparison_visual(scene, colors).move_to(DOWN * 0.12)
    left_notes = bullet_group(scene.get("key_points", [])[:2], colors, width=2.35, font_size=18).move_to(LEFT * 1.95 + DOWN * 0.82)
    right_notes = VGroup(*[label_chip(item, colors, width=2.0).scale(0.72) for item in scene.get("highlight_terms", [])[:2]]).arrange(DOWN, buff=0.18)
    if len(right_notes) == 0:
        right_notes = VGroup(label_chip("compare", colors, width=2.0).scale(0.72))
    right_notes.move_to(RIGHT * 1.95 + DOWN * 0.98)
    footer = paragraph_block(scene.get("takeaway", ""), width=10.0, font_size=22, color=colors["muted"], line_width=36, max_height=0.9).to_edge(DOWN, buff=0.24)
    return {"title": title, "hook": hook, "visual": visual, "support": VGroup(left_notes, right_notes), "footer": footer}


def grid_composition(scene, colors):
    title = title_block(scene["headline"], colors, width=5.6).to_corner(UL, buff=0.44)
    hook = paragraph_block(scene.get("hook", ""), width=4.9, font_size=22, color=colors["accent"], weight=SEMIBOLD, line_width=18, max_height=1.0).next_to(title, DOWN, buff=0.16, aligned_edge=LEFT)
    visual = timeline_visual(scene, colors).to_edge(RIGHT, buff=0.4).shift(DOWN * 0.12)
    support_labels = scene.get("visual_items", [])[:4]
    while len(support_labels) < 4:
        support_labels.append(scene.get("highlight_terms", ["idea"])[0])
    cards = []
    positions = [LEFT * 3.65 + UP * 1.15, LEFT * 3.65 + DOWN * 0.25, LEFT * 3.65 + DOWN * 1.65]
    for index, label in enumerate(support_labels[:3]):
        card = panel(2.15, 0.92, colors)
        text = paragraph_block(label, width=1.75, font_size=18, color=colors["ink"], weight=MEDIUM, line_width=14, max_height=0.5)
        chip = Dot(radius=0.08, color=[colors["accent"], colors["accent_2"], colors["accent_3"]][index % 3]).move_to(card.get_left() + RIGHT * 0.22)
        cards.append(VGroup(card, text, chip).move_to(positions[index]))
    support = VGroup(*cards)
    footer = paragraph_block(scene.get("takeaway", ""), width=10.0, font_size=22, color=colors["muted"], line_width=36, max_height=0.9).to_edge(DOWN, buff=0.24)
    return {"title": title, "hook": hook, "visual": visual, "support": support, "footer": footer}


def stage_composition(scene, colors):
    title = title_block(scene["headline"], colors, width=7.5).to_edge(UP, buff=0.42)
    hook = paragraph_block(scene.get("hook", ""), width=5.5, font_size=22, color=colors["accent"], weight=SEMIBOLD, line_width=20, max_height=1.0).next_to(title, DOWN, buff=0.16)
    visual = raw_visual(scene, colors).move_to(LEFT * 1.1 + DOWN * 0.25)
    side_panel = panel(2.45, 4.0, colors, fill_opacity=0.82).to_edge(RIGHT, buff=0.5).shift(DOWN * 0.05)
    side_text = bullet_group(scene.get("key_points", []), colors, width=1.95, font_size=17).move_to(side_panel.get_center())
    support = VGroup(side_panel, side_text)
    footer = paragraph_block(scene.get("takeaway", ""), width=10.5, font_size=22, color=colors["muted"], line_width=38, max_height=0.9).to_edge(DOWN, buff=0.24)
    return {"title": title, "hook": hook, "visual": visual, "support": support, "footer": footer}


def orbit_scene_composition(scene, colors):
    title = title_block(scene["headline"], colors, width=8.5).to_edge(UP, buff=0.42)
    hook = paragraph_block(scene.get("hook", ""), width=6.4, font_size=23, color=colors["accent"], weight=SEMIBOLD, line_width=20, max_height=1.0).next_to(title, DOWN, buff=0.16)
    visual = orbit_visual(scene, colors).move_to(DOWN * 0.1)
    support = chip_row(scene.get("highlight_terms", []), colors, width=6.8).to_edge(LEFT, buff=0.6).shift(DOWN * 2.35)
    footer = paragraph_block(scene.get("takeaway", ""), width=10.5, font_size=22, color=colors["muted"], line_width=38, max_height=0.9).to_edge(DOWN, buff=0.24)
    return {"title": title, "hook": hook, "visual": visual, "support": support, "footer": footer}


def magazine_composition(scene, colors):
    title = title_block(scene["headline"], colors, width=4.7).to_corner(UL, buff=0.46)
    hook = paragraph_block(scene.get("hook", ""), width=3.8, font_size=21, color=colors["accent"], weight=SEMIBOLD, line_width=15, max_height=1.2).next_to(title, DOWN, buff=0.16, aligned_edge=LEFT)
    visual = flow_visual(scene, colors).to_edge(RIGHT, buff=0.4).shift(UP * 0.22)
    quote_panel = panel(4.25, 1.5, colors).to_edge(DOWN, buff=0.55).shift(LEFT * 1.0)
    takeaway = paragraph_block(scene.get("takeaway", ""), width=3.65, font_size=21, color=colors["ink"], weight=MEDIUM, line_width=24, max_height=0.95).move_to(quote_panel.get_center())
    support = VGroup(quote_panel, takeaway)
    footer = chip_row(scene.get("highlight_terms", []), colors, width=4.4).next_to(title, DOWN, buff=2.7, aligned_edge=LEFT)
    return {"title": title, "hook": hook, "visual": visual, "support": VGroup(support, footer), "footer": VGroup()}


def composition(scene, colors):
    variant = scene.get("scene_variant", "split")
    if variant == "hero":
        return hero_composition(scene, colors)
    if variant == "spotlight":
        return spotlight_composition(scene, colors)
    if variant == "compare":
        return compare_composition(scene, colors)
    if variant == "grid":
        return grid_composition(scene, colors)
    if variant == "stage":
        return stage_composition(scene, colors)
    if variant == "orbit":
        return orbit_scene_composition(scene, colors)
    if variant == "magazine":
        return magazine_composition(scene, colors)
    return split_composition(scene, colors)


def animate_visual(scene_obj, visual, direction=DOWN):
    items = list(visual) if isinstance(visual, VGroup) else [visual]
    scene_obj.play(LaggedStart(*[FadeIn(item, shift=0.14 * direction) for item in items], lag_ratio=0.05), run_time=0.8)


def render_scene_page(scene_obj, scene_data):
    colors = palette()
    scene_obj.camera.background_color = colors["background"]
    background = ambient_background(colors)
    scene_obj.add(background)

    total = max(8.0, float(scene_data.get("target_duration_seconds", 12.0)))
    layout = composition(scene_data, colors)
    title = layout["title"]
    hook = layout["hook"]
    visual = layout["visual"]
    support = layout["support"]
    footer = layout["footer"]

    support_items = list(support) if isinstance(support, VGroup) else ([support] if support else [])
    footer_items = list(footer) if isinstance(footer, VGroup) else ([footer] if footer else [])

    beat_units = 5 + len(support_items) + len(footer_items)
    beat_wait = max((total - 3.6) / max(beat_units, 1), 0.25)

    scene_obj.play(FadeIn(title, shift=UP * 0.16), run_time=0.42)
    scene_obj.play(FadeIn(hook, shift=RIGHT * 0.12), run_time=0.3)
    scene_obj.wait(beat_wait)

    animate_visual(scene_obj, visual, direction=DOWN)
    scene_obj.wait(beat_wait)

    for item in support_items:
        scene_obj.play(FadeIn(item, shift=UP * 0.1), run_time=0.24)
        scene_obj.wait(beat_wait)

    for item in footer_items:
        scene_obj.play(FadeIn(item, shift=UP * 0.08), run_time=0.28)
    scene_obj.wait(max(0.3, beat_wait))


__SCENE_CLASSES__
'''


def _scene_class_block(class_name: str, index: int) -> str:
    return f'''
class {class_name}(Scene):
    def construct(self):
        render_scene_page(self, SCENES[{index}])
'''


def build_manim_module(*, storyboard: dict, output_path: Path) -> Path:
    scenes = storyboard["scenes"]
    scene_classes = "\n".join(_scene_class_block(scene["class_name"], index) for index, scene in enumerate(scenes))
    module = (
        MODULE_TEMPLATE.replace("__STORY_JSON__", json.dumps(storyboard, indent=2))
        .replace("__SCENE_CLASS_NAMES__", json.dumps([scene["class_name"] for scene in scenes]))
        .replace("__SCENE_CLASSES__", scene_classes)
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(module, encoding="utf-8")
    return output_path
