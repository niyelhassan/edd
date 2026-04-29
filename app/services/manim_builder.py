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


def setup_frame(scene_obj, scene_data, pal, *, show_counter=True, show_brand=False, show_bottom_rule=True):
    scene_obj.camera.background_color = pal["background"]
    if show_bottom_rule:
        scene_obj.add(make_bottom_rule(pal))
    if show_brand:
        scene_obj.add(make_brand_mark(pal).to_corner(DR, buff=0.55))
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
    setup_frame(scene_obj, scene_data, pal, show_counter=False, show_brand=False)
    title = (TITLE or scene_data.get("headline") or "Lesson").strip()
    eyebrow_text = "RESEARCH EXPLAINER SERIES"

    candidates = [scene_data.get("hook"), STORY.get("learning_objective"), STORY.get("summary")]
    subtitle_text = next(
        ((c or "").strip() for c in candidates if _is_distinct(c, title, eyebrow_text)),
        "",
    )

    accent_line = Rectangle(height=0.035, width=0.70, stroke_width=0, fill_color=pal["accent"], fill_opacity=1)
    headline = safe_text(title, font_size=64, weight=SEMIBOLD, color=pal["ink"], width=11.2, wrap=24)
    subtitle = (
        safe_text(subtitle_text, font_size=23, color=pal["muted"], width=8.8, wrap=52)
        if subtitle_text else None
    )
    series = make_eyebrow_label(eyebrow_text, pal, color=pal["light"], font_size=13)
    left_rule = Rectangle(height=0.018, width=0.34, stroke_width=0, fill_color=pal["soft"], fill_opacity=1)
    right_rule = left_rule.copy()
    footer = VGroup(left_rule, series, right_rule).arrange(RIGHT, buff=0.22)

    parts = [accent_line, headline] + ([subtitle] if subtitle is not None else []) + [footer]
    main_block = VGroup(*parts).arrange(DOWN, buff=0.42).move_to(UP * 0.05)
    footer.shift(DOWN * 0.25)

    scene_obj.play(GrowFromCenter(accent_line), run_time=0.35)
    scene_obj.play(Write(headline), run_time=1.0)
    if subtitle is not None:
        scene_obj.play(FadeIn(subtitle, shift=UP * 0.08), run_time=0.45)
    scene_obj.play(FadeIn(footer, shift=UP * 0.08), run_time=0.35)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 8.0), 2.5)


def render_summary(scene_obj, scene_data, pal):
    """Key takeaways: bold accent statement + 2–3 checkmark bullets."""
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

    big = safe_text(
        takeaway or "Key takeaway", font_size=34, weight=SEMIBOLD,
        color=pal["ink"], width=11.0, wrap=44,
    )

    rows = VGroup()
    for line in bullets:
        check_bg = Circle(
            radius=0.20, color=pal["accent_mid"], stroke_width=1.5,
            fill_color=pal["accent_soft"], fill_opacity=1,
        )
        check_mark = VGroup(
            Line([-0.08, 0.0, 0], [-0.02, -0.07, 0], stroke_width=3.5, color=pal["accent"]),
            Line([-0.02, -0.07, 0], [0.10, 0.07, 0], stroke_width=3.5, color=pal["accent"]),
        )
        check_icon = VGroup(check_bg, check_mark)
        text = safe_text(line, font_size=21, color=pal["ink"], width=9.4, wrap=64)
        rows.add(VGroup(check_icon, text).arrange(RIGHT, buff=0.32, aligned_edge=UP))
    if len(rows):
        rows.arrange(DOWN, buff=0.34, aligned_edge=LEFT)

    body = VGroup(*([big, rows] if len(rows) else [big])).arrange(DOWN, buff=0.55, aligned_edge=LEFT)
    place_body(body, top=CHROME_BOTTOM_Y - 0.4, center_x=-0.3, max_height=4.6, max_width=11.5)

    scene_obj.play(FadeIn(big, shift=UP * 0.12), run_time=0.6)
    if len(rows):
        scene_obj.play(LaggedStart(*[FadeIn(r, shift=RIGHT * 0.15) for r in rows], lag_ratio=0.18), run_time=0.9)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 12.0), 1.8)


