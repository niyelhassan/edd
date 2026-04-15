from __future__ import annotations

import json
from pathlib import Path


MODULE_TEMPLATE = '''from manim import *

STORY = __STORY_JSON__
SCENES = STORY["scenes"]

THEMES = {
    "blueprint": {"background": "#F8FAFC", "ink": "#0F172A", "muted": "#475569", "accent": "#2563EB", "accent_2": "#0EA5E9", "panel": "#E2E8F0"},
    "chalk": {"background": "#F7F3E9", "ink": "#1F2937", "muted": "#6B7280", "accent": "#0F766E", "accent_2": "#14B8A6", "panel": "#D6D3D1"},
    "lab": {"background": "#F8FAFC", "ink": "#111827", "muted": "#4B5563", "accent": "#7C3AED", "accent_2": "#EC4899", "panel": "#E5E7EB"},
    "signal": {"background": "#FFF7ED", "ink": "#1C1917", "muted": "#57534E", "accent": "#DC2626", "accent_2": "#EA580C", "panel": "#E7E5E4"},
    "midnight": {"background": "#0B1020", "ink": "#E2E8F0", "muted": "#94A3B8", "accent": "#60A5FA", "accent_2": "#A78BFA", "panel": "#1E293B"},
    "sunset": {"background": "#FFF6ED", "ink": "#431407", "muted": "#9A3412", "accent": "#EA580C", "accent_2": "#F97316", "panel": "#FED7AA"},
}


def colors():
    return THEMES.get(STORY.get("visual_theme", "blueprint"), THEMES["blueprint"])


def fit_box(mobject, width, height=None):
    if mobject.width > width:
        mobject.scale_to_fit_width(width)
    if height and mobject.height > height:
        mobject.scale_to_fit_height(height)
    return mobject


def safe_text(text, *, font_size, color, weight=NORMAL, width=None, height=None):
    obj = Text(str(text or ""), font_size=font_size, color=color, weight=weight)
    if width or height:
        fit_box(obj, width or obj.width, height)
    return obj


def safe_math(expr, palette):
    if not expr:
        return None
    try:
        obj = MathTex(expr, color=palette["ink"], font_size=52)
    except Exception:
        obj = safe_text(expr, font_size=28, color=palette["ink"], weight=SEMIBOLD)
    return fit_box(obj, 5.8, 1.4)


def bullet_lines(scene):
    lines = []
    for item in scene.get("key_points", [])[:3]:
        if item:
            lines.append(item)
    if not lines:
        for item in scene.get("visual_items", [])[:3]:
            if item:
                lines.append(item)
    if not lines:
        for item in scene.get("highlight_terms", [])[:3]:
            if item:
                lines.append(item)
    return lines[:3]


def build_info_column(scene, palette):
    title = safe_text(scene.get("headline", "Scene"), font_size=34, color=palette["ink"], weight=BOLD, width=5.3, height=1.3)
    title.to_edge(UP, buff=0.6).to_edge(LEFT, buff=0.7)

    hook_text = scene.get("hook") or scene.get("takeaway") or ""
    hook = safe_text(hook_text, font_size=22, color=palette["accent"], weight=SEMIBOLD, width=5.1, height=1.1)
    hook.next_to(title, DOWN, buff=0.28, aligned_edge=LEFT)

    bullets = []
    for line in bullet_lines(scene):
        dot = Dot(radius=0.05, color=palette["accent"])
        text = safe_text(line, font_size=22, color=palette["ink"], width=4.5, height=0.7)
        bullets.append(VGroup(dot, text).arrange(RIGHT, buff=0.18, aligned_edge=UP))

    bullet_group = VGroup(*bullets).arrange(DOWN, buff=0.24, aligned_edge=LEFT) if bullets else VGroup()
    if len(bullet_group):
        bullet_group.next_to(hook, DOWN, buff=0.4, aligned_edge=LEFT)

    return VGroup(title, hook, bullet_group)


def concept_visual(scene, palette):
    center = Circle(radius=0.9, color=palette["accent"], stroke_width=4).set_fill(palette["accent"], opacity=0.08)
    center_label = safe_text((scene.get("highlight_terms") or [scene.get("headline", "Idea")])[0], font_size=24, color=palette["ink"], weight=BOLD, width=1.5, height=0.8)
    center_group = VGroup(center, center_label)

    items = scene.get("visual_items", [])[:3] or scene.get("key_points", [])[:3]
    positions = [UP * 2.1 + RIGHT * 1.6, RIGHT * 2.5 + DOWN * 0.3, DOWN * 2.0 + LEFT * 0.2]
    nodes = []
    for index, item in enumerate(items[:3]):
        box = RoundedRectangle(corner_radius=0.2, width=2.3, height=0.85, stroke_color=palette["panel"], fill_color=WHITE, fill_opacity=0.92)
        if palette["background"] == "#0B1020":
            box.set_fill(palette["panel"], opacity=0.92)
        label = safe_text(item, font_size=20, color=palette["ink"], width=1.9, height=0.5)
        group = VGroup(box, label).move_to(positions[index])
        line = Line(center_group.get_center(), group.get_center(), color=palette["panel"], stroke_width=3)
        nodes.extend([line, group])
    return VGroup(center_group, *nodes)


def comparison_visual(scene, palette):
    left = RoundedRectangle(corner_radius=0.22, width=2.6, height=3.2, stroke_color=palette["panel"], fill_color=WHITE, fill_opacity=0.95).shift(LEFT * 1.9)
    right = left.copy().shift(RIGHT * 3.8)
    if palette["background"] == "#0B1020":
        left.set_fill(palette["panel"], opacity=0.95)
        right.set_fill(palette["panel"], opacity=0.95)
    left_label = safe_text((scene.get("visual_items") or ["Left"])[0], font_size=24, color=palette["ink"], weight=SEMIBOLD, width=2.0, height=0.7).move_to(left)
    right_source = scene.get("visual_items", [None, None])
    right_text = right_source[1] if len(right_source) > 1 and right_source[1] else (scene.get("highlight_terms") or ["Right"])[-1]
    right_label = safe_text(right_text, font_size=24, color=palette["ink"], weight=SEMIBOLD, width=2.0, height=0.7).move_to(right)
    divider = Line(UP * 2.0, DOWN * 2.0, color=palette["panel"], stroke_width=3)
    return VGroup(left, right, left_label, right_label, divider)


def axes_visual(scene, palette):
    axes = Axes(
        x_range=[-3, 3, 1],
        y_range=[-3, 3, 1],
        x_length=5.4,
        y_length=4.8,
        axis_config={"color": palette["muted"], "stroke_width": 3},
        tips=False,
    )
    labels = scene.get("highlight_terms", [])
    x_label = safe_text(labels[0] if labels else "x", font_size=20, color=palette["muted"]).next_to(axes.x_axis, RIGHT, buff=0.1)
    y_label = safe_text(labels[1] if len(labels) > 1 else "y", font_size=20, color=palette["muted"]).next_to(axes.y_axis, UP, buff=0.1)
    points = []
    for index, item in enumerate((scene.get("visual_items", [])[:3] or scene.get("key_points", [])[:3])):
        coord = [(-2, -1), (0.8, 1.8), (2.1, 0.4)][index]
        dot = Dot(axes.c2p(*coord), radius=0.08, color=palette["accent"] if index % 2 == 0 else palette["accent_2"])
        label = safe_text(item, font_size=18, color=palette["ink"], width=1.6, height=0.4).next_to(dot, UR, buff=0.08)
        points.extend([dot, label])
    return VGroup(axes, x_label, y_label, *points)


def timeline_visual(scene, palette):
    base = Line(LEFT * 3.0, RIGHT * 3.0, color=palette["panel"], stroke_width=5)
    entries = scene.get("visual_items", [])[:3] or scene.get("key_points", [])[:3]
    groups = [base]
    offsets = [-2.4, 0, 2.4]
    for index, item in enumerate(entries[:3]):
        dot = Dot(radius=0.12, color=palette["accent"] if index % 2 == 0 else palette["accent_2"]).move_to(base.get_center() + RIGHT * offsets[index])
        label = safe_text(item, font_size=18, color=palette["ink"], width=1.8, height=0.7).next_to(dot, UP if index != 1 else DOWN, buff=0.25)
        groups.extend([dot, label])
    return VGroup(*groups)


def equation_visual(scene, palette):
    eq = safe_math((scene.get("equations") or [""])[0], palette)
    if eq is None:
        return concept_visual(scene, palette)
    ring = Circle(radius=1.9, color=palette["accent"], stroke_width=3).set_fill(palette["accent"], opacity=0.04)
    return VGroup(ring, eq)


def flow_visual(scene, palette):
    entries = scene.get("visual_items", [])[:3] or scene.get("key_points", [])[:3]
    groups = []
    previous = None
    for index, item in enumerate(entries[:3]):
        box = RoundedRectangle(corner_radius=0.2, width=1.9, height=0.82, stroke_width=0, fill_color=palette["accent"] if index % 2 == 0 else palette["accent_2"], fill_opacity=0.95)
        label = safe_text(item, font_size=19, color=WHITE, width=1.5, height=0.4)
        node = VGroup(box, label).move_to(LEFT * 2.4 + RIGHT * (index * 2.4))
        groups.append(node)
        if previous is not None:
            groups.append(Arrow(previous.get_right(), node.get_left(), color=palette["panel"], stroke_width=4, buff=0.16, tip_length=0.12))
        previous = node
    return VGroup(*groups)


def orbit_visual(scene, palette):
    center = Dot(radius=0.14, color=palette["accent"])
    orbit = Circle(radius=2.1, color=palette["panel"], stroke_width=2)
    terms = scene.get("visual_items", [])[:3] or scene.get("highlight_terms", [])[:3]
    nodes = [center, orbit]
    positions = [RIGHT * 2.1, UP * 1.8 + LEFT * 0.9, DOWN * 1.8 + LEFT * 0.9]
    for index, item in enumerate(terms[:3]):
        dot = Dot(radius=0.09, color=palette["accent"] if index % 2 == 0 else palette["accent_2"]).move_to(positions[index])
        label = safe_text(item, font_size=18, color=palette["ink"], width=1.5, height=0.4).next_to(dot, UR, buff=0.08)
        nodes.extend([dot, label])
    return VGroup(*nodes)


def build_visual(scene, palette):
    layout = scene.get("layout", "auto")
    if layout == "comparison":
        return comparison_visual(scene, palette)
    if layout == "axes":
        return axes_visual(scene, palette)
    if layout == "timeline":
        return timeline_visual(scene, palette)
    if layout == "equation" or scene.get("equations"):
        return equation_visual(scene, palette)
    if layout == "flow":
        return flow_visual(scene, palette)
    if layout == "orbit":
        return orbit_visual(scene, palette)
    return concept_visual(scene, palette)


def render_scene_page(scene_obj, scene_data):
    palette = colors()
    scene_obj.camera.background_color = palette["background"]

    accent_bar = Rectangle(height=7.2, width=0.18, stroke_width=0, fill_color=palette["accent"], fill_opacity=1).to_edge(LEFT, buff=0)
    scene_obj.add(accent_bar)

    info = build_info_column(scene_data, palette)
    visual = build_visual(scene_data, palette)
    visual.scale_to_fit_width(5.7)
    visual.move_to(RIGHT * 3.1)

    total = max(8.0, float(scene_data.get("target_duration_seconds", 12.0)))
    scene_obj.play(FadeIn(info[0], shift=UP * 0.2), run_time=0.35)
    if len(info) > 1:
        scene_obj.play(FadeIn(info[1], shift=RIGHT * 0.12), run_time=0.25)
    if len(info) > 2 and len(info[2]):
        for row in info[2]:
            scene_obj.play(FadeIn(row, shift=UP * 0.1), run_time=0.2)

    if isinstance(visual, VGroup):
        animations = []
        for item in visual:
            if isinstance(item, (Line, Arrow, Axes)):
                animations.append(Create(item))
            elif isinstance(item, (Circle, Dot, RoundedRectangle, Rectangle)):
                animations.append(GrowFromCenter(item))
            else:
                animations.append(FadeIn(item, shift=UP * 0.08))
        scene_obj.play(LaggedStart(*animations, lag_ratio=0.08), run_time=min(1.5, total * 0.22))
    else:
        scene_obj.play(FadeIn(visual, shift=UP * 0.08), run_time=min(1.5, total * 0.22))

    scene_obj.wait(max(0.4, total - 2.3))


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
        .replace("__SCENE_CLASSES__", scene_classes)
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(module, encoding="utf-8")
    return output_path
