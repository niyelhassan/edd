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
    "slate":  {"accent": "#38BDF8", "accent_2": "#64748B", "accent_soft": "#E0F2FE", "accent_mid": "#CBD5E1"},
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

CHROME_BOTTOM_Y = 1.95


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
    label = safe_text(_truncate(text, 28), font_size=font_size, weight=SEMIBOLD, color="#0369A1")
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
    """Header chrome: uppercase accent label + bold headline, left-aligned."""
    setup_frame(scene_obj, scene_data, pal)

    eyebrow_text = (TITLE or "Lesson").strip().upper()
    headline_text = (scene_data.get("headline") or "").strip()
    show_eyebrow = _is_distinct(eyebrow_text, headline_text)

    eyebrow = make_eyebrow_label(eyebrow_text, pal) if show_eyebrow else None
    headline = safe_text(
        headline_text or " ", font_size=42, weight=SEMIBOLD,
        color=pal["ink"], width=11.0, wrap=46,
    )

    parts = [m for m in (eyebrow, headline) if m is not None]
    header = VGroup(*parts)
    if len(parts) > 1:
        header.arrange(DOWN, buff=0.22, aligned_edge=LEFT)
    header.to_edge(UP, buff=0.62).to_edge(LEFT, buff=0.90)

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
    headline = safe_text(title, font_size=66, weight=SEMIBOLD, color=pal["ink"], width=11.2, wrap=24)
    subtitle = (
        safe_text(subtitle_text, font_size=23, color=pal["muted"], width=8.8, wrap=44)
        if subtitle_text else None
    )
    series = make_eyebrow_label(eyebrow_text, pal, color=pal["light"], font_size=13)
    left_rule = Rectangle(height=0.018, width=0.34, stroke_width=0, fill_color=pal["soft"], fill_opacity=1)
    right_rule = left_rule.copy()
    footer = VGroup(left_rule, series, right_rule).arrange(RIGHT, buff=0.22)

    parts = [accent_line, headline] + ([subtitle] if subtitle is not None else []) + [footer]
    main_block = VGroup(*parts).arrange(DOWN, buff=0.42).move_to(UP * 0.05)
    for mob in (headline, subtitle, footer):
        if mob is not None:
            mob.move_to([0, mob.get_center()[1], 0])
    footer.shift(DOWN * 0.25)

    scene_obj.play(GrowFromCenter(accent_line), run_time=0.35)
    scene_obj.play(Write(headline), run_time=1.0)
    if subtitle is not None:
        scene_obj.play(FadeIn(subtitle, shift=UP * 0.08), run_time=0.45)
    scene_obj.play(FadeIn(footer, shift=UP * 0.08), run_time=0.35)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 8.0), 2.5)


def render_summary(scene_obj, scene_data, pal):
    """Key takeaways: bold accent statement + clean bullet points."""
    add_top_bar(scene_obj, scene_data, pal)

    headline = scene_data.get("headline", "")
    takeaway = (scene_data.get("takeaway") or "").strip()
    if not _is_distinct(takeaway, headline):
        takeaway = (STORY.get("closing_takeaway") or "").strip()

    bullets, seen = [], {_norm(headline), _norm(takeaway)}
    for b in (scene_data.get("key_points") or []):
        n = _norm(b)
        if n and n not in seen:
            seen.add(n); bullets.append(b)
        if len(bullets) >= 3:
            break

    accent_top = Rectangle(
        height=0.035, width=1.2, stroke_width=0,
        fill_color=pal["accent"], fill_opacity=1,
    )
    big = safe_text(
        takeaway or "Key takeaway", font_size=38, weight=SEMIBOLD,
        color=pal["ink"], width=11.0, wrap=40,
    )

    divider = Line(LEFT * 5.5, RIGHT * 5.5, color=pal["soft"], stroke_width=1.5)

    rows = VGroup()
    for line in bullets:
        marker = Dot(radius=0.08, color=pal["accent"], fill_opacity=1)
        text = safe_text(line, font_size=21, color=pal["ink"], width=10.0, wrap=66)
        row = VGroup(marker, text).arrange(RIGHT, buff=0.30, aligned_edge=UP)
        marker.shift(DOWN * 0.05)
        rows.add(row)
    if len(rows):
        rows.arrange(DOWN, buff=0.34, aligned_edge=LEFT)

    parts = [accent_top, big] + ([divider, rows] if len(rows) else [])
    body = VGroup(*parts).arrange(DOWN, buff=0.38, aligned_edge=LEFT)
    place_body(body, top=CHROME_BOTTOM_Y - 0.35, center_x=-0.3, max_height=4.8, max_width=11.5)

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
    thanks = safe_text("Thanks", font_size=76, weight=SEMIBOLD, color=pal["ink"], width=11.5, wrap=24)
    accent_line = Rectangle(height=0.035, width=0.70, stroke_width=0, fill_color=pal["accent"], fill_opacity=1)
    parts = [label, thanks, accent_line]
    main_block = VGroup(*parts).arrange(DOWN, buff=0.40).move_to(ORIGIN)

    scene_obj.play(FadeIn(label, shift=DOWN * 0.12), run_time=0.35)
    scene_obj.play(Write(thanks), run_time=1.0)
    scene_obj.play(GrowFromCenter(accent_line), run_time=0.25)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 5.0), 2.05)


# ---- content layouts ----