def render_thanks(scene_obj, scene_data, pal):
    """Closing card: restrained thank-you screen matching the opener."""
    setup_frame(scene_obj, scene_data, pal, show_counter=False, show_brand=False)

    label = make_eyebrow_label("Thank You", pal, font_size=14)
    thanks = safe_text("Keep Exploring", font_size=60, weight=SEMIBOLD, color=pal["ink"], width=11.5, wrap=24)
    accent_line = Rectangle(height=0.035, width=0.70, stroke_width=0, fill_color=pal["accent"], fill_opacity=1)
    sub_text = (scene_data.get("hook") or "").strip()
    sub = (
        safe_text(sub_text, font_size=21, color=pal["muted"], width=8.4, wrap=54)
        if sub_text else None
    )
    links = VGroup(*[safe_text(t, font_size=15, color=pal["accent"] if i == 0 else pal["light"])
                     for i, t in enumerate(["Review", "Practice", "Next Topic"])])
    links.arrange(RIGHT, buff=0.65)

    parts = [label, thanks, accent_line] + ([sub] if sub is not None else []) + [links]
    main_block = VGroup(*parts).arrange(DOWN, buff=0.40).move_to(ORIGIN)
    if sub is not None:
        links.shift(DOWN * 0.25)

    scene_obj.play(FadeIn(label, shift=DOWN * 0.12), run_time=0.35)
    scene_obj.play(Write(thanks), run_time=1.0)
    scene_obj.play(GrowFromCenter(accent_line), run_time=0.25)
    if sub is not None:
        scene_obj.play(FadeIn(sub, shift=UP * 0.08), run_time=0.45)
    scene_obj.play(FadeIn(links, shift=UP * 0.08), run_time=0.35)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 5.0), 2.4)


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
        safe_text(hook, font_size=25, weight=SEMIBOLD, color=pal["ink"], width=10.5, wrap=58)
        if hook else None
    )

    rows = VGroup()
    for i, line in enumerate(bullets):
        chip_bg = Circle(
            radius=0.26, color=pal["accent"], stroke_width=1.6,
            fill_color=pal["accent_soft"], fill_opacity=1,
        )
        chip_text = safe_text(str(i + 1), font_size=18, weight=BOLD, color=pal["accent"]).move_to(chip_bg)
        chip = VGroup(chip_bg, chip_text)
        text = safe_text(line, font_size=22, color=pal["ink"], width=9.0, wrap=58)
        rows.add(VGroup(chip, text).arrange(RIGHT, buff=0.42, aligned_edge=UP))
    if len(rows):
        rows.arrange(DOWN, buff=0.44, aligned_edge=LEFT)

    parts = [m for m in (hook_text, rows) if m is not None and (not isinstance(m, VGroup) or len(m))]
    body = VGroup(*parts).arrange(DOWN, buff=0.55, aligned_edge=LEFT)
    accent_rule = Rectangle(
        height=max(body.height, 3.1), width=0.045, stroke_width=0,
        fill_color=pal["accent"], fill_opacity=1,
    )
    body_with_rule = VGroup(accent_rule, body).arrange(RIGHT, buff=0.48, aligned_edge=UP)
    place_body(body_with_rule, top=CHROME_BOTTOM_Y - 0.5, center_x=-0.25, max_height=5.0, max_width=11.0)

    if hook_text is not None:
        scene_obj.play(FadeIn(hook_text, shift=UP * 0.1), run_time=0.4)
    scene_obj.play(GrowFromEdge(accent_rule, UP), run_time=0.35)
    for row in rows:
        scene_obj.play(FadeIn(row[0], scale=0.85), FadeIn(row[1], shift=RIGHT * 0.1), run_time=0.35)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 12.0), 1.0 + 0.4 * (len(rows) + 1))


