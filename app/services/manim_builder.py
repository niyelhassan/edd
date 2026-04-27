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

# Brand palette: monochrome + a single confident blue. Light theme only.
PALETTE = {
    "background": "#FAFAFB",
    "ink": "#0A0A0A",
    "ink_soft": "#171717",
    "muted": "#737373",
    "soft": "#E5E5E5",
    "panel": "#F4F4F5",
    "panel_2": "#FFFFFF",
    "accent": "#1D4ED8",
    "accent_2": "#0EA5E9",
    "accent_soft": "#DBEAFE",
    "good": "#059669",
    "warn": "#DC2626",
    "highlight": "#FACC15",
}


def palette():
    return PALETTE


# ---- typography helpers ----
SANS = "sans-serif"

# Render text at this base size and scale to the requested visual size.
# Pango produces noticeably better kerning at large rasterizations; scaling
# down preserves that quality while letting layouts request small visual sizes.
TEXT_BASE_FONT_SIZE = 96


def _wrap(text, width):
    text = (text or "").strip()
    if not text:
        return ""
    return "\\n".join(textwrap.wrap(text, width=width, break_long_words=False, break_on_hyphens=False))


def safe_text(text, *, font_size=24, color=None, weight=NORMAL, width=None, height=None, wrap=None, font=SANS):
    """Render text crisply: build at TEXT_BASE_FONT_SIZE, then scale to visual size.

    width / height clamp the result so it can never overflow its slot.
    """
    palette_ = palette()
    color = color or palette_["ink"]
    raw = str(text or "").strip()
    if wrap and raw:
        raw = _wrap(raw, wrap)
    obj = Text(
        raw or " ",
        font=font,
        font_size=TEXT_BASE_FONT_SIZE,
        color=color,
        weight=weight,
        line_spacing=0.95,
    )
    obj.scale(font_size / TEXT_BASE_FONT_SIZE)
    if width and obj.width > width:
        obj.scale_to_fit_width(width)
    if height and obj.height > height:
        obj.scale_to_fit_height(height)
    return obj


def safe_math(expr, *, color=None, font_size=48, max_width=10.5, max_height=2.6):
    palette_ = palette()
    color = color or palette_["ink"]
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


# ---- chrome helpers (eyebrow, footer, brand mark) ----
def make_eyebrow(text, palette_):
    obj = safe_text(
        (text or "").upper(),
        font_size=18,
        color=palette_["muted"],
        weight=BOLD,
        width=10.0,
        wrap=64,
    )
    return obj


def make_headline(text, palette_, *, max_width=11.0, wrap=42, font_size=46):
    return safe_text(text, font_size=font_size, weight=BOLD, color=palette_["ink"], width=max_width, wrap=wrap)


def make_subheadline(text, palette_, *, max_width=10.5, wrap=66, font_size=24):
    if not text:
        return None
    return safe_text(text, font_size=font_size, color=palette_["muted"], weight=NORMAL, width=max_width, wrap=wrap)


def make_brand_mark(palette_):
    mark = safe_text("lern", font_size=20, color=palette_["muted"], weight=SEMIBOLD)
    mark.set_opacity(0.55)
    return mark


def make_progress_dots(index, total, palette_):
    if total <= 1:
        return VGroup()
    dots = VGroup()
    for i in range(total):
        dot = Dot(radius=0.07, color=palette_["accent"] if i == index else palette_["soft"])
        dots.add(dot)
    dots.arrange(RIGHT, buff=0.16)
    counter = safe_text(
        f"{index + 1}/{total}",
        font_size=16, weight=SEMIBOLD, color=palette_["muted"],
    )
    counter.set_opacity(0.7)
    return VGroup(counter, dots).arrange(RIGHT, buff=0.28)


def setup_frame(scene_obj, scene_data, palette_, *, draw_accent_bar=True):
    scene_obj.camera.background_color = palette_["background"]

    if draw_accent_bar:
        accent_bar = Rectangle(
            height=8.0, width=0.16,
            stroke_width=0,
            fill_color=palette_["accent"],
            fill_opacity=1,
        ).to_edge(LEFT, buff=0)
        scene_obj.add(accent_bar)

    brand = make_brand_mark(palette_).to_corner(DR, buff=0.45)
    scene_obj.add(brand)

    scene_index = int(scene_data.get("scene_number", 1)) - 1
    total = int(scene_data.get("scene_total", len(SCENES)) or len(SCENES))
    dots = make_progress_dots(scene_index, total, palette_)
    if len(dots):
        dots.to_corner(DL, buff=0.55)
        scene_obj.add(dots)


CHROME_BOTTOM_Y = 1.95  # body content should anchor below this y value


def add_top_bar(scene_obj, scene_data, palette_):
    """Set up brand chrome + top bar with eyebrow (lesson title) and headline."""
    setup_frame(scene_obj, scene_data, palette_)
    eyebrow_text = (TITLE or "Lesson").strip()
    headline_text = scene_data.get("headline", "").strip()

    # Avoid eyebrow that simply repeats the headline.
    show_eyebrow = _is_distinct(eyebrow_text, headline_text)

    eyebrow = make_eyebrow(eyebrow_text, palette_) if show_eyebrow else None
    headline = make_headline(headline_text, palette_, max_width=11.0, wrap=46)

    if eyebrow is not None:
        eyebrow.to_edge(UP, buff=0.55).to_edge(LEFT, buff=0.85)
        headline.next_to(eyebrow, DOWN, buff=0.22, aligned_edge=LEFT)
    else:
        headline.to_edge(UP, buff=0.65).to_edge(LEFT, buff=0.85)

    underline = Line(
        headline.get_corner(DL) + DOWN * 0.18,
        headline.get_corner(DL) + DOWN * 0.18 + RIGHT * min(1.6, headline.width * 0.28),
        color=palette_["accent"],
        stroke_width=4,
    )

    if eyebrow is not None:
        scene_obj.play(FadeIn(eyebrow, shift=DOWN * 0.1), run_time=0.35)
    scene_obj.play(
        Write(headline, run_time=0.6),
        Create(underline, run_time=0.5),
    )
    parts = [eyebrow, headline, underline] if eyebrow is not None else [headline, underline]
    return VGroup(*parts)