def render_bullets(scene_obj, scene_data, pal):
    add_top_bar(scene_obj, scene_data, pal)
    headline = scene_data.get("headline", "")
    hook = (scene_data.get("hook") or "").strip()
    if not _is_distinct(hook, headline):
        hook = (scene_data.get("takeaway") or "").strip()
        if not _is_distinct(hook, headline):
            hook = ""

    raw = scene_data.get("key_points") or scene_data.get("visual_items") or []
    bullets, seen = [], {_norm(headline), _norm(hook)}
    for b in raw:
        n = _norm(b)
        if n and n not in seen:
            seen.add(n); bullets.append(b)
        if len(bullets) >= 3:
            break

    hook_text = (
        safe_text(hook, font_size=26, weight=SEMIBOLD, color=pal["ink"], width=10.5, wrap=56)
        if hook else None
    )

    rows = VGroup()
    for line in bullets:
        marker = Dot(radius=0.09, color=pal["accent"], fill_opacity=1)
        text = safe_text(line, font_size=22, color=pal["ink"], width=9.6, wrap=60)
        row = VGroup(marker, text).arrange(RIGHT, buff=0.36, aligned_edge=UP)
        marker.shift(DOWN * 0.06)
        rows.add(row)
    if len(rows):
        rows.arrange(DOWN, buff=0.46, aligned_edge=LEFT)

    parts = [m for m in (hook_text, rows) if m is not None and (not isinstance(m, VGroup) or len(m))]
    body = VGroup(*parts).arrange(DOWN, buff=0.52, aligned_edge=LEFT)
    accent_rule = Rectangle(
        height=max(body.height, 3.1), width=0.045, stroke_width=0,
        fill_color=pal["accent"], fill_opacity=1,
    )
    body_with_rule = VGroup(accent_rule, body).arrange(RIGHT, buff=0.50, aligned_edge=UP)
    place_body(body_with_rule, top=CHROME_BOTTOM_Y - 0.5, center_x=-0.25, max_height=5.0, max_width=11.0)

    if hook_text is not None:
        scene_obj.play(FadeIn(hook_text, shift=UP * 0.1), run_time=0.4)
    scene_obj.play(GrowFromEdge(accent_rule, UP), run_time=0.35)
    for row in rows:
        scene_obj.play(FadeIn(row[0], scale=0.5), FadeIn(row[1], shift=RIGHT * 0.1), run_time=0.35)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 12.0), 1.0 + 0.4 * (len(rows) + 1))


def render_equation(scene_obj, scene_data, pal):
    """Equation card with component labels and supporting definitions."""
    add_top_bar(scene_obj, scene_data, pal)

    expr_list = [e for e in (scene_data.get("equations") or []) if e]
    primary = expr_list[0] if expr_list else None
    secondary = expr_list[1] if len(expr_list) > 1 else None

    eq_main = safe_math(primary, color=pal["ink"], font_size=60, max_width=9.8) if primary else None
    eq_secondary = safe_math(secondary, color=pal["muted"], font_size=38, max_width=8.8) if secondary else None
    if eq_main is None:
        eq_main = safe_text(
            scene_data.get("hook") or scene_data.get("headline") or "Idea",
            font_size=42, weight=BOLD, color=pal["ink"], width=9.6, wrap=22,
        )

    eq_block_parts = [eq_main] + ([eq_secondary] if eq_secondary is not None else [])
    eq_block = VGroup(*eq_block_parts).arrange(DOWN, buff=0.40)
    card_w = max(eq_block.width + 1.7, 6.6)
    card_h = eq_block.height + 1.15
    eq_card = make_card(card_w, card_h, pal, radius=0.14, stroke_width=1.2)
    accent_rule = Rectangle(
        height=card_h, width=0.07, stroke_width=0,
        fill_color=pal["accent"], fill_opacity=1,
    ).align_to(eq_card, LEFT).move_to(eq_card.get_left() + RIGHT * 0.035)
    eq_block.move_to(eq_card)
    eq_panel = VGroup(eq_card, accent_rule, eq_block)

    component_terms = [t for t in (scene_data.get("highlight_terms") or []) if t][:4]
    definitions = [p for p in (scene_data.get("key_points") or []) if p][:4]
    chips = VGroup()
    for i, term in enumerate(component_terms):
        label = make_tag(term, pal, font_size=14)
        if i < len(definitions):
            detail = safe_text(definitions[i], font_size=14, color=pal["muted"], width=2.35, height=0.58, wrap=24)
            chip = VGroup(label, detail).arrange(DOWN, buff=0.10)
        else:
            chip = label
        chips.add(chip)
    if len(chips):
        chips.arrange_in_grid(rows=1 if len(chips) <= 2 else 2, buff=(0.24, 0.20))

    note_text = ""
    for cand in [scene_data.get("takeaway"), scene_data.get("hook")]:
        if _is_distinct(cand, scene_data.get("headline"), primary, secondary):
            note_text = cand
            break
    note = safe_text(note_text, font_size=17, color=pal["muted"], width=9.2, wrap=60) if note_text else None

    layout_parts = [eq_panel] + ([chips] if len(chips) else []) + ([note] if note is not None else [])
    body = VGroup(*layout_parts).arrange(DOWN, buff=0.42)
    place_body(body, top=CHROME_BOTTOM_Y - 0.5, max_height=4.8, max_width=11.5)

    scene_obj.play(FadeIn(eq_card, shift=UP * 0.05), GrowFromEdge(accent_rule, UP), run_time=0.45)
    scene_obj.play(Write(eq_main), run_time=1.2)
    if eq_secondary is not None:
        scene_obj.play(Write(eq_secondary), run_time=0.7)
    if len(chips):
        scene_obj.play(LaggedStart(*[FadeIn(c, shift=UP * 0.08) for c in chips], lag_ratio=0.15), run_time=0.6)
    if note is not None:
        scene_obj.play(FadeIn(note, shift=UP * 0.06), run_time=0.3)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 3.25)


