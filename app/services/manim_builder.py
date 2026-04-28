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

# Single accent color drives the whole theme; everything else is monochrome ink.
THEME_ACCENTS = {
    "blue":   {"accent": "#1D4ED8", "accent_2": "#0EA5E9", "accent_soft": "#DBEAFE"},
    "violet": {"accent": "#6D28D9", "accent_2": "#A855F7", "accent_soft": "#EDE9FE"},
    "green":  {"accent": "#059669", "accent_2": "#10B981", "accent_soft": "#D1FAE5"},
    "amber":  {"accent": "#B45309", "accent_2": "#F59E0B", "accent_soft": "#FEF3C7"},
    "rose":   {"accent": "#BE185D", "accent_2": "#F472B6", "accent_soft": "#FCE7F3"},
    "slate":  {"accent": "#0F172A", "accent_2": "#475569", "accent_soft": "#E2E8F0"},
}


def palette():
    theme = str(STORY.get("color_theme") or "blue").strip().lower()
    accents = THEME_ACCENTS.get(theme, THEME_ACCENTS["blue"])
    return {
        "background": "#FAFAFB",
        "ink": "#0A0A0A",
        "muted": "#737373",
        "soft": "#E5E5E5",
        "panel": "#F4F4F5",
        "accent": accents["accent"],
        "accent_2": accents["accent_2"],
        "accent_soft": accents["accent_soft"],
        "good": "#059669",
    }


SANS = "sans-serif"
TEXT_BASE_FONT_SIZE = 96


def _wrap(text, width):
    text = (text or "").strip()
    if not text:
        return ""
    return "\\n".join(textwrap.wrap(text, width=width, break_long_words=False, break_on_hyphens=False))


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
    mark = safe_text("lern", font_size=20, color=pal["muted"], weight=SEMIBOLD)
    mark.set_opacity(0.55)
    return mark


def make_progress_dots(index, total, pal):
    if total <= 1:
        return VGroup()
    dots = VGroup()
    for i in range(total):
        dot = Dot(radius=0.07, color=pal["accent"] if i == index else pal["soft"])
        dots.add(dot)
    dots.arrange(RIGHT, buff=0.16)
    counter = safe_text(f"{index + 1}/{total}", font_size=16, weight=SEMIBOLD, color=pal["muted"])
    counter.set_opacity(0.7)
    return VGroup(counter, dots).arrange(RIGHT, buff=0.28)


def setup_frame(scene_obj, scene_data, pal, *, draw_accent_bar=True):
    scene_obj.camera.background_color = pal["background"]

    if draw_accent_bar:
        accent_bar = Rectangle(
            height=8.0, width=0.16,
            stroke_width=0,
            fill_color=pal["accent"],
            fill_opacity=1,
        ).to_edge(LEFT, buff=0)
        scene_obj.add(accent_bar)

    scene_obj.add(make_brand_mark(pal).to_corner(DR, buff=0.45))

    scene_index = int(scene_data.get("scene_number", 1)) - 1
    total = int(scene_data.get("scene_total", len(SCENES)) or len(SCENES))
    dots = make_progress_dots(scene_index, total, pal)
    if len(dots):
        dots.to_corner(DL, buff=0.55)
        scene_obj.add(dots)