def render_concept_map(scene_obj, scene_data, pal):
    """Hub-and-spoke: refined center card with three soft satellite cards."""
    add_top_bar(scene_obj, scene_data, pal)

    items = ([i for i in (scene_data.get("visual_items") or []) if i][:3]
             or [i for i in (scene_data.get("key_points") or []) if i][:3])
    center_label = (scene_data.get("highlight_terms") or [scene_data.get("headline", "Idea")])[0]

    center_bg = Circle(
        radius=1.05, color=pal["accent"], stroke_width=2.0,
        fill_color=pal["accent_soft"], fill_opacity=1,
    )
    center_text = safe_text(
        center_label, font_size=22, weight=BOLD, color=pal["ink"],
        width=1.7, height=1.2, wrap=14,
    )
    hub = VGroup(center_bg, center_text.move_to(center_bg))

    angles = [PI / 2, PI / 2 + 2 * PI / 3, PI / 2 + 4 * PI / 3]
    radius = 2.55

    spokes = VGroup()
    nodes = VGroup()
    for i, item in enumerate(items[:3]):
        pos = np.array([math.cos(angles[i]) * radius, math.sin(angles[i]) * radius, 0])
        bg = make_card(2.8, 1.02, pal, radius=0.14, stroke_width=1.3)
        label = safe_text(
            item, font_size=17, weight=SEMIBOLD, color=pal["ink"],
            width=2.3, height=0.75, wrap=20,
        )
        node = VGroup(bg, label.move_to(bg)).move_to(pos)
        nodes.add(node)
        spokes.add(Line(hub.get_center(), node.get_center(), color=pal["soft"], stroke_width=2.0))

    diagram = VGroup(spokes, hub, nodes)
    place_body(diagram, top=CHROME_BOTTOM_Y - 0.3, max_height=5.4, max_width=11.0)

    scene_obj.play(FadeIn(hub, scale=0.85), run_time=0.5)
    if len(spokes):
        scene_obj.play(LaggedStart(*[Create(s) for s in spokes], lag_ratio=0.12), run_time=0.7)
    if len(nodes):
        scene_obj.play(LaggedStart(*[FadeIn(n, shift=UP * 0.1) for n in nodes], lag_ratio=0.12), run_time=0.7)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 12.0), 2.4)


def render_equation(scene_obj, scene_data, pal):
    """Equation centered on a white formula card with left accent rule and term tags."""
    add_top_bar(scene_obj, scene_data, pal)

    expr_list = [e for e in (scene_data.get("equations") or []) if e]
    primary = expr_list[0] if expr_list else None
    secondary = expr_list[1] if len(expr_list) > 1 else None

    eq_main = safe_math(primary, color=pal["ink"], font_size=64, max_width=10.0) if primary else None
    eq_secondary = safe_math(secondary, color=pal["muted"], font_size=42, max_width=9.0) if secondary else None
    if eq_main is None:
        eq_main = safe_text(
            scene_data.get("hook") or scene_data.get("headline") or "Idea",
            font_size=46, weight=BOLD, color=pal["ink"], width=10.0, wrap=22,
        )

    eq_block_parts = [eq_main] + ([eq_secondary] if eq_secondary is not None else [])
    eq_block = VGroup(*eq_block_parts).arrange(DOWN, buff=0.40)
    card_w = max(eq_block.width + 1.6, 6.0)
    card_h = eq_block.height + 1.2
    eq_card = make_card(card_w, card_h, pal, radius=0.14, stroke_width=1.2)
    accent_rule = Rectangle(
        height=card_h, width=0.07, stroke_width=0,
        fill_color=pal["accent"], fill_opacity=1,
    ).align_to(eq_card, LEFT).move_to(eq_card.get_left() + RIGHT * 0.035)
    eq_block.move_to(eq_card)
    eq_panel = VGroup(eq_card, accent_rule, eq_block)

    chips = VGroup()
    for t in [t for t in (scene_data.get("highlight_terms") or []) if t][:3]:
        chips.add(make_tag(t, pal, font_size=15))
    if len(chips):
        chips.arrange(RIGHT, buff=0.28)

    layout_parts = [eq_panel] + ([chips] if len(chips) else [])
    body = VGroup(*layout_parts).arrange(DOWN, buff=0.55)
    place_body(body, top=CHROME_BOTTOM_Y - 0.5, max_height=4.8, max_width=11.5)

    scene_obj.play(FadeIn(eq_card, shift=UP * 0.05), GrowFromEdge(accent_rule, UP), run_time=0.45)
    scene_obj.play(Write(eq_main), run_time=1.2)
    if eq_secondary is not None:
        scene_obj.play(Write(eq_secondary), run_time=0.7)
    if len(chips):
        scene_obj.play(LaggedStart(*[FadeIn(c, shift=UP * 0.08) for c in chips], lag_ratio=0.15), run_time=0.6)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 2.95)