def render_step_derivation(scene_obj, scene_data, pal):
    """Stacked derivation steps with room for longer multi-line work."""
    add_top_bar(scene_obj, scene_data, pal)

    equations = [e for e in (scene_data.get("equations") or []) if e][:6]
    if not equations:
        equations = [scene_data.get("headline") or "Start", scene_data.get("takeaway") or "Result"]
    labels = _labels(scene_data, "visual_items", "highlight_terms", limit=len(equations))

    rows = VGroup()
    for i, expr in enumerate(equations):
        step_label = safe_text(
            labels[i] if i < len(labels) else ("Given" if i == 0 else f"Step {i + 1}"),
            font_size=12,
            weight=SEMIBOLD,
            color=pal["accent"] if i == 0 else pal["muted"],
            width=1.55,
            wrap=13,
        )
        sep = Rectangle(
            height=0.028, width=0.26, stroke_width=0,
            fill_color=pal["accent"] if i == 0 else pal["soft"],
            fill_opacity=1,
        )
        label_col = VGroup(step_label, sep).arrange(DOWN, buff=0.10, aligned_edge=LEFT)
        math_obj = safe_math(expr, color=pal["ink"], font_size=35 if len(equations) > 4 else 39, max_width=7.7, max_height=0.72)
        row = VGroup(label_col, math_obj).arrange(RIGHT, buff=0.44, aligned_edge=DOWN)
        rows.add(row)
    rows.arrange(DOWN, buff=0.24 if len(rows) > 4 else 0.32, aligned_edge=LEFT)

    connector = Rectangle(
        height=rows.height,
        width=0.05,
        stroke_width=0,
        fill_color=pal["accent_soft"],
        fill_opacity=1,
    )
    accent_cap = Rectangle(
        height=0.26,
        width=0.05,
        stroke_width=0,
        fill_color=pal["accent"],
        fill_opacity=1,
    ).align_to(connector, UP)
    connector_group = VGroup(connector, accent_cap)

    content = VGroup(connector_group, rows).arrange(RIGHT, buff=0.44, aligned_edge=UP)
    card = make_card(content.width + 1.0, content.height + 0.62, pal, radius=0.14, stroke_width=1.2)
    content.move_to(card)
    panel = VGroup(card, content)
    note_text = ""
    for cand in [scene_data.get("takeaway"), scene_data.get("hook")]:
        if _is_distinct(cand, scene_data.get("headline"), *equations):
            note_text = cand
            break
    note = safe_text(note_text, font_size=16, color=pal["muted"], width=9.6, wrap=66) if note_text else None
    body = VGroup(panel, note).arrange(DOWN, buff=0.26) if note is not None else panel
    place_body(body, top=CHROME_BOTTOM_Y - 0.35, max_height=5.35, max_width=11.5)

    scene_obj.play(FadeIn(card, shift=UP * 0.05), GrowFromEdge(connector, UP), run_time=0.45)
    scene_obj.play(FadeIn(accent_cap), run_time=0.20)
    for row in rows:
        scene_obj.play(FadeIn(row[0], shift=RIGHT * 0.10), Write(row[1]), run_time=0.55)
    if note is not None:
        scene_obj.play(FadeIn(note, shift=UP * 0.06), run_time=0.25)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 0.95 + 0.55 * len(rows))


def render_distribution(scene_obj, scene_data, pal):
    """Bell curve with shaded tail and a concise interpretation line."""
    add_top_bar(scene_obj, scene_data, pal)

    axes = Axes(
        x_range=[-3.5, 3.5, 1], y_range=[0, 0.5, 0.1],
        x_length=8.6, y_length=3.6,
        axis_config={"color": pal["muted"], "stroke_width": 2}, tips=False,
    ).move_to([0, -0.35, 0])

    def normal(x): return math.exp(-x * x / 2) / math.sqrt(2 * math.pi)

    curve = axes.plot(normal, x_range=[-3.4, 3.4], color=pal["ink"], stroke_width=4)
    cutoff = 1.65
    shade = axes.get_area(curve, x_range=[cutoff, 3.4], color=pal["accent"], opacity=0.50)
    threshold = DashedLine(
        axes.c2p(cutoff, 0), axes.c2p(cutoff, normal(cutoff)),
        color=pal["accent"], dash_length=0.12, stroke_width=3,
    )

    terms = [t for t in (scene_data.get("highlight_terms") or []) if t]
    tail_label = safe_text(
        (terms[-1] if terms else "Tail area"),
        font_size=18, weight=SEMIBOLD, color=pal["accent"], width=2.6, wrap=22,
    )
    tail_label.next_to(shade, RIGHT, buff=0.3)
    x_label = safe_text(
        (terms[0] if terms else "test statistic"),
        font_size=18, color=pal["muted"], width=2.6, wrap=22,
    )
    x_label.next_to(axes.x_axis, RIGHT, buff=0.18)

    note_text = ""
    for cand in [scene_data.get("takeaway"), scene_data.get("hook"), *(scene_data.get("key_points") or [])]:
        if _is_distinct(cand, scene_data.get("headline"), *terms):
            note_text = cand
            break
    note = safe_text(note_text, font_size=17, color=pal["muted"], width=8.6, wrap=62) if note_text else None
    if note is not None:
        note.next_to(axes, DOWN, buff=0.26)

    scene_obj.play(Create(axes), run_time=0.5)
    scene_obj.play(Create(curve), run_time=1.2)
    scene_obj.play(FadeIn(x_label, shift=RIGHT * 0.1), run_time=0.35)
    scene_obj.play(Create(threshold), run_time=0.35)
    scene_obj.play(FadeIn(shade, shift=RIGHT * 0.06), FadeIn(tail_label, shift=LEFT * 0.06), run_time=0.6)
    if note is not None:
        scene_obj.play(FadeIn(note, shift=UP * 0.06), run_time=0.3)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 3.3)