def place_body(group, *, top=None, center_x=0.0, max_height=None, max_width=None):
    """Position a body group below the chrome and recenter horizontally.

    If max_height/max_width are given, the group is scaled down to fit.
    """
    if max_width and group.width > max_width:
        group.scale_to_fit_width(max_width)
    top_y = top if top is not None else CHROME_BOTTOM_Y - 0.4
    bottom_limit = -3.7
    available_h = top_y - bottom_limit
    if max_height is not None:
        available_h = min(available_h, max_height)
    if group.height > available_h:
        group.scale_to_fit_height(available_h)
    group.move_to([center_x, top_y - group.height / 2, 0])
    return group


# ---- per-template builders ----
def _node_label(text, palette_, *, fill, font_color=None, width=2.0, height=0.9, font_size=22, corner=0.18):
    box = RoundedRectangle(
        corner_radius=corner, width=width, height=height,
        stroke_width=0, fill_color=fill, fill_opacity=1.0,
    )
    label = safe_text(
        text, font_size=font_size,
        color=font_color or "#FFFFFF",
        weight=SEMIBOLD,
        width=width - 0.4,
        height=height - 0.3,
        wrap=18,
    )
    return VGroup(box, label.move_to(box))


def render_title_card(scene_obj, scene_data, palette_):
    """Cinematic title card: lesson title big, supporting subtitle, no repeats.

    The viewer should see exactly two distinct pieces of text:
      - the lesson title (big), and
      - one supporting line (the scene's hook OR the lesson's learning objective).
    Anything that duplicates the title is suppressed.
    """
    setup_frame(scene_obj, scene_data, palette_, draw_accent_bar=False)

    lesson_title = (TITLE or scene_data.get("headline") or "Lesson").strip()
    eyebrow_text = "TODAY'S LESSON"

    # Pick a non-duplicating subtitle: prefer scene hook, fall back to learning objective / summary.
    candidates = [
        scene_data.get("hook"),
        scene_data.get("takeaway"),
        STORY.get("learning_objective"),
        STORY.get("summary"),
    ]
    subtitle_text = ""
    for c in candidates:
        if _is_distinct(c, lesson_title, eyebrow_text):
            subtitle_text = (c or "").strip()
            break

    eyebrow = safe_text(eyebrow_text, font_size=18, weight=BOLD, color=palette_["muted"], width=10.0)
    accent_line = Rectangle(
        height=0.10, width=1.6,
        stroke_width=0,
        fill_color=palette_["accent"], fill_opacity=1,
    )
    headline = safe_text(
        lesson_title,
        font_size=70, weight=BOLD, color=palette_["ink"],
        width=11.5, wrap=24,
    )
    subtitle = (
        safe_text(subtitle_text, font_size=26, weight=NORMAL, color=palette_["muted"], width=10.5, wrap=58)
        if subtitle_text else None
    )

    parts = [eyebrow, accent_line, headline]
    if subtitle is not None:
        parts.append(subtitle)
    group = VGroup(*parts).arrange(DOWN, buff=0.42, aligned_edge=LEFT)

    # Soft accent shape, top right, for visual interest.
    halo = Circle(
        radius=1.6, color=palette_["accent_soft"], stroke_width=0,
        fill_color=palette_["accent_soft"], fill_opacity=1,
    ).to_corner(UR, buff=0).shift(RIGHT * 0.6 + UP * 0.5)
    halo.set_z_index(-1)

    accent_dot = Dot(radius=0.18, color=palette_["accent"]).move_to(halo.get_center())
    accent_dot.set_z_index(-1)

    group.move_to(ORIGIN).shift(LEFT * 0.4 + DOWN * 0.1)

    scene_obj.add(halo, accent_dot)
    scene_obj.play(FadeIn(eyebrow, shift=DOWN * 0.15), run_time=0.4)
    scene_obj.play(GrowFromCenter(accent_line), run_time=0.35)
    scene_obj.play(Write(headline), run_time=1.0)
    if subtitle is not None:
        scene_obj.play(FadeIn(subtitle, shift=UP * 0.1), run_time=0.5)

    total = max(6.0, float(scene_data.get("target_duration_seconds", 8.0)))
    scene_obj.wait(max(0.5, total - 2.6))


def render_summary(scene_obj, scene_data, palette_):
    """Closing takeaways: large takeaway phrase + checkmark bullets, all distinct."""
    chrome = add_top_bar(scene_obj, scene_data, palette_)

    headline = scene_data.get("headline", "")
    takeaway = (scene_data.get("takeaway") or "").strip()
    fallback_takeaway = (STORY.get("closing_takeaway") or "").strip()
    if not _is_distinct(takeaway, headline):
        takeaway = fallback_takeaway if _is_distinct(fallback_takeaway, headline) else takeaway

    bullets = []
    seen = {_norm(headline), _norm(takeaway)}
    for b in (scene_data.get("key_points") or []):
        n = _norm(b)
        if not n or n in seen:
            continue
        seen.add(n)
        bullets.append(b)
        if len(bullets) >= 3:
            break

    big = safe_text(
        takeaway or "Key takeaway",
        font_size=36, weight=BOLD, color=palette_["accent"],
        width=11.5, wrap=42,
    )

    items = VGroup()
    for line in bullets:
        check = Triangle(color=palette_["good"], fill_opacity=1).scale(0.16).rotate(-PI / 2)
        text = safe_text(line, font_size=24, color=palette_["ink"], width=9.5, wrap=64)
        row = VGroup(check, text).arrange(RIGHT, buff=0.32, aligned_edge=UP)
        items.add(row)
    if len(items):
        items.arrange(DOWN, buff=0.32, aligned_edge=LEFT)

    body_parts = [big]
    if len(items):
        body_parts.append(items)
    body = VGroup(*body_parts).arrange(DOWN, buff=0.55, aligned_edge=LEFT)
    place_body(body, top=CHROME_BOTTOM_Y - 0.4, center_x=-0.5, max_height=4.6, max_width=11.5)

    scene_obj.play(FadeIn(big, shift=UP * 0.15), run_time=0.6)
    if len(items):
        scene_obj.play(LaggedStart(*[FadeIn(row, shift=RIGHT * 0.2) for row in items], lag_ratio=0.2), run_time=1.0)

    total = max(7.0, float(scene_data.get("target_duration_seconds", 12.0)))
    scene_obj.wait(max(0.6, total - 2.5))