def add_top_bar(scene_obj, scene_data, pal):
    """Minimal top chrome: small lesson eyebrow + bold scene headline + hairline underline."""
    setup_frame(scene_obj, scene_data, pal)
    eyebrow_text = (TITLE or "Lesson").strip().upper()
    headline_text = (scene_data.get("headline") or "").strip()

    show_eyebrow = _is_distinct(eyebrow_text, headline_text)
    eyebrow = (
        safe_text(eyebrow_text, font_size=16, color=pal["muted"], weight=BOLD, width=10.0, wrap=64)
        if show_eyebrow else None
    )
    headline = safe_text(headline_text, font_size=44, weight=BOLD, color=pal["ink"], width=11.0, wrap=46)

    if eyebrow is not None:
        eyebrow.to_edge(UP, buff=0.55).to_edge(LEFT, buff=0.85)
        headline.next_to(eyebrow, DOWN, buff=0.20, aligned_edge=LEFT)
    else:
        headline.to_edge(UP, buff=0.65).to_edge(LEFT, buff=0.85)

    underline = Line(
        headline.get_corner(DL) + DOWN * 0.16,
        headline.get_corner(DL) + DOWN * 0.16 + RIGHT * min(1.5, headline.width * 0.25),
        color=pal["accent"], stroke_width=4,
    )

    if eyebrow is not None:
        scene_obj.play(FadeIn(eyebrow, shift=DOWN * 0.08), run_time=0.3)
    scene_obj.play(Write(headline, run_time=0.55), Create(underline, run_time=0.45))
    return VGroup(*([eyebrow, headline, underline] if eyebrow else [headline, underline]))


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
    """Calm, minimal opener: small eyebrow, big lesson title, one supporting line."""
    setup_frame(scene_obj, scene_data, pal, draw_accent_bar=False)
    title = (TITLE or scene_data.get("headline") or "Lesson").strip()
    eyebrow_text = "TODAY'S LESSON"

    candidates = [scene_data.get("hook"), STORY.get("learning_objective"), STORY.get("summary")]
    subtitle_text = next(
        ((c or "").strip() for c in candidates if _is_distinct(c, title, eyebrow_text)),
        "",
    )

    eyebrow = safe_text(eyebrow_text, font_size=16, weight=BOLD, color=pal["muted"], width=10.0)
    accent_line = Rectangle(height=0.08, width=1.4, stroke_width=0, fill_color=pal["accent"], fill_opacity=1)
    headline = safe_text(title, font_size=68, weight=BOLD, color=pal["ink"], width=11.5, wrap=24)
    subtitle = (
        safe_text(subtitle_text, font_size=24, color=pal["muted"], width=10.0, wrap=58)
        if subtitle_text else None
    )

    parts = [eyebrow, accent_line, headline] + ([subtitle] if subtitle else [])
    group = VGroup(*parts).arrange(DOWN, buff=0.36, aligned_edge=LEFT).move_to(ORIGIN)

    scene_obj.play(FadeIn(eyebrow, shift=DOWN * 0.12), run_time=0.4)
    scene_obj.play(GrowFromCenter(accent_line), run_time=0.3)
    scene_obj.play(Write(headline), run_time=1.0)
    if subtitle is not None:
        scene_obj.play(FadeIn(subtitle, shift=UP * 0.08), run_time=0.45)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 8.0), 2.2)


def render_summary(scene_obj, scene_data, pal):
    """Key takeaways: bold headline + 2–3 checked bullets."""
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

    big = safe_text(takeaway or "Key takeaway", font_size=34, weight=BOLD, color=pal["accent"], width=11.5, wrap=42)

    rows = VGroup()
    for line in bullets:
        check = Triangle(color=pal["good"], fill_opacity=1).scale(0.14).rotate(-PI / 2)
        text = safe_text(line, font_size=23, color=pal["ink"], width=9.5, wrap=64)
        rows.add(VGroup(check, text).arrange(RIGHT, buff=0.30, aligned_edge=UP))
    if len(rows):
        rows.arrange(DOWN, buff=0.30, aligned_edge=LEFT)

    body = VGroup(*([big, rows] if len(rows) else [big])).arrange(DOWN, buff=0.5, aligned_edge=LEFT)
    place_body(body, top=CHROME_BOTTOM_Y - 0.4, center_x=-0.5, max_height=4.6, max_width=11.5)

    scene_obj.play(FadeIn(big, shift=UP * 0.12), run_time=0.55)
    if len(rows):
        scene_obj.play(LaggedStart(*[FadeIn(r, shift=RIGHT * 0.15) for r in rows], lag_ratio=0.2), run_time=0.9)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 12.0), 1.8)