def render_axes_plot(scene_obj, scene_data, pal):
    """Generic XY function plot with readable labels and explanatory context."""
    add_top_bar(scene_obj, scene_data, pal)

    axes = Axes(
        x_range=[-4, 4, 1], y_range=[-2.5, 2.5, 1],
        x_length=8.2, y_length=3.55,
        axis_config={"color": pal["muted"], "stroke_width": 2}, tips=False,
    ).move_to([0, -0.35, 0])

    items = [s for s in (scene_data.get("highlight_terms") or []) if s]
    x_lab = safe_text(items[0] if items else "x", font_size=16, color=pal["muted"], width=2.2, wrap=18)
    x_lab.next_to(axes.x_axis, DOWN, buff=0.28).align_to(axes.x_axis, RIGHT).shift(LEFT * 0.20)
    y_lab = safe_text(items[1] if len(items) > 1 else "y", font_size=16, color=pal["muted"], width=2.0, wrap=16)
    y_lab.next_to(axes.y_axis, LEFT, buff=0.22).align_to(axes.y_axis, UP).shift(DOWN * 0.15)

    blob = ((scene_data.get("headline") or "") + " " + (scene_data.get("hook") or "")).lower()
    if any(w in blob for w in ("exp", "growth", "decay")):
        fn = lambda x: 1.6 * math.exp(0.5 * x) / math.exp(2.0)
    elif any(w in blob for w in ("sin", "wave", "oscill", "period", "frequency")):
        fn = lambda x: 2.0 * math.sin(1.4 * x)
    elif "log" in blob:
        fn = lambda x: math.log(max(x + 4.1, 0.05))
    elif any(w in blob for w in ("quad", "parab", "square")):
        fn = lambda x: 0.4 * x * x - 1.5
    else:
        fn = lambda x: 0.5 * x + 0.4 * math.sin(1.6 * x)

    curve = axes.plot(fn, x_range=[-3.8, 3.8], color=pal["accent"], stroke_width=4)

    markers = VGroup()
    points = [s for s in (scene_data.get("visual_items") or scene_data.get("key_points") or []) if s][:3]
    sample_xs = [-2.4, 0.4, 2.2]
    for i, label_str in enumerate(points):
        x = sample_xs[i % 3]
        try:
            y = fn(x)
        except Exception:
            y = 0
        pt = Dot(axes.c2p(x, y), radius=0.10, color=pal["accent_2"])
        lab = safe_text(label_str, font_size=15, weight=SEMIBOLD, color=pal["ink"], width=2.45, height=0.55, wrap=20)
        direction = UR if i == 0 else (UL if i == 1 else DOWN)
        lab.next_to(pt, direction, buff=0.20)
        markers.add(pt, lab)

    note_text = ""
    for cand in [scene_data.get("takeaway"), scene_data.get("hook"), *(scene_data.get("key_points") or [])]:
        if _is_distinct(cand, scene_data.get("headline"), *items, *points):
            note_text = cand
            break
    note = safe_text(note_text, font_size=17, color=pal["muted"], width=8.7, wrap=62) if note_text else None
    if note is not None:
        note.next_to(axes, DOWN, buff=0.34)

    scene_obj.play(Create(axes), run_time=0.5)
    scene_obj.play(FadeIn(x_lab, shift=RIGHT * 0.1), FadeIn(y_lab, shift=UP * 0.1), run_time=0.3)
    scene_obj.play(Create(curve), run_time=1.2)
    if len(markers):
        scene_obj.play(LaggedStart(*[FadeIn(m, shift=UP * 0.1) for m in markers], lag_ratio=0.12), run_time=0.8)
    if note is not None:
        scene_obj.play(FadeIn(note, shift=UP * 0.06), run_time=0.3)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 3.1)


def render_line_chart(scene_obj, scene_data, pal):
    """Ordered trend line with summary, labels, and a clear final value."""
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
        y_length=3.15,
        axis_config={"color": pal["muted"], "stroke_width": 2},
        tips=False,
    ).move_to([0, -0.15, 0])

    coords = [axes.c2p(i, value) for i, (_, value) in enumerate(points)]
    segments = VGroup(*[Line(coords[i], coords[i + 1], color=pal["accent"], stroke_width=4) for i in range(len(coords) - 1)])
    dots = VGroup(*[Dot(coord, radius=0.09, color=pal["accent_2"]) for coord in coords])
    labels = VGroup()
    for i, (label, _value) in enumerate(points):
        labels.add(safe_text(label, font_size=14, weight=SEMIBOLD, color=pal["muted"], width=1.35, wrap=10)
                   .next_to(axes.c2p(i, low - pad), DOWN, buff=0.12))
    value_label = safe_text(
        f"{points[-1][1]:g}",
        font_size=20,
        weight=BOLD,
        color=pal["accent"],
        width=2.0,
    ).next_to(dots[-1], UR, buff=0.16)

    summary = safe_text(
        scene_data.get("takeaway") or scene_data.get("hook") or "The final point shows the direction of change.",
        font_size=18,
        color=pal["ink"],
        width=8.8,
        wrap=60,
    )
    summary.next_to(axes, UP, buff=0.22)
    note = safe_text(
        (scene_data.get("key_points") or ["Compare the slope, turning points, and final value."])[0],
        font_size=15,
        color=pal["muted"],
        width=8.6,
        wrap=62,
    ).next_to(axes, DOWN, buff=0.34)

    chart = VGroup(summary, axes, segments, dots, labels, value_label, note)
    place_body(chart, top=CHROME_BOTTOM_Y - 0.28, max_height=5.35, max_width=11.4)

    scene_obj.play(Create(axes), run_time=0.5)
    if len(segments):
        scene_obj.play(LaggedStart(*[Create(s) for s in segments], lag_ratio=0.16), run_time=1.0)
    scene_obj.play(FadeIn(dots, scale=0.8), FadeIn(labels, shift=UP * 0.05), run_time=0.55)
    scene_obj.play(FadeIn(value_label, shift=LEFT * 0.08), run_time=0.25)
    scene_obj.play(FadeIn(summary, shift=DOWN * 0.06), FadeIn(note, shift=UP * 0.06), run_time=0.35)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 2.65)