def render_bullets(scene_obj, scene_data, palette_):
    """Centered hook + clean bullet list. Used when no more visual layout fits."""
    chrome = add_top_bar(scene_obj, scene_data, palette_)

    headline = scene_data.get("headline", "")
    hook = (scene_data.get("hook") or "").strip()
    if not _is_distinct(hook, headline):
        hook = ""
    takeaway = (scene_data.get("takeaway") or "").strip()
    if not hook and _is_distinct(takeaway, headline):
        hook = takeaway

    raw_bullets = scene_data.get("key_points") or scene_data.get("visual_items") or []
    bullets = []
    seen = {_norm(headline), _norm(hook)}
    for b in raw_bullets:
        n = _norm(b)
        if not n or n in seen:
            continue
        seen.add(n)
        bullets.append(b)
        if len(bullets) >= 3:
            break

    hook_text = safe_text(hook, font_size=30, weight=SEMIBOLD, color=palette_["accent"], width=10.5, wrap=58) if hook else None

    rows = VGroup()
    for i, line in enumerate(bullets):
        bullet_bg = Circle(radius=0.22, color=palette_["accent"] if i == 0 else palette_["accent_2"],
                           stroke_width=0, fill_color=palette_["accent"] if i == 0 else palette_["accent_2"], fill_opacity=1)
        idx_label = safe_text(str(i + 1), font_size=20, weight=BOLD, color="#FFFFFF").move_to(bullet_bg)
        idx = VGroup(bullet_bg, idx_label)
        text = safe_text(line, font_size=24, color=palette_["ink"], width=8.8, wrap=64)
        rows.add(VGroup(idx, text).arrange(RIGHT, buff=0.42, aligned_edge=UP))
    if len(rows):
        rows.arrange(DOWN, buff=0.45, aligned_edge=LEFT)

    body_parts = [m for m in (hook_text, rows) if m is not None and (not isinstance(m, VGroup) or len(m))]
    body = VGroup(*body_parts).arrange(DOWN, buff=0.6, aligned_edge=LEFT)
    place_body(body, top=CHROME_BOTTOM_Y - 0.5, center_x=-0.3, max_height=5.0, max_width=11.0)

    if hook_text is not None:
        scene_obj.play(FadeIn(hook_text, shift=UP * 0.1), run_time=0.45)
    for row in rows:
        scene_obj.play(FadeIn(row[0], scale=0.85), FadeIn(row[1], shift=RIGHT * 0.12), run_time=0.4)

    total = max(7.0, float(scene_data.get("target_duration_seconds", 12.0)))
    scene_obj.wait(max(0.5, total - (1.0 + 0.45 * (len(rows) + 1))))


def build_concept_visual(scene_data, palette_, compact=False):
    """Hub-and-spoke concept map. Used standalone or as an inset."""
    items = ([i for i in (scene_data.get("visual_items") or []) if i][:3]
             or [i for i in (scene_data.get("highlight_terms") or []) if i][:3]
             or [i for i in (scene_data.get("key_points") or []) if i][:3])
    center_label = (scene_data.get("highlight_terms") or [scene_data.get("headline", "Idea")])[0]
    center = Circle(radius=0.95, color=palette_["accent"], stroke_width=4).set_fill(palette_["accent"], opacity=0.10)
    center_text = safe_text(center_label, font_size=22, weight=BOLD, color=palette_["ink"], width=1.55, height=1.0, wrap=12)
    hub = VGroup(center, center_text)

    angles = [PI / 2, PI / 2 + 2 * PI / 3, PI / 2 + 4 * PI / 3]
    radius = 2.4
    nodes = VGroup(hub)
    for i, item in enumerate(items[:3]):
        pos = np.array([math.cos(angles[i]) * radius, math.sin(angles[i]) * radius, 0])
        accent = palette_["accent"] if i % 2 == 0 else palette_["accent_2"]
        node = _node_label(item, palette_, fill=accent, width=2.5, height=0.95, font_size=20)
        node.move_to(pos)
        line = Line(hub.get_center(), node.get_center(), color=palette_["soft"], stroke_width=3)
        nodes.add(line, node)
    return nodes


def render_concept_map(scene_obj, scene_data, palette_):
    chrome = add_top_bar(scene_obj, scene_data, palette_)
    visual = build_concept_visual(scene_data, palette_)
    place_body(visual, top=CHROME_BOTTOM_Y - 0.3, max_height=5.2, max_width=10.5)

    intro = []
    for m in visual:
        if isinstance(m, Line):
            intro.append(Create(m))
        elif isinstance(m, VGroup):
            intro.append(FadeIn(m, scale=0.85))
        else:
            intro.append(GrowFromCenter(m))
    scene_obj.play(LaggedStart(*intro, lag_ratio=0.10), run_time=1.4)

    total = max(7.0, float(scene_data.get("target_duration_seconds", 12.0)))
    scene_obj.wait(max(0.6, total - 2.6))


def render_equation(scene_obj, scene_data, palette_):
    """Single equation builds in piece by piece with annotation chips."""
    chrome = add_top_bar(scene_obj, scene_data, palette_)

    expr_list = [e for e in (scene_data.get("equations") or []) if e]
    primary = expr_list[0] if expr_list else None
    secondary = expr_list[1] if len(expr_list) > 1 else None

    eq_main = safe_math(primary, color=palette_["ink"], font_size=64, max_width=10.5) if primary else None
    eq_secondary = safe_math(secondary, color=palette_["muted"], font_size=42, max_width=9.5) if secondary else None
    if eq_main is None:
        eq_main = safe_text(scene_data.get("hook") or scene_data.get("headline") or "Idea",
                            font_size=48, weight=BOLD, color=palette_["ink"], width=10.0, wrap=22)

    rays = VGroup()
    for i in range(8):
        angle = i * PI / 4
        ray = Line(
            np.array([math.cos(angle) * 0.6, math.sin(angle) * 0.6, 0]),
            np.array([math.cos(angle) * 1.1, math.sin(angle) * 1.1, 0]),
            color=palette_["accent_2"], stroke_width=3,
        ).set_opacity(0.25)
        rays.add(ray)
    rays.move_to(eq_main.get_center())

    annotations = VGroup()
    terms = [t for t in (scene_data.get("highlight_terms") or []) if t][:3]
    if terms:
        for i, t in enumerate(terms):
            chip_bg = RoundedRectangle(corner_radius=0.18, width=2.8, height=0.6, stroke_width=0,
                                       fill_color=palette_["panel"], fill_opacity=1)
            chip_text = safe_text(t, font_size=18, weight=SEMIBOLD, color=palette_["ink_soft"],
                                  width=2.4, height=0.4, wrap=22)
            chip = VGroup(chip_bg, chip_text.move_to(chip_bg))
            annotations.add(chip)
        annotations.arrange(RIGHT, buff=0.3)

    layout_items = [eq_main]
    if eq_secondary is not None:
        layout_items.append(eq_secondary)
    if len(annotations):
        layout_items.append(annotations)
    body = VGroup(*layout_items).arrange(DOWN, buff=0.5)
    place_body(body, top=CHROME_BOTTOM_Y - 0.5, max_height=4.8, max_width=11.5)

    scene_obj.play(FadeIn(rays.move_to(eq_main.get_center()), scale=0.8), run_time=0.6)
    scene_obj.play(Write(eq_main), run_time=1.4)
    if eq_secondary is not None:
        scene_obj.play(Write(eq_secondary), run_time=0.9)
    if len(annotations):
        scene_obj.play(LaggedStart(*[FadeIn(c, shift=UP * 0.1) for c in annotations], lag_ratio=0.15), run_time=0.7)

    pulse = Circle(radius=eq_main.height * 0.85, color=palette_["accent"], stroke_width=2).set_opacity(0)
    pulse.move_to(eq_main)
    scene_obj.add(pulse)
    scene_obj.play(pulse.animate.scale(1.4).set_opacity(0.0), run_time=1.2)
    scene_obj.remove(pulse)

    total = max(8.0, float(scene_data.get("target_duration_seconds", 14.0)))
    scene_obj.wait(max(0.5, total - 4.2))