def render_thanks(scene_obj, scene_data, pal):
    """Closing thanks card: brand wordmark and a brief sign-off."""
    setup_frame(scene_obj, scene_data, pal, draw_accent_bar=False)
    thanks = safe_text("Thanks for watching", font_size=58, weight=BOLD, color=pal["ink"], width=11.5, wrap=24)
    sub_text = (scene_data.get("hook") or "Made with lern").strip()
    sub = safe_text(sub_text, font_size=22, color=pal["muted"], width=9.5, wrap=58)
    accent_line = Rectangle(height=0.06, width=1.0, stroke_width=0, fill_color=pal["accent"], fill_opacity=1)
    group = VGroup(thanks, accent_line, sub).arrange(DOWN, buff=0.45).move_to(ORIGIN)

    scene_obj.play(Write(thanks), run_time=1.0)
    scene_obj.play(GrowFromCenter(accent_line), run_time=0.3)
    scene_obj.play(FadeIn(sub, shift=UP * 0.1), run_time=0.45)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 5.0), 1.8)


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
        safe_text(hook, font_size=28, weight=SEMIBOLD, color=pal["accent"], width=10.5, wrap=58)
        if hook else None
    )

    rows = VGroup()
    for i, line in enumerate(bullets):
        bg = Circle(radius=0.20, color=pal["accent"], stroke_width=0, fill_color=pal["accent"], fill_opacity=1)
        idx = safe_text(str(i + 1), font_size=18, weight=BOLD, color="#FFFFFF").move_to(bg)
        text = safe_text(line, font_size=23, color=pal["ink"], width=9.0, wrap=64)
        rows.add(VGroup(VGroup(bg, idx), text).arrange(RIGHT, buff=0.36, aligned_edge=UP))
    if len(rows):
        rows.arrange(DOWN, buff=0.40, aligned_edge=LEFT)

    parts = [m for m in (hook_text, rows) if m is not None and (not isinstance(m, VGroup) or len(m))]
    body = VGroup(*parts).arrange(DOWN, buff=0.55, aligned_edge=LEFT)
    place_body(body, top=CHROME_BOTTOM_Y - 0.5, center_x=-0.3, max_height=5.0, max_width=11.0)

    if hook_text is not None:
        scene_obj.play(FadeIn(hook_text, shift=UP * 0.1), run_time=0.4)
    for row in rows:
        scene_obj.play(FadeIn(row[0], scale=0.85), FadeIn(row[1], shift=RIGHT * 0.1), run_time=0.35)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 12.0), 1.0 + 0.4 * (len(rows) + 1))


def render_concept_map(scene_obj, scene_data, pal):
    """Hub-and-spoke: one central concept with up to 3 supporting nodes."""
    add_top_bar(scene_obj, scene_data, pal)

    items = ([i for i in (scene_data.get("visual_items") or []) if i][:3]
             or [i for i in (scene_data.get("key_points") or []) if i][:3])
    center_label = (scene_data.get("highlight_terms") or [scene_data.get("headline", "Idea")])[0]

    center = Circle(radius=0.95, color=pal["accent"], stroke_width=4).set_fill(pal["accent"], opacity=0.10)
    center_text = safe_text(center_label, font_size=22, weight=BOLD, color=pal["ink"], width=1.55, height=1.0, wrap=12)
    hub = VGroup(center, center_text)

    angles = [PI / 2, PI / 2 + 2 * PI / 3, PI / 2 + 4 * PI / 3]
    radius = 2.4
    nodes = VGroup(hub)
    for i, item in enumerate(items[:3]):
        pos = np.array([math.cos(angles[i]) * radius, math.sin(angles[i]) * radius, 0])
        bg = RoundedRectangle(corner_radius=0.18, width=2.5, height=0.95, stroke_width=0,
                              fill_color=pal["accent"] if i % 2 == 0 else pal["accent_2"], fill_opacity=1)
        label = safe_text(item, font_size=20, color="#FFFFFF", weight=SEMIBOLD, width=2.1, height=0.65, wrap=18)
        node = VGroup(bg, label.move_to(bg)).move_to(pos)
        line = Line(hub.get_center(), node.get_center(), color=pal["soft"], stroke_width=3)
        nodes.add(line, node)

    place_body(nodes, top=CHROME_BOTTOM_Y - 0.3, max_height=5.2, max_width=10.5)
    intro = []
    for m in nodes:
        intro.append(Create(m) if isinstance(m, Line) else FadeIn(m, scale=0.85))
    scene_obj.play(LaggedStart(*intro, lag_ratio=0.10), run_time=1.3)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 12.0), 2.4)