def render_comparison(scene_obj, scene_data, pal):
    """Side-by-side comparison cards with one softly highlighted side."""
    add_top_bar(scene_obj, scene_data, pal)

    items = [s for s in (scene_data.get("visual_items") or []) if s]
    points = [s for s in (scene_data.get("key_points") or []) if s]
    left_title = items[0] if items else "Approach A"
    right_title = items[1] if len(items) > 1 else "Approach B"

    def panel(label, lines, accent, highlighted=False):
        bg = make_card(
            5.3, 4.5, pal,
            fill=pal["accent_soft"] if highlighted else pal["panel"],
            stroke=pal["accent_mid"] if highlighted else pal["soft"],
            radius=0.14,
            stroke_width=1.35,
        )
        header_label = make_eyebrow_label(label, pal, color=accent, font_size=15)
        header_label.move_to([bg.get_center()[0], bg.get_top()[1] - 0.55, 0])

        rows = VGroup()
        for line in lines[:3]:
            dot = Dot(radius=0.07, color=accent)
            text = safe_text(line, font_size=18, color=pal["ink"], width=4.1, wrap=32)
            rows.add(VGroup(dot, text).arrange(RIGHT, buff=0.22, aligned_edge=UP))
        if len(rows):
            rows.arrange(DOWN, buff=0.34, aligned_edge=LEFT)
            rows.move_to(bg.get_center() + DOWN * 0.35)
        return VGroup(bg, header_label, rows)

    if len(points) >= 2:
        split = max(1, math.ceil(len(points) / 2))
        left_lines = points[:split][:3]
        right_lines = points[split:][:3] or points[:1]
    else:
        left_lines = points[:1] or [scene_data.get("hook") or left_title]
        right_lines = [scene_data.get("takeaway") or right_title]

    left = panel(left_title, left_lines, pal["muted"], highlighted=False)
    right = panel(right_title, right_lines, pal["accent"], highlighted=True)

    vs_bg = Circle(
        radius=0.32, stroke_width=1.2,
        color=pal["soft"], fill_color=pal["background"], fill_opacity=1,
    )
    vs_text = safe_text("vs", font_size=14, weight=SEMIBOLD, color=pal["light"]).move_to(vs_bg)
    vs_node = VGroup(vs_bg, vs_text)

    pair = VGroup(left, vs_node, right).arrange(RIGHT, buff=0.28)
    place_body(pair, top=CHROME_BOTTOM_Y - 0.3, max_height=5.2, max_width=11.5)

    scene_obj.play(FadeIn(left, shift=LEFT * 0.15), FadeIn(right, shift=RIGHT * 0.15), run_time=0.7)
    scene_obj.play(FadeIn(vs_node, scale=0.7), run_time=0.30)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 1.7)


def render_before_after(scene_obj, scene_data, pal):
    """Transformation cards with a strong before-to-after direction."""
    add_top_bar(scene_obj, scene_data, pal)

    items = _labels(scene_data, "visual_items", limit=2)
    before = items[0] if items else "Before"
    after = items[1] if len(items) > 1 else "After"
    points = _labels(scene_data, "key_points", "highlight_terms", limit=3)

    def state_card(title, subtitle, highlighted=False):
        bg = make_card(
            4.7,
            3.6,
            pal,
            fill=pal["accent_soft"] if highlighted else pal["panel"],
            stroke=pal["accent_mid"] if highlighted else pal["soft"],
            radius=0.14,
            stroke_width=1.35,
        )
        label = make_eyebrow_label(title, pal, color=pal["accent"] if highlighted else pal["muted"], font_size=14)
        label.move_to([bg.get_center()[0], bg.get_top()[1] - 0.48, 0])
        body = safe_text(subtitle, font_size=22, weight=SEMIBOLD, color=pal["ink"], width=3.75, height=1.35, wrap=22)
        body.move_to(bg.get_center() + DOWN * 0.05)
        return VGroup(bg, label, body)

    left = state_card("Before", before, highlighted=False)
    right = state_card("After", after, highlighted=True)
    arrow = Arrow(LEFT * 0.72, RIGHT * 0.72, color=pal["accent"], stroke_width=4, buff=0.05, tip_length=0.22)
    arrow_label = safe_text("changes", font_size=15, weight=SEMIBOLD, color=pal["muted"]).next_to(arrow, UP, buff=0.16)
    pair = VGroup(left, VGroup(arrow, arrow_label), right).arrange(RIGHT, buff=0.42)

    chips = VGroup(*[make_tag(point, pal, font_size=14) for point in points])
    if len(chips):
        chips.arrange(RIGHT, buff=0.24)
        body = VGroup(pair, chips).arrange(DOWN, buff=0.45)
    else:
        body = pair
    place_body(body, top=CHROME_BOTTOM_Y - 0.3, max_height=5.2, max_width=11.5)

    scene_obj.play(FadeIn(left, shift=LEFT * 0.15), run_time=0.45)
    scene_obj.play(Create(arrow), FadeIn(arrow_label), run_time=0.45)
    scene_obj.play(FadeIn(right, shift=RIGHT * 0.15), run_time=0.45)
    if len(chips):
        scene_obj.play(LaggedStart(*[FadeIn(c, shift=UP * 0.06) for c in chips], lag_ratio=0.12), run_time=0.5)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 2.0)


def render_flow(scene_obj, scene_data, pal):
    """Numbered process nodes with wrapped text boxes below each stage."""
    add_top_bar(scene_obj, scene_data, pal)

    items = [s for s in (scene_data.get("visual_items") or scene_data.get("key_points") or []) if s][:4]
    if not items:
        items = [scene_data.get("headline", "step")]
    if len(items) == 1:
        items = items + [(scene_data.get("highlight_terms") or [items[0]])[0]]
    n = len(items)

    spacing = 3.0 if n <= 3 else 2.5
    total_width = (n - 1) * spacing
    start_x = -total_width / 2

    nodes = VGroup()
    boxes = VGroup()
    connectors = VGroup()
    detail_lines = [s for s in (scene_data.get("key_points") or []) if s]
    for i, item in enumerate(items):
        x = start_x + i * spacing
        is_first = i == 0
        is_last = i == n - 1
        bg = Circle(
            radius=0.44,
            color=pal["accent"],
            stroke_width=2.0 if is_first or is_last else 1.6,
            fill_color=pal["accent"] if is_first else (pal["accent_mid"] if is_last else pal["accent_soft"]),
            fill_opacity=1,
        )
        dot = Dot(
            radius=0.12,
            color="#FFFFFF" if is_first else pal["accent"],
            fill_opacity=1,
        ).move_to(bg)
        node = VGroup(bg, dot).move_to([x, 0.35, 0])
        nodes.add(node)
        title = safe_text(item, font_size=15, weight=SEMIBOLD, color=pal["ink"], width=spacing - 0.55, height=0.40, wrap=16)
        detail_source = detail_lines[i] if i < len(detail_lines) and _is_distinct(detail_lines[i], item) else ""
        detail = safe_text(detail_source, font_size=12, color=pal["muted"], width=spacing - 0.50, height=0.58, wrap=24)
        card = make_card(spacing - 0.30, 1.12, pal, radius=0.12, stroke_width=1.0)
        text = VGroup(title, detail).arrange(DOWN, buff=0.08)
        box = VGroup(card, text.move_to(card)).next_to(node, DOWN, buff=0.32)
        boxes.add(box)
        if i > 0:
            prev_node = nodes[i - 1]
            arrow = Arrow(
                prev_node[0].get_right(), bg.get_left(),
                color=pal["soft"], stroke_width=2.4, buff=0.05,
                tip_length=0.17, max_tip_length_to_length_ratio=0.30,
            )
            connectors.add(arrow)

    pipeline = VGroup(connectors, nodes, boxes)
    pipeline.move_to(ORIGIN + DOWN * 0.10)
    place_body(pipeline, top=CHROME_BOTTOM_Y - 0.25, max_height=5.1, max_width=11.5)

    scene_obj.play(LaggedStart(*[FadeIn(node, scale=0.7) for node in nodes], lag_ratio=0.15), run_time=0.9)
    if len(connectors):
        scene_obj.play(LaggedStart(*[Create(c) for c in connectors], lag_ratio=0.15), run_time=0.7)
    scene_obj.play(LaggedStart(*[FadeIn(b, shift=UP * 0.1) for b in boxes], lag_ratio=0.12), run_time=0.6)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 2.5)


