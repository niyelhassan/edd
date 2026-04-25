from __future__ import annotations

import json
from pathlib import Path


MODULE_TEMPLATE = r'''from manim import *
import math
import numpy as np

STORY = __STORY_JSON__
SCENES = STORY["scenes"]

THEMES = {
    "blueprint": {"background": "#F4F7FB", "ink": "#0F172A", "muted": "#64748B", "accent": "#2563EB", "accent_2": "#0EA5E9", "panel": "#DBE3EE", "grid": "#C8D3E2"},
    "chalk":     {"background": "#F4EEDF", "ink": "#1F2937", "muted": "#6B7280", "accent": "#0F766E", "accent_2": "#14B8A6", "panel": "#D6D3D1", "grid": "#C9C2AF"},
    "lab":       {"background": "#F6F4FB", "ink": "#111827", "muted": "#4B5563", "accent": "#7C3AED", "accent_2": "#EC4899", "panel": "#E5E0F2", "grid": "#D2C9E8"},
    "signal":    {"background": "#FFF4EC", "ink": "#1C1917", "muted": "#57534E", "accent": "#DC2626", "accent_2": "#EA580C", "panel": "#FACFB6", "grid": "#F2C2A2"},
    "midnight":  {"background": "#0B1020", "ink": "#E2E8F0", "muted": "#94A3B8", "accent": "#60A5FA", "accent_2": "#A78BFA", "panel": "#1E293B", "grid": "#1A2438"},
    "sunset":    {"background": "#1F1430", "ink": "#FDE68A", "muted": "#C4B5FD", "accent": "#F472B6", "accent_2": "#FB923C", "panel": "#3B2752", "grid": "#2A1E40"},
}


def palette():
    return THEMES.get(STORY.get("visual_theme", "blueprint"), THEMES["blueprint"])


# ---------- helpers ----------

def fit(mob, w=None, h=None):
    if w and mob.width > w:
        mob.scale_to_fit_width(w)
    if h and mob.height > h:
        mob.scale_to_fit_height(h)
    return mob


def txt(s, *, size=24, color=None, weight=NORMAL, w=None, h=None):
    obj = Text(str(s or "").strip(), font_size=size, color=color, weight=weight)
    return fit(obj, w, h)


def math_safe(expr, *, size=44, color=None):
    try:
        return MathTex(expr, color=color, font_size=size)
    except Exception:
        return txt(expr, size=int(size * 0.6), color=color, weight=SEMIBOLD)


def lighten(hex_color, mix=0.5):
    rgb = color_to_rgb(hex_color)
    blended = rgb + (np.array([1, 1, 1]) - rgb) * mix
    return rgb_to_color(blended)


def darken(hex_color, mix=0.4):
    rgb = color_to_rgb(hex_color)
    blended = rgb * (1 - mix)
    return rgb_to_color(blended)


def is_dark_theme(p):
    return p["background"][1] in "012"


# ---------- chrome ----------

def make_background(p):
    bg = VGroup()
    if is_dark_theme(p):
        glow = Dot(radius=6.5, color=p["accent"]).set_opacity(0.10).move_to(LEFT * 4 + UP * 2)
        glow2 = Dot(radius=5.5, color=p["accent_2"]).set_opacity(0.08).move_to(RIGHT * 4 + DOWN * 2)
        bg.add(glow, glow2)
    grid = VGroup()
    for x in np.arange(-7, 7.5, 0.5):
        for y in np.arange(-4, 4.5, 0.5):
            d = Dot(point=[x, y, 0], radius=0.012, color=p["grid"]).set_opacity(0.55)
            grid.add(d)
    bg.add(grid)
    return bg


def build_chrome(scene_data, p, *, scene_index, total_scenes, story_title):
    accent_bar = Rectangle(height=8.0, width=0.14, stroke_width=0,
                           fill_color=p["accent"], fill_opacity=1).to_edge(LEFT, buff=0)

    badge_text = f"{scene_index:02d} / {total_scenes:02d}"
    badge_label = txt(badge_text, size=18, color=p["muted"], weight=SEMIBOLD)
    badge_pill = RoundedRectangle(corner_radius=0.18, width=badge_label.width + 0.5,
                                  height=0.55, stroke_color=p["panel"],
                                  stroke_width=2, fill_opacity=0)
    badge = VGroup(badge_pill, badge_label).arrange(ORIGIN)
    badge.to_edge(UP, buff=0.35).to_edge(LEFT, buff=0.6)

    title_small = txt(story_title or "", size=18, color=p["muted"], w=5.0, h=0.4)
    title_small.to_edge(UP, buff=0.45).to_edge(RIGHT, buff=0.6)

    headline = txt(scene_data.get("headline", "Scene"), size=44,
                   color=p["ink"], weight=BOLD, w=11.5, h=1.1)
    headline.to_edge(UP, buff=1.15).to_edge(LEFT, buff=0.85)

    underline = Line(LEFT * 0.0, RIGHT * 1.6, color=p["accent"], stroke_width=5)
    underline.next_to(headline, DOWN, buff=0.18, aligned_edge=LEFT)

    hook_text = scene_data.get("hook") or scene_data.get("takeaway") or ""
    hook = txt(hook_text, size=22, color=p["accent"], weight=SEMIBOLD, w=11.5, h=0.6)
    hook.next_to(underline, DOWN, buff=0.18, aligned_edge=LEFT)

    take = scene_data.get("takeaway") or ""
    if take and take != hook_text:
        take_label = txt(take, size=20, color=p["ink"], w=10.5, h=0.5)
        take_pill = RoundedRectangle(corner_radius=0.22, width=take_label.width + 0.9,
                                     height=0.7, stroke_width=0,
                                     fill_color=lighten(p["accent"], 0.78) if not is_dark_theme(p) else p["panel"],
                                     fill_opacity=1)
        takeaway = VGroup(take_pill, take_label).arrange(ORIGIN)
        takeaway.to_edge(DOWN, buff=0.5)
    else:
        takeaway = VGroup()

    return {
        "accent_bar": accent_bar,
        "badge": badge,
        "title_small": title_small,
        "headline": headline,
        "underline": underline,
        "hook": hook,
        "takeaway": takeaway,
    }


def play_chrome_intro(scene, chrome):
    scene.add(chrome["accent_bar"])
    scene.play(
        FadeIn(chrome["badge"], shift=RIGHT * 0.15),
        FadeIn(chrome["title_small"], shift=LEFT * 0.15),
        run_time=0.4,
    )
    scene.play(
        FadeIn(chrome["headline"], shift=UP * 0.2),
        run_time=0.55,
    )
    scene.play(
        Create(chrome["underline"]),
        FadeIn(chrome["hook"], shift=UP * 0.1),
        run_time=0.45,
    )


def play_takeaway_outro(scene, chrome):
    if len(chrome["takeaway"]) == 0:
        return 0.0
    scene.play(FadeIn(chrome["takeaway"], shift=UP * 0.2), run_time=0.5)
    return 0.5


CANVAS_CENTER = np.array([0.0, -0.7, 0.0])
CANVAS_W = 11.5
CANVAS_H = 4.6


def canvas_box(p, *, fill_opacity=0.0):
    box = RoundedRectangle(corner_radius=0.28, width=CANVAS_W, height=CANVAS_H,
                           stroke_color=p["panel"], stroke_width=2,
                           fill_color=p["panel"], fill_opacity=fill_opacity)
    box.move_to(CANVAS_CENTER)
    return box


# ---------- layouts ----------

def layout_title_card(scene, data, p, budget):
    title_big = txt(data.get("headline", "Concept"), size=82, color=p["ink"], weight=BOLD, w=12)
    title_big.move_to(CANVAS_CENTER + UP * 0.2)
    sub = txt(data.get("hook") or data.get("takeaway") or "", size=28, color=p["accent_2"], w=10.5, h=0.6)
    sub.next_to(title_big, DOWN, buff=0.4)

    rings = VGroup()
    for i, r in enumerate([2.4, 3.1, 3.8]):
        c = Circle(radius=r, color=p["accent"] if i % 2 == 0 else p["accent_2"],
                   stroke_width=2, fill_opacity=0)
        c.set_stroke(opacity=0.45)
        c.move_to(CANVAS_CENTER)
        rings.add(c)

    scene.play(LaggedStart(*[Create(r) for r in rings], lag_ratio=0.2), run_time=1.0)
    scene.play(Write(title_big), run_time=1.0)
    if sub.width > 0:
        scene.play(FadeIn(sub, shift=UP * 0.15), run_time=0.5)
    scene.play(Rotate(rings, angle=PI * 0.25, about_point=CANVAS_CENTER), run_time=min(2.0, budget - 2.5))
    return 2.5 + min(2.0, budget - 2.5)


def layout_concept_map(scene, data, p, budget):
    items = (data.get("visual_items") or [])[:5] or (data.get("key_points") or [])[:5]
    items = [str(i) for i in items if i]
    if not items:
        items = (data.get("highlight_terms") or [])[:4] or [data.get("headline", "Idea")]

    center_label = (data.get("highlight_terms") or [data.get("headline", "Idea")])[0]
    center_circle = Circle(radius=1.1, color=p["accent"], stroke_width=4
                           ).set_fill(p["accent"], opacity=1.0)
    text_color = WHITE if is_dark_theme(p) else p["background"]
    center_text = txt(center_label, size=22, color=text_color, weight=BOLD, w=1.8, h=0.7)
    center = VGroup(center_circle, center_text).move_to(CANVAS_CENTER)
    center.set_z_index(5)

    n = min(len(items), 5)
    radius = 3.1
    nodes = VGroup()
    edges = VGroup()
    for i, item in enumerate(items[:n]):
        angle = (PI / 2) - i * (TAU / n)
        pos = CANVAS_CENTER + np.array([radius * 1.4 * math.cos(angle),
                                        radius * 0.85 * math.sin(angle), 0])
        box_color = p["accent"] if i % 2 == 0 else p["accent_2"]
        box = RoundedRectangle(corner_radius=0.18, width=2.6, height=0.78,
                               stroke_color=box_color, stroke_width=2.5,
                               fill_color=lighten(box_color, 0.85) if not is_dark_theme(p) else p["panel"],
                               fill_opacity=0.95)
        label = txt(item, size=19, color=p["ink"], weight=SEMIBOLD, w=2.2, h=0.5)
        node = VGroup(box, label).move_to(pos)
        edge = Line(center.get_center(), node.get_center(),
                    color=p["panel"], stroke_width=3).set_opacity(0.7)
        edges.add(edge)
        nodes.add(node)

    scene.play(GrowFromCenter(center), run_time=0.5)
    scene.play(Indicate(center_circle, color=p["accent_2"], scale_factor=1.15), run_time=0.4)
    per = max(0.3, min(0.8, (budget - 1.5) / max(n, 1)))
    for edge, node in zip(edges, nodes):
        scene.play(Create(edge), FadeIn(node, scale=0.9), run_time=per)
    return 0.9 + per * n


def layout_equation_walkthrough(scene, data, p, budget):
    eq_str = (data.get("equations") or [""])[0] or "y = f(x)"
    eq = math_safe(eq_str, size=72, color=p["ink"])
    fit(eq, w=10.5, h=2.0)
    eq.move_to(CANVAS_CENTER + UP * 0.6)

    terms = (data.get("highlight_terms") or [])[:3]
    annotations = VGroup()
    arrows = VGroup()
    for i, term in enumerate(terms[:3]):
        positions = [LEFT * 3.5, ORIGIN, RIGHT * 3.5]
        anchor = eq.get_center() + DOWN * 1.1 + positions[i] * 0.9
        label = txt(term, size=22, color=p["accent"] if i % 2 == 0 else p["accent_2"],
                    weight=SEMIBOLD, w=2.6, h=0.6)
        label.move_to(anchor + DOWN * 0.9)
        arrow = Arrow(label.get_top(), anchor + UP * 0.05, color=label.color,
                      stroke_width=3, max_tip_length_to_length_ratio=0.18, buff=0.05)
        annotations.add(label)
        arrows.add(arrow)

    scene.play(Write(eq), run_time=1.4)
    scene.play(Indicate(eq, color=p["accent"], scale_factor=1.05), run_time=0.6)

    per = max(0.4, min(1.0, (budget - 2.5) / max(len(terms), 1)))
    for label, arrow in zip(annotations, arrows):
        scene.play(GrowArrow(arrow), FadeIn(label, shift=UP * 0.15), run_time=per)
    return 2.0 + per * len(terms)


def layout_proof_steps(scene, data, p, budget):
    steps = [s for s in (data.get("equations") or []) if s][:4]
    if not steps:
        return layout_equation_walkthrough(scene, data, p, budget)
    eqs = [math_safe(s, size=52, color=p["ink"]) for s in steps]
    for e in eqs:
        fit(e, w=10.0, h=1.4)
        e.move_to(CANVAS_CENTER + UP * 0.4)

    scene.play(Write(eqs[0]), run_time=1.0)
    used = 1.0
    per = max(0.6, min(1.4, (budget - 1.4) / max(len(eqs) - 1, 1)))
    for prev, nxt in zip(eqs, eqs[1:]):
        try:
            scene.play(TransformMatchingTex(prev, nxt), run_time=per)
        except Exception:
            scene.play(ReplacementTransform(prev, nxt), run_time=per)
        used += per
    return used


def layout_comparison(scene, data, p, budget):
    pairs = data.get("comparison_pairs") or []
    if not pairs:
        items = data.get("visual_items") or []
        mid = max(1, len(items) // 2)
        pairs = [{"left": items[i] if i < mid else "", "right": items[i + mid] if (i + mid) < len(items) else ""}
                 for i in range(min(3, mid))]
    pairs = [pp for pp in pairs if pp.get("left") or pp.get("right")][:4]

    left_title_text = (data.get("highlight_terms") or ["A"])[0]
    right_title_text = (data.get("highlight_terms") or ["A", "B"])[-1] if len(data.get("highlight_terms") or []) > 1 else "B"

    panel_w, panel_h = 4.7, 4.0
    left_panel = RoundedRectangle(corner_radius=0.28, width=panel_w, height=panel_h,
                                  stroke_color=p["accent"], stroke_width=3,
                                  fill_color=lighten(p["accent"], 0.88) if not is_dark_theme(p) else p["panel"],
                                  fill_opacity=0.5).move_to(CANVAS_CENTER + LEFT * 2.85)
    right_panel = RoundedRectangle(corner_radius=0.28, width=panel_w, height=panel_h,
                                   stroke_color=p["accent_2"], stroke_width=3,
                                   fill_color=lighten(p["accent_2"], 0.88) if not is_dark_theme(p) else p["panel"],
                                   fill_opacity=0.5).move_to(CANVAS_CENTER + RIGHT * 2.85)

    lt = txt(left_title_text, size=26, color=p["accent"], weight=BOLD, w=4.0, h=0.7
             ).move_to(left_panel.get_top() + DOWN * 0.5)
    rt = txt(right_title_text, size=26, color=p["accent_2"], weight=BOLD, w=4.0, h=0.7
             ).move_to(right_panel.get_top() + DOWN * 0.5)

    vs = txt("vs", size=32, color=p["muted"], weight=BOLD).move_to(CANVAS_CENTER)

    scene.play(
        FadeIn(left_panel, shift=RIGHT * 0.5),
        FadeIn(right_panel, shift=LEFT * 0.5),
        run_time=0.6,
    )
    scene.play(Write(lt), Write(rt), FadeIn(vs, scale=0.5), run_time=0.6)

    per = max(0.3, min(0.8, (budget - 1.6) / max(len(pairs), 1)))
    used = 1.2
    for i, pair in enumerate(pairs):
        y = -0.4 - i * 0.7
        l_text = txt("• " + (pair.get("left") or ""), size=20, color=p["ink"], w=panel_w - 0.6, h=0.5)
        r_text = txt("• " + (pair.get("right") or ""), size=20, color=p["ink"], w=panel_w - 0.6, h=0.5)
        l_text.move_to(left_panel.get_center() + np.array([0, y, 0])).align_to(left_panel.get_left() + RIGHT * 0.4, LEFT)
        r_text.move_to(right_panel.get_center() + np.array([0, y, 0])).align_to(right_panel.get_left() + RIGHT * 0.4, LEFT)
        scene.play(FadeIn(l_text, shift=RIGHT * 0.2), FadeIn(r_text, shift=LEFT * 0.2), run_time=per)
        used += per
    return used


def _safe_func(expr_str):
    expr_str = (expr_str or "").strip()
    if not expr_str:
        return None
    safe = {"sin": math.sin, "cos": math.cos, "tan": math.tan, "exp": math.exp,
            "log": math.log, "sqrt": math.sqrt, "abs": abs, "pi": math.pi, "e": math.e,
            "pow": pow}
    try:
        compiled = compile(expr_str, "<expr>", "eval")
        for name in compiled.co_names:
            if name not in safe and name != "x":
                return None
        return lambda x: float(eval(compiled, {"__builtins__": {}}, {**safe, "x": x}))
    except Exception:
        return None


def layout_axes_plot(scene, data, p, budget):
    axes = Axes(
        x_range=[-4, 4, 1], y_range=[-2.5, 2.5, 1],
        x_length=9.5, y_length=4.2,
        axis_config={"color": p["muted"], "stroke_width": 2.5,
                     "include_numbers": False, "include_tip": False},
    ).move_to(CANVAS_CENTER + UP * 0.1)

    func = _safe_func(data.get("function_expr"))
    if func is None:
        func = lambda x: 0.9 * math.sin(x) + 0.4 * math.cos(2 * x)

    def safe_eval(x):
        try:
            v = func(x)
            if not np.isfinite(v):
                return 0.0
            return max(-2.5, min(2.5, v))
        except Exception:
            return 0.0

    curve = axes.plot(safe_eval, x_range=[-4, 4, 0.05],
                      color=p["accent"], stroke_width=4)

    labels_terms = (data.get("highlight_terms") or [])[:2]
    x_label = txt(labels_terms[0] if labels_terms else "x", size=20, color=p["muted"]
                  ).next_to(axes.x_axis, RIGHT, buff=0.15)
    y_label = txt(labels_terms[1] if len(labels_terms) > 1 else "y", size=20, color=p["muted"]
                  ).next_to(axes.y_axis, UP, buff=0.15)

    points_group = VGroup()
    items = (data.get("visual_items") or [])[:3]
    sample_xs = [-2.0, 0.5, 2.3]
    for i, item in enumerate(items[:3]):
        x = sample_xs[i]
        y = safe_eval(x)
        d = Dot(axes.c2p(x, y), radius=0.1,
                color=p["accent_2"] if i % 2 else p["accent"])
        l = txt(item, size=17, color=p["ink"], w=2.0, h=0.4).next_to(d, UR, buff=0.08)
        points_group.add(VGroup(d, l))

    scene.play(Create(axes), FadeIn(x_label), FadeIn(y_label), run_time=0.7)
    scene.play(Create(curve), run_time=min(2.0, max(1.0, budget * 0.4)))
    used = 0.7 + min(2.0, max(1.0, budget * 0.4))
    per = max(0.3, min(0.7, (budget - used - 0.3) / max(len(points_group), 1)))
    for grp in points_group:
        scene.play(GrowFromCenter(grp[0]), FadeIn(grp[1], shift=UP * 0.1), run_time=per)
        used += per
    return used


def layout_bar_chart(scene, data, p, budget):
    raw = data.get("data_points") or []
    bars_data = [(d.get("label", ""), float(d.get("value", 0))) for d in raw if d]
    if not bars_data:
        items = (data.get("visual_items") or [])[:5]
        bars_data = [(item, (i + 1) * 1.0) for i, item in enumerate(items)]
    if not bars_data:
        return layout_concept_map(scene, data, p, budget)

    n = len(bars_data)
    max_val = max(abs(v) for _, v in bars_data) or 1.0
    chart_w = 9.5
    chart_h = 3.6
    bar_w = min(1.1, (chart_w - 1.0) / n - 0.2)
    spacing = (chart_w - bar_w * n) / max(n, 1)
    baseline_y = CANVAS_CENTER[1] - chart_h / 2 + 0.4

    baseline = Line(np.array([CANVAS_CENTER[0] - chart_w / 2, baseline_y, 0]),
                    np.array([CANVAS_CENTER[0] + chart_w / 2, baseline_y, 0]),
                    color=p["muted"], stroke_width=2)

    bars = VGroup()
    labels = VGroup()
    values = VGroup()
    for i, (lab, v) in enumerate(bars_data):
        h = (abs(v) / max_val) * chart_h * 0.85
        x = CANVAS_CENTER[0] - chart_w / 2 + spacing / 2 + i * (bar_w + spacing) + bar_w / 2
        bar_color = p["accent"] if i % 2 == 0 else p["accent_2"]
        bar = Rectangle(width=bar_w, height=max(h, 0.05), stroke_width=0,
                        fill_color=bar_color, fill_opacity=0.95)
        bar.move_to(np.array([x, baseline_y + h / 2, 0]))
        lbl = txt(lab, size=17, color=p["ink"], w=bar_w + spacing - 0.1, h=0.4)
        lbl.next_to(np.array([x, baseline_y, 0]), DOWN, buff=0.18)
        val = txt(f"{v:g}", size=18, color=bar_color, weight=SEMIBOLD)
        val.next_to(bar, UP, buff=0.12)
        bars.add(bar)
        labels.add(lbl)
        values.add(val)

    scene.play(Create(baseline), run_time=0.4)
    scene.play(LaggedStart(*[FadeIn(l, shift=UP * 0.1) for l in labels], lag_ratio=0.1), run_time=0.6)
    per = max(0.4, min(0.8, (budget - 1.4) / max(n, 1)))
    for bar, val in zip(bars, values):
        scene.play(GrowFromEdge(bar, DOWN), FadeIn(val, shift=UP * 0.1), run_time=per)
    return 1.0 + per * n


def layout_timeline(scene, data, p, budget):
    items = (data.get("visual_items") or [])[:5] or (data.get("key_points") or [])[:5]
    items = [i for i in items if i][:5]
    if not items:
        items = ["start", "middle", "end"]

    n = len(items)
    line = Line(LEFT * 5.0, RIGHT * 5.0, color=p["panel"], stroke_width=4
                ).move_to(CANVAS_CENTER)
    progress = Line(line.get_start(), line.get_start(), color=p["accent"], stroke_width=6)

    points = []
    labels = []
    for i, item in enumerate(items):
        t = i / max(n - 1, 1)
        pt = line.get_start() + (line.get_end() - line.get_start()) * t
        dot = Dot(pt, radius=0.13, color=p["accent"] if i % 2 == 0 else p["accent_2"])
        offset = UP * 0.7 if i % 2 == 0 else DOWN * 0.7
        lab = txt(item, size=18, color=p["ink"], w=2.4, h=0.7).move_to(pt + offset)
        connector = Line(pt, lab.get_center() + (DOWN * 0.3 if i % 2 == 0 else UP * 0.3),
                         color=p["muted"], stroke_width=1.5).set_opacity(0.6)
        points.append((dot, lab, connector, t))

    scene.play(Create(line), run_time=0.6)
    scene.add(progress)

    per_total = max(2.0, min(budget - 1.2, n * 0.9))
    used = 0.6
    for i, (dot, lab, connector, t) in enumerate(points):
        target_end = line.get_start() + (line.get_end() - line.get_start()) * t
        seg_time = per_total / n
        scene.play(
            progress.animate.put_start_and_end_on(line.get_start(), target_end),
            run_time=max(0.3, seg_time * 0.55),
        )
        scene.play(
            GrowFromCenter(dot),
            Create(connector),
            FadeIn(lab, shift=UP * 0.1 if i % 2 == 0 else DOWN * 0.1),
            run_time=max(0.3, seg_time * 0.45),
        )
        used += seg_time
    return used


def layout_flow(scene, data, p, budget):
    items = (data.get("visual_items") or [])[:5] or (data.get("key_points") or [])[:4]
    items = [i for i in items if i][:5]
    if len(items) < 2:
        items = (items + ["Step A", "Step B", "Step C"])[:3]

    n = len(items)
    box_w = min(2.6, (CANVAS_W - 1.0) / n - 0.4)
    box_h = 1.3
    spacing = (CANVAS_W - 1.0 - box_w * n) / max(n - 1, 1) if n > 1 else 0

    nodes = []
    arrows = []
    start_x = CANVAS_CENTER[0] - (CANVAS_W - 1.0) / 2 + box_w / 2
    for i, item in enumerate(items):
        x = start_x + i * (box_w + spacing)
        c = p["accent"] if i % 2 == 0 else p["accent_2"]
        box = RoundedRectangle(corner_radius=0.22, width=box_w, height=box_h,
                               stroke_width=0, fill_color=c, fill_opacity=0.95)
        lbl = txt(item, size=19, color=WHITE, weight=SEMIBOLD,
                  w=box_w - 0.3, h=box_h - 0.4)
        node = VGroup(box, lbl).move_to(np.array([x, CANVAS_CENTER[1], 0]))
        nodes.append(node)

    for a, b in zip(nodes, nodes[1:]):
        arr = Arrow(a.get_right() + RIGHT * 0.05, b.get_left() + LEFT * 0.05,
                    color=p["muted"], stroke_width=4, buff=0.05,
                    max_tip_length_to_length_ratio=0.25)
        arrows.append(arr)

    per = max(0.4, min(0.9, (budget - 0.4) / max(n + len(arrows), 1)))
    used = 0.0
    for i, node in enumerate(nodes):
        scene.play(FadeIn(node, scale=0.85), run_time=per)
        scene.play(Indicate(node, color=p["ink"], scale_factor=1.06), run_time=per * 0.5)
        used += per * 1.5
        if i < len(arrows):
            scene.play(GrowArrow(arrows[i]), run_time=per * 0.7)
            used += per * 0.7
    return used


def layout_orbit(scene, data, p, budget):
    items = (data.get("visual_items") or [])[:4] or (data.get("highlight_terms") or [])[:4]
    items = [i for i in items if i][:4] or [data.get("headline", "core")]

    center_text = txt((data.get("highlight_terms") or [data.get("headline", "Core")])[0],
                      size=24, color=WHITE if is_dark_theme(p) else p["background"],
                      weight=BOLD, w=1.8, h=0.7)
    center_disc = Circle(radius=1.0, color=p["accent"], stroke_width=4
                         ).set_fill(p["accent"], opacity=1.0)
    center = VGroup(center_disc, center_text).move_to(CANVAS_CENTER)
    center.set_z_index(5)

    rings = []
    satellites = []
    radii = [1.8, 2.6, 3.2]
    for i, item in enumerate(items[:4]):
        r = radii[i % len(radii)]
        ring = Circle(radius=r, color=p["panel"], stroke_width=2,
                      fill_opacity=0).move_to(CANVAS_CENTER)
        ring.set_stroke(opacity=0.6)
        rings.append(ring)
        angle0 = i * (TAU / max(len(items), 1)) + PI / 4
        pt = CANVAS_CENTER + np.array([r * math.cos(angle0), r * 0.62 * math.sin(angle0), 0])
        sat_color = p["accent"] if i % 2 == 0 else p["accent_2"]
        sat = Dot(pt, radius=0.16, color=sat_color)
        lbl = txt(item, size=18, color=p["ink"], w=2.4, h=0.5).next_to(sat, UR, buff=0.12)
        satellites.append((sat, lbl, ring, angle0))

    scene.play(GrowFromCenter(center), run_time=0.5)
    scene.play(LaggedStart(*[Create(r) for r in rings], lag_ratio=0.15), run_time=0.7)
    for sat, lbl, ring, _ in satellites:
        scene.play(FadeIn(sat, scale=0.5), FadeIn(lbl, shift=UP * 0.1), run_time=0.3)

    spin_time = max(1.5, budget - 1.5 - 0.3 * len(satellites) - 1.2)
    angle_tracker = ValueTracker(0.0)
    for sat, lbl, ring, angle0 in satellites:
        r = ring.radius
        a0 = angle0

        def updater_factory(rr, aa, sat_obj, lbl_obj):
            def upd(_):
                ang = aa + angle_tracker.get_value()
                pt = CANVAS_CENTER + np.array([rr * math.cos(ang), rr * 0.62 * math.sin(ang), 0])
                sat_obj.move_to(pt)
                lbl_obj.next_to(sat_obj, UR, buff=0.12)
            return upd

        sat.add_updater(updater_factory(r, a0, sat, lbl))

    scene.play(angle_tracker.animate.set_value(TAU * 0.75), run_time=spin_time, rate_func=linear)
    for sat, lbl, _, _ in satellites:
        sat.clear_updaters()
    return 0.5 + 0.7 + 0.3 * len(satellites) + spin_time


def layout_stack_build(scene, data, p, budget):
    items = (data.get("visual_items") or [])[:5] or (data.get("key_points") or [])[:5]
    items = [i for i in items if i][:5]
    if not items:
        return layout_concept_map(scene, data, p, budget)

    n = len(items)
    box_w = 7.0
    box_h = min(0.85, 4.0 / n)
    base_y = CANVAS_CENTER[1] - n * box_h / 2 + box_h / 2
    layers = []
    for i, item in enumerate(items):
        c = p["accent"] if i % 2 == 0 else p["accent_2"]
        box = RoundedRectangle(corner_radius=0.18, width=box_w, height=box_h * 0.92,
                               stroke_width=0, fill_color=c, fill_opacity=0.85)
        lbl = txt(item, size=20, color=WHITE, weight=SEMIBOLD,
                  w=box_w - 0.5, h=box_h * 0.7)
        layer = VGroup(box, lbl).move_to(np.array([CANVAS_CENTER[0], base_y + i * box_h, 0]))
        layers.append(layer)

    per = max(0.4, min(1.0, (budget - 0.5) / n))
    for layer in layers:
        scene.play(FadeIn(layer, shift=UP * 0.4), run_time=per)
    return per * n


def layout_wave(scene, data, p, budget):
    axes = Axes(
        x_range=[-PI, PI, PI / 2], y_range=[-1.6, 1.6, 0.5],
        x_length=9.5, y_length=3.8,
        axis_config={"color": p["muted"], "stroke_width": 2,
                     "include_numbers": False, "include_tip": False},
    ).move_to(CANVAS_CENTER + UP * 0.1)

    amp = ValueTracker(0.5)
    freq = ValueTracker(1.0)
    phase = ValueTracker(0.0)

    def make_curve():
        return axes.plot(
            lambda x: amp.get_value() * math.sin(freq.get_value() * x + phase.get_value()),
            x_range=[-PI, PI, 0.05],
            color=p["accent"], stroke_width=4,
        )

    curve = always_redraw(make_curve)

    terms = (data.get("highlight_terms") or [])[:3]
    legend = VGroup()
    for i, term in enumerate(terms):
        sw = Line(LEFT * 0.2, RIGHT * 0.2, color=p["accent"] if i % 2 == 0 else p["accent_2"],
                  stroke_width=4)
        lab = txt(term, size=18, color=p["ink"], w=2.6, h=0.5)
        item = VGroup(sw, lab).arrange(RIGHT, buff=0.18)
        legend.add(item)
    legend.arrange(DOWN, buff=0.2, aligned_edge=LEFT)
    legend.move_to(CANVAS_CENTER + RIGHT * 4.4 + DOWN * 1.2)

    scene.play(Create(axes), run_time=0.5)
    scene.add(curve)
    scene.play(amp.animate.set_value(1.4), run_time=min(1.5, budget * 0.25))
    used = 0.5 + min(1.5, budget * 0.25)
    if len(legend):
        scene.play(FadeIn(legend, shift=LEFT * 0.2), run_time=0.4)
        used += 0.4
    remaining = max(1.5, budget - used - 0.5)
    scene.play(
        freq.animate.set_value(2.2),
        phase.animate.set_value(TAU),
        run_time=remaining, rate_func=smooth,
    )
    return used + remaining


def layout_network(scene, data, p, budget):
    items = (data.get("visual_items") or [])[:6] or (data.get("highlight_terms") or [])[:6]
    items = [i for i in items if i][:6]
    if len(items) < 3:
        items = (items + ["A", "B", "C"])[:5]

    n = len(items)
    nodes = []
    np.random.seed(7)
    for i, item in enumerate(items):
        angle = i * TAU / n + PI / 6
        r = 2.4 + 0.4 * (i % 2)
        pt = CANVAS_CENTER + np.array([r * math.cos(angle), r * 0.7 * math.sin(angle), 0])
        c = p["accent"] if i % 2 == 0 else p["accent_2"]
        circle = Circle(radius=0.42, color=c, stroke_width=3
                        ).set_fill(lighten(c, 0.7) if not is_dark_theme(p) else p["panel"], opacity=0.9)
        lbl = txt(item, size=17, color=p["ink"], weight=SEMIBOLD, w=1.2, h=0.5)
        node = VGroup(circle, lbl).move_to(pt)
        nodes.append(node)

    edges = []
    edge_set = set()
    for i in range(n):
        for j in [(i + 1) % n, (i + 2) % n]:
            key = tuple(sorted((i, j)))
            if key in edge_set or i == j:
                continue
            edge_set.add(key)
            ln = Line(nodes[i].get_center(), nodes[j].get_center(),
                      color=p["muted"], stroke_width=2).set_opacity(0.55)
            edges.append(ln)

    scene.play(LaggedStart(*[FadeIn(nd, scale=0.6) for nd in nodes], lag_ratio=0.12),
               run_time=min(1.4, budget * 0.3))
    scene.play(LaggedStart(*[Create(e) for e in edges], lag_ratio=0.05),
               run_time=min(1.6, budget * 0.3))
    used = min(1.4, budget * 0.3) + min(1.6, budget * 0.3)

    pulses_time = max(1.0, budget - used - 0.5)
    pulses = []
    for e in edges[:6]:
        pulse = Dot(e.get_start(), radius=0.08, color=p["accent_2"])
        pulses.append((pulse, e))
        scene.add(pulse)
    if pulses:
        scene.play(*[MoveAlongPath(d, e) for d, e in pulses],
                   run_time=pulses_time, rate_func=linear)
        for d, _ in pulses:
            scene.remove(d)
    return used + pulses_time


def layout_closing_card(scene, data, p, budget):
    take = data.get("takeaway") or data.get("hook") or data.get("headline", "")
    big = txt(take, size=46, color=p["ink"], weight=BOLD, w=11)
    big.move_to(CANVAS_CENTER + UP * 0.2)

    deco_left = Line(LEFT * 1.6, LEFT * 0.5, color=p["accent"], stroke_width=4)
    deco_right = Line(RIGHT * 0.5, RIGHT * 1.6, color=p["accent_2"], stroke_width=4)
    deco_left.next_to(big, DOWN, buff=0.45).shift(LEFT * 1.0)
    deco_right.next_to(big, DOWN, buff=0.45).shift(RIGHT * 1.0)

    sub_terms = (data.get("highlight_terms") or [])[:3]
    chips = VGroup()
    for i, term in enumerate(sub_terms):
        c = p["accent"] if i % 2 == 0 else p["accent_2"]
        lbl = txt(term, size=18, color=c, weight=SEMIBOLD)
        pill = RoundedRectangle(corner_radius=0.22, width=lbl.width + 0.6, height=0.55,
                                stroke_color=c, stroke_width=2, fill_opacity=0)
        chips.add(VGroup(pill, lbl).arrange(ORIGIN))
    chips.arrange(RIGHT, buff=0.25)
    chips.next_to(deco_left, DOWN, buff=0.5).move_to([CANVAS_CENTER[0], chips.get_y(), 0])

    scene.play(FadeIn(big, shift=UP * 0.3), run_time=1.0)
    scene.play(Create(deco_left), Create(deco_right), run_time=0.5)
    if len(chips):
        scene.play(LaggedStart(*[FadeIn(c, scale=0.85) for c in chips], lag_ratio=0.15),
                   run_time=min(1.5, budget - 1.8))
    return min(budget, 1.5 + 1.5)


LAYOUT_HANDLERS = {
    "title_card": layout_title_card,
    "concept_map": layout_concept_map,
    "equation_walkthrough": layout_equation_walkthrough,
    "proof_steps": layout_proof_steps,
    "comparison": layout_comparison,
    "axes_plot": layout_axes_plot,
    "bar_chart": layout_bar_chart,
    "timeline": layout_timeline,
    "flow": layout_flow,
    "orbit": layout_orbit,
    "stack_build": layout_stack_build,
    "wave": layout_wave,
    "network": layout_network,
    "closing_card": layout_closing_card,
}


def render_scene_page(scene_obj, scene_data, scene_index, total_scenes):
    p = palette()
    scene_obj.camera.background_color = p["background"]

    bg = make_background(p)
    scene_obj.add(bg)

    chrome = build_chrome(scene_data, p, scene_index=scene_index,
                          total_scenes=total_scenes, story_title=STORY.get("title", ""))
    play_chrome_intro(scene_obj, chrome)

    total = max(8.0, float(scene_data.get("target_duration_seconds", 12.0)))
    intro_used = 1.4
    outro_reserved = 1.0
    budget = max(3.0, total - intro_used - outro_reserved)

    layout = scene_data.get("layout") or "concept_map"
    handler = LAYOUT_HANDLERS.get(layout, layout_concept_map)
    try:
        used = handler(scene_obj, scene_data, p, budget)
    except Exception:
        used = layout_concept_map(scene_obj, scene_data, p, budget)
    used = float(used or 0.0)

    outro_used = play_takeaway_outro(scene_obj, chrome)
    consumed = intro_used + used + outro_used
    remaining = total - consumed
    if remaining > 0.2:
        scene_obj.wait(remaining)


__SCENE_CLASSES__
'''


def _scene_class_block(class_name: str, index: int, total: int) -> str:
    return f'''
class {class_name}(Scene):
    def construct(self):
        render_scene_page(self, SCENES[{index}], {index + 1}, {total})
'''


def build_manim_module(*, storyboard: dict, output_path: Path) -> Path:
    scenes = storyboard["scenes"]
    total = len(scenes)
    scene_classes = "\n".join(
        _scene_class_block(scene["class_name"], index, total)
        for index, scene in enumerate(scenes)
    )
    module = (
        MODULE_TEMPLATE.replace("__STORY_JSON__", json.dumps(storyboard, indent=2))
        .replace("__SCENE_CLASSES__", scene_classes)
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(module, encoding="utf-8")
    return output_path