def render_equation(scene_obj, scene_data, pal):
    """Single equation, calm reveal, optional symbol chips. No decorative rays."""
    add_top_bar(scene_obj, scene_data, pal)

    expr_list = [e for e in (scene_data.get("equations") or []) if e]
    primary = expr_list[0] if expr_list else None
    secondary = expr_list[1] if len(expr_list) > 1 else None

    eq_main = safe_math(primary, color=pal["ink"], font_size=64, max_width=10.5) if primary else None
    eq_secondary = safe_math(secondary, color=pal["muted"], font_size=42, max_width=9.5) if secondary else None
    if eq_main is None:
        eq_main = safe_text(scene_data.get("hook") or scene_data.get("headline") or "Idea",
                            font_size=46, weight=BOLD, color=pal["ink"], width=10.0, wrap=22)

    chips = VGroup()
    for t in [t for t in (scene_data.get("highlight_terms") or []) if t][:3]:
        bg = RoundedRectangle(corner_radius=0.16, width=2.5, height=0.55, stroke_width=0,
                              fill_color=pal["panel"], fill_opacity=1)
        text = safe_text(t, font_size=17, weight=SEMIBOLD, color=pal["ink"], width=2.2, height=0.4, wrap=22)
        chips.add(VGroup(bg, text.move_to(bg)))
    if len(chips):
        chips.arrange(RIGHT, buff=0.28)

    layout = [eq_main] + ([eq_secondary] if eq_secondary else []) + ([chips] if len(chips) else [])
    body = VGroup(*layout).arrange(DOWN, buff=0.5)
    place_body(body, top=CHROME_BOTTOM_Y - 0.5, max_height=4.8, max_width=11.5)

    scene_obj.play(Write(eq_main), run_time=1.3)
    if eq_secondary is not None:
        scene_obj.play(Write(eq_secondary), run_time=0.8)
    if len(chips):
        scene_obj.play(LaggedStart(*[FadeIn(c, shift=UP * 0.08) for c in chips], lag_ratio=0.15), run_time=0.6)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 2.7)


def render_distribution(scene_obj, scene_data, pal):
    """Bell curve with shaded tail. Minimal labeling."""
    add_top_bar(scene_obj, scene_data, pal)

    axes = Axes(
        x_range=[-3.5, 3.5, 1], y_range=[0, 0.5, 0.1],
        x_length=8.6, y_length=3.6,
        axis_config={"color": pal["muted"], "stroke_width": 2}, tips=False,
    ).move_to([0, -0.7, 0])

    def normal(x): return math.exp(-x * x / 2) / math.sqrt(2 * math.pi)

    curve = axes.plot(normal, x_range=[-3.4, 3.4], color=pal["ink"], stroke_width=4)
    cutoff = 1.65
    shade = axes.get_area(curve, x_range=[cutoff, 3.4], color=pal["accent"], opacity=0.45)
    threshold = DashedLine(axes.c2p(cutoff, 0), axes.c2p(cutoff, normal(cutoff)),
                           color=pal["accent"], dash_length=0.12, stroke_width=3)

    terms = [t for t in (scene_data.get("highlight_terms") or []) if t]
    tail_label = safe_text((terms[-1] if terms else "Tail area"),
                           font_size=20, weight=SEMIBOLD, color=pal["accent"], width=2.6, wrap=22)
    tail_label.next_to(shade, RIGHT, buff=0.3)
    x_label = safe_text((terms[0] if terms else "test statistic"),
                        font_size=20, color=pal["muted"], width=2.6, wrap=22)
    x_label.next_to(axes.x_axis, RIGHT, buff=0.18)

    scene_obj.play(Create(axes), run_time=0.6)
    scene_obj.play(Create(curve), run_time=1.3)
    scene_obj.play(FadeIn(x_label, shift=RIGHT * 0.1), run_time=0.4)
    scene_obj.play(Create(threshold), run_time=0.4)
    scene_obj.play(FadeIn(shade, shift=RIGHT * 0.08), FadeIn(tail_label, shift=LEFT * 0.08), run_time=0.6)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 3.3)