def render_timeline(scene_obj, scene_data, pal):
    """Horizontal milestone sequence with centered vertical placement and note."""
    add_top_bar(scene_obj, scene_data, pal)

    items = _labels(scene_data, "visual_items", "key_points", limit=5)
    if len(items) < 2:
        items = [scene_data.get("headline", "Start"), scene_data.get("takeaway", "Finish") or "Finish"]
    n = len(items)
    width = 9.4
    y = 0.10
    line = Line(LEFT * (width / 2), RIGHT * (width / 2), color=pal["soft"], stroke_width=3).move_to([0, y, 0])

    dots = VGroup()
    labels = VGroup()
    for i, item in enumerate(items):
        x = -width / 2 + i * (width / max(n - 1, 1))
        dot = Circle(
            radius=0.16,
            color=pal["accent"],
            stroke_width=2,
            fill_color=pal["accent"] if i == 0 else pal["accent_soft"],
            fill_opacity=1,
        ).move_to([x, y, 0])
        dots.add(dot)
        label = safe_text(item, font_size=17, weight=SEMIBOLD, color=pal["ink"], width=2.0, height=0.8, wrap=16)
        direction = UP if i % 2 == 0 else DOWN
        label.next_to(dot, direction, buff=0.34)
        labels.add(label)

    note_text = ""
    for cand in [scene_data.get("takeaway"), scene_data.get("hook")]:
        if _is_distinct(cand, scene_data.get("headline"), *items):
            note_text = cand
            break
    note = safe_text(note_text, font_size=16, color=pal["muted"], width=9.3, wrap=64) if note_text else None
    if note is not None:
        note.next_to(VGroup(line, dots, labels), DOWN, buff=0.42)
    body = VGroup(line, dots, labels, note) if note is not None else VGroup(line, dots, labels)
    place_body(body, top=CHROME_BOTTOM_Y - 0.18, max_height=5.15, max_width=11.5)

    scene_obj.play(Create(line), run_time=0.5)
    scene_obj.play(LaggedStart(*[FadeIn(d, scale=0.75) for d in dots], lag_ratio=0.14), run_time=0.8)
    scene_obj.play(LaggedStart(*[FadeIn(l, shift=UP * 0.08) for l in labels], lag_ratio=0.12), run_time=0.7)
    if note is not None:
        scene_obj.play(FadeIn(note, shift=UP * 0.06), run_time=0.3)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 2.7)


def render_bar_chart(scene_obj, scene_data, pal):
    """Rounded bars with a compact explanation and value labels."""
    add_top_bar(scene_obj, scene_data, pal)

    points = _data_points(scene_data, limit=4)
    items = [label for label, _value in points]
    raw_values = [max(value, 0.0) for _label, value in points]
    max_raw = max(raw_values) if raw_values else 1.0
    if max_raw <= 0:
        max_raw = 1.0
    values = [0.28 + 0.72 * (value / max_raw) for value in raw_values]
    max_val = max(values)

    base_y, max_h = -2.05, 3.0
    n, w, spacing = len(items), 0.92, 0.55
    total_w = n * w + (n - 1) * spacing
    start_x = -total_w / 2 + w / 2

    baseline = Line(
        LEFT * (total_w / 2 + 0.6), RIGHT * (total_w / 2 + 0.6),
        color=pal["soft"], stroke_width=2,
    ).move_to([0, base_y, 0])

    bars, labels, value_labels = VGroup(), VGroup(), VGroup()
    for i, (item, v) in enumerate(zip(items, values)):
        is_top = v >= max_val - 0.001
        color = pal["accent"] if is_top else pal["accent_2"]
        opacity = 1.0 if is_top else 0.85
        bar = RoundedRectangle(
            corner_radius=0.10, width=w, height=v * max_h,
            stroke_width=0, fill_color=color, fill_opacity=opacity,
        )
        bar.move_to([start_x + i * (w + spacing), base_y + (v * max_h) / 2, 0])
        bars.add(bar)
        labels.add(safe_text(item, font_size=15, weight=SEMIBOLD, color=pal["ink"], width=w + 0.6, wrap=14)
                   .next_to(bar, DOWN, buff=0.22))
        value_labels.add(safe_text(f"{raw_values[i]:g}", font_size=18, weight=BOLD, color=color)
                         .next_to(bar, UP, buff=0.16))

    summary = safe_text(
        scene_data.get("takeaway") or scene_data.get("hook") or "Compare the tallest bar against the rest.",
        font_size=18,
        color=pal["ink"],
        width=8.8,
        wrap=58,
    )
    summary.next_to(VGroup(bars, value_labels), UP, buff=0.32)
    note = safe_text(
        (scene_data.get("key_points") or ["Magnitude is easiest to read from bar height."])[0],
        font_size=15,
        color=pal["muted"],
        width=8.4,
        wrap=60,
    ).next_to(labels, DOWN, buff=0.30)

    chart = VGroup(summary, baseline, bars, labels, value_labels, note)
    place_body(chart, top=CHROME_BOTTOM_Y - 0.28, max_height=5.35, max_width=11.0)

    scene_obj.play(Create(baseline), run_time=0.4)
    scene_obj.play(LaggedStart(*[GrowFromEdge(b, DOWN) for b in bars], lag_ratio=0.12), run_time=1.1)
    scene_obj.play(LaggedStart(*[FadeIn(l, shift=UP * 0.05) for l in labels], lag_ratio=0.1), run_time=0.5)
    scene_obj.play(LaggedStart(*[FadeIn(v) for v in value_labels], lag_ratio=0.08), run_time=0.4)
    scene_obj.play(FadeIn(summary, shift=DOWN * 0.06), FadeIn(note, shift=UP * 0.06), run_time=0.35)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 2.75)