def render_distribution(scene_obj, scene_data, palette_):
    """Bell curve with shaded tail (p-value / probability visualizations)."""
    chrome = add_top_bar(scene_obj, scene_data, palette_)

    axes = Axes(
        x_range=[-3.5, 3.5, 1], y_range=[0, 0.5, 0.1],
        x_length=8.6, y_length=3.6,
        axis_config={"color": palette_["muted"], "stroke_width": 2, "include_ticks": True, "tip_width": 0.18, "tip_height": 0.18},
        tips=False,
    )
    axes.move_to([0, -0.7, 0])

    def normal(x):
        return math.exp(-x * x / 2) / math.sqrt(2 * math.pi)

    curve = axes.plot(normal, x_range=[-3.4, 3.4], color=palette_["ink"], stroke_width=4)

    threshold_label = "Tail area"
    terms = [t for t in (scene_data.get("highlight_terms") or []) if t]
    if terms:
        threshold_label = terms[-1]
    cutoff = 1.65

    shade = axes.get_area(curve, x_range=[cutoff, 3.4], color=palette_["accent"], opacity=0.45)
    threshold_line = DashedLine(
        axes.c2p(cutoff, 0), axes.c2p(cutoff, normal(cutoff)),
        color=palette_["accent"], dash_length=0.12, stroke_width=3,
    )

    label = safe_text(threshold_label, font_size=20, weight=SEMIBOLD, color=palette_["accent"], width=2.6, wrap=22)
    label.next_to(shade, RIGHT, buff=0.3)

    x_axis_label = safe_text(
        (terms[0] if terms else "test statistic"),
        font_size=20, color=palette_["muted"], width=2.6, wrap=22,
    )
    x_axis_label.next_to(axes.x_axis, RIGHT, buff=0.18)

    null_label = safe_text("Null distribution", font_size=20, color=palette_["muted"], width=3.0)
    null_label.next_to(axes.c2p(-1.5, normal(-1.5)), UP, buff=0.2)

    scene_obj.play(Create(axes, run_time=0.7))
    scene_obj.play(Create(curve, run_time=1.4))
    scene_obj.play(FadeIn(null_label, shift=UP * 0.1), FadeIn(x_axis_label, shift=RIGHT * 0.1), run_time=0.5)
    scene_obj.play(Create(threshold_line), run_time=0.5)
    scene_obj.play(FadeIn(shade, shift=RIGHT * 0.1), FadeIn(label, shift=LEFT * 0.1), run_time=0.7)

    total = max(8.0, float(scene_data.get("target_duration_seconds", 14.0)))
    scene_obj.wait(max(0.5, total - 3.8))


def render_axes_plot(scene_obj, scene_data, palette_):
    """Generic XY plot: draws a function curve plus markers."""
    chrome = add_top_bar(scene_obj, scene_data, palette_)

    axes = Axes(
        x_range=[-4, 4, 1], y_range=[-2.5, 2.5, 1],
        x_length=8.6, y_length=4.0,
        axis_config={"color": palette_["muted"], "stroke_width": 2},
        tips=False,
    )
    axes.move_to([0, -0.6, 0])

    items = [s for s in (scene_data.get("highlight_terms") or []) if s]
    x_lab = safe_text(items[0] if items else "x", font_size=20, color=palette_["muted"]).next_to(axes.x_axis, RIGHT, buff=0.18)
    y_lab = safe_text(items[1] if len(items) > 1 else "y", font_size=20, color=palette_["muted"]).next_to(axes.y_axis, UP, buff=0.18)

    head = (scene_data.get("headline") or "").lower()
    hook = (scene_data.get("hook") or "").lower()
    text_blob = head + " " + hook

    if any(w in text_blob for w in ("exp", "growth", "decay")):
        fn = lambda x: 1.6 * math.exp(0.5 * x) / math.exp(2.0)
    elif any(w in text_blob for w in ("sin", "wave", "oscill", "period")):
        fn = lambda x: 2.0 * math.sin(1.4 * x)
    elif any(w in text_blob for w in ("log",)):
        fn = lambda x: math.log(max(x + 4.1, 0.05))
    elif any(w in text_blob for w in ("quad", "parab", "square")):
        fn = lambda x: 0.4 * x * x - 1.5
    else:
        fn = lambda x: 0.5 * x + 0.4 * math.sin(1.6 * x)

    curve = axes.plot(fn, x_range=[-3.8, 3.8], color=palette_["accent"], stroke_width=4)

    markers = VGroup()
    items_for_points = [s for s in (scene_data.get("visual_items") or scene_data.get("key_points") or []) if s][:3]
    sample_xs = [-2.4, 0.4, 2.2]
    for i, label_str in enumerate(items_for_points):
        x = sample_xs[i % 3]
        try:
            y = fn(x)
        except Exception:
            y = 0
        pt = Dot(axes.c2p(x, y), radius=0.10, color=palette_["accent_2"])
        lab = safe_text(label_str, font_size=20, color=palette_["ink"], width=3.0, wrap=24)
        lab.next_to(pt, UR if i % 2 == 0 else UL, buff=0.18)
        markers.add(pt, lab)

    scene_obj.play(Create(axes, run_time=0.6))
    scene_obj.play(FadeIn(x_lab, shift=RIGHT * 0.1), FadeIn(y_lab, shift=UP * 0.1), run_time=0.4)
    scene_obj.play(Create(curve, run_time=1.4))
    if len(markers):
        scene_obj.play(LaggedStart(*[FadeIn(m, shift=UP * 0.1) for m in markers], lag_ratio=0.12), run_time=0.9)

    total = max(8.0, float(scene_data.get("target_duration_seconds", 14.0)))
    scene_obj.wait(max(0.5, total - 3.6))