def render_distribution(scene_obj, scene_data, pal):
    """Bell curve with shaded tail. Minimal labeling."""
    add_top_bar(scene_obj, scene_data, pal)

    axes = Axes(
        x_range=[-3.5, 3.5, 1], y_range=[0, 0.5, 0.1],
        x_length=8.6, y_length=3.6,
        axis_config={"color": pal["muted"], "stroke_width": 2}, tips=False,
    ).move_to([0, -0.6, 0])

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

    scene_obj.play(Create(axes), run_time=0.5)
    scene_obj.play(Create(curve), run_time=1.2)
    scene_obj.play(FadeIn(x_label, shift=RIGHT * 0.1), run_time=0.35)
    scene_obj.play(Create(threshold), run_time=0.35)
    scene_obj.play(FadeIn(shade, shift=RIGHT * 0.06), FadeIn(tail_label, shift=LEFT * 0.06), run_time=0.6)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 3.0)


def render_axes_plot(scene_obj, scene_data, pal):
    """Generic XY function plot with up to three labelled points."""
    add_top_bar(scene_obj, scene_data, pal)

    axes = Axes(
        x_range=[-4, 4, 1], y_range=[-2.5, 2.5, 1],
        x_length=8.6, y_length=4.0,
        axis_config={"color": pal["muted"], "stroke_width": 2}, tips=False,
    ).move_to([0, -0.5, 0])

    items = [s for s in (scene_data.get("highlight_terms") or []) if s]
    x_lab = safe_text(items[0] if items else "x", font_size=18, color=pal["muted"]).next_to(axes.x_axis, RIGHT, buff=0.18)
    y_lab = safe_text(items[1] if len(items) > 1 else "y", font_size=18, color=pal["muted"]).next_to(axes.y_axis, UP, buff=0.18)

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
        lab = safe_text(label_str, font_size=18, weight=SEMIBOLD, color=pal["ink"], width=3.0, wrap=24)
        lab.next_to(pt, UR if i % 2 == 0 else UL, buff=0.18)
        markers.add(pt, lab)

    scene_obj.play(Create(axes), run_time=0.5)
    scene_obj.play(FadeIn(x_lab, shift=RIGHT * 0.1), FadeIn(y_lab, shift=UP * 0.1), run_time=0.3)
    scene_obj.play(Create(curve), run_time=1.2)
    if len(markers):
        scene_obj.play(LaggedStart(*[FadeIn(m, shift=UP * 0.1) for m in markers], lag_ratio=0.12), run_time=0.8)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 2.8)


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
        header_label.move_to(bg.get_top() + DOWN * 0.55).align_to(bg, LEFT).shift(RIGHT * 0.42)

        rows = VGroup()
        for line in lines[:3]:
            dot = Dot(radius=0.07, color=accent)
            text = safe_text(line, font_size=18, color=pal["ink"], width=4.1, wrap=32)
            rows.add(VGroup(dot, text).arrange(RIGHT, buff=0.22, aligned_edge=UP))
        if len(rows):
            rows.arrange(DOWN, buff=0.34, aligned_edge=LEFT)
            rows.move_to(bg.get_center() + DOWN * 0.35)
        return VGroup(bg, header_label, rows)

    left_lines = points[:3] if items else points[:3]
    right_lines = points[3:6] if len(points) > 3 else (points[:3] if not items else [])

    left = panel(left_title, left_lines, pal["muted"], highlighted=False)
    right = panel(right_title, right_lines, pal["accent"], highlighted=True)

    pair = VGroup(left, right).arrange(RIGHT, buff=0.5)
    place_body(pair, top=CHROME_BOTTOM_Y - 0.3, max_height=5.2, max_width=11.5)

    scene_obj.play(FadeIn(left, shift=LEFT * 0.15), FadeIn(right, shift=RIGHT * 0.15), run_time=0.7)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 1.7)