def render_proportional_chart(scene_obj, scene_data, pal):
    """Pie chart for parts-of-a-whole explanations."""
    add_top_bar(scene_obj, scene_data, pal)

    points = _data_points(scene_data, limit=5)
    positive = [(label, max(value, 0.0)) for label, value in points]
    total = sum(value for _label, value in positive) or len(positive) or 1
    colors = [pal["accent"], pal["accent_2"], pal["accent_mid"], pal["soft"], pal["muted"]]

    start_angle = PI / 2
    radius = 1.45
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
            color=pal["panel"],
            stroke_width=2,
            fill_color=color,
            fill_opacity=1,
        )
        start_angle -= angle
        slices.add(sector)
        swatch = Square(side_length=0.16, stroke_width=0, fill_color=color, fill_opacity=1)
        text = safe_text(f"{label} {frac * 100:.0f}%", font_size=15, weight=SEMIBOLD, color=pal["ink"], width=2.6, wrap=20)
        legend.add(VGroup(swatch, text).arrange(RIGHT, buff=0.16, aligned_edge=DOWN))
    if len(legend):
        legend.arrange(DOWN, buff=0.22, aligned_edge=LEFT)
    title = safe_text(scene_data.get("takeaway") or "Parts of the whole", font_size=23, weight=SEMIBOLD, color=pal["ink"], width=9.0, wrap=44)
    note = safe_text(scene_data.get("hook") or "Each slice shows its share of the total.", font_size=15, color=pal["muted"], width=8.5, wrap=60)
    chart_row = VGroup(slices, legend).arrange(RIGHT, buff=0.75)
    frame = make_card(10.4, 4.45, pal, radius=0.14, stroke_width=1.2)
    content = VGroup(title, chart_row, note).arrange(DOWN, buff=0.34)
    content.move_to(frame)
    body = VGroup(frame, content)
    place_body(body, top=CHROME_BOTTOM_Y - 0.30, max_height=5.25, max_width=11.5)

    scene_obj.play(FadeIn(frame, shift=UP * 0.05), FadeIn(title), run_time=0.45)
    scene_obj.play(LaggedStart(*[FadeIn(s, scale=0.92) for s in slices], lag_ratio=0.08), run_time=0.9)
    if len(legend):
        scene_obj.play(LaggedStart(*[FadeIn(row, shift=UP * 0.05) for row in legend], lag_ratio=0.1), run_time=0.55)
    scene_obj.play(FadeIn(note, shift=UP * 0.06), run_time=0.25)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 2.45)


def render_cause_effect(scene_obj, scene_data, pal):
    """One cause branching into two to four effects."""
    add_top_bar(scene_obj, scene_data, pal)

    cause = (_labels(scene_data, "highlight_terms", limit=1) or [scene_data.get("headline", "Cause")])[0]
    effects = _labels(scene_data, "visual_items", "key_points", limit=4)
    if not effects:
        effects = [scene_data.get("takeaway", "Effect") or "Effect"]

    cause_card = make_card(3.0, 1.35, pal, fill=pal["accent_soft"], stroke=pal["accent_mid"])
    cause_text = safe_text(cause, font_size=23, weight=BOLD, color=pal["ink"], width=2.35, height=0.9, wrap=18)
    cause_node = VGroup(cause_card, cause_text.move_to(cause_card)).move_to(LEFT * 3.4)

    effect_nodes = VGroup()
    arrows = VGroup()
    y_positions = [1.35, 0.45, -0.45, -1.35] if len(effects) > 3 else [0.95, 0.0, -0.95]
    if len(effects) == 1:
        y_positions = [0.0]
    for i, effect in enumerate(effects):
        bg = make_card(3.6, 0.82, pal, radius=0.14, stroke_width=1.2)
        label = safe_text(effect, font_size=17, weight=SEMIBOLD, color=pal["ink"], width=3.0, height=0.55, wrap=24)
        node = VGroup(bg, label.move_to(bg)).move_to([2.7, y_positions[i], 0])
        effect_nodes.add(node)
        arrows.add(Arrow(cause_node.get_right(), node.get_left(), color=pal["soft"], stroke_width=2.4, buff=0.12, tip_length=0.16))

    body = VGroup(cause_node, arrows, effect_nodes)
    body.move_to(ORIGIN)
    place_body(body, top=CHROME_BOTTOM_Y - 0.12, max_height=5.3, max_width=11.5)

    scene_obj.play(FadeIn(cause_node, scale=0.9), run_time=0.45)
    scene_obj.play(LaggedStart(*[Create(a) for a in arrows], lag_ratio=0.12), run_time=0.75)
    scene_obj.play(LaggedStart(*[FadeIn(n, shift=LEFT * 0.12) for n in effect_nodes], lag_ratio=0.12), run_time=0.75)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 2.2)