def render_comparison(scene_obj, scene_data, palette_):
    """Side-by-side panel comparison."""
    chrome = add_top_bar(scene_obj, scene_data, palette_)

    items = [s for s in (scene_data.get("visual_items") or []) if s]
    points = [s for s in (scene_data.get("key_points") or []) if s]
    left_title = items[0] if items else "Approach A"
    right_title = items[1] if len(items) > 1 else "Approach B"

    def panel(label, sub_lines, fill, accent):
        bg = RoundedRectangle(corner_radius=0.28, width=4.9, height=4.6, stroke_width=0,
                              fill_color=fill, fill_opacity=1.0)
        title = safe_text(label, font_size=28, weight=BOLD, color=accent, width=4.4, wrap=22)
        title.move_to(bg.get_top() + DOWN * 0.55)
        rows = VGroup()
        for line in sub_lines[:3]:
            r = safe_text(line, font_size=20, color=palette_["ink"], width=4.4, wrap=30)
            rows.add(r)
        if len(rows):
            rows.arrange(DOWN, buff=0.28, aligned_edge=LEFT)
            rows.move_to(bg.get_center() + DOWN * 0.2)
        accent_bar = Rectangle(width=4.0, height=0.06, stroke_width=0, fill_color=accent, fill_opacity=1)
        accent_bar.next_to(title, DOWN, buff=0.18)
        return VGroup(bg, title, accent_bar, rows)

    left_lines = points[:3] if items else points[:3]
    right_lines = points[3:6] if len(points) > 3 else (points[:3] if not items else [])

    left = panel(left_title, left_lines, palette_["panel"], palette_["accent"])
    right = panel(right_title, right_lines, palette_["panel_2"], palette_["accent_2"])
    right[0].set_stroke(palette_["soft"], width=2)

    pair = VGroup(left, right).arrange(RIGHT, buff=0.6)
    place_body(pair, top=CHROME_BOTTOM_Y - 0.3, max_height=5.2, max_width=11.5)

    vs = Circle(radius=0.45, color=palette_["ink"], stroke_width=3).set_fill(palette_["background"], opacity=1)
    vs_label = safe_text("vs", font_size=22, weight=BOLD, color=palette_["ink"])
    vs_group = VGroup(vs, vs_label.move_to(vs)).move_to(pair.get_center())

    scene_obj.play(FadeIn(left, shift=LEFT * 0.2), FadeIn(right, shift=RIGHT * 0.2), run_time=0.7)
    scene_obj.play(GrowFromCenter(vs_group), run_time=0.4)

    total = max(8.0, float(scene_data.get("target_duration_seconds", 14.0)))
    scene_obj.wait(max(0.5, total - 2.5))


def render_timeline(scene_obj, scene_data, palette_):
    """Horizontal timeline with 3-4 nodes; a marker glides through."""
    chrome = add_top_bar(scene_obj, scene_data, palette_)

    items = [s for s in (scene_data.get("visual_items") or scene_data.get("key_points") or []) if s][:4]
    if not items:
        items = [scene_data.get("headline", "Step")]

    base = Line(LEFT * 5.2, RIGHT * 5.2, color=palette_["soft"], stroke_width=4)
    base.move_to([0, -0.3, 0])

    n = len(items)
    if n == 1:
        offsets = [0.0]
    else:
        offsets = [(-5.0 + i * (10.0 / (n - 1))) for i in range(n)]

    nodes = VGroup()
    labels = VGroup()
    for i, (offset, item) in enumerate(zip(offsets, items)):
        accent = palette_["accent"] if i % 2 == 0 else palette_["accent_2"]
        outer = Circle(radius=0.22, color=accent, stroke_width=3, fill_color=palette_["background"], fill_opacity=1)
        inner = Dot(radius=0.10, color=accent)
        node = VGroup(outer, inner).move_to(base.get_center() + RIGHT * offset)
        nodes.add(node)
        label = safe_text(item, font_size=20, color=palette_["ink"], width=2.4, wrap=18)
        label.next_to(node, UP if i % 2 == 0 else DOWN, buff=0.35)
        labels.add(label)

    marker = Triangle(color=palette_["accent"], fill_opacity=1).scale(0.18)
    marker.next_to(nodes[0], UP, buff=0.05)

    scene_obj.play(Create(base), run_time=0.5)
    scene_obj.play(LaggedStart(*[GrowFromCenter(n) for n in nodes], lag_ratio=0.15), run_time=1.0)
    scene_obj.play(LaggedStart(*[FadeIn(l, shift=UP * 0.1) for l in labels], lag_ratio=0.12), run_time=0.9)
    scene_obj.play(FadeIn(marker, shift=DOWN * 0.05), run_time=0.3)
    if len(nodes) > 1:
        for n_idx in range(1, len(nodes)):
            scene_obj.play(marker.animate.next_to(nodes[n_idx], UP, buff=0.05), run_time=0.55)

    total = max(8.0, float(scene_data.get("target_duration_seconds", 14.0)))
    scene_obj.wait(max(0.4, total - 4.0))