def render_axes_plot(scene_obj, scene_data, pal):
    """Generic XY function plot with up to three labelled points."""
    add_top_bar(scene_obj, scene_data, pal)

    axes = Axes(
        x_range=[-4, 4, 1], y_range=[-2.5, 2.5, 1],
        x_length=8.6, y_length=4.0,
        axis_config={"color": pal["muted"], "stroke_width": 2}, tips=False,
    ).move_to([0, -0.6, 0])

    items = [s for s in (scene_data.get("highlight_terms") or []) if s]
    x_lab = safe_text(items[0] if items else "x", font_size=20, color=pal["muted"]).next_to(axes.x_axis, RIGHT, buff=0.18)
    y_lab = safe_text(items[1] if len(items) > 1 else "y", font_size=20, color=pal["muted"]).next_to(axes.y_axis, UP, buff=0.18)

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
        lab = safe_text(label_str, font_size=19, color=pal["ink"], width=3.0, wrap=24)
        lab.next_to(pt, UR if i % 2 == 0 else UL, buff=0.18)
        markers.add(pt, lab)

    scene_obj.play(Create(axes), run_time=0.55)
    scene_obj.play(FadeIn(x_lab, shift=RIGHT * 0.1), FadeIn(y_lab, shift=UP * 0.1), run_time=0.35)
    scene_obj.play(Create(curve), run_time=1.3)
    if len(markers):
        scene_obj.play(LaggedStart(*[FadeIn(m, shift=UP * 0.1) for m in markers], lag_ratio=0.12), run_time=0.8)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 3.0)


def render_comparison(scene_obj, scene_data, pal):
    """Two clean panels with titles + 2–3 traits each. Minimal divider."""
    add_top_bar(scene_obj, scene_data, pal)

    items = [s for s in (scene_data.get("visual_items") or []) if s]
    points = [s for s in (scene_data.get("key_points") or []) if s]
    left_title = items[0] if items else "Approach A"
    right_title = items[1] if len(items) > 1 else "Approach B"

    def panel(label, lines, fill, accent):
        bg = RoundedRectangle(corner_radius=0.26, width=4.9, height=4.5, stroke_width=0,
                              fill_color=fill, fill_opacity=1.0)
        title = safe_text(label, font_size=26, weight=BOLD, color=accent, width=4.4, wrap=22)
        title.move_to(bg.get_top() + DOWN * 0.5)
        accent_bar = Rectangle(width=3.6, height=0.05, stroke_width=0, fill_color=accent, fill_opacity=1)
        accent_bar.next_to(title, DOWN, buff=0.15)
        rows = VGroup()
        for line in lines[:3]:
            r = safe_text(line, font_size=19, color=pal["ink"], width=4.4, wrap=30)
            rows.add(r)
        if len(rows):
            rows.arrange(DOWN, buff=0.24, aligned_edge=LEFT)
            rows.move_to(bg.get_center() + DOWN * 0.2)
        return VGroup(bg, title, accent_bar, rows)

    left_lines = points[:3] if items else points[:3]
    right_lines = points[3:6] if len(points) > 3 else (points[:3] if not items else [])

    left = panel(left_title, left_lines, pal["panel"], pal["accent"])
    right = panel(right_title, right_lines, "#FFFFFF", pal["accent_2"])
    right[0].set_stroke(pal["soft"], width=2)

    pair = VGroup(left, right).arrange(RIGHT, buff=0.6)
    place_body(pair, top=CHROME_BOTTOM_Y - 0.3, max_height=5.2, max_width=11.5)

    scene_obj.play(FadeIn(left, shift=LEFT * 0.15), FadeIn(right, shift=RIGHT * 0.15), run_time=0.65)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 1.8)


