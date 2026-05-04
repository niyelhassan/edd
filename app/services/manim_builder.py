from __future__ import annotations

import json
from pathlib import Path


MODULE_TEMPLATE = '''from manim import *
import math
import random
import textwrap

STORY = __STORY_JSON__
SCENES = STORY["scenes"]
TITLE = STORY.get("title", "")

# Slide-style theme inspired by the app's video template gallery.
THEME_ACCENTS = {
    "blue":   {"accent": "#38BDF8", "accent_2": "#0EA5E9", "accent_soft": "#E0F2FE", "accent_mid": "#BAE6FD"},
    "violet": {"accent": "#8B5CF6", "accent_2": "#7C3AED", "accent_soft": "#EDE9FE", "accent_mid": "#DDD6FE"},
    "green":  {"accent": "#10B981", "accent_2": "#059669", "accent_soft": "#D1FAE5", "accent_mid": "#A7F3D0"},
    "amber":  {"accent": "#F59E0B", "accent_2": "#D97706", "accent_soft": "#FEF3C7", "accent_mid": "#FDE68A"},
    "rose":   {"accent": "#F43F5E", "accent_2": "#E11D48", "accent_soft": "#FFE4E6", "accent_mid": "#FECDD3"},
    "slate":  {"accent": "#64748B", "accent_2": "#475569", "accent_soft": "#F1F5F9", "accent_mid": "#CBD5E1"},
}


def palette():
    theme = str(STORY.get("color_theme") or "blue").strip().lower()
    accents = THEME_ACCENTS.get(theme, THEME_ACCENTS["blue"])
    return {
        "background": "#F8F9FA",
        "ink": "#0F172A",
        "muted": "#64748B",
        "light": "#94A3B8",
        "soft": "#E2E8F0",
        "panel": "#FFFFFF",
        "accent": accents["accent"],
        "accent_2": accents["accent_2"],
        "accent_soft": accents["accent_soft"],
        "accent_mid": accents["accent_mid"],
        "good": "#10B981",
        "danger": "#EF4444",
    }


SANS = "Avenir Next"
TEXT_BASE_FONT_SIZE = 96


def _wrap(text, width):
    text = (text or "").strip()
    if not text:
        return ""
    return "\\n".join(textwrap.wrap(text, width=width, break_long_words=False, break_on_hyphens=False))


def _truncate(text, max_len):
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max(1, max_len - 1)].rstrip() + "…"


def safe_text(text, *, font_size=24, color=None, weight=NORMAL, width=None, height=None, wrap=None):
    pal = palette()
    color = color or pal["ink"]
    raw = str(text or "").strip()
    if wrap and raw:
        raw = _wrap(raw, wrap)
    obj = Text(raw or " ", font=SANS, font_size=TEXT_BASE_FONT_SIZE, color=color, weight=weight, line_spacing=0.95)
    obj.scale(font_size / TEXT_BASE_FONT_SIZE)
    if width and obj.width > width:
        obj.scale_to_fit_width(width)
    if height and obj.height > height:
        obj.scale_to_fit_height(height)
    return obj


def safe_centered_text(text, *, font_size=24, color=None, weight=NORMAL, width=None, height=None, wrap=None):
    pal = palette()
    color = color or pal["ink"]
    raw = str(text or "").strip()
    lines = textwrap.wrap(raw, width=wrap, break_long_words=False, break_on_hyphens=False) if wrap and raw else [raw]
    if not lines or all(not l.strip() for l in lines):
        lines = [" "]
    if len(lines) == 1:
        obj = Text(lines[0], font=SANS, font_size=TEXT_BASE_FONT_SIZE, color=color, weight=weight)
    else:
        line_objs = [Text(l, font=SANS, font_size=TEXT_BASE_FONT_SIZE, color=color, weight=weight) for l in lines]
        obj = VGroup(*line_objs).arrange(DOWN, buff=0.12)
    obj.scale(font_size / TEXT_BASE_FONT_SIZE)
    if width and obj.width > width:
        obj.scale_to_fit_width(width)
    if height and obj.height > height:
        obj.scale_to_fit_height(height)
    return obj


def safe_math(expr, *, color=None, font_size=48, max_width=10.5, max_height=2.6):
    pal = palette()
    color = color or pal["ink"]
    if not expr:
        return None
    try:
        obj = MathTex(expr, color=color, font_size=font_size)
    except Exception:
        obj = safe_text(expr, font_size=int(font_size * 0.7), color=color, weight=SEMIBOLD)
    if obj.width > max_width:
        obj.scale_to_fit_width(max_width)
    if obj.height > max_height:
        obj.scale_to_fit_height(max_height)
    return obj


def _norm(s):
    return (s or "").strip().lower()


def _is_distinct(candidate, *others):
    cand = _norm(candidate)
    if not cand:
        return False
    for other in others:
        oth = _norm(other)
        if not oth:
            continue
        if cand == oth or cand in oth or oth in cand:
            return False
    return True


def _labels(scene_data, *keys, limit=5):
    seen = set()
    items = []
    for key in keys:
        for raw in (scene_data.get(key) or []):
            text = str(raw or "").strip()
            norm = _norm(text)
            if text and norm not in seen:
                items.append(text)
                seen.add(norm)
            if len(items) >= limit:
                return items
    return items


def _data_points(scene_data, fallback_labels=None, limit=6):
    points = []
    for raw in (scene_data.get("data_points") or []):
        if not isinstance(raw, dict):
            continue
        label = str(raw.get("label") or "").strip()
        try:
            value = float(raw.get("value"))
        except Exception:
            continue
        if label:
            points.append((label, value))
        if len(points) >= limit:
            break
    if points:
        return points

    labels = fallback_labels or _labels(scene_data, "visual_items", "key_points", limit=limit)
    if not labels:
        labels = [scene_data.get("headline", "Value")]
    rng = random.Random(sum(ord(c) for c in (scene_data.get("slug") or "values")))
    return [(label, 30 + rng.random() * 70) for label in labels[:limit]]


# ---- shared chrome ----

CHROME_BOTTOM_Y = 2.20


def make_brand_mark(pal):
    mark = safe_text("lern", font_size=18, color=pal["muted"], weight=SEMIBOLD)
    mark.set_opacity(0.30)
    return mark


def make_eyebrow_label(text, pal, *, color=None, font_size=14):
    """Small uppercase label used throughout the slide system."""
    label = safe_text(
        _truncate(text, 40).upper(),
        font_size=font_size,
        weight=SEMIBOLD,
        color=color or pal["accent"],
        width=6.0,
        wrap=40,
    )
    label.set_opacity(0.98)
    return label


def make_tag(text, pal, *, font_size=15):
    label = safe_text(_truncate(text, 48), font_size=font_size, weight=SEMIBOLD, color="#0369A1")
    pad_x, pad_y = 0.30, 0.14
    bg = RoundedRectangle(
        corner_radius=(label.height + pad_y * 2) / 2,
        width=label.width + pad_x * 2,
        height=label.height + pad_y * 2,
        stroke_width=0,
        fill_color=pal["accent_soft"],
        fill_opacity=1,
    )
    return VGroup(bg, label.move_to(bg))


def make_card(width, height, pal, *, fill=None, stroke=None, radius=0.14, stroke_width=1.4):
    return RoundedRectangle(
        corner_radius=radius,
        width=width,
        height=height,
        stroke_width=stroke_width,
        stroke_color=stroke or pal["soft"],
        fill_color=fill or pal["panel"],
        fill_opacity=1,
    )


def make_bottom_rule(pal):
    return Rectangle(
        height=0.045,
        width=config.frame_width,
        stroke_width=0,
        fill_color=pal["accent"],
        fill_opacity=1,
    ).to_edge(DOWN, buff=0)


def make_scene_counter(scene_data, pal):
    index = int(scene_data.get("scene_number", 1))
    total = int(scene_data.get("scene_total", len(SCENES)) or len(SCENES))
    if total <= 1:
        return None
    text = safe_text(f"{index:02d} / {total:02d}", font_size=14, weight=SEMIBOLD, color=pal["muted"])
    text.set_opacity(0.55)
    return text


def setup_frame(scene_obj, scene_data, pal, *, show_counter=False, show_brand=True, show_bottom_rule=True):
    scene_obj.camera.background_color = pal["background"]
    if show_bottom_rule:
        scene_obj.add(make_bottom_rule(pal))
    if show_brand:
        scene_obj.add(make_brand_mark(pal).to_corner(DR, buff=0.45))
    if show_counter:
        counter = make_scene_counter(scene_data, pal)
        if counter is not None:
            counter.to_corner(UR, buff=0.55)
            scene_obj.add(counter)


def add_top_bar(scene_obj, scene_data, pal):
    """Header chrome: left-aligned uppercase accent label + bold headline."""
    setup_frame(scene_obj, scene_data, pal)

    eyebrow_text = (TITLE or "Lesson").strip().upper()
    headline_text = (scene_data.get("headline") or "").strip()
    show_eyebrow = _is_distinct(eyebrow_text, headline_text)

    eyebrow = make_eyebrow_label(eyebrow_text, pal) if show_eyebrow else None
    headline = safe_text(
        headline_text or " ", font_size=40, weight=SEMIBOLD,
        color=pal["ink"], width=11.0, wrap=48,
    )

    parts = [m for m in (eyebrow, headline) if m is not None]
    header = VGroup(*parts)
    if len(parts) > 1:
        header.arrange(DOWN, buff=0.18, aligned_edge=LEFT)
    header.to_edge(UP, buff=0.55)
    header.to_edge(LEFT, buff=0.85)

    if eyebrow is not None:
        scene_obj.play(FadeIn(eyebrow, shift=DOWN * 0.08), run_time=0.3)
    scene_obj.play(Write(headline, run_time=0.6))
    return header


def place_body(group, *, top=None, center_x=0.0, max_height=None, max_width=None):
    if max_width and group.width > max_width:
        group.scale_to_fit_width(max_width)
    top_y = top if top is not None else CHROME_BOTTOM_Y - 0.4
    available_h = top_y - (-3.7)
    if max_height is not None:
        available_h = min(available_h, max_height)
    if group.height > available_h:
        group.scale_to_fit_height(available_h)
    group.move_to([center_x, top_y - group.height / 2, 0])
    return group


def _hold(scene_obj, target, used):
    """Wait out the remainder of the requested scene runtime."""
    scene_obj.wait(max(0.4, float(target) - used))


# ---- title card / summary / thanks ----

def render_title_card(scene_obj, scene_data, pal):
    """Centered opener: fine accent rule, large title, soft supporting line."""
    setup_frame(scene_obj, scene_data, pal, show_counter=False)
    title = (TITLE or scene_data.get("headline") or "Lesson").strip()
    eyebrow_text = "MADE WITH LERN"

    candidates = [scene_data.get("hook"), STORY.get("learning_objective"), STORY.get("summary")]
    subtitle_text = next(
        ((c or "").strip() for c in candidates if _is_distinct(c, title, eyebrow_text)),
        "",
    )

    accent_line = Rectangle(height=0.035, width=0.70, stroke_width=0, fill_color=pal["accent"], fill_opacity=1)
    headline = safe_text(title, font_size=66, weight=SEMIBOLD, color=pal["ink"], width=11.2, wrap=40)
    subtitle = (
        safe_centered_text(subtitle_text, font_size=23, color=pal["muted"], width=8.8, wrap=44)
        if subtitle_text else None
    )
    series = make_eyebrow_label(eyebrow_text, pal, color=pal["light"], font_size=13)
    left_rule = Rectangle(height=0.018, width=0.34, stroke_width=0, fill_color=pal["soft"], fill_opacity=1)
    right_rule = left_rule.copy()
    footer = VGroup(left_rule, series, right_rule).arrange(RIGHT, buff=0.22)

    parts = [accent_line, headline] + ([subtitle] if subtitle is not None else []) + [footer]
    main_block = VGroup(*parts).arrange(DOWN, buff=0.42)
    main_block.move_to(UP * 0.05)
    for mob in (accent_line, headline, subtitle, footer):
        if mob is not None:
            mob.set_x(0)
    footer.shift(DOWN * 0.25)

    scene_obj.play(GrowFromCenter(accent_line), run_time=0.35)
    scene_obj.play(Write(headline), run_time=1.0)
    if subtitle is not None:
        scene_obj.play(FadeIn(subtitle, shift=UP * 0.08), run_time=0.45)
    scene_obj.play(FadeIn(footer, shift=UP * 0.08), run_time=0.35)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 8.0), 2.5)


def render_summary(scene_obj, scene_data, pal):
    """Key takeaways: centered bold accent statement + clean bullet list."""
    add_top_bar(scene_obj, scene_data, pal)

    headline = scene_data.get("headline", "")
    takeaway = (scene_data.get("takeaway") or "").strip()
    if not _is_distinct(takeaway, headline):
        takeaway = (STORY.get("closing_takeaway") or "").strip()

    points, seen = [], {_norm(headline), _norm(takeaway)}
    for b in (scene_data.get("key_points") or []):
        n = _norm(b)
        if n and n not in seen:
            seen.add(n); points.append(b)
        if len(points) >= 4:
            break

    accent_top = Rectangle(
        height=0.035, width=1.2, stroke_width=0,
        fill_color=pal["accent"], fill_opacity=1,
    )
    big = safe_centered_text(
        takeaway or "Key takeaway", font_size=36, weight=SEMIBOLD,
        color=pal["ink"], width=10.5, wrap=42,
    )

    divider = Line(LEFT * 4.5, RIGHT * 4.5, color=pal["soft"], stroke_width=1.5)

    rows = VGroup()
    for line in points:
        marker = Dot(radius=0.08, color=pal["accent"], fill_opacity=1)
        text = safe_centered_text(line, font_size=20, color=pal["ink"], width=9.0, wrap=60)
        row = VGroup(marker, text).arrange(RIGHT, buff=0.30, aligned_edge=UP)
        marker.shift(DOWN * 0.05)
        rows.add(row)
    if len(rows):
        rows.arrange(DOWN, buff=0.32, aligned_edge=LEFT)
        rows.set_x(0)

    parts = [accent_top, big] + ([divider, rows] if len(rows) else [])
    body = VGroup(*parts).arrange(DOWN, buff=0.36)
    for mob in parts:
        if mob is not accent_top:
            mob.set_x(0)
    accent_top.set_x(0)
    place_body(body, top=CHROME_BOTTOM_Y - 0.35, max_height=4.6, max_width=11.5)

    scene_obj.play(GrowFromCenter(accent_top), run_time=0.30)
    scene_obj.play(FadeIn(big, shift=UP * 0.12), run_time=0.6)
    if len(rows):
        scene_obj.play(Create(divider), run_time=0.25)
        scene_obj.play(LaggedStart(*[FadeIn(r, shift=RIGHT * 0.12) for r in rows], lag_ratio=0.18), run_time=0.9)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 12.0), 1.8)


def render_thanks(scene_obj, scene_data, pal):
    """Closing card: restrained thank-you screen matching the opener."""
    setup_frame(scene_obj, scene_data, pal, show_counter=False)

    label = make_eyebrow_label("MADE WITH LERN", pal, font_size=14)
    thanks = safe_text("Thank you for watching.", font_size=58, weight=SEMIBOLD, color=pal["ink"], width=11.0, wrap=28)
    sub = safe_centered_text(
        "Take a moment to review the key ideas, then try the quiz to see what stuck.",
        font_size=21, color=pal["muted"], width=9.0, wrap=52,
    )
    accent_line = Rectangle(height=0.035, width=0.70, stroke_width=0, fill_color=pal["accent"], fill_opacity=1)
    parts = [label, thanks, sub, accent_line]
    main_block = VGroup(*parts).arrange(DOWN, buff=0.38)
    main_block.move_to(ORIGIN)
    for mob in (label, thanks, sub, accent_line):
        mob.set_x(0)

    scene_obj.play(FadeIn(label, shift=DOWN * 0.12), run_time=0.35)
    scene_obj.play(Write(thanks), run_time=1.0)
    scene_obj.play(FadeIn(sub, shift=UP * 0.08), run_time=0.40)
    scene_obj.play(GrowFromCenter(accent_line), run_time=0.25)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 5.0), 2.3)


# ---- content layouts ----


def render_equation(scene_obj, scene_data, pal):
    """Centered equation showcase with variable definitions and takeaway."""
    add_top_bar(scene_obj, scene_data, pal)

    expr_list = [e for e in (scene_data.get("equations") or []) if e]
    primary = expr_list[0] if expr_list else None
    secondary = expr_list[1] if len(expr_list) > 1 else None

    eq_main = safe_math(primary, color=pal["ink"], font_size=58, max_width=9.6) if primary else None
    eq_secondary = safe_math(secondary, color=pal["muted"], font_size=36, max_width=8.6) if secondary else None
    if eq_main is None:
        eq_main = safe_centered_text(
            scene_data.get("hook") or scene_data.get("headline") or "Idea",
            font_size=42, weight=BOLD, color=pal["ink"], width=9.6, wrap=22,
        )

    eq_block_parts = [eq_main] + ([eq_secondary] if eq_secondary is not None else [])
    eq_block = VGroup(*eq_block_parts).arrange(DOWN, buff=0.38)
    card_w = max(eq_block.width + 2.0, 7.0)
    card_h = eq_block.height + 1.20
    eq_card = make_card(card_w, card_h, pal, radius=0.14, stroke_width=1.2)
    accent_bottom = Rectangle(
        height=0.06, width=card_w, stroke_width=0,
        fill_color=pal["accent"], fill_opacity=1,
    ).align_to(eq_card, DOWN).move_to(eq_card.get_bottom() + UP * 0.03)
    eq_block.move_to(eq_card)
    eq_panel = VGroup(eq_card, accent_bottom, eq_block)
    eq_panel.set_x(0)

    component_terms = [t for t in (scene_data.get("highlight_terms") or []) if t][:5]
    definitions = [p for p in (scene_data.get("key_points") or []) if p][:5]
    var_rows = VGroup()
    for i, term in enumerate(component_terms):
        sym = safe_centered_text(term, font_size=15, weight=BOLD, color=pal["accent"], width=1.8, wrap=12)
        dash = safe_text("—", font_size=14, color=pal["light"])
        defn_text = definitions[i] if i < len(definitions) else ""
        defn = safe_text(defn_text, font_size=15, color=pal["ink"], width=6.8, wrap=50) if defn_text else None
        if defn is not None:
            row = VGroup(sym, dash, defn).arrange(RIGHT, buff=0.18, aligned_edge=DOWN)
        else:
            row = VGroup(sym, dash).arrange(RIGHT, buff=0.18, aligned_edge=DOWN)
        var_rows.add(row)
    if len(var_rows):
        var_rows.arrange(DOWN, buff=0.22, aligned_edge=LEFT)
        var_rows.set_x(0)

    takeaway = (scene_data.get("takeaway") or "").strip()
    headline = scene_data.get("headline", "")
    show_takeaway = takeaway and _is_distinct(takeaway, headline)
    takeaway_obj = safe_centered_text(
        takeaway, font_size=17, color=pal["muted"], width=9.0, wrap=62,
    ) if show_takeaway else None

    layout_parts = [eq_panel]
    if len(var_rows):
        layout_parts.append(var_rows)
    if takeaway_obj is not None:
        layout_parts.append(takeaway_obj)
    body = VGroup(*layout_parts).arrange(DOWN, buff=0.34)
    body.set_x(0)
    place_body(body, top=CHROME_BOTTOM_Y - 0.40, max_height=5.0, max_width=11.5)

    scene_obj.play(FadeIn(eq_card, shift=UP * 0.05), GrowFromCenter(accent_bottom), run_time=0.45)
    scene_obj.play(Write(eq_main), run_time=1.2)
    if eq_secondary is not None:
        scene_obj.play(Write(eq_secondary), run_time=0.7)
    if len(var_rows):
        scene_obj.play(LaggedStart(*[FadeIn(r, shift=RIGHT * 0.08) for r in var_rows], lag_ratio=0.14), run_time=0.7)
    if takeaway_obj is not None:
        scene_obj.play(FadeIn(takeaway_obj, shift=UP * 0.06), run_time=0.3)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 3.25)


def render_step_derivation(scene_obj, scene_data, pal):
    """Centered stacked derivation steps with step labels and takeaway."""
    add_top_bar(scene_obj, scene_data, pal)

    equations = [e for e in (scene_data.get("equations") or []) if e][:8]
    if not equations:
        equations = [scene_data.get("headline") or "Start", scene_data.get("takeaway") or "Result"]
    step_labels = _labels(scene_data, "visual_items", "highlight_terms", limit=len(equations))
    n = len(equations)
    eq_font = 42 if n <= 3 else (36 if n <= 5 else (30 if n <= 7 else 26))
    row_gap = 0.38 if n <= 4 else (0.26 if n <= 6 else 0.18)

    rows = VGroup()
    for i, expr in enumerate(equations):
        raw_label = step_labels[i] if i < len(step_labels) else ("Given" if i == 0 else f"Step {i}")
        is_first = i == 0
        is_last = i == n - 1
        step_num = safe_centered_text(
            str(i + 1),
            font_size=13,
            weight=BOLD,
            color="#FFFFFF" if (is_first or is_last) else pal["accent"],
        )
        num_bg = Circle(
            radius=0.22,
            stroke_width=0,
            fill_color=pal["accent"] if (is_first or is_last) else pal["accent_soft"],
            fill_opacity=1,
        )
        step_num.move_to(num_bg)
        num_node = VGroup(num_bg, step_num)
        step_text = safe_text(
            raw_label,
            font_size=11,
            weight=SEMIBOLD,
            color=pal["accent"] if (is_first or is_last) else pal["muted"],
            width=1.45,
            wrap=12,
        )
        label_col = VGroup(num_node, step_text).arrange(DOWN, buff=0.08)
        math_obj = safe_math(expr, color=pal["ink"] if not is_last else pal["accent"],
                             font_size=eq_font, max_width=8.0, max_height=0.85)
        row = VGroup(label_col, math_obj).arrange(RIGHT, buff=0.40, aligned_edge=DOWN)
        rows.add(row)
    rows.arrange(DOWN, buff=row_gap)
    rows.set_x(0)

    takeaway = (scene_data.get("takeaway") or "").strip()
    headline = scene_data.get("headline", "")
    show_takeaway = takeaway and _is_distinct(takeaway, headline)
    takeaway_obj = safe_centered_text(
        takeaway, font_size=16, color=pal["muted"], width=9.0, wrap=62,
    ) if show_takeaway else None

    parts = [rows] + ([takeaway_obj] if takeaway_obj is not None else [])
    content = VGroup(*parts).arrange(DOWN, buff=0.36)
    content.set_x(0)
    place_body(content, top=CHROME_BOTTOM_Y - 0.38, max_height=5.0, max_width=11.5)

    for row in rows:
        scene_obj.play(FadeIn(row[0], shift=RIGHT * 0.10), Write(row[1]), run_time=0.50)
    if takeaway_obj is not None:
        scene_obj.play(FadeIn(takeaway_obj, shift=UP * 0.06), run_time=0.3)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 0.50 * n + 0.5)



def render_line_chart(scene_obj, scene_data, pal):
    """Centered trend line with summary, labels, and interpretation."""
    add_top_bar(scene_obj, scene_data, pal)

    points = _data_points(scene_data, limit=6)
    values = [value for _, value in points]
    low, high = min(values), max(values)
    if abs(high - low) < 0.001:
        low -= 1
        high += 1
    pad = max((high - low) * 0.18, 1)
    axes = Axes(
        x_range=[0, max(len(points) - 1, 1), 1],
        y_range=[low - pad, high + pad, max((high - low) / 3, 1)],
        x_length=8.2,
        y_length=3.0,
        axis_config={"color": pal["muted"], "stroke_width": 2},
        tips=False,
    )

    coords = [axes.c2p(i, value) for i, (_, value) in enumerate(points)]
    segments = VGroup(*[Line(coords[i], coords[i + 1], color=pal["accent"], stroke_width=4) for i in range(len(coords) - 1)])
    dots = VGroup(*[Dot(coord, radius=0.09, color=pal["accent_2"]) for coord in coords])
    labels = VGroup()
    for i, (label, _value) in enumerate(points):
        labels.add(safe_centered_text(label, font_size=13, weight=SEMIBOLD, color=pal["muted"], width=1.35, wrap=10)
                   .next_to(axes.c2p(i, low - pad), DOWN, buff=0.12))
    value_label = safe_centered_text(
        f"{points[-1][1]:g}",
        font_size=20, weight=BOLD, color=pal["accent"], width=2.0,
    ).next_to(dots[-1], UR, buff=0.16)

    summary = safe_centered_text(
        scene_data.get("takeaway") or scene_data.get("hook") or "The trend reveals the direction of change.",
        font_size=18, color=pal["ink"], width=9.0, wrap=58,
    )
    note_text = (scene_data.get("key_points") or [""])[0]
    note = safe_centered_text(
        note_text, font_size=15, color=pal["muted"], width=8.6, wrap=62,
    ) if note_text else None

    chart_group = VGroup(axes, segments, dots, labels, value_label)
    parts = [summary, chart_group] + ([note] if note is not None else [])
    body = VGroup(*parts).arrange(DOWN, buff=0.28)
    body.set_x(0)
    place_body(body, top=CHROME_BOTTOM_Y - 0.28, max_height=5.1, max_width=11.4)

    scene_obj.play(FadeIn(summary, shift=DOWN * 0.06), run_time=0.35)
    scene_obj.play(Create(axes), run_time=0.5)
    if len(segments):
        scene_obj.play(LaggedStart(*[Create(s) for s in segments], lag_ratio=0.16), run_time=1.0)
    scene_obj.play(FadeIn(dots, scale=0.8), FadeIn(labels, shift=UP * 0.05), run_time=0.55)
    scene_obj.play(FadeIn(value_label, shift=LEFT * 0.08), run_time=0.25)
    if note is not None:
        scene_obj.play(FadeIn(note, shift=UP * 0.06), run_time=0.3)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 2.95)


def render_comparison(scene_obj, scene_data, pal):
    """Centered side-by-side comparison cards with takeaway."""
    add_top_bar(scene_obj, scene_data, pal)

    items = [s for s in (scene_data.get("visual_items") or []) if s]
    if len(items) < 2:
        for src in (scene_data.get("headline", ""), scene_data.get("hook", "")):
            for sep in (" vs ", " vs. ", " versus "):
                low = src.lower()
                if sep in low:
                    idx = low.index(sep)
                    a = src[:idx].strip()
                    b = src[idx + len(sep):].strip()
                    for end in (":", " - ", " \\u2014 "):
                        if end in b:
                            b = b[:b.index(end)].strip()
                            break
                    if a and b:
                        items = [a, b]
                        break
            if len(items) >= 2:
                break
    if len(items) < 2:
        terms = [s for s in (scene_data.get("highlight_terms") or []) if s]
        if len(terms) >= 2:
            items = terms[:2]
    points = [s for s in (scene_data.get("key_points") or []) if s]
    left_title = items[0] if items else "Option A"
    right_title = items[1] if len(items) > 1 else "Option B"

    def panel(label, lines, accent, highlighted=False):
        bullet_limit = 4
        bg = make_card(
            5.0, 4.2, pal,
            fill=pal["accent_soft"] if highlighted else pal["panel"],
            stroke=pal["accent_mid"] if highlighted else pal["soft"],
            radius=0.14,
            stroke_width=1.35,
        )
        header_label = make_eyebrow_label(label, pal, color=accent, font_size=15)
        header_label.move_to([bg.get_center()[0], bg.get_top()[1] - 0.48, 0])

        rows = VGroup()
        for line in lines[:bullet_limit]:
            dot = Dot(radius=0.07, color=accent)
            text = safe_centered_text(line, font_size=16, color=pal["ink"], width=3.8, wrap=30)
            rows.add(VGroup(dot, text).arrange(RIGHT, buff=0.20, aligned_edge=UP))
        if len(rows):
            rows.arrange(DOWN, buff=0.26, aligned_edge=LEFT)
            rows.move_to(bg.get_center() + DOWN * 0.20)
            if rows.height > bg.height - 1.1:
                rows.scale_to_fit_height(bg.height - 1.1)
        return VGroup(bg, header_label, rows)

    if len(points) >= 2:
        split = max(1, math.ceil(len(points) / 2))
        left_lines = points[:split][:4]
        right_lines = (points[split:][:4]) or points[:1]
    else:
        left_lines = points[:1] or [scene_data.get("hook") or left_title]
        right_lines = [scene_data.get("takeaway") or right_title]

    left = panel(left_title, left_lines, pal["muted"], highlighted=False)
    right = panel(right_title, right_lines, pal["accent"], highlighted=True)

    vs_bg = Circle(
        radius=0.30, stroke_width=1.2,
        color=pal["soft"], fill_color=pal["background"], fill_opacity=1,
    )
    vs_text = safe_centered_text("vs", font_size=13, weight=SEMIBOLD, color=pal["light"]).move_to(vs_bg)
    vs_node = VGroup(vs_bg, vs_text)

    pair = VGroup(left, vs_node, right).arrange(RIGHT, buff=0.24)

    takeaway = (scene_data.get("takeaway") or "").strip()
    headline = scene_data.get("headline", "")
    show_takeaway = takeaway and _is_distinct(takeaway, headline)
    takeaway_obj = safe_centered_text(
        takeaway, font_size=16, color=pal["muted"], width=9.5, wrap=64,
    ) if show_takeaway else None

    parts = [pair] + ([takeaway_obj] if takeaway_obj is not None else [])
    body = VGroup(*parts).arrange(DOWN, buff=0.30)
    body.set_x(0)
    place_body(body, top=CHROME_BOTTOM_Y - 0.25, max_height=5.3, max_width=11.5)

    scene_obj.play(FadeIn(left, shift=LEFT * 0.15), FadeIn(right, shift=RIGHT * 0.15), run_time=0.7)
    scene_obj.play(FadeIn(vs_node, scale=0.7), run_time=0.30)
    if takeaway_obj is not None:
        scene_obj.play(FadeIn(takeaway_obj, shift=UP * 0.06), run_time=0.3)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 1.7)


def render_before_after(scene_obj, scene_data, pal):
    """Centered transformation cards with key changes and takeaway."""
    add_top_bar(scene_obj, scene_data, pal)

    items = _labels(scene_data, "visual_items", limit=2)
    before = items[0] if items else "Before"
    after = items[1] if len(items) > 1 else "After"
    points = _labels(scene_data, "key_points", "highlight_terms", limit=3)

    def state_card(title, subtitle, detail_lines, highlighted=False):
        bg = make_card(
            4.5,
            3.8,
            pal,
            fill=pal["accent_soft"] if highlighted else pal["panel"],
            stroke=pal["accent_mid"] if highlighted else pal["soft"],
            radius=0.14,
            stroke_width=1.35,
        )
        label = make_eyebrow_label(title, pal, color=pal["accent"] if highlighted else pal["muted"], font_size=14)
        label.move_to([bg.get_center()[0], bg.get_top()[1] - 0.42, 0])
        body = safe_centered_text(subtitle, font_size=20, weight=SEMIBOLD, color=pal["ink"], width=3.6, height=1.0, wrap=22)
        content_parts = [body]
        for dl in detail_lines[:2]:
            content_parts.append(safe_centered_text(dl, font_size=13, color=pal["muted"], width=3.4, wrap=28))
        content = VGroup(*content_parts).arrange(DOWN, buff=0.14)
        content.move_to(bg.get_center() + DOWN * 0.10)
        if content.height > bg.height - 1.0:
            content.scale_to_fit_height(bg.height - 1.0)
        return VGroup(bg, label, content)

    left_details = [p for p in points[:1] if _is_distinct(p, before)]
    right_details = [p for p in points[1:2] if _is_distinct(p, after)]
    left = state_card("Before", before, left_details, highlighted=False)
    right = state_card("After", after, right_details, highlighted=True)
    arrow = Arrow(LEFT * 0.72, RIGHT * 0.72, color=pal["accent"], stroke_width=4, buff=0.05, tip_length=0.22)
    pair = VGroup(left, arrow, right).arrange(RIGHT, buff=0.38)

    chips = VGroup(*[make_tag(point, pal, font_size=13) for point in points])
    takeaway = (scene_data.get("takeaway") or "").strip()
    headline = scene_data.get("headline", "")
    show_takeaway = takeaway and _is_distinct(takeaway, headline)
    takeaway_obj = safe_centered_text(
        takeaway, font_size=16, color=pal["muted"], width=9.5, wrap=64,
    ) if show_takeaway else None

    body_parts = [pair]
    if len(chips):
        chips.arrange(RIGHT, buff=0.24)
        if chips.width > 11.0:
            chips.scale_to_fit_width(11.0)
        body_parts.append(chips)
    if takeaway_obj is not None:
        body_parts.append(takeaway_obj)
    body = VGroup(*body_parts).arrange(DOWN, buff=0.32)
    body.set_x(0)
    place_body(body, top=CHROME_BOTTOM_Y - 0.3, max_height=5.2, max_width=11.5)

    scene_obj.play(FadeIn(left, shift=LEFT * 0.15), run_time=0.45)
    scene_obj.play(Create(arrow), run_time=0.35)
    scene_obj.play(FadeIn(right, shift=RIGHT * 0.15), run_time=0.45)
    if len(chips):
        scene_obj.play(LaggedStart(*[FadeIn(c, shift=UP * 0.06) for c in chips], lag_ratio=0.12), run_time=0.5)
    if takeaway_obj is not None:
        scene_obj.play(FadeIn(takeaway_obj, shift=UP * 0.06), run_time=0.3)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 2.1)


def render_flow(scene_obj, scene_data, pal):
    """Centered numbered process nodes with content boxes and takeaway."""
    add_top_bar(scene_obj, scene_data, pal)

    items = [s for s in (scene_data.get("visual_items") or scene_data.get("key_points") or []) if s][:4]
    if not items:
        items = [scene_data.get("headline", "step")]
    if len(items) == 1:
        items = items + [(scene_data.get("highlight_terms") or [items[0]])[0]]
    n = len(items)

    spacing = 2.85 if n <= 3 else 2.45
    total_width = (n - 1) * spacing
    start_x = -total_width / 2

    nodes = VGroup()
    boxes = VGroup()
    connectors = VGroup()
    detail_lines = [s for s in (scene_data.get("key_points") or []) if s]
    extra_details = [s for s in (scene_data.get("highlight_terms") or []) if s]
    for i, item in enumerate(items):
        x = start_x + i * spacing
        is_first = i == 0
        is_last = i == n - 1
        bg = Circle(
            radius=0.42,
            color=pal["accent"],
            stroke_width=2.0 if is_first or is_last else 1.6,
            fill_color=pal["accent"] if is_first else (pal["accent_mid"] if is_last else pal["accent_soft"]),
            fill_opacity=1,
        )
        num_label = safe_centered_text(str(i + 1), font_size=16, weight=BOLD,
                              color="#FFFFFF" if is_first else pal["accent"]).move_to(bg)
        node = VGroup(bg, num_label).move_to([x, 0.40, 0])
        nodes.add(node)

        title = safe_centered_text(item, font_size=14, weight=SEMIBOLD, color=pal["ink"],
                          width=spacing - 0.50, height=0.44, wrap=17)
        detail_source = ""
        if i < len(detail_lines) and _is_distinct(detail_lines[i], item):
            detail_source = detail_lines[i]
        elif i < len(extra_details) and _is_distinct(extra_details[i], item):
            detail_source = extra_details[i]
        detail = safe_centered_text(detail_source, font_size=12, color=pal["muted"],
                           width=spacing - 0.44, height=0.72, wrap=24)
        card = make_card(spacing - 0.24, 1.50, pal, radius=0.12, stroke_width=1.0)
        content = VGroup(title, detail).arrange(DOWN, buff=0.10)
        if content.height > card.height - 0.22:
            content.scale_to_fit_height(card.height - 0.22)
        content.move_to(card)
        box = VGroup(card, content).next_to(node, DOWN, buff=0.28)
        boxes.add(box)
        if i > 0:
            prev_node = nodes[i - 1]
            arrow = Arrow(
                prev_node[0].get_right(), bg.get_left(),
                color=pal["soft"], stroke_width=2.2, buff=0.05,
                tip_length=0.16, max_tip_length_to_length_ratio=0.28,
            )
            connectors.add(arrow)

    pipeline = VGroup(connectors, nodes, boxes)

    takeaway = (scene_data.get("takeaway") or "").strip()
    headline = scene_data.get("headline", "")
    show_takeaway = takeaway and _is_distinct(takeaway, headline)
    takeaway_obj = safe_centered_text(
        takeaway, font_size=16, color=pal["muted"], width=9.5, wrap=64,
    ) if show_takeaway else None

    parts = [pipeline] + ([takeaway_obj] if takeaway_obj is not None else [])
    body = VGroup(*parts).arrange(DOWN, buff=0.32)
    body.set_x(0)
    place_body(body, top=CHROME_BOTTOM_Y - 0.22, max_height=5.2, max_width=11.5)

    scene_obj.play(LaggedStart(*[FadeIn(node, scale=0.7) for node in nodes], lag_ratio=0.15), run_time=0.9)
    if len(connectors):
        scene_obj.play(LaggedStart(*[Create(c) for c in connectors], lag_ratio=0.15), run_time=0.7)
    scene_obj.play(LaggedStart(*[FadeIn(b, shift=UP * 0.1) for b in boxes], lag_ratio=0.12), run_time=0.6)
    if takeaway_obj is not None:
        scene_obj.play(FadeIn(takeaway_obj, shift=UP * 0.06), run_time=0.3)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 2.5)


def render_timeline(scene_obj, scene_data, pal):
    """Centered horizontal milestone sequence with details and takeaway."""
    add_top_bar(scene_obj, scene_data, pal)

    items = _labels(scene_data, "visual_items", "key_points", limit=5)
    if len(items) < 2:
        items = [scene_data.get("headline", "Start"), scene_data.get("takeaway", "Finish") or "Finish"]
    details = [s for s in (scene_data.get("key_points") or []) if s]
    extra = [s for s in (scene_data.get("highlight_terms") or []) if s]
    n = len(items)
    spine_width = 9.6
    spine_y = 0.0
    line = Line(LEFT * (spine_width / 2), RIGHT * (spine_width / 2),
                color=pal["soft"], stroke_width=3).move_to([0, spine_y, 0])

    dots = VGroup()
    label_blocks = VGroup()
    for i, item in enumerate(items):
        x = -spine_width / 2 + i * (spine_width / max(n - 1, 1))
        is_first = i == 0
        is_last = i == n - 1
        dot = Circle(
            radius=0.20,
            color=pal["accent"],
            stroke_width=2.2,
            fill_color=pal["accent"] if (is_first or is_last) else pal["accent_soft"],
            fill_opacity=1,
        ).move_to([x, spine_y, 0])
        dots.add(dot)

        detail_src = ""
        if i < len(details) and _is_distinct(details[i], item):
            detail_src = details[i]
        elif i < len(extra) and _is_distinct(extra[i], item):
            detail_src = extra[i]

        block_w = min(spine_width / max(n, 1) - 0.22, 2.20)
        title = safe_centered_text(item, font_size=14, weight=SEMIBOLD, color=pal["ink"], width=block_w, wrap=14)
        if detail_src:
            detail_obj = safe_centered_text(detail_src, font_size=11, color=pal["muted"], width=block_w, wrap=20)
            block = VGroup(title, detail_obj).arrange(DOWN, buff=0.08)
        else:
            block = title

        stacks_down = i % 2 == 1
        direction = DOWN if stacks_down else UP
        block.next_to(dot, direction, buff=0.30)
        block.set_x(x)
        label_blocks.add(block)

    note_text = ""
    for cnd in [scene_data.get("takeaway"), scene_data.get("hook")]:
        if _is_distinct(cnd, scene_data.get("headline"), *items):
            note_text = cnd
            break
    note = safe_centered_text(note_text, font_size=16, color=pal["muted"], width=9.5, wrap=66) if note_text else None

    content = VGroup(line, dots, label_blocks)
    if note is not None:
        note.next_to(content, DOWN, buff=0.40)
        note.set_x(0)
        body = VGroup(content, note)
    else:
        body = content
    body.set_x(0)
    place_body(body, top=CHROME_BOTTOM_Y - 0.12, max_height=5.4, max_width=11.5)

    scene_obj.play(Create(line), run_time=0.5)
    scene_obj.play(LaggedStart(*[FadeIn(d, scale=0.75) for d in dots], lag_ratio=0.14), run_time=0.8)
    scene_obj.play(LaggedStart(*[FadeIn(lb, shift=UP * 0.08) for lb in label_blocks], lag_ratio=0.12), run_time=0.8)
    if note is not None:
        scene_obj.play(FadeIn(note, shift=UP * 0.06), run_time=0.3)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 2.7)


def render_bar_chart(scene_obj, scene_data, pal):
    """Centered rounded bars with value labels and interpretation text."""
    add_top_bar(scene_obj, scene_data, pal)

    points = _data_points(scene_data, limit=5)
    items = [label for label, _value in points]
    raw_values = [max(value, 0.0) for _label, value in points]
    max_raw = max(raw_values) if raw_values else 1.0
    if max_raw <= 0:
        max_raw = 1.0
    values = [0.28 + 0.72 * (value / max_raw) for value in raw_values]
    max_val = max(values)

    base_y, max_h = -2.25, 2.55
    n = len(items)
    w = min(0.92, 7.5 / max(n, 1) - 0.40)
    spacing = 0.45
    total_w = n * w + (n - 1) * spacing
    start_x = -total_w / 2 + w / 2

    baseline = Line(
        LEFT * (total_w / 2 + 0.5), RIGHT * (total_w / 2 + 0.5),
        color=pal["soft"], stroke_width=2,
    ).move_to([0, base_y, 0])

    bars, labels, value_labels = VGroup(), VGroup(), VGroup()
    for i, (item, v) in enumerate(zip(items, values)):
        is_top = v >= max_val - 0.001
        color = pal["accent"] if is_top else pal["accent_2"]
        opacity = 1.0 if is_top else 0.82
        bar = RoundedRectangle(
            corner_radius=0.09, width=w, height=v * max_h,
            stroke_width=0, fill_color=color, fill_opacity=opacity,
        )
        bar.move_to([start_x + i * (w + spacing), base_y + (v * max_h) / 2, 0])
        bars.add(bar)
        labels.add(safe_centered_text(item, font_size=13, weight=SEMIBOLD, color=pal["ink"], width=w + 0.55, wrap=13)
                   .next_to(bar, DOWN, buff=0.20))
        value_labels.add(safe_centered_text(f"{raw_values[i]:g}", font_size=16, weight=BOLD, color=color)
                         .next_to(bar, UP, buff=0.14))

    main_text = safe_centered_text(
        scene_data.get("takeaway") or scene_data.get("hook") or "Compare the tallest bar against the rest.",
        font_size=18, weight=SEMIBOLD, color=pal["ink"], width=9.0, wrap=58,
    )
    sub_text_raw = (scene_data.get("key_points") or [""])[0]
    sub_text = safe_centered_text(sub_text_raw, font_size=15, color=pal["muted"], width=8.8, wrap=62) if sub_text_raw else None

    chart = VGroup(baseline, bars, labels, value_labels)
    bottom_parts = [main_text] + ([sub_text] if sub_text else [])
    bottom = VGroup(*bottom_parts).arrange(DOWN, buff=0.16)

    place_body(chart, top=CHROME_BOTTOM_Y - 0.35, max_height=4.4, max_width=10.5)
    bottom.next_to(chart, DOWN, buff=0.30)
    bottom.set_x(0)

    scene_obj.play(Create(baseline), run_time=0.4)
    scene_obj.play(LaggedStart(*[GrowFromEdge(b, DOWN) for b in bars], lag_ratio=0.12), run_time=1.1)
    scene_obj.play(LaggedStart(*[FadeIn(l, shift=UP * 0.05) for l in labels], lag_ratio=0.1), run_time=0.5)
    scene_obj.play(LaggedStart(*[FadeIn(v) for v in value_labels], lag_ratio=0.08), run_time=0.4)
    scene_obj.play(FadeIn(main_text, shift=UP * 0.06), run_time=0.35)
    if sub_text:
        scene_obj.play(FadeIn(sub_text, shift=UP * 0.06), run_time=0.25)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 2.75)


def render_proportional_chart(scene_obj, scene_data, pal):
    """Centered pie chart with legend, takeaway, and interpretation."""
    add_top_bar(scene_obj, scene_data, pal)

    points = _data_points(scene_data, limit=5)
    positive = [(label, max(value, 0.0)) for label, value in points]
    total = sum(value for _label, value in positive) or len(positive) or 1
    colors = [pal["accent"], pal["accent_2"], pal["accent_mid"], "#94A3B8", "#CBD5E1"]

    start_angle = PI / 2
    radius = 1.55
    slices = VGroup()
    legend = VGroup()
    for i, (label, value) in enumerate(positive):
        frac = value / total
        color = colors[i % len(colors)]
        angle = max(frac * TAU, 0.001)
        sector = Sector(
            outer_radius=radius,
            inner_radius=0,
            angle=angle,
            start_angle=start_angle - angle,
            color=pal["background"],
            stroke_width=2,
            fill_color=color,
            fill_opacity=1,
        )
        start_angle -= angle
        slices.add(sector)
        swatch = RoundedRectangle(corner_radius=0.04, width=0.22, height=0.22,
                                  stroke_width=0, fill_color=color, fill_opacity=1)
        label_text = safe_centered_text(f"{label}", font_size=15, weight=SEMIBOLD, color=pal["ink"], width=2.5, wrap=20)
        pct_text = safe_centered_text(f"{frac * 100:.0f}%", font_size=14, weight=BOLD, color=color, width=0.7)
        row = VGroup(swatch, label_text, pct_text).arrange(RIGHT, buff=0.14, aligned_edge=DOWN)
        legend.add(row)
    if len(legend):
        legend.arrange(DOWN, buff=0.24, aligned_edge=LEFT)

    title = safe_centered_text(
        scene_data.get("takeaway") or "Parts of the whole",
        font_size=20, weight=SEMIBOLD, color=pal["ink"], width=9.5, wrap=48,
    )
    note_text = (scene_data.get("key_points") or [""])[0]
    note = safe_centered_text(
        note_text or "Each slice shows its share of the total.",
        font_size=15, color=pal["muted"], width=9.2, wrap=62,
    )
    chart_row = VGroup(slices, legend).arrange(RIGHT, buff=0.80)
    body = VGroup(title, chart_row, note).arrange(DOWN, buff=0.34)
    body.set_x(0)
    place_body(body, top=CHROME_BOTTOM_Y - 0.28, max_height=5.1, max_width=11.5)

    scene_obj.play(FadeIn(title), run_time=0.35)
    scene_obj.play(LaggedStart(*[FadeIn(s, scale=0.90) for s in slices], lag_ratio=0.08), run_time=0.9)
    if len(legend):
        scene_obj.play(LaggedStart(*[FadeIn(row, shift=UP * 0.05) for row in legend], lag_ratio=0.10), run_time=0.55)
    scene_obj.play(FadeIn(note, shift=UP * 0.06), run_time=0.25)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 2.30)


def render_cause_effect(scene_obj, scene_data, pal):
    """Centered cause branching into effects with descriptions and takeaway."""
    add_top_bar(scene_obj, scene_data, pal)

    cause = (_labels(scene_data, "highlight_terms", limit=1) or [scene_data.get("headline", "Cause")])[0]
    effects = _labels(scene_data, "visual_items", "key_points", limit=4)
    if not effects:
        effects = [scene_data.get("takeaway", "Effect") or "Effect"]
    effect_details = [s for s in (scene_data.get("key_points") or []) if s]

    cause_card = make_card(3.0, 1.45, pal, fill=pal["accent_soft"], stroke=pal["accent_mid"])
    cause_text = safe_centered_text(cause, font_size=20, weight=BOLD, color=pal["ink"], width=2.35, height=0.9, wrap=18)
    cause_node = VGroup(cause_card, cause_text.move_to(cause_card))

    effect_nodes = VGroup()
    arrows = VGroup()
    n_eff = len(effects)
    y_positions = [1.35, 0.45, -0.45, -1.35] if n_eff > 3 else ([0.95, 0.0, -0.95] if n_eff == 3 else ([0.55, -0.55] if n_eff == 2 else [0.0]))
    for i, effect in enumerate(effects):
        detail_src = effect_details[i] if i < len(effect_details) and _is_distinct(effect_details[i], effect) else ""
        bg = make_card(3.8, 1.10 if detail_src else 0.85, pal, radius=0.14, stroke_width=1.2)
        title = safe_centered_text(effect, font_size=15, weight=SEMIBOLD, color=pal["ink"], width=3.2, height=0.42, wrap=24)
        if detail_src:
            detail = safe_centered_text(detail_src, font_size=12, color=pal["muted"], width=3.2, height=0.40, wrap=28)
            content = VGroup(title, detail).arrange(DOWN, buff=0.06).move_to(bg)
        else:
            content = title.move_to(bg)
        node = VGroup(bg, content)
        nodes_x = cause_node.get_center()[0] + 3.8
        node.move_to([nodes_x, y_positions[i] if i < len(y_positions) else 0, 0])
        effect_nodes.add(node)
        arrows.add(Arrow(
            cause_node.get_right(), node.get_left(),
            color=pal["soft"], stroke_width=2.2, buff=0.10, tip_length=0.15,
        ))

    diagram = VGroup(cause_node, arrows, effect_nodes)
    diagram.move_to(ORIGIN)

    note_text = ""
    for cnd in [scene_data.get("takeaway"), scene_data.get("hook")]:
        if _is_distinct(cnd, cause, scene_data.get("headline")):
            note_text = cnd
            break
    note = safe_centered_text(note_text, font_size=16, color=pal["muted"], width=10.0, wrap=66) if note_text else None

    if note is not None:
        body = VGroup(diagram, note).arrange(DOWN, buff=0.36)
        note.set_x(0)
    else:
        body = diagram
    body.set_x(0)
    place_body(body, top=CHROME_BOTTOM_Y - 0.20, max_height=5.3, max_width=11.5)

    scene_obj.play(FadeIn(cause_node, scale=0.9), run_time=0.45)
    scene_obj.play(LaggedStart(*[Create(a) for a in arrows], lag_ratio=0.12), run_time=0.75)
    scene_obj.play(LaggedStart(*[FadeIn(n, shift=LEFT * 0.12) for n in effect_nodes], lag_ratio=0.12), run_time=0.75)
    if note is not None:
        scene_obj.play(FadeIn(note, shift=UP * 0.08), run_time=0.35)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 2.4)


def render_network(scene_obj, scene_data, pal):
    """Centered hub-and-spoke diagram with child details."""
    add_top_bar(scene_obj, scene_data, pal)

    child_titles = _labels(scene_data, "visual_items", limit=5)
    if len(child_titles) < 2:
        child_titles = _labels(scene_data, "highlight_terms", "key_points", limit=5)
    if len(child_titles) < 2:
        child_titles = ["Input", "Output"]
    child_details = [s for s in (scene_data.get("key_points") or []) if s]
    center_title = (_labels(scene_data, "highlight_terms", limit=1) or [scene_data.get("headline", "Core")])[0]
    center_body = scene_data.get("hook") or scene_data.get("takeaway") or ""

    n = len(child_titles)
    radius = 2.60 if n <= 3 else (2.90 if n == 4 else 3.10)
    child_w = 2.50 if n <= 4 else 2.30
    child_h = 1.15

    nodes = VGroup()
    center_bg = make_card(2.9, 1.55, pal, fill=pal["accent_soft"], stroke=pal["accent_mid"], radius=0.18, stroke_width=1.5)
    center_text = VGroup(
        safe_centered_text(center_title, font_size=17, weight=BOLD, color=pal["ink"], width=2.40, height=0.44, wrap=20),
        safe_centered_text(center_body, font_size=11, color=pal["muted"], width=2.38, height=0.58, wrap=26),
    ).arrange(DOWN, buff=0.08)
    center_node = VGroup(center_bg, center_text.move_to(center_bg))
    nodes.add(center_node)

    for i, title in enumerate(child_titles):
        angle = PI / 2 + i * TAU / n
        pos = np.array([math.cos(angle) * radius, math.sin(angle) * radius - 0.08, 0])
        bg = make_card(child_w, child_h, pal, radius=0.14, stroke_width=1.15)
        detail_source = child_details[i] if i < len(child_details) and _is_distinct(child_details[i], title) else ""
        title_obj = safe_centered_text(title, font_size=14, weight=SEMIBOLD, color=pal["ink"],
                              width=child_w - 0.40, height=0.38, wrap=18)
        if detail_source:
            detail_obj = safe_centered_text(detail_source, font_size=11, color=pal["muted"],
                                   width=child_w - 0.40, height=0.48, wrap=24)
            content = VGroup(title_obj, detail_obj).arrange(DOWN, buff=0.07)
        else:
            content = title_obj
        nodes.add(VGroup(bg, content.move_to(bg)).move_to(pos))

    edges = VGroup()
    for i in range(1, len(nodes)):
        edges.add(Line(nodes[0].get_center(), nodes[i].get_center(), color=pal["soft"], stroke_width=2.0))

    body = VGroup(edges, nodes)
    body.set_x(0)
    place_body(body, top=CHROME_BOTTOM_Y - 0.18, max_height=5.3, max_width=11.5)

    scene_obj.play(LaggedStart(*[Create(e) for e in edges], lag_ratio=0.08), run_time=0.9)
    scene_obj.play(LaggedStart(*[FadeIn(nd, scale=0.80) for nd in nodes], lag_ratio=0.10), run_time=0.85)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 2.1)


def render_statement(scene_obj, scene_data, pal):
    """Full-frame centered bold statement with accent line and supporting content."""
    setup_frame(scene_obj, scene_data, pal)

    terms = _labels(scene_data, "highlight_terms", limit=1)
    eyebrow_str = (terms[0] if terms else "Key Insight").upper()
    eyebrow = make_eyebrow_label(eyebrow_str, pal, font_size=14)

    statement_text = next(
        (t.strip() for t in [
            scene_data.get("takeaway"),
            scene_data.get("hook"),
            scene_data.get("headline"),
        ] if t and len((t or "").strip()) > 12),
        "Key Insight",
    )

    big = safe_centered_text(
        statement_text, font_size=44, weight=SEMIBOLD,
        color=pal["ink"], width=10.5, wrap=32,
    )

    accent_line = Rectangle(
        height=0.04, width=1.6, stroke_width=0,
        fill_color=pal["accent"], fill_opacity=1,
    )

    context_lines = []
    seen = {_norm(statement_text)}
    for cand in (scene_data.get("key_points") or []):
        cand = str(cand or "").strip()
        n = _norm(cand)
        if cand and n not in seen and _is_distinct(cand, statement_text):
            seen.add(n)
            context_lines.append(cand)
        if len(context_lines) >= 3:
            break

    sub_group = VGroup()
    for line in context_lines:
        sub_group.add(safe_centered_text(line, font_size=19, color=pal["muted"], width=9.5, wrap=56))
    if len(sub_group):
        sub_group.arrange(DOWN, buff=0.24)

    parts = [eyebrow, big, accent_line] + ([sub_group] if len(sub_group) else [])
    full = VGroup(*parts).arrange(DOWN, buff=0.34)
    full.move_to(ORIGIN + UP * 0.05)
    for mob in parts:
        mob.set_x(0)

    if full.width > 11.5:
        full.scale_to_fit_width(11.5)
    if full.height > 6.5:
        full.scale_to_fit_height(6.5)

    scene_obj.play(FadeIn(eyebrow, shift=DOWN * 0.08), run_time=0.28)
    scene_obj.play(Write(big, run_time=0.95))
    scene_obj.play(GrowFromCenter(accent_line), run_time=0.30)
    if len(sub_group):
        scene_obj.play(LaggedStart(*[FadeIn(s, shift=UP * 0.06) for s in sub_group], lag_ratio=0.15), run_time=0.6)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 12.0), 2.2)


# ---- dispatcher ----
LAYOUT_RENDERERS = {
    "title_card": render_title_card,
    "summary": render_summary,
    "thanks": render_thanks,
    "statement": render_statement,
    "equation": render_equation,
    "step_derivation": render_step_derivation,
    "line_chart": render_line_chart,
    "comparison": render_comparison,
    "before_after": render_before_after,
    "flow": render_flow,
    "timeline": render_timeline,
    "bar_chart": render_bar_chart,
    "proportional_chart": render_proportional_chart,
    "cause_effect": render_cause_effect,
    "network": render_network,
}


def auto_layout(scene_data):
    head = ((scene_data.get("headline") or "") + " " + (scene_data.get("hook") or "") + " " + (scene_data.get("narration") or "")).lower()
    if scene_data.get("equations"):
        return "step_derivation" if len(scene_data.get("equations") or []) > 2 else "equation"
    if any(w in head for w in ("timeline", "history", "milestone", "phase", "era", "lifecycle", "life cycle")):
        return "timeline"
    if any(w in head for w in ("before", "after", "misconception", "correct", "transform", "change from")):
        return "before_after"
    if any(w in head for w in ("cause", "effect", "leads to", "drives", "because")):
        return "cause_effect"
    if any(w in head for w in ("network", "graph", "dependency", "relationship", "connected", "interaction")):
        return "network"
    if any(w in head for w in ("proportion", "ratio", "percent breakdown", "parts of", "composition", "mixture")):
        return "proportional_chart"
    if scene_data.get("data_points") and any(w in head for w in ("trend", "over time", "line chart", "trajectory")):
        return "line_chart"
    if scene_data.get("data_points") and any(w in head for w in ("bar chart", "ranking", "share", "percentage", "magnitude")):
        return "bar_chart"
    if any(w in head for w in ("vs ", " versus ", "compare", "comparison")):
        return "comparison"
    if any(w in head for w in ("step", "process", "pipeline", "workflow", "stage", "first then")):
        return "flow"
    if scene_data.get("data_points"):
        return "bar_chart"
    if any(w in head for w in ("insight", "key principle", "fundamental", "remember", "rule of thumb", "in essence", "at its core", "definition", "means that")):
        return "statement"
    return "statement"


def render_scene_page(scene_obj, scene_data):
    pal = palette()
    layout = (scene_data.get("layout") or "auto").lower()
    if layout == "auto" or layout not in LAYOUT_RENDERERS:
        layout = auto_layout(scene_data)
    LAYOUT_RENDERERS.get(layout, render_statement)(scene_obj, scene_data, pal)


__SCENE_CLASSES__
'''


def _scene_class_block(class_name: str, index: int) -> str:
    return f'''
class {class_name}(Scene):
    def construct(self):
        render_scene_page(self, SCENES[{index}])
'''


def build_manim_module(*, storyboard: dict, output_path: Path) -> Path:
    theme = str(storyboard.get("color_theme") or "blue").strip().lower()
    storyboard["color_theme"] = theme if theme in {
        "blue", "violet", "green", "amber", "rose", "slate",
    } else "blue"
    scenes = storyboard["scenes"]
    total = len(scenes)
    for i, scene in enumerate(scenes, start=1):
        scene["scene_number"] = i
        scene["scene_total"] = total
    scene_classes = "\n".join(_scene_class_block(scene["class_name"], i) for i, scene in enumerate(scenes))
    module = (
        MODULE_TEMPLATE.replace("__STORY_JSON__", json.dumps(storyboard, indent=2))
        .replace("__SCENE_CLASSES__", scene_classes)
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(module, encoding="utf-8")
    return output_path