def render_flow(scene_obj, scene_data, palette_):
    """Pipeline of 3-4 steps with arrows, packets traverse the arrows."""
    chrome = add_top_bar(scene_obj, scene_data, palette_)

    items = [s for s in (scene_data.get("visual_items") or scene_data.get("key_points") or []) if s][:4]
    if len(items) < 2:
        items = items + [(scene_data.get("highlight_terms") or [scene_data.get("headline", "step")])[0]]
    n = len(items)

    boxes = VGroup()
    arrows = VGroup()
    width = 2.2
    spacing = 0.9
    total_width = n * width + (n - 1) * spacing
    start_x = -total_width / 2 + width / 2
    for i, item in enumerate(items):
        accent = palette_["accent"] if i % 2 == 0 else palette_["accent_2"]
        node = _node_label(item, palette_, fill=accent, width=width, height=1.0, font_size=18, corner=0.2)
        node.move_to(np.array([start_x + i * (width + spacing), 0, 0]))
        boxes.add(node)
        if i > 0:
            prev = boxes[i - 1]
            arrow = Arrow(prev.get_right() + RIGHT * 0.05, node.get_left() + LEFT * 0.05,
                          color=palette_["muted"], stroke_width=4, buff=0.06,
                          tip_length=0.18, max_tip_length_to_length_ratio=0.35)
            arrows.add(arrow)
    pipeline = VGroup(boxes, arrows)
    place_body(pipeline, top=CHROME_BOTTOM_Y - 0.5, max_height=4.5, max_width=11.5)

    scene_obj.play(LaggedStart(*[GrowFromCenter(b) for b in boxes], lag_ratio=0.12), run_time=1.0)
    if len(arrows):
        scene_obj.play(LaggedStart(*[Create(a) for a in arrows], lag_ratio=0.15), run_time=0.7)

    if len(arrows):
        for arrow in arrows:
            packet = Dot(radius=0.10, color=palette_["highlight"]).move_to(arrow.get_start())
            scene_obj.add(packet)
            scene_obj.play(packet.animate.move_to(arrow.get_end()), run_time=0.45)
            scene_obj.remove(packet)

    total = max(8.0, float(scene_data.get("target_duration_seconds", 14.0)))
    scene_obj.wait(max(0.4, total - 4.4))


def render_orbit(scene_obj, scene_data, palette_):
    """Center node with orbiting satellites; continuous rotation while narration plays."""
    chrome = add_top_bar(scene_obj, scene_data, palette_)

    center_label = (scene_data.get("highlight_terms") or [scene_data.get("headline", "Core")])[0]
    center = Circle(radius=0.85, color=palette_["accent"], stroke_width=4).set_fill(palette_["accent"], opacity=0.10)
    center_text = safe_text(center_label, font_size=20, weight=BOLD, color=palette_["ink"], width=1.4, wrap=12)
    hub_center_y = -0.9
    hub = VGroup(center, center_text).move_to([0, hub_center_y, 0])

    orbit_radius = 2.4
    orbit = Circle(radius=orbit_radius, color=palette_["soft"], stroke_width=2).move_to(hub.get_center())

    items = [s for s in (scene_data.get("visual_items") or scene_data.get("highlight_terms") or [])[1:] if s][:3]
    satellites = VGroup()
    base_angle = ValueTracker(0)
    sat_data = []
    for i, item in enumerate(items):
        accent = palette_["accent"] if i % 2 == 0 else palette_["accent_2"]
        node = _node_label(item, palette_, fill=accent, width=2.0, height=0.78, font_size=18)
        sat_data.append((node, i * 2 * PI / max(len(items), 1)))
        satellites.add(node)

    def make_updater(node, phase):
        def updater(m):
            angle = base_angle.get_value() + phase
            center_pt = hub.get_center()
            m.move_to(center_pt + np.array([math.cos(angle) * orbit_radius, math.sin(angle) * orbit_radius, 0]))
        return updater

    for node, phase in sat_data:
        node.add_updater(make_updater(node, phase))
        node.update()

    scene_obj.play(Create(orbit), run_time=0.6)
    scene_obj.play(GrowFromCenter(hub), run_time=0.5)
    if len(satellites):
        scene_obj.play(LaggedStart(*[FadeIn(s) for s in satellites], lag_ratio=0.15), run_time=0.7)

    total = max(8.0, float(scene_data.get("target_duration_seconds", 14.0)))
    rotate_time = max(2.0, total - 2.5)
    scene_obj.play(base_angle.animate.set_value(2 * PI), run_time=rotate_time, rate_func=linear)
    for node, _ in sat_data:
        node.clear_updaters()
    scene_obj.wait(0.4)


def render_bar_chart(scene_obj, scene_data, palette_):
    """Animated bar chart growing from baseline."""
    chrome = add_top_bar(scene_obj, scene_data, palette_)

    items = [s for s in (scene_data.get("visual_items") or scene_data.get("key_points") or []) if s][:4]
    if not items:
        items = [scene_data.get("headline", "value")]

    rng = random.Random(sum(ord(c) for c in (scene_data.get("slug") or "")))
    values = [0.5 + rng.random() * 0.9 for _ in items]

    base_y = -2.6
    max_h = 4.0
    n = len(items)
    width = 0.9
    spacing = 0.7
    total_w = n * width + (n - 1) * spacing
    start_x = -total_w / 2 + width / 2

    baseline = Line(LEFT * (total_w / 2 + 0.5), RIGHT * (total_w / 2 + 0.5), color=palette_["soft"], stroke_width=3)
    baseline.move_to([0, base_y, 0])

    bars = VGroup()
    labels = VGroup()
    value_labels = VGroup()
    for i, (item, v) in enumerate(zip(items, values)):
        accent = palette_["accent"] if v >= max(values) - 0.001 else (palette_["accent_2"] if i % 2 else palette_["muted"])
        bar = Rectangle(width=width, height=v * max_h, stroke_width=0, fill_color=accent, fill_opacity=1)
        bar.move_to([start_x + i * (width + spacing), base_y + (v * max_h) / 2, 0])
        bars.add(bar)
        lbl = safe_text(item, font_size=20, color=palette_["ink"], width=width + 0.5, wrap=14)
        lbl.next_to(bar, DOWN, buff=0.20)
        labels.add(lbl)
        vlabel = safe_text(f"{int(v * 100)}", font_size=20, weight=BOLD, color=palette_["ink"])
        vlabel.next_to(bar, UP, buff=0.12)
        value_labels.add(vlabel)

    chart = VGroup(baseline, bars, labels, value_labels)
    place_body(chart, top=CHROME_BOTTOM_Y - 0.4, max_height=5.4, max_width=11.0)

    initial_bars = [bar.copy().stretch_to_fit_height(0.001).align_to(bar, DOWN) for bar in bars]
    for ib, b in zip(initial_bars, bars):
        scene_obj.add(ib)

    scene_obj.play(Create(baseline), run_time=0.4)
    scene_obj.play(LaggedStart(*[Transform(ib, b) for ib, b in zip(initial_bars, bars)], lag_ratio=0.12), run_time=1.4)
    scene_obj.play(LaggedStart(*[FadeIn(l, shift=UP * 0.05) for l in labels], lag_ratio=0.1), run_time=0.6)
    scene_obj.play(LaggedStart(*[FadeIn(v) for v in value_labels], lag_ratio=0.08), run_time=0.5)

    total = max(8.0, float(scene_data.get("target_duration_seconds", 14.0)))
    scene_obj.wait(max(0.5, total - 4.0))