def render_flow(scene_obj, scene_data, pal):
    """Linear pipeline: 3–4 nodes connected by arrows; a single packet traces the path."""
    add_top_bar(scene_obj, scene_data, pal)

    items = [s for s in (scene_data.get("visual_items") or scene_data.get("key_points") or []) if s][:4]
    if len(items) < 2:
        items = items + [(scene_data.get("highlight_terms") or [scene_data.get("headline", "step")])[0]]
    n = len(items)

    boxes = VGroup()
    arrows = VGroup()
    width, spacing = 2.2, 0.9
    total_width = n * width + (n - 1) * spacing
    start_x = -total_width / 2 + width / 2
    for i, item in enumerate(items):
        accent = pal["accent"] if i % 2 == 0 else pal["accent_2"]
        bg = RoundedRectangle(corner_radius=0.20, width=width, height=1.0, stroke_width=0,
                              fill_color=accent, fill_opacity=1)
        text = safe_text(item, font_size=18, weight=SEMIBOLD, color="#FFFFFF",
                         width=width - 0.4, height=0.7, wrap=18)
        node = VGroup(bg, text.move_to(bg)).move_to(np.array([start_x + i * (width + spacing), 0, 0]))
        boxes.add(node)
        if i > 0:
            prev = boxes[i - 1]
            arrow = Arrow(prev.get_right() + RIGHT * 0.05, node.get_left() + LEFT * 0.05,
                          color=pal["muted"], stroke_width=4, buff=0.06,
                          tip_length=0.18, max_tip_length_to_length_ratio=0.35)
            arrows.add(arrow)
    pipeline = VGroup(boxes, arrows)
    place_body(pipeline, top=CHROME_BOTTOM_Y - 0.5, max_height=4.5, max_width=11.5)

    scene_obj.play(LaggedStart(*[GrowFromCenter(b) for b in boxes], lag_ratio=0.12), run_time=0.9)
    if len(arrows):
        scene_obj.play(LaggedStart(*[Create(a) for a in arrows], lag_ratio=0.15), run_time=0.6)
    if len(arrows):
        packet = Dot(radius=0.10, color=pal["accent"]).move_to(arrows[0].get_start())
        scene_obj.add(packet)
        for arrow in arrows:
            scene_obj.play(packet.animate.move_to(arrow.get_end()), run_time=0.42)
        scene_obj.remove(packet)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 1.5 + 0.42 * len(arrows))


def render_bar_chart(scene_obj, scene_data, pal):
    """Up to four bars rising from a baseline. Tallest bar uses primary accent."""
    add_top_bar(scene_obj, scene_data, pal)

    items = [s for s in (scene_data.get("visual_items") or scene_data.get("key_points") or []) if s][:4]
    if not items:
        items = [scene_data.get("headline", "value")]

    rng = random.Random(sum(ord(c) for c in (scene_data.get("slug") or "")))
    values = [0.5 + rng.random() * 0.9 for _ in items]
    max_val = max(values)

    base_y, max_h = -2.6, 4.0
    n, w, spacing = len(items), 0.9, 0.7
    total_w = n * w + (n - 1) * spacing
    start_x = -total_w / 2 + w / 2

    baseline = Line(LEFT * (total_w / 2 + 0.5), RIGHT * (total_w / 2 + 0.5), color=pal["soft"], stroke_width=3)
    baseline.move_to([0, base_y, 0])

    bars, labels, value_labels = VGroup(), VGroup(), VGroup()
    for i, (item, v) in enumerate(zip(items, values)):
        accent = pal["accent"] if v >= max_val - 0.001 else pal["accent_2"]
        bar = Rectangle(width=w, height=v * max_h, stroke_width=0, fill_color=accent, fill_opacity=1)
        bar.move_to([start_x + i * (w + spacing), base_y + (v * max_h) / 2, 0])
        bars.add(bar)
        labels.add(safe_text(item, font_size=19, color=pal["ink"], width=w + 0.5, wrap=14).next_to(bar, DOWN, buff=0.20))
        value_labels.add(safe_text(f"{int(v * 100)}", font_size=19, weight=BOLD, color=pal["ink"]).next_to(bar, UP, buff=0.12))

    chart = VGroup(baseline, bars, labels, value_labels)
    place_body(chart, top=CHROME_BOTTOM_Y - 0.4, max_height=5.4, max_width=11.0)

    initial_bars = [b.copy().stretch_to_fit_height(0.001).align_to(b, DOWN) for b in bars]
    for ib in initial_bars:
        scene_obj.add(ib)

    scene_obj.play(Create(baseline), run_time=0.4)
    scene_obj.play(LaggedStart(*[Transform(ib, b) for ib, b in zip(initial_bars, bars)], lag_ratio=0.12), run_time=1.3)
    scene_obj.play(LaggedStart(*[FadeIn(l, shift=UP * 0.05) for l in labels], lag_ratio=0.1), run_time=0.5)
    scene_obj.play(LaggedStart(*[FadeIn(v) for v in value_labels], lag_ratio=0.08), run_time=0.4)
    _hold(scene_obj, scene_data.get("target_duration_seconds", 14.0), 2.6)


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
