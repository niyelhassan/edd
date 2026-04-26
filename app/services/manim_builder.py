from __future__ import annotations

import json
from pathlib import Path


MODULE_TEMPLATE = r'''from manim import *
import numpy as np
import math
import re

STORY = __STORY_JSON__
SCENES = STORY["scenes"]

FONT_SANS = "Helvetica Neue"
FONT_SANS_FALLBACK = "Helvetica"
FONT_MONO = "Menlo"

THEMES = {
    "light": {
        "background": "#FFFFFF",
        "surface": "#F5F5F5",
        "ink": "#171717",
        "muted": "#737373",
        "subtle": "#A3A3A3",
        "border": "#E5E5E5",
        "accent": "#1D4ED8",
        "accent_soft": "#DBEAFE",
        "warm": "#EA580C",
        "good": "#047857",
    },
    "dark": {
        "background": "#0A0A0A",
        "surface": "#171717",
        "ink": "#FAFAFA",
        "muted": "#A3A3A3",
        "subtle": "#525252",
        "border": "#262626",
        "accent": "#60A5FA",
        "accent_soft": "#1E3A8A",
        "warm": "#FB923C",
        "good": "#34D399",
    },
    "paper": {
        "background": "#FAF7F0",
        "surface": "#F0E9D6",
        "ink": "#1C1917",
        "muted": "#78716C",
        "subtle": "#A8A29E",
        "border": "#D6D3D1",
        "accent": "#1D4ED8",
        "accent_soft": "#FEF3C7",
        "warm": "#9A3412",
        "good": "#15803D",
    },
}


def palette():
    return THEMES.get(STORY.get("visual_theme", "light"), THEMES["light"])


# === Text utilities =========================================================

def text_obj(text, *, size=28, color=None, weight=NORMAL):
    p = palette()
    return Text(
        str(text or ""),
        font_size=size,
        color=color if color is not None else p["ink"],
        font=FONT_SANS,
        weight=weight,
    )


def wrap_text(text, *, size=26, color=None, weight=NORMAL, max_width=10.5, line_buff=0.18):
    """Word-wrap a string into stacked Text() lines that fit within max_width."""
    raw = (str(text or "")).strip()
    if not raw:
        return VGroup()
    p = palette()
    use_color = color if color is not None else p["ink"]

    words = re.split(r"\s+", raw)
    lines = []
    current = []
    for word in words:
        trial_words = current + [word]
        probe = Text(
            " ".join(trial_words),
            font_size=size,
            color=use_color,
            font=FONT_SANS,
            weight=weight,
        )
        if probe.width <= max_width or not current:
            current = trial_words
        else:
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))

    line_objs = []
    for line in lines:
        obj = Text(line, font_size=size, color=use_color, font=FONT_SANS, weight=weight)
        if obj.width > max_width:
            obj.scale_to_fit_width(max_width)
        line_objs.append(obj)
    group = VGroup(*line_objs).arrange(DOWN, aligned_edge=LEFT, buff=line_buff)
    return group


def smart_headline(text):
    """Normalize a headline: strip trailing punctuation, collapse whitespace."""
    raw = (str(text or "")).strip()
    raw = re.sub(r"\s+", " ", raw)
    raw = raw.rstrip(".!?,;:")
    if not raw:
        return ""
    return raw[0].upper() + raw[1:]


def sentence_case(text):
    raw = (str(text or "")).strip()
    raw = re.sub(r"\s+", " ", raw)
    if not raw:
        return ""
    if not raw.endswith((".", "!", "?")):
        raw = raw
    return raw[0].upper() + raw[1:]


def safe_math(expr, *, color=None, size=64, max_width=10.0):
    if not expr:
        return None
    p = palette()
    use_color = color if color is not None else p["ink"]
    expr_str = str(expr)
    try:
        obj = MathTex(expr_str, color=use_color, font_size=size)
    except Exception:
        obj = text_obj(expr_str, size=int(size * 0.55), color=use_color, weight=BOLD)
    if obj.width > max_width:
        obj.scale_to_fit_width(max_width)
    return obj


def fit_within(mob, *, width=None, height=None):
    if width is not None and mob.width > width:
        mob.scale_to_fit_width(width)
    if height is not None and mob.height > height:
        mob.scale_to_fit_height(height)
    return mob


# === Chrome / branding ======================================================

def chrome(scene_data):
    p = palette()
    parts = []

    wordmark = Text("lern", font_size=22, color=p["ink"], font=FONT_SANS, weight=BOLD)
    wordmark.to_corner(UL, buff=0.42)
    accent_dot = Dot(radius=0.07, color=p["accent"]).next_to(wordmark, RIGHT, buff=0.16)
    parts.extend([wordmark, accent_dot])

    scene_no = scene_data.get("scene_number", 1)
    total = len(SCENES)
    label = f"{scene_no:02d} / {total:02d}"
    counter = Text(label, font_size=16, color=p["muted"], font=FONT_SANS, weight=BOLD).to_corner(UR, buff=0.5)
    parts.append(counter)

    title_clean = smart_headline(STORY.get("title", ""))
    if title_clean:
        sub = Text(title_clean.upper(), font_size=12, color=p["subtle"], font=FONT_SANS, weight=BOLD)
        sub.next_to(wordmark, DOWN, buff=0.05, aligned_edge=LEFT)
        parts.append(sub)

    bottom_line = Line(
        np.array([-7.0, -3.85, 0]),
        np.array([7.0, -3.85, 0]),
        color=p["border"],
        stroke_width=1.2,
    )
    progress_width = 14.0 * (scene_no / max(1, total))
    progress = Line(
        np.array([-7.0, -3.85, 0]),
        np.array([-7.0 + progress_width, -3.85, 0]),
        color=p["accent"],
        stroke_width=2.6,
    )
    parts.extend([bottom_line, progress])

    return VGroup(*parts)


# === Layout helpers =========================================================

CONTENT_TOP_Y = 2.7
CONTENT_BOTTOM_Y = -3.2
CONTENT_LEFT_X = -6.6
CONTENT_RIGHT_X = 6.6
CONTENT_WIDTH = CONTENT_RIGHT_X - CONTENT_LEFT_X


def header_block(scene_data, *, max_width=12.4, title_size=46, hook_size=22):
    p = palette()
    headline = smart_headline(scene_data.get("headline") or "")
    hook = sentence_case(scene_data.get("hook") or "")

    if headline.lower() == hook.lower():
        hook = ""

    title = wrap_text(headline, size=title_size, color=p["ink"], weight=BOLD, max_width=max_width, line_buff=0.12)
    title.move_to(np.array([0, CONTENT_TOP_Y - title.height / 2, 0]))

    parts = [title]
    if hook:
        sub = wrap_text(hook, size=hook_size, color=p["accent"], weight=NORMAL, max_width=max_width - 1.0, line_buff=0.12)
        sub.next_to(title, DOWN, buff=0.28)
        parts.append(sub)
    return VGroup(*parts)


def caption_block(scene_data, *, max_width=12.4):
    p = palette()
    takeaway = sentence_case(scene_data.get("takeaway") or "")
    if not takeaway:
        return VGroup()
    cap = wrap_text(takeaway, size=20, color=p["muted"], weight=NORMAL, max_width=max_width, line_buff=0.12)
    cap.move_to(np.array([0, CONTENT_BOTTOM_Y + cap.height / 2 + 0.05, 0]))
    return cap


# === Templates ==============================================================

def _bullet_lines(scene_data, limit=3):
    out = []
    for source in ("key_points", "visual_items", "highlight_terms"):
        for item in scene_data.get(source) or []:
            text = str(item or "").strip()
            if text and text.lower() not in {x.lower() for x in out}:
                out.append(text)
            if len(out) >= limit:
                return out
    return out


def template_title_card(scene_obj, scene_data, total):
    p = palette()
    headline = smart_headline(scene_data.get("headline") or "")
    hook = sentence_case(scene_data.get("hook") or "")
    if hook.lower() == headline.lower():
        hook = sentence_case(scene_data.get("takeaway") or "")

    eyebrow_raw = (STORY.get("title") or "").strip()
    eyebrow = Text(eyebrow_raw.upper(), font_size=14, color=p["accent"], font=FONT_SANS, weight=BOLD)

    title = wrap_text(headline, size=68, color=p["ink"], weight=BOLD, max_width=11.5, line_buff=0.16)
    underline = Rectangle(width=0.9, height=0.10, stroke_width=0, fill_color=p["accent"], fill_opacity=1)

    sub = wrap_text(hook, size=26, color=p["muted"], weight=NORMAL, max_width=10.5, line_buff=0.18) if hook else VGroup()

    block = VGroup(eyebrow, title, underline, sub).arrange(DOWN, buff=0.32, aligned_edge=LEFT)
    block.move_to(ORIGIN).shift(LEFT * 0.0)

    scene_obj.play(FadeIn(eyebrow, shift=UP * 0.2), run_time=0.45)
    scene_obj.play(Write(title), run_time=min(1.6, max(0.9, len(headline) * 0.04)))
    scene_obj.play(GrowFromEdge(underline, LEFT), run_time=0.4)
    if len(sub):
        scene_obj.play(FadeIn(sub, shift=UP * 0.15), run_time=0.55)

    scene_obj.wait(max(0.4, total - 3.4))


def template_bullets(scene_obj, scene_data, total):
    p = palette()
    header = header_block(scene_data, max_width=12.0, title_size=46)
    scene_obj.play(FadeIn(header, shift=UP * 0.15), run_time=0.55)

    bullets = _bullet_lines(scene_data, limit=3)
    if not bullets:
        bullets = [smart_headline(scene_data.get("takeaway") or scene_data.get("hook") or scene_data.get("headline") or "")]

    rows = []
    for index, line in enumerate(bullets, start=1):
        num_bg = Circle(radius=0.32, color=p["accent"], stroke_width=0).set_fill(p["accent"], opacity=1)
        num_label = Text(str(index), font_size=22, color="#FFFFFF", font=FONT_SANS, weight=BOLD).move_to(num_bg)
        badge = VGroup(num_bg, num_label)

        body = wrap_text(sentence_case(line), size=26, color=p["ink"], weight=NORMAL, max_width=9.5, line_buff=0.14)
        row = VGroup(badge, body).arrange(RIGHT, buff=0.35, aligned_edge=UP)
        rows.append(row)

    bullet_group = VGroup(*rows).arrange(DOWN, buff=0.45, aligned_edge=LEFT)
    fit_within(bullet_group, width=11.5, height=4.2)
    bullet_group.next_to(header, DOWN, buff=0.7).align_to(header, LEFT) if header.width < 8 else bullet_group.next_to(header, DOWN, buff=0.7)
    bullet_group.move_to(np.array([0, -0.5, 0]))

    for row in rows:
        scene_obj.play(FadeIn(row[0], scale=0.6), FadeIn(row[1], shift=RIGHT * 0.15), run_time=0.45)
        scene_obj.wait(0.05)

    cap = caption_block(scene_data)
    if len(cap):
        scene_obj.play(FadeIn(cap, shift=UP * 0.1), run_time=0.4)

    scene_obj.wait(max(0.4, total - (1.0 + 0.5 * len(rows) + 0.6)))


def template_equation(scene_obj, scene_data, total):
    p = palette()
    header = header_block(scene_data, max_width=12.0, title_size=42)
    scene_obj.play(FadeIn(header, shift=UP * 0.15), run_time=0.5)

    equations = scene_data.get("equations") or []
    primary = equations[0] if equations else None
    secondary = equations[1] if len(equations) > 1 else None

    eq_card = RoundedRectangle(corner_radius=0.25, width=11.0, height=2.6, stroke_color=p["border"], stroke_width=2, fill_color=p["surface"], fill_opacity=1.0)
    eq_card.move_to(np.array([0, 0.2, 0]))

    eq_obj = safe_math(primary, color=p["ink"], size=72, max_width=9.5) if primary else text_obj(scene_data.get("hook") or "", size=44, color=p["ink"], weight=BOLD)
    eq_obj.move_to(eq_card.get_center())

    scene_obj.play(FadeIn(eq_card, scale=0.97), run_time=0.45)
    scene_obj.play(Write(eq_obj), run_time=min(1.6, max(0.9, len(str(primary or "")) * 0.08)))

    annotation_terms = (scene_data.get("highlight_terms") or [])[:3]
    annotations = VGroup()
    for index, term in enumerate(annotation_terms):
        chip_text = text_obj(term, size=18, color=p["accent"], weight=BOLD)
        chip_bg = RoundedRectangle(
            corner_radius=0.12,
            width=chip_text.width + 0.5,
            height=chip_text.height + 0.3,
            stroke_color=p["accent"],
            stroke_width=1.4,
            fill_color=p["accent_soft"],
            fill_opacity=0.7,
        )
        chip = VGroup(chip_bg, chip_text)
        annotations.add(chip)
    if len(annotations):
        annotations.arrange(RIGHT, buff=0.35).next_to(eq_card, DOWN, buff=0.45)
        fit_within(annotations, width=11.5)
        for chip in annotations:
            scene_obj.play(FadeIn(chip, shift=UP * 0.1), run_time=0.3)

    if secondary:
        eq2 = safe_math(secondary, color=p["muted"], size=40, max_width=8.5)
        if eq2:
            eq2.next_to(annotations if len(annotations) else eq_card, DOWN, buff=0.35)
            scene_obj.play(FadeIn(eq2, shift=UP * 0.1), run_time=0.5)
    else:
        cap = caption_block(scene_data)
        if len(cap):
            scene_obj.play(FadeIn(cap, shift=UP * 0.1), run_time=0.4)

    scene_obj.wait(max(0.4, total - 3.5))


def template_distribution(scene_obj, scene_data, total):
    p = palette()
    header = header_block(scene_data, title_size=40)
    scene_obj.play(FadeIn(header, shift=UP * 0.15), run_time=0.5)

    axes = Axes(
        x_range=[-4, 4, 1],
        y_range=[0, 0.5, 0.1],
        x_length=10.5,
        y_length=3.8,
        axis_config={"color": p["muted"], "stroke_width": 2, "include_ticks": True, "tick_size": 0.05},
        tips=False,
    ).move_to(np.array([0, -0.6, 0]))

    def gauss(x):
        return (1.0 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * x * x)

    curve = axes.plot(lambda x: gauss(x), x_range=[-3.8, 3.8], color=p["accent"], stroke_width=4)

    threshold_x = 1.6
    shaded = axes.get_area(curve, x_range=[threshold_x, 3.8], color=p["warm"], opacity=0.55)
    shaded_left = axes.get_area(curve, x_range=[-3.8, -threshold_x], color=p["warm"], opacity=0.55)

    threshold_line = DashedLine(
        axes.c2p(threshold_x, 0),
        axes.c2p(threshold_x, gauss(threshold_x)),
        color=p["ink"],
        stroke_width=2,
        dash_length=0.08,
    )

    label_x = text_obj(((scene_data.get("highlight_terms") or ["x"])[0]), size=18, color=p["muted"]).next_to(axes.x_axis, RIGHT, buff=0.15)
    label_y = text_obj("p(x)", size=18, color=p["muted"]).next_to(axes.y_axis, UP, buff=0.15)

    tail_label_text = "tail"
    if scene_data.get("highlight_terms") and len(scene_data["highlight_terms"]) > 1:
        tail_label_text = scene_data["highlight_terms"][1]
    tail_label = text_obj(tail_label_text, size=18, color=p["warm"], weight=BOLD)
    tail_label.next_to(axes.c2p(2.4, gauss(2.4)), UR, buff=0.15)

    scene_obj.play(Create(axes), FadeIn(label_x), FadeIn(label_y), run_time=0.7)
    scene_obj.play(Create(curve), run_time=1.4)
    scene_obj.play(Create(threshold_line), run_time=0.4)
    scene_obj.play(FadeIn(shaded), FadeIn(shaded_left), FadeIn(tail_label), run_time=0.7)

    cap = caption_block(scene_data)
    if len(cap):
        scene_obj.play(FadeIn(cap, shift=UP * 0.1), run_time=0.4)

    scene_obj.wait(max(0.4, total - 4.0))


def template_axes(scene_obj, scene_data, total):
    p = palette()
    header = header_block(scene_data, title_size=40)
    scene_obj.play(FadeIn(header, shift=UP * 0.15), run_time=0.5)

    x_label_txt = (scene_data.get("highlight_terms") or ["x"])[0]
    y_label_txt = (scene_data.get("highlight_terms") or ["", "y"])[1] if len(scene_data.get("highlight_terms") or []) > 1 else "y"

    axes = Axes(
        x_range=[-4, 4, 1],
        y_range=[-2, 4, 1],
        x_length=10.0,
        y_length=4.0,
        axis_config={"color": p["muted"], "stroke_width": 2, "include_ticks": True, "tick_size": 0.06},
        tips=False,
    ).move_to(np.array([0, -0.6, 0]))

    label_x = text_obj(x_label_txt, size=18, color=p["muted"]).next_to(axes.x_axis, RIGHT, buff=0.15)
    label_y = text_obj(y_label_txt, size=18, color=p["muted"]).next_to(axes.y_axis, UP, buff=0.15)

    curve = axes.plot(lambda x: 0.4 * (x ** 2) - 1, x_range=[-3.2, 3.2], color=p["accent"], stroke_width=4)
    moving_dot = Dot(color=p["warm"], radius=0.10).move_to(axes.c2p(-3.2, 0.4 * 3.2 ** 2 - 1))

    points = (scene_data.get("visual_items") or [])[:3]
    callouts = []
    coords = [(-2.0, 0.6), (0.8, -0.74), (2.4, 1.3)]
    for index, item in enumerate(points):
        cx, cy = coords[index]
        dot = Dot(axes.c2p(cx, cy), radius=0.08, color=p["good"] if index % 2 == 0 else p["accent"])
        label = text_obj(item, size=16, color=p["ink"], weight=BOLD)
        label.next_to(dot, UR if cy >= 0 else DR, buff=0.12)
        callouts.append(VGroup(dot, label))

    scene_obj.play(Create(axes), FadeIn(label_x), FadeIn(label_y), run_time=0.7)
    scene_obj.play(Create(curve), run_time=1.6)
    scene_obj.play(GrowFromCenter(moving_dot), run_time=0.4)
    if callouts:
        scene_obj.play(LaggedStart(*[FadeIn(c, shift=UP * 0.1) for c in callouts], lag_ratio=0.25), run_time=0.9)

    cap = caption_block(scene_data)
    if len(cap):
        scene_obj.play(FadeIn(cap, shift=UP * 0.1), run_time=0.4)

    scene_obj.wait(max(0.4, total - 4.0))


def template_comparison(scene_obj, scene_data, total):
    p = palette()
    header = header_block(scene_data, title_size=40)
    scene_obj.play(FadeIn(header, shift=UP * 0.15), run_time=0.5)

    items = (scene_data.get("visual_items") or [])[:2]
    if len(items) < 2:
        items = items + ["Option A", "Option B"][len(items):2]
    terms = (scene_data.get("highlight_terms") or [])
    sub_a = terms[0] if len(terms) > 0 else ""
    sub_b = terms[1] if len(terms) > 1 else ""

    def make_card(title_text, sub_text, fill, ink, accent):
        card = RoundedRectangle(corner_radius=0.25, width=5.0, height=4.0, stroke_color=accent, stroke_width=2.5, fill_color=fill, fill_opacity=1.0)
        title = wrap_text(sentence_case(title_text), size=30, color=ink, weight=BOLD, max_width=4.4, line_buff=0.12)
        title.move_to(card.get_center() + UP * 0.6)
        if sub_text:
            sub = wrap_text(sentence_case(sub_text), size=18, color=p["muted"], weight=NORMAL, max_width=4.4, line_buff=0.1)
            sub.move_to(card.get_center() + DOWN * 0.6)
        else:
            sub = VGroup()
        return VGroup(card, title, sub)

    left = make_card(items[0], sub_a, p["surface"], p["ink"], p["accent"])
    right = make_card(items[1], sub_b, p["surface"], p["ink"], p["warm"])

    pair = VGroup(left, right).arrange(RIGHT, buff=0.7).move_to(np.array([0, -0.5, 0]))

    vs = text_obj("vs", size=22, color=p["muted"], weight=BOLD).move_to(pair.get_center())
    vs_circle = Circle(radius=0.42, color=p["border"], stroke_width=2).set_fill(p["background"], opacity=1).move_to(vs)
    vs_group = VGroup(vs_circle, vs)

    scene_obj.play(FadeIn(left, shift=RIGHT * 0.2), run_time=0.5)
    scene_obj.play(FadeIn(right, shift=LEFT * 0.2), run_time=0.5)
    scene_obj.play(GrowFromCenter(vs_group), run_time=0.4)

    cap = caption_block(scene_data)
    if len(cap):
        scene_obj.play(FadeIn(cap, shift=UP * 0.1), run_time=0.4)

    scene_obj.wait(max(0.4, total - 2.5))


def template_flow(scene_obj, scene_data, total):
    p = palette()
    header = header_block(scene_data, title_size=40)
    scene_obj.play(FadeIn(header, shift=UP * 0.15), run_time=0.5)

    items = (scene_data.get("visual_items") or [])[:4] or _bullet_lines(scene_data, limit=4)
    if not items:
        items = ["Step 1", "Step 2", "Step 3"]

    nodes = []
    arrows = []
    n = len(items)
    node_w = 2.0
    gap = 0.95
    spacing = node_w + gap
    total_width = spacing * n - gap
    start_x = -total_width / 2 + node_w / 2

    for index, label_text in enumerate(items):
        cx = start_x + index * spacing
        node = RoundedRectangle(corner_radius=0.18, width=node_w, height=1.25, stroke_color=p["accent"], stroke_width=2, fill_color=p["accent_soft"] if index % 2 == 0 else p["surface"], fill_opacity=1.0)
        label = wrap_text(sentence_case(label_text), size=17, color=p["ink"], weight=BOLD, max_width=node_w - 0.3, line_buff=0.08)
        fit_within(label, width=node_w - 0.3, height=0.95)
        label.move_to(node.get_center())
        node_group = VGroup(node, label).move_to(np.array([cx, -0.5, 0]))
        nodes.append(node_group)
        if index > 0:
            arrow = Arrow(
                nodes[index - 1].get_right(),
                node_group.get_left(),
                color=p["ink"],
                stroke_width=4,
                buff=0.12,
                max_tip_length_to_length_ratio=0.35,
                tip_length=0.22,
            )
            arrows.append(arrow)

    for index, node_group in enumerate(nodes):
        scene_obj.play(FadeIn(node_group, shift=UP * 0.15), run_time=0.4)
        if index < len(arrows):
            scene_obj.play(GrowArrow(arrows[index]), run_time=0.25)

    cap = caption_block(scene_data)
    if len(cap):
        scene_obj.play(FadeIn(cap, shift=UP * 0.1), run_time=0.4)

    scene_obj.wait(max(0.4, total - (0.7 * len(nodes) + 1.0)))


def template_concept_map(scene_obj, scene_data, total):
    p = palette()
    header = header_block(scene_data, title_size=40)
    scene_obj.play(FadeIn(header, shift=UP * 0.15), run_time=0.5)

    center_text = (scene_data.get("highlight_terms") or [smart_headline(scene_data.get("headline") or "")])[0]
    center_circle = Circle(radius=0.95, color=p["accent"], stroke_width=3).set_fill(p["accent_soft"], opacity=1.0)
    center_label = wrap_text(sentence_case(center_text), size=20, color=p["ink"], weight=BOLD, max_width=1.6, line_buff=0.08)
    fit_within(center_label, width=1.6, height=1.1)
    center_label.move_to(center_circle.get_center())
    center = VGroup(center_circle, center_label).move_to(np.array([0, -0.7, 0]))

    items = (scene_data.get("visual_items") or [])[:4] or _bullet_lines(scene_data, limit=4)
    if not items:
        items = ["Concept A", "Concept B", "Concept C"]

    n = len(items)
    angles = [math.pi / 2 + i * (2 * math.pi / n) for i in range(n)]
    radius_x = 3.3
    radius_y = 1.85

    satellites = []
    lines = []
    for index, label_text in enumerate(items):
        angle = angles[index]
        sx = math.cos(angle) * radius_x
        sy = math.sin(angle) * radius_y
        satellite_box = RoundedRectangle(corner_radius=0.15, width=2.4, height=0.85, stroke_color=p["border"], stroke_width=1.5, fill_color=p["surface"], fill_opacity=1.0)
        sat_label = wrap_text(sentence_case(label_text), size=17, color=p["ink"], weight=NORMAL, max_width=2.1, line_buff=0.08)
        fit_within(sat_label, width=2.1, height=0.6)
        sat_label.move_to(satellite_box.get_center())
        satellite = VGroup(satellite_box, sat_label).move_to(center.get_center() + np.array([sx, sy, 0]))
        direction = satellite.get_center() - center.get_center()
        norm = np.linalg.norm(direction)
        unit = direction / norm if norm > 1e-6 else np.array([1.0, 0.0, 0.0])
        line_start = center.get_center() + unit * 0.95
        line_end = satellite.get_center() - unit * 1.0
        line = Line(line_start, line_end, color=p["border"], stroke_width=2)
        satellites.append(satellite)
        lines.append(line)

    scene_obj.play(GrowFromCenter(center), run_time=0.5)
    for sat, line in zip(satellites, lines):
        scene_obj.play(Create(line), FadeIn(sat, scale=0.85), run_time=0.35)

    scene_obj.wait(max(0.4, total - (0.5 + 0.4 * n)))


def template_timeline(scene_obj, scene_data, total):
    p = palette()
    header = header_block(scene_data, title_size=40)
    scene_obj.play(FadeIn(header, shift=UP * 0.15), run_time=0.5)

    items = (scene_data.get("visual_items") or [])[:4] or _bullet_lines(scene_data, limit=4)
    if not items:
        items = ["Start", "Middle", "End"]
    n = len(items)

    base = Line(np.array([-5.5, -0.6, 0]), np.array([5.5, -0.6, 0]), color=p["border"], stroke_width=3)
    progress_to_x = lambda i: -5.5 + (11.0 / max(1, n - 1)) * i if n > 1 else 0
    progress = Line(np.array([-5.5, -0.6, 0]), np.array([progress_to_x(n - 1), -0.6, 0]), color=p["accent"], stroke_width=4)

    nodes = []
    for index in range(n):
        x = progress_to_x(index) if n > 1 else 0
        dot_outer = Circle(radius=0.22, color=p["accent"], stroke_width=2).set_fill(p["background"], opacity=1).move_to(np.array([x, -0.6, 0]))
        dot_inner = Dot(radius=0.10, color=p["accent"]).move_to(dot_outer)
        node_label = wrap_text(sentence_case(items[index]), size=17, color=p["ink"], weight=BOLD, max_width=2.6, line_buff=0.08)
        fit_within(node_label, width=2.6, height=0.8)
        node_label.next_to(dot_outer, UP if index % 2 == 0 else DOWN, buff=0.35)
        nodes.append(VGroup(dot_outer, dot_inner, node_label))

    scene_obj.play(Create(base), run_time=0.5)
    scene_obj.play(Create(progress), run_time=0.7)
    for node in nodes:
        scene_obj.play(GrowFromCenter(node[0]), GrowFromCenter(node[1]), FadeIn(node[2], shift=UP * 0.1 if node[2].get_center()[1] > -0.6 else DOWN * 0.1), run_time=0.35)

    cap = caption_block(scene_data)
    if len(cap):
        scene_obj.play(FadeIn(cap, shift=UP * 0.1), run_time=0.4)

    scene_obj.wait(max(0.4, total - (1.5 + 0.4 * n)))


def template_bar_chart(scene_obj, scene_data, total):
    p = palette()
    header = header_block(scene_data, title_size=40)
    scene_obj.play(FadeIn(header, shift=UP * 0.15), run_time=0.5)

    labels = (scene_data.get("visual_items") or [])[:5] or _bullet_lines(scene_data, limit=5)
    if not labels:
        labels = ["A", "B", "C"]

    n = len(labels)
    rng = np.random.default_rng(seed=sum(ord(c) for c in str(scene_data.get("headline", "x"))))
    raw = rng.uniform(0.35, 1.0, size=n)
    raw[rng.integers(0, n)] = 1.0
    heights = (raw * 3.0).tolist()

    chart_left = -5.5
    chart_right = 5.5
    bar_area = chart_right - chart_left
    bar_width = min(1.1, bar_area / (n * 1.5))
    spacing = bar_area / n
    base_y = -2.05

    bars = []
    value_labels = []
    cat_labels = []
    for index in range(n):
        cx = chart_left + spacing / 2 + index * spacing
        h = heights[index]
        bar = Rectangle(width=bar_width, height=h, stroke_width=0, fill_color=p["accent"] if index == int(np.argmax(heights)) else p["accent_soft"], fill_opacity=1.0)
        bar.move_to(np.array([cx, base_y + h / 2, 0]))
        bars.append(bar)
        value = text_obj(f"{int(round(raw[index] * 100))}", size=16, color=p["ink"], weight=BOLD)
        value.next_to(bar, UP, buff=0.12)
        value_labels.append(value)
        cat = wrap_text(sentence_case(labels[index]), size=15, color=p["muted"], max_width=spacing * 0.9, line_buff=0.08)
        fit_within(cat, width=spacing * 0.9, height=0.7)
        cat.next_to(np.array([cx, base_y, 0]), DOWN, buff=0.18)
        cat_labels.append(cat)

    base_line = Line(np.array([chart_left, base_y, 0]), np.array([chart_right, base_y, 0]), color=p["border"], stroke_width=2)

    scene_obj.play(Create(base_line), run_time=0.4)
    grow_anims = []
    for bar in bars:
        bar_target = bar.copy()
        bar.stretch_to_fit_height(0.001).move_to(np.array([bar.get_center()[0], base_y, 0]))
        grow_anims.append(Transform(bar, bar_target))
    scene_obj.play(LaggedStart(*grow_anims, lag_ratio=0.15), run_time=1.6)
    scene_obj.play(LaggedStart(*[FadeIn(v) for v in value_labels], lag_ratio=0.1), run_time=0.6)
    scene_obj.play(LaggedStart(*[FadeIn(c) for c in cat_labels], lag_ratio=0.08), run_time=0.5)

    scene_obj.wait(max(0.4, total - 3.5))


def template_wave(scene_obj, scene_data, total):
    p = palette()
    header = header_block(scene_data, title_size=40)
    scene_obj.play(FadeIn(header, shift=UP * 0.15), run_time=0.5)

    axes = Axes(
        x_range=[0, 4 * math.pi, math.pi],
        y_range=[-1.5, 1.5, 0.5],
        x_length=11.0,
        y_length=3.6,
        axis_config={"color": p["muted"], "stroke_width": 2, "include_ticks": False},
        tips=False,
    ).move_to(np.array([0, -0.6, 0]))

    wave1 = axes.plot(lambda x: math.sin(x), color=p["accent"], stroke_width=4)
    wave2 = axes.plot(lambda x: math.sin(x + math.pi / 3) * 0.7, color=p["warm"], stroke_width=4)

    label1_text = (scene_data.get("highlight_terms") or ["wave"])[0]
    label2_text = (scene_data.get("highlight_terms") or ["", "phase"])[1] if len(scene_data.get("highlight_terms") or []) > 1 else "phase"

    chip_a = text_obj(sentence_case(label1_text), size=18, color=p["accent"], weight=BOLD).move_to(axes.c2p(math.pi * 0.5, 1.25))
    chip_b = text_obj(sentence_case(label2_text), size=18, color=p["warm"], weight=BOLD).move_to(axes.c2p(math.pi * 1.7, -1.1))

    scene_obj.play(Create(axes), run_time=0.6)
    scene_obj.play(Create(wave1), run_time=1.4)
    scene_obj.play(FadeIn(chip_a), run_time=0.3)
    scene_obj.play(Create(wave2), run_time=1.4)
    scene_obj.play(FadeIn(chip_b), run_time=0.3)

    cap = caption_block(scene_data)
    if len(cap):
        scene_obj.play(FadeIn(cap, shift=UP * 0.1), run_time=0.4)

    scene_obj.wait(max(0.4, total - 4.5))


def template_tree(scene_obj, scene_data, total):
    p = palette()
    header = header_block(scene_data, title_size=40)
    scene_obj.play(FadeIn(header, shift=UP * 0.15), run_time=0.5)

    items = (scene_data.get("visual_items") or [])[:4] or _bullet_lines(scene_data, limit=4)
    while len(items) < 3:
        items.append(f"Branch {len(items) + 1}")

    root_text = (scene_data.get("highlight_terms") or [smart_headline(scene_data.get("headline") or "Root")])[0]
    root_box = RoundedRectangle(corner_radius=0.18, width=3.4, height=0.95, stroke_color=p["accent"], stroke_width=2, fill_color=p["accent_soft"], fill_opacity=1.0)
    root_label = wrap_text(sentence_case(root_text), size=20, color=p["ink"], weight=BOLD, max_width=3.0, line_buff=0.08)
    fit_within(root_label, width=3.0, height=0.7)
    root_label.move_to(root_box.get_center())
    root = VGroup(root_box, root_label).move_to(np.array([0, 0.95, 0]))

    branch_count = min(3, len(items))
    branches = items[:branch_count]
    extra = items[branch_count : branch_count + branch_count]

    base_y = -1.2
    spread = 4.6
    children = []
    edges = []
    for index, label in enumerate(branches):
        cx = -spread / 2 + (spread / max(1, branch_count - 1)) * index if branch_count > 1 else 0
        box = RoundedRectangle(corner_radius=0.15, width=2.4, height=0.85, stroke_color=p["border"], stroke_width=1.5, fill_color=p["surface"], fill_opacity=1.0)
        lab = wrap_text(sentence_case(label), size=16, color=p["ink"], weight=BOLD, max_width=2.1, line_buff=0.08)
        fit_within(lab, width=2.1, height=0.6)
        lab.move_to(box.get_center())
        node = VGroup(box, lab).move_to(np.array([cx, base_y, 0]))
        edge = Line(root.get_bottom(), node.get_top(), color=p["muted"], stroke_width=2)
        children.append(node)
        edges.append(edge)

    scene_obj.play(GrowFromCenter(root), run_time=0.45)
    for edge, child in zip(edges, children):
        scene_obj.play(Create(edge), FadeIn(child, shift=DOWN * 0.1), run_time=0.35)

    scene_obj.wait(max(0.4, total - (0.45 + 0.35 * len(children) + 0.5)))


def template_scatter(scene_obj, scene_data, total):
    p = palette()
    header = header_block(scene_data, title_size=40)
    scene_obj.play(FadeIn(header, shift=UP * 0.15), run_time=0.5)

    axes = Axes(
        x_range=[0, 10, 1],
        y_range=[0, 6, 1],
        x_length=10.0,
        y_length=3.8,
        axis_config={"color": p["muted"], "stroke_width": 2, "include_ticks": True, "tick_size": 0.05},
        tips=False,
    ).move_to(np.array([0, -0.6, 0]))

    rng = np.random.default_rng(seed=sum(ord(c) for c in str(scene_data.get("headline", "scatter"))))
    n = 22
    xs = rng.uniform(0.5, 9.5, size=n)
    ys = 0.45 * xs + 0.6 + rng.normal(0, 0.55, size=n)
    ys = np.clip(ys, 0.1, 5.7)

    dots = VGroup(*[Dot(axes.c2p(x, y), radius=0.07, color=p["accent"]) for x, y in zip(xs, ys)])

    a = float(np.cov(xs, ys, bias=True)[0, 1] / np.var(xs))
    b = float(np.mean(ys) - a * np.mean(xs))
    fit = axes.plot(lambda x: a * x + b, x_range=[0.5, 9.5], color=p["warm"], stroke_width=3)

    x_label = text_obj((scene_data.get("highlight_terms") or ["x"])[0], size=18, color=p["muted"]).next_to(axes.x_axis, RIGHT, buff=0.15)
    y_label = text_obj((scene_data.get("highlight_terms") or ["", "y"])[1] if len(scene_data.get("highlight_terms") or []) > 1 else "y", size=18, color=p["muted"]).next_to(axes.y_axis, UP, buff=0.15)

    scene_obj.play(Create(axes), FadeIn(x_label), FadeIn(y_label), run_time=0.7)
    scene_obj.play(LaggedStart(*[GrowFromCenter(d) for d in dots], lag_ratio=0.05), run_time=1.4)
    scene_obj.play(Create(fit), run_time=1.0)

    cap = caption_block(scene_data)
    if len(cap):
        scene_obj.play(FadeIn(cap, shift=UP * 0.1), run_time=0.4)

    scene_obj.wait(max(0.4, total - 4.0))


def template_process(scene_obj, scene_data, total):
    p = palette()
    header = header_block(scene_data, title_size=40)
    scene_obj.play(FadeIn(header, shift=UP * 0.15), run_time=0.5)

    items = _bullet_lines(scene_data, limit=4)
    if not items:
        items = ["Setup", "Compute", "Interpret"]

    rows = []
    for index, line in enumerate(items, start=1):
        num = Text(str(index), font_size=44, color=p["accent_soft"], font=FONT_SANS, weight=BOLD)
        num_box = num
        title = text_obj(sentence_case(line.split(":")[0]) if ":" in line else sentence_case(line), size=24, color=p["ink"], weight=BOLD)
        body_text = sentence_case(line.split(":", 1)[1].strip()) if ":" in line else ""
        body = wrap_text(body_text, size=18, color=p["muted"], max_width=8.5, line_buff=0.08) if body_text else VGroup()
        text_col = VGroup(title, body).arrange(DOWN, aligned_edge=LEFT, buff=0.1) if len(body) else VGroup(title)
        row = VGroup(num_box, text_col).arrange(RIGHT, buff=0.4, aligned_edge=UP)
        rows.append(row)

    block = VGroup(*rows).arrange(DOWN, aligned_edge=LEFT, buff=0.45)
    fit_within(block, width=11.5, height=4.6)
    block.move_to(np.array([0, -0.5, 0]))

    for row in rows:
        scene_obj.play(FadeIn(row, shift=RIGHT * 0.15), run_time=0.45)

    cap = caption_block(scene_data)
    if len(cap):
        scene_obj.play(FadeIn(cap, shift=UP * 0.1), run_time=0.4)

    scene_obj.wait(max(0.4, total - (0.6 + 0.5 * len(rows) + 0.5)))


def template_summary(scene_obj, scene_data, total):
    p = palette()
    eyebrow = Text("KEY TAKEAWAY", font_size=14, color=p["accent"], font=FONT_SANS, weight=BOLD)
    headline_text = smart_headline(scene_data.get("takeaway") or scene_data.get("headline") or "")
    title = wrap_text(headline_text, size=46, color=p["ink"], weight=BOLD, max_width=11.5, line_buff=0.16)
    underline = Rectangle(width=1.5, height=0.08, stroke_width=0, fill_color=p["accent"], fill_opacity=1)

    bullets = _bullet_lines(scene_data, limit=3)
    bullet_rows = []
    for index, line in enumerate(bullets, start=1):
        marker = Dot(radius=0.10, color=p["accent"])
        body = wrap_text(sentence_case(line), size=22, color=p["ink"], weight=NORMAL, max_width=9.5, line_buff=0.12)
        bullet_rows.append(VGroup(marker, body).arrange(RIGHT, buff=0.3, aligned_edge=UP))

    bullet_group = VGroup(*bullet_rows).arrange(DOWN, aligned_edge=LEFT, buff=0.28) if bullet_rows else VGroup()

    block_parts = [eyebrow, title, underline]
    if len(bullet_group):
        block_parts.append(bullet_group)
    block = VGroup(*block_parts).arrange(DOWN, buff=0.3, aligned_edge=LEFT).move_to(ORIGIN)

    scene_obj.play(FadeIn(eyebrow, shift=UP * 0.1), run_time=0.4)
    scene_obj.play(Write(title), run_time=min(1.6, max(0.9, len(headline_text) * 0.04)))
    scene_obj.play(GrowFromEdge(underline, LEFT), run_time=0.4)
    if len(bullet_group):
        for row in bullet_group:
            scene_obj.play(FadeIn(row, shift=UP * 0.1), run_time=0.35)

    scene_obj.wait(max(0.4, total - 3.0))


# === Template selection =====================================================

TEMPLATES = {
    "title_card": template_title_card,
    "bullets": template_bullets,
    "equation": template_equation,
    "distribution": template_distribution,
    "axes": template_axes,
    "comparison": template_comparison,
    "flow": template_flow,
    "concept_map": template_concept_map,
    "timeline": template_timeline,
    "bar_chart": template_bar_chart,
    "wave": template_wave,
    "tree": template_tree,
    "scatter": template_scatter,
    "process": template_process,
    "summary": template_summary,
}


KEYWORD_HINTS = [
    ("distribution", ["distribution", "p-value", "p value", "sigma", "gaussian", "normal curve", "tail", "probability density", "bell curve", "z-score", "z score", "pdf"]),
    ("wave", ["wave", "oscillation", "frequency", "amplitude", "interference", "harmonic", "phase", "sinusoid"]),
    ("tree", ["bayes", "bayesian", "decision tree", "branch", "conditional probability", "posterior", "prior", "likelihood"]),
    ("scatter", ["regression", "correlation", "scatter", "fit line", "least squares", "linear fit", "data points"]),
    ("bar_chart", ["compare values", "ranking", "bar chart", "histogram", "frequency", "counts", "categories"]),
    ("timeline", ["timeline", "history", "sequence of events", "evolution", "stages over time", "milestone"]),
    ("flow", ["pipeline", "process", "workflow", "steps", "stages", "procedure", "algorithm"]),
    ("equation", ["equation", "formula", "derive", "derivation", "theorem", "law of"]),
    ("comparison", ["versus", " vs ", "contrast", "difference between", "compared to"]),
    ("concept_map", ["framework", "components of", "relate", "structure of", "map of"]),
]


def _pick_layout(scene_data):
    declared = (scene_data.get("layout") or "").strip()
    if declared and declared != "auto" and declared in TEMPLATES:
        return declared

    # Heuristic by keyword presence in narration / headline / hook
    haystack = " ".join([
        str(scene_data.get("headline") or ""),
        str(scene_data.get("hook") or ""),
        str(scene_data.get("narration") or ""),
        str(scene_data.get("visual_goal") or ""),
        str(scene_data.get("takeaway") or ""),
    ]).lower()

    for layout, hints in KEYWORD_HINTS:
        for hint in hints:
            if hint in haystack:
                return layout

    if scene_data.get("equations"):
        return "equation"

    bullets = _bullet_lines(scene_data, limit=3)
    if len(bullets) >= 2:
        return "bullets"

    scene_no = scene_data.get("scene_number", 1)
    if scene_no == 1:
        return "title_card"
    if scene_no >= len(SCENES):
        return "summary"

    return "concept_map"


def render_scene_page(scene_obj, scene_data):
    p = palette()
    scene_obj.camera.background_color = p["background"]

    chrome_group = chrome(scene_data)
    scene_obj.add(chrome_group)

    layout = _pick_layout(scene_data)
    builder = TEMPLATES.get(layout, template_concept_map)

    total = max(8.0, float(scene_data.get("target_duration_seconds", 12.0)))
    builder(scene_obj, scene_data, total)


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
    for index, scene in enumerate(scenes, start=1):
        scene["scene_number"] = index
    scene_classes = "\n".join(_scene_class_block(scene["class_name"], index) for index, scene in enumerate(scenes))
    module = (
        MODULE_TEMPLATE.replace("__STORY_JSON__", json.dumps(storyboard, indent=2))
        .replace("__SCENE_CLASSES__", scene_classes)
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(module, encoding="utf-8")
    return output_path