def render_process(scene_obj, scene_data, palette_):
    """Vertical step list, each step appearing in turn with a connector."""
    chrome = add_top_bar(scene_obj, scene_data, palette_)

    items = [s for s in (scene_data.get("key_points") or scene_data.get("visual_items") or []) if s][:4]
    if not items:
        items = [scene_data.get("hook") or scene_data.get("headline", "Step")]

    rows = VGroup()
    connectors = VGroup()
    for i, item in enumerate(items):
        num_bg = Circle(radius=0.32, color=palette_["accent"], stroke_width=0,
                        fill_color=palette_["accent"], fill_opacity=1)
        num = safe_text(str(i + 1), font_size=22, weight=BOLD, color="#FFFFFF").move_to(num_bg)
        idx = VGroup(num_bg, num)
        text = safe_text(item, font_size=22, color=palette_["ink"], width=8.5, wrap=66)
        row = VGroup(idx, text).arrange(RIGHT, buff=0.42, aligned_edge=UP)
        rows.add(row)
    rows.arrange(DOWN, buff=0.55, aligned_edge=LEFT)
    place_body(rows, top=CHROME_BOTTOM_Y - 0.5, center_x=-0.5, max_height=5.0, max_width=11.0)

    for i in range(len(rows) - 1):
        a = rows[i][0].get_center() + DOWN * 0.32
        b = rows[i + 1][0].get_center() + UP * 0.32
        seg = DashedLine(a, b, color=palette_["soft"], dash_length=0.1, stroke_width=2)
        connectors.add(seg)

    for i, row in enumerate(rows):
        scene_obj.play(FadeIn(row[0], scale=0.85), run_time=0.25)
        scene_obj.play(Write(row[1], run_time=0.55))
        if i < len(connectors):
            scene_obj.play(Create(connectors[i]), run_time=0.25)

    total = max(8.0, float(scene_data.get("target_duration_seconds", 14.0)))
    scene_obj.wait(max(0.4, total - (len(rows) * 1.05 + 1.0)))


def render_network(scene_obj, scene_data, palette_):
    """Graph of nodes connected by edges; edges pulse to show flow."""
    chrome = add_top_bar(scene_obj, scene_data, palette_)

    items = [s for s in (scene_data.get("visual_items") or scene_data.get("highlight_terms") or scene_data.get("key_points") or []) if s][:5]
    if len(items) < 3:
        seed = (scene_data.get("highlight_terms") or [scene_data.get("headline", "node")])[0]
        items = [seed, "input", "output", "state"][: max(3, len(items))]
    n = len(items)

    rng = random.Random(sum(ord(c) for c in (scene_data.get("slug") or "n")))
    radius = 2.5
    positions = []
    for i in range(n):
        angle = 2 * PI * i / n + rng.random() * 0.2
        r = radius * (0.85 + rng.random() * 0.3)
        positions.append(np.array([math.cos(angle) * r, math.sin(angle) * r * 0.85, 0]))

    nodes = VGroup()
    for i, (item, pos) in enumerate(zip(items, positions)):
        accent = palette_["accent"] if i == 0 else palette_["accent_2"]
        outer = Circle(radius=0.55, color=accent, stroke_width=3,
                       fill_color=palette_["panel_2"],
                       fill_opacity=1.0)
        label = safe_text(item, font_size=18, color=palette_["ink"], width=1.0, height=0.7, wrap=10).move_to(outer)
        node = VGroup(outer, label).move_to(pos)
        nodes.add(node)

    edges = VGroup()
    edge_pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            if rng.random() < 0.6 or j - i == 1:
                edge_pairs.append((i, j))
    for i, j in edge_pairs:
        edge = Line(nodes[i].get_center(), nodes[j].get_center(),
                    color=palette_["soft"], stroke_width=2)
        edges.add(edge)

    graph = VGroup(edges, nodes).move_to([0, -0.7, 0])

    scene_obj.play(LaggedStart(*[Create(e) for e in edges], lag_ratio=0.05), run_time=0.8)
    scene_obj.play(LaggedStart(*[GrowFromCenter(n_) for n_ in nodes], lag_ratio=0.1), run_time=0.8)

    pulses = []
    for _ in range(min(3, len(edges))):
        e = rng.choice(list(edges))
        pulse = Dot(radius=0.10, color=palette_["highlight"]).move_to(e.get_start())
        pulses.append((pulse, e))

    for pulse, edge in pulses:
        scene_obj.add(pulse)
        scene_obj.play(pulse.animate.move_to(edge.get_end()), run_time=0.5)
        scene_obj.remove(pulse)

    total = max(8.0, float(scene_data.get("target_duration_seconds", 14.0)))
    scene_obj.wait(max(0.4, total - 3.5 - 0.5 * len(pulses)))