def render_flow(scene_obj, scene_data, pal):
    """Numbered process nodes with thin connectors and restrained labels."""
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
    labels = VGroup()
    connectors = VGroup()
    for i, item in enumerate(items):
        x = start_x + i * spacing
        is_first = i == 0
        bg = Circle(
            radius=0.46,
            color=pal["accent"],
            stroke_width=1.8,
            fill_color=pal["accent"] if is_first else pal["accent_soft"],
            fill_opacity=1,
        )
        num = safe_text(
            f"{i + 1:02d}", font_size=17, weight=BOLD,
            color="#FFFFFF" if is_first else pal["accent"],
        ).move_to(bg)
        node = VGroup(bg, num).move_to([x, 0.35, 0])
        nodes.add(node)
        lab = safe_text(item, font_size=17, weight=SEMIBOLD, color=pal["ink"], width=spacing - 0.3, wrap=18)
        lab.next_to(node, DOWN, buff=0.40)
        labels.add(lab)
        if i > 0:
            prev_node = nodes[i - 1]
            arrow = Arrow(
                prev_node[0].get_right(), bg.get_left(),
                color=pal["soft"], stroke_width=2.6, buff=0.05,
                tip_length=0.18, max_tip_length_to_length_ratio=0.32,
            )
            connectors.add(arrow)

    pipeline = VGroup(connectors, nodes, labels)
    place_body(pipeline, top=CHROME_BOTTOM_Y - 0.4, max_height=4.6, max_width=11.5)

    scene_obj.play(LaggedStart(*[FadeIn(node, scale=0.7) for node in nodes], lag_ratio=0.15), run_time=0.9)
    if len(connectors):
        scene_obj.play(LaggedStart(*[Create(c) for c in connectors], lag_ratio=0.15), run_time=0.7)
    scene_obj.play(LaggedStart(*[FadeIn(l, shift=UP * 0.1) for l in labels], lag_ratio=0.12), run_time=0.6)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 2.5)


def render_bar_chart(scene_obj, scene_data, pal):
    """Rounded bars rising from a soft baseline. Tallest uses primary accent."""
    add_top_bar(scene_obj, scene_data, pal)

    items = [s for s in (scene_data.get("visual_items") or scene_data.get("key_points") or []) if s][:4]
    if not items:
        items = [scene_data.get("headline", "value")]

    rng = random.Random(sum(ord(c) for c in (scene_data.get("slug") or "bars")))
    values = [0.45 + rng.random() * 0.95 for _ in items]
    max_val = max(values)

    base_y, max_h = -2.6, 4.0
    n, w, spacing = len(items), 1.0, 0.6
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
        labels.add(safe_text(item, font_size=18, weight=SEMIBOLD, color=pal["ink"], width=w + 0.5, wrap=14)
                   .next_to(bar, DOWN, buff=0.22))
        value_labels.add(safe_text(f"{int(v * 100)}", font_size=20, weight=BOLD, color=color)
                         .next_to(bar, UP, buff=0.16))

    chart = VGroup(baseline, bars, labels, value_labels)
    place_body(chart, top=CHROME_BOTTOM_Y - 0.4, max_height=5.4, max_width=11.0)

    scene_obj.play(Create(baseline), run_time=0.4)
    scene_obj.play(LaggedStart(*[GrowFromEdge(b, DOWN) for b in bars], lag_ratio=0.12), run_time=1.1)
    scene_obj.play(LaggedStart(*[FadeIn(l, shift=UP * 0.05) for l in labels], lag_ratio=0.1), run_time=0.5)
    scene_obj.play(LaggedStart(*[FadeIn(v) for v in value_labels], lag_ratio=0.08), run_time=0.4)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 2.4)


# ---- dispatcher ----
LAYOUT_RENDERERS = {
    "title_card": render_title_card,
    "summary": render_summary,
    "thanks": render_thanks,
    "bullets": render_bullets,
    "concept_map": render_concept_map,
    "equation": render_equation,
    "distribution": render_distribution,
    "axes_plot": render_axes_plot,
    "comparison": render_comparison,
    "flow": render_flow,
    "bar_chart": render_bar_chart,
}


def auto_layout(scene_data):
    head = ((scene_data.get("headline") or "") + " " + (scene_data.get("hook") or "") + " " + (scene_data.get("narration") or "")).lower()
    if scene_data.get("equations"):
        return "equation"
    if any(w in head for w in ("p-value", "p value", "distribution", "bell curve", "gaussian", "normal distribution", "probability density")):
        return "distribution"
    if any(w in head for w in ("vs ", " versus ", "compare", "comparison", "before vs after")):
        return "comparison"
    if any(w in head for w in ("step", "process", "pipeline", "workflow", "stage", "first then")):
        return "flow"
    if any(w in head for w in ("axis", "axes", "plot", "graph of", "function", "growth", "decay", "exponential", "wave", "sine", "oscill")):
        return "axes_plot"
    if any(w in head for w in ("bar chart", "ranking", "share", "percentage", "magnitude")):
        return "bar_chart"
    if any(w in head for w in ("idea", "concept", "framework", "model", "components")):
        return "concept_map"
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