def render_network(scene_obj, scene_data, pal):
    """Center node with title/body text and formatted child nodes."""
    add_top_bar(scene_obj, scene_data, pal)

    child_titles = _labels(scene_data, "visual_items", limit=4)
    if len(child_titles) < 2:
        child_titles = _labels(scene_data, "highlight_terms", "key_points", limit=4)
    if len(child_titles) < 2:
        child_titles = ["Input", "Output"]
    child_details = [s for s in (scene_data.get("key_points") or []) if s]
    center_title = (_labels(scene_data, "highlight_terms", limit=1) or [scene_data.get("headline", "Core")])[0]
    center_body = scene_data.get("hook") or scene_data.get("takeaway") or ""

    n = len(child_titles)
    radius = 2.55
    nodes = VGroup()
    center_bg = make_card(2.7, 1.42, pal, fill=pal["accent_soft"], stroke=pal["accent_mid"], radius=0.16, stroke_width=1.5)
    center_text = VGroup(
        safe_text(center_title, font_size=17, weight=BOLD, color=pal["ink"], width=2.25, height=0.40, wrap=18),
        safe_text(center_body, font_size=12, color=pal["muted"], width=2.22, height=0.54, wrap=24),
    ).arrange(DOWN, buff=0.08)
    center_node = VGroup(center_bg, center_text.move_to(center_bg))
    nodes.add(center_node)

    for i, title in enumerate(child_titles):
        angle = PI / 2 + i * TAU / n
        pos = np.array([math.cos(angle) * radius, math.sin(angle) * radius - 0.10, 0])
        bg = make_card(2.35, 1.02, pal, radius=0.14, stroke_width=1.15)
        detail_source = child_details[i] if i < len(child_details) and _is_distinct(child_details[i], title) else ""
        text = VGroup(
            safe_text(title, font_size=14, weight=SEMIBOLD, color=pal["ink"], width=1.95, height=0.34, wrap=16),
            safe_text(detail_source, font_size=11, color=pal["muted"], width=1.95, height=0.42, wrap=22),
        ).arrange(DOWN, buff=0.06)
        nodes.add(VGroup(bg, text.move_to(bg)).move_to(pos))

    edges = VGroup()
    for i in range(1, len(nodes)):
        edges.add(Line(nodes[0].get_center(), nodes[i].get_center(), color=pal["soft"], stroke_width=2.0))

    body = VGroup(edges, nodes)
    place_body(body, top=CHROME_BOTTOM_Y - 0.22, max_height=5.35, max_width=11.2)

    scene_obj.play(LaggedStart(*[Create(e) for e in edges], lag_ratio=0.08), run_time=0.9)
    scene_obj.play(LaggedStart(*[FadeIn(n, scale=0.78) for n in nodes], lag_ratio=0.1), run_time=0.85)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 2.1)


def render_statement(scene_obj, scene_data, pal):
    """Full-frame bold statement: left accent bar, large text, soft supporting context."""
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

    big = safe_text(
        statement_text, font_size=45, weight=SEMIBOLD,
        color=pal["ink"], width=10.0, wrap=34,
    )

    context_text = ""
    for cand in (scene_data.get("key_points") or []):
        cand = str(cand or "").strip()
        if cand and _is_distinct(cand, statement_text):
            context_text = cand
            break

    sub = (
        safe_text(context_text, font_size=21, color=pal["muted"], width=9.5, wrap=58)
        if context_text else None
    )

    text_parts = [eyebrow, big] + ([sub] if sub else [])
    text_block = VGroup(*text_parts).arrange(DOWN, buff=0.32, aligned_edge=LEFT)

    bar_height = max(text_block.height + 0.50, 2.0)
    left_bar = Rectangle(
        height=bar_height, width=0.065, stroke_width=0,
        fill_color=pal["accent"], fill_opacity=1,
    )

    full = VGroup(left_bar, text_block).arrange(RIGHT, buff=0.54, aligned_edge=UP)
    full.move_to(ORIGIN + UP * 0.05)

    if full.width > 11.5:
        full.scale_to_fit_width(11.5)
    if full.height > 6.5:
        full.scale_to_fit_height(6.5)

    scene_obj.play(GrowFromEdge(left_bar, UP), run_time=0.35)
    scene_obj.play(FadeIn(eyebrow, shift=DOWN * 0.08), run_time=0.28)
    scene_obj.play(Write(big, run_time=0.95))
    if sub:
        scene_obj.play(FadeIn(sub, shift=UP * 0.08), run_time=0.40)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 12.0), 2.1)


# ---- dispatcher ----
LAYOUT_RENDERERS = {
    "title_card": render_title_card,
    "summary": render_summary,
    "thanks": render_thanks,
    "bullets": render_bullets,
    "statement": render_statement,
    "equation": render_equation,
    "step_derivation": render_step_derivation,
    "distribution": render_distribution,
    "axes_plot": render_axes_plot,
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
    if any(w in head for w in ("p-value", "p value", "distribution", "bell curve", "gaussian", "normal distribution", "probability density")):
        return "distribution"
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
    if any(w in head for w in ("vs ", " versus ", "compare", "comparison", "before vs after")):
        return "comparison"
    if any(w in head for w in ("step", "process", "pipeline", "workflow", "stage", "first then")):
        return "flow"
    if any(w in head for w in ("axis", "axes", "plot", "graph of", "function", "growth", "decay", "exponential", "wave", "sine", "oscill")):
        return "axes_plot"
    if any(w in head for w in ("bar chart", "ranking", "share", "percentage", "magnitude")):
        return "bar_chart"
    if any(w in head for w in ("insight", "key principle", "fundamental", "remember", "rule of thumb", "in essence", "at its core")):
        return "statement"
    if any(w in head for w in ("idea", "concept", "framework", "model", "components")):
        return "network"
    return "bullets"


def render_scene_page(scene_obj, scene_data):
    pal = palette()
    layout = (scene_data.get("layout") or "auto").lower()
    if layout == "auto" or layout not in LAYOUT_RENDERERS:
        layout = auto_layout(scene_data)
    LAYOUT_RENDERERS.get(layout, render_bullets)(scene_obj, scene_data, pal)


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