def render_wave(scene_obj, scene_data, palette_):
    """Continuously oscillating sine wave to evoke periodicity / signals."""
    chrome = add_top_bar(scene_obj, scene_data, palette_)

    axes = Axes(
        x_range=[-PI, PI, PI / 2], y_range=[-2, 2, 1],
        x_length=9.0, y_length=3.4,
        axis_config={"color": palette_["muted"], "stroke_width": 2},
        tips=False,
    )
    axes.move_to([0, -0.6, 0])

    phase = ValueTracker(0)
    amp = 1.4
    freq = 1.2

    wave = always_redraw(lambda: axes.plot(
        lambda x: amp * math.sin(freq * x + phase.get_value()),
        x_range=[-PI + 0.05, PI - 0.05],
        color=palette_["accent"],
        stroke_width=4,
    ))

    rider = always_redraw(lambda: Dot(
        axes.c2p(0, amp * math.sin(phase.get_value())),
        radius=0.10, color=palette_["accent_2"],
    ))

    terms = [t for t in (scene_data.get("highlight_terms") or []) if t]
    annotations = VGroup()
    if terms:
        a_lab = safe_text(terms[0], font_size=20, color=palette_["muted"], width=2.0, wrap=18)
        a_lab.next_to(axes.c2p(-PI / 2, amp), UP, buff=0.20)
        annotations.add(a_lab)
    if len(terms) > 1:
        b_lab = safe_text(terms[1], font_size=20, color=palette_["muted"], width=2.0, wrap=18)
        b_lab.next_to(axes.c2p(PI / 2, -amp), DOWN, buff=0.20)
        annotations.add(b_lab)

    scene_obj.play(Create(axes), run_time=0.6)
    scene_obj.add(wave, rider)
    scene_obj.play(FadeIn(annotations, lag_ratio=0.2), run_time=0.5)

    total = max(8.0, float(scene_data.get("target_duration_seconds", 14.0)))
    osc_time = max(2.0, total - 2.5)
    scene_obj.play(phase.animate.set_value(2 * PI * 1.5), run_time=osc_time, rate_func=linear)
    scene_obj.remove(wave, rider)
    static_wave = axes.plot(lambda x: amp * math.sin(freq * x + phase.get_value()),
                            x_range=[-PI + 0.05, PI - 0.05],
                            color=palette_["accent"], stroke_width=4)
    scene_obj.add(static_wave)
    scene_obj.wait(0.4)


def render_vector_field(scene_obj, scene_data, palette_):
    """Grid of small arrows hinting at a vector field / gradient."""
    chrome = add_top_bar(scene_obj, scene_data, palette_)

    bounds = (-3.5, 3.5, -1.8, 1.8)
    field = VGroup()
    for x in range(-3, 4):
        for y in range(-2, 3):
            angle = math.atan2(y, x + 0.6) + math.sin(x * 0.5) * 0.4
            length = 0.4 + 0.05 * (x + y)
            start = np.array([x * 0.85, y * 0.7, 0])
            end = start + np.array([math.cos(angle) * length, math.sin(angle) * length, 0])
            arrow = Arrow(start, end, color=palette_["accent"], stroke_width=2,
                          buff=0, max_tip_length_to_length_ratio=0.4, tip_length=0.10)
            arrow.set_opacity(0.55 + abs(y) * 0.05)
            field.add(arrow)
    field.move_to([0, -0.7, 0])

    particle = Dot(radius=0.12, color=palette_["accent_2"])
    path = ParametricFunction(
        lambda t: np.array([3 * math.cos(t), 1.5 * math.sin(t * 1.2), 0]),
        t_range=[0, 2 * PI], color=palette_["accent_2"], stroke_width=3,
    )
    path.set_fill(opacity=0)
    path.set_stroke(opacity=0.45)
    path.move_to(field.get_center())

    scene_obj.play(LaggedStart(*[GrowArrow(a) for a in field], lag_ratio=0.005), run_time=1.4)
    scene_obj.play(Create(path), run_time=0.7)
    particle.move_to(path.get_start())
    scene_obj.add(particle)
    scene_obj.play(MoveAlongPath(particle, path), run_time=max(2.5, float(scene_data.get("target_duration_seconds", 12.0)) - 4.0), rate_func=linear)
    scene_obj.wait(0.4)


# ---- dispatcher ----
LAYOUT_RENDERERS = {
    "title_card": render_title_card,
    "summary": render_summary,
    "bullets": render_bullets,
    "concept_map": render_concept_map,
    "equation": render_equation,
    "distribution": render_distribution,
    "axes": render_axes_plot,
    "axes_plot": render_axes_plot,
    "comparison": render_comparison,
    "timeline": render_timeline,
    "flow": render_flow,
    "orbit": render_orbit,
    "bar_chart": render_bar_chart,
    "process": render_process,
    "network": render_network,
    "wave": render_wave,
    "vector_field": render_vector_field,
}


def auto_layout(scene_data):
    head = (scene_data.get("headline", "") + " " + scene_data.get("hook", "") + " " + scene_data.get("narration", "")).lower()
    if scene_data.get("equations"):
        return "equation"
    if any(w in head for w in ("p-value", "p value", "distribution", "bell curve", "gaussian", "normal distribution", "probability density")):
        return "distribution"
    if any(w in head for w in ("vs ", " versus ", "compare", "comparison", "before vs after")):
        return "comparison"
    if any(w in head for w in ("timeline", "history", "evolved", "evolution", "over time", "decade", "century")):
        return "timeline"
    if any(w in head for w in ("step", "process", "pipeline", "first then", "workflow")):
        return "flow"
    if any(w in head for w in ("network", "graph", "connection", "neural", "social network")):
        return "network"
    if any(w in head for w in ("wave", "sine", "oscill", "frequency", "signal", "fourier")):
        return "wave"
    if any(w in head for w in ("axis", "axes", "plot", "graph of", "function", "growth", "decay", "exponential")):
        return "axes_plot"
    if any(w in head for w in ("field", "vector", "flow of", "gradient")):
        return "vector_field"
    if any(w in head for w in ("bar chart", "ranking", "share", "percentage", "distribution of")):
        return "bar_chart"
    if scene_data.get("scene_number") == 1:
        return "title_card"
    if scene_data.get("scene_number") == scene_data.get("scene_total"):
        return "summary"
    if any(w in head for w in ("orbit", "around", "satellite", "planet", "central")):
        return "orbit"
    if any(w in head for w in ("idea", "concept", "key concept", "framework")):
        return "concept_map"
    return "bullets"


def render_scene_page(scene_obj, scene_data):
    palette_ = palette()
    layout = (scene_data.get("layout") or "auto").lower()
    if layout == "auto" or layout not in LAYOUT_RENDERERS:
        layout = auto_layout(scene_data)
    renderer = LAYOUT_RENDERERS.get(layout, render_bullets)
    renderer(scene_obj, scene_data, palette_)


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
    total = len(scenes)
    for i, scene in enumerate(scenes, start=1):
        scene["scene_number"] = i
        scene["scene_total"] = total
    scene_classes = "\n".join(_scene_class_block(scene["class_name"], index) for index, scene in enumerate(scenes))
    module = (
        MODULE_TEMPLATE.replace("__STORY_JSON__", json.dumps(storyboard, indent=2))
        .replace("__SCENE_CLASSES__", scene_classes)
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(module, encoding="utf-8")
    return output_path
