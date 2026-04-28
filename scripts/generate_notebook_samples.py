#!/usr/bin/env python3
"""
generate_notebook_samples.py — Build handwriting-style SVG "notebook page"
samples for every Notebook Capture item in the Aylana homework. Each SVG
mimics a photo of a student's handwritten work: ruled paper, slight tilt,
ink-blue cursive font, hand-drawn-looking diagram.

Run:
  python scripts/generate_notebook_samples.py \
    --out D:/Homework_Builder/repo/dist/aylananing_kesuvchilari_burchaklari_xossasi/static/samples/

Each generated file is a standalone SVG that renders correctly when loaded
as <img> or as a data URL.
"""

from __future__ import annotations

import argparse
import math
import random
from pathlib import Path

# Color palette — looks like a real ballpoint on lined paper
PAPER = "#FBFAF5"          # warm off-white
RULE_LINE = "#BFD8E6"      # light blue ruling
MARGIN_LINE = "#E8B5C0"    # red margin
INK_DARK = "#1F2A6E"       # navy ink
INK_LIGHT = "#3F4FA8"      # slightly lighter ink
PENCIL = "#2C2C2C"         # graphite for sketches

# Fonts: system-only handwriting stack — no external @import so the SVG
# can be rasterized via canvas in any browser security context.
# Order: Mac (Bradley Hand, Marker Felt) -> Windows (Segoe Script,
# Comic Sans MS) -> generic cursive fallback.
FONT_IMPORT = """
<style>
.hw, .hwm { font-family: 'Bradley Hand ITC', 'Bradley Hand', 'Marker Felt', 'Segoe Script', 'Comic Sans MS', cursive; fill: #1F2A6E; }
.hw  { font-size: 30px; font-weight: 500; }
.hwm { font-size: 24px; font-weight: 400; }
.hwl { font-family: 'Bradley Hand ITC', 'Marker Felt', 'Segoe Script', 'Comic Sans MS', cursive; font-size: 20px; fill: #3F4FA8; }
.hwbig { font-family: 'Bradley Hand ITC', 'Marker Felt', 'Segoe Script', 'Comic Sans MS', cursive; font-size: 36px; font-weight: 600; fill: #1F2A6E; }
.hwlabel { font-family: 'Bradley Hand ITC', 'Marker Felt', 'Segoe Script', 'Comic Sans MS', cursive; font-size: 16px; fill: #2C2C2C; }
</style>
"""


def jitter(seed: int, amplitude: float = 1.5) -> float:
    """Tiny pseudo-random offset — we use it to make lines look hand-drawn."""
    random.seed(seed)
    return (random.random() - 0.5) * amplitude * 2


def hand_line(x1, y1, x2, y2, color=PENCIL, width=1.8, seed=0) -> str:
    """Draw a line with a slightly wobbly path so it looks pencil-stroked."""
    # Quadratic curve with mid-point jitter
    mx = (x1 + x2) / 2 + jitter(seed, 1.5)
    my = (y1 + y2) / 2 + jitter(seed + 1, 1.5)
    return (
        f'<path d="M {x1:.1f} {y1:.1f} Q {mx:.1f} {my:.1f} {x2:.1f} {y2:.1f}" '
        f'fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round"/>'
    )


def hand_circle(cx, cy, r, color=PENCIL, width=1.8, seed=0) -> str:
    """A wobbly circle drawn as a path — looks hand-drawn."""
    # Use 4 cubic-bezier arcs with slight radius jitter on each control
    ps = []
    for i in range(8):
        theta = i * math.pi / 4
        rr = r + jitter(seed + i, 1.0)
        x = cx + rr * math.cos(theta)
        y = cy + rr * math.sin(theta)
        ps.append((x, y))
    # Close the loop
    ps.append(ps[0])
    d = f"M {ps[0][0]:.1f} {ps[0][1]:.1f}"
    for i in range(1, len(ps)):
        x_prev, y_prev = ps[i - 1]
        x_cur, y_cur = ps[i]
        cx_ctrl = (x_prev + x_cur) / 2 + jitter(seed + 100 + i, 0.5)
        cy_ctrl = (y_prev + y_cur) / 2 + jitter(seed + 200 + i, 0.5)
        d += f" Q {cx_ctrl:.1f} {cy_ctrl:.1f} {x_cur:.1f} {y_cur:.1f}"
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round"/>'


def hand_circle_label(cx, cy, r, color=PENCIL, width=2.5, seed=0) -> str:
    """Imperfect circle around a final answer, like a student's emphasis circle."""
    return hand_circle(cx, cy, r, color=INK_LIGHT, width=width, seed=seed)


def hand_arc(cx, cy, r, start_deg, end_deg, color=PENCIL, width=1.8, seed=0) -> str:
    """Arc segment with hand-drawn quality."""
    sa = math.radians(start_deg)
    ea = math.radians(end_deg)
    x1 = cx + r * math.cos(sa)
    y1 = cy + r * math.sin(sa)
    x2 = cx + r * math.cos(ea)
    y2 = cy + r * math.sin(ea)
    sweep = 1 if end_deg > start_deg else 0
    large = 1 if abs(end_deg - start_deg) > 180 else 0
    return (
        f'<path d="M {x1:.1f} {y1:.1f} A {r} {r} 0 {large} {sweep} {x2:.1f} {y2:.1f}" '
        f'fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round"/>'
    )


def paper_background(width: int, height: int, tilt_deg: float = 0) -> str:
    """White lined notebook paper with a red margin and slight tilt."""
    # Horizontal ruling every 30 px starting at y=80
    rules = []
    for y in range(80, height - 20, 30):
        wob = jitter(y, 0.8)
        rules.append(
            f'<line x1="0" y1="{y + wob:.1f}" x2="{width}" y2="{y - wob:.1f}" '
            f'stroke="{RULE_LINE}" stroke-width="1"/>'
        )
    margin = (
        f'<line x1="60" y1="0" x2="60" y2="{height}" '
        f'stroke="{MARGIN_LINE}" stroke-width="1"/>'
    )
    return f"""<rect width="{width}" height="{height}" fill="{PAPER}"/>
    {margin}
    {''.join(rules)}"""


def make_svg(content_inner: str, width: int = 600, height: int = 800,
              tilt_deg: float = 0) -> str:
    """Wrap content in a tilted SVG that mimics a photographed notebook page."""
    cx = width / 2
    cy = height / 2
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}"
     style="background: #2A2820;">
  {FONT_IMPORT}
  <!-- subtle desk shadow -->
  <rect x="20" y="20" width="{width-40}" height="{height-40}"
        fill="rgba(0,0,0,0.25)" rx="3"/>
  <g transform="rotate({tilt_deg} {cx} {cy})">
    {paper_background(width, height, tilt_deg)}
    {content_inner}
  </g>
</svg>"""


# ----------------------------------------------------------------------------
# Per-item content renderers
# ----------------------------------------------------------------------------

def aq_q1():
    """Arc 100°, arc 40° → ∠P = 30°"""
    inner = f"""
    <text x="80" y="120" class="hwbig">1-savol</text>
    <text x="80" y="160" class="hwl">Berilgan: katta yoy = 100°, kichik yoy = 40°</text>

    <text x="80" y="220" class="hw">Aylana kesuvchilari xossasi:</text>
    <text x="80" y="270" class="hw">∠P = (katta − kichik) / 2</text>

    <text x="80" y="340" class="hw">∠P = (100° − 40°) / 2</text>
    <text x="80" y="385" class="hw">    = 60° / 2</text>
    <text x="80" y="430" class="hw">    = 30°</text>

    <!-- Diagram in the lower right -->
    <g transform="translate(360, 220)">
      {hand_circle(80, 80, 60, color=PENCIL, seed=11)}
      <!-- Two secants from external point P -->
      {hand_line(-40, 80, 145, 50, color=PENCIL, seed=12)}
      {hand_line(-40, 80, 145, 110, color=PENCIL, seed=13)}
      <!-- Arc highlights -->
      {hand_arc(80, 80, 60, -25, 25, color=INK_LIGHT, width=2.5, seed=14)}
      {hand_arc(80, 80, 60, 155, 205, color=INK_LIGHT, width=2.5, seed=15)}
      <text x="-35" y="84" class="hwlabel">P</text>
      <text x="155" y="50" class="hwlabel" fill="{INK_DARK}">100°</text>
      <text x="-10" y="84" class="hwlabel" fill="{INK_DARK}">40°</text>
    </g>

    <!-- Final circled answer -->
    <text x="220" y="540" class="hwbig">∠P = 30°</text>
    {hand_circle_label(305, 530, 95, seed=99)}
    """
    return make_svg(inner, tilt_deg=-1.2)


def aq_q2():
    """Tangent + secant, arcs 140° and 60° → angle = 40°"""
    inner = f"""
    <text x="80" y="120" class="hwbig">2-savol</text>
    <text x="80" y="160" class="hwl">Urinma + kesuvchi, katta = 140°, kichik = 60°</text>

    <text x="80" y="220" class="hw">Bu holat ham aynan</text>
    <text x="80" y="265" class="hw">ayirma qoidasiga bo'ysunadi:</text>

    <text x="80" y="340" class="hw">∠ = (140° − 60°) / 2</text>
    <text x="80" y="385" class="hw">  = 80° / 2</text>
    <text x="80" y="430" class="hw">  = 40°</text>

    <g transform="translate(380, 240)">
      {hand_circle(80, 70, 55, color=PENCIL, seed=21)}
      {hand_line(-30, 70, 130, 30, color=PENCIL, seed=22)}
      {hand_line(-30, 70, 80, 130, color=PENCIL, seed=23)}
      {hand_arc(80, 70, 55, -60, 60, color=INK_LIGHT, width=2.5, seed=24)}
      <text x="-32" y="74" class="hwlabel">P</text>
      <text x="135" y="30" class="hwlabel" fill="{INK_DARK}">140°</text>
      <text x="20" y="138" class="hwlabel" fill="{INK_DARK}">60°</text>
    </g>

    <text x="220" y="560" class="hwbig">∠ = 40°</text>
    {hand_circle_label(290, 552, 80, seed=98)}
    """
    return make_svg(inner, tilt_deg=0.8)


def aq_q3():
    """45° = (150° - x) / 2 → x = 60°"""
    inner = f"""
    <text x="80" y="120" class="hwbig">3-savol</text>
    <text x="80" y="160" class="hwl">∠ = 45°, katta = 150°, kichik = ?</text>

    <text x="80" y="220" class="hw">45° = (150° − x) / 2</text>
    <text x="80" y="270" class="hw">| · 2</text>

    <text x="80" y="340" class="hw">90° = 150° − x</text>
    <text x="80" y="385" class="hw">x = 150° − 90°</text>
    <text x="80" y="430" class="hw">x = 60°</text>

    <g transform="translate(380, 240)">
      {hand_circle(80, 70, 55, color=PENCIL, seed=31)}
      {hand_line(-30, 70, 130, 30, color=PENCIL, seed=32)}
      {hand_line(-30, 70, 130, 110, color=PENCIL, seed=33)}
      {hand_arc(80, 70, 55, -45, 45, color=INK_LIGHT, width=2.5, seed=34)}
      <text x="-32" y="74" class="hwlabel">P</text>
      <text x="-5" y="76" class="hwlabel" fill="{INK_DARK}">45°</text>
      <text x="138" y="30" class="hwlabel" fill="{INK_DARK}">150°</text>
      <text x="35" y="74" class="hwlabel" fill="{INK_LIGHT}">x = ?</text>
    </g>

    <text x="220" y="560" class="hwbig">x = 60°</text>
    {hand_circle_label(285, 552, 78, seed=97)}
    """
    return make_svg(inner, tilt_deg=-0.6)


def aq_q4():
    """50° = (x - 20°) / 2 → x = 120°"""
    inner = f"""
    <text x="80" y="120" class="hwbig">4-savol</text>
    <text x="80" y="160" class="hwl">∠ = 50°, kichik = 20°, katta = ?</text>

    <text x="80" y="220" class="hw">50° = (x − 20°) / 2</text>

    <text x="80" y="290" class="hw">100° = x − 20°</text>
    <text x="80" y="335" class="hw">x = 100° + 20°</text>
    <text x="80" y="380" class="hw">x = 120°</text>

    <text x="80" y="450" class="hwm">Tekshirish:</text>
    <text x="80" y="490" class="hw">(120° − 20°) / 2 = 50° ✓</text>

    <g transform="translate(380, 240)">
      {hand_circle(80, 70, 55, color=PENCIL, seed=41)}
      {hand_line(-30, 70, 130, 35, color=PENCIL, seed=42)}
      {hand_line(-30, 70, 130, 105, color=PENCIL, seed=43)}
      {hand_arc(80, 70, 55, -50, 50, color=INK_LIGHT, width=2.5, seed=44)}
      <text x="-32" y="74" class="hwlabel">P</text>
      <text x="-5" y="76" class="hwlabel" fill="{INK_DARK}">50°</text>
      <text x="138" y="40" class="hwlabel" fill="{INK_LIGHT}">x</text>
      <text x="20" y="78" class="hwlabel" fill="{INK_DARK}">20°</text>
    </g>

    <text x="220" y="610" class="hwbig">x = 120°</text>
    {hand_circle_label(305, 602, 95, seed=96)}
    """
    return make_svg(inner, tilt_deg=1.0)


def aq_q5():
    """∠P = 40°, katta = 3x, kichik = x → x = 40°"""
    inner = f"""
    <text x="80" y="120" class="hwbig">5-savol</text>
    <text x="80" y="160" class="hwl">∠P = 40°, katta : kichik = 3 : 1</text>

    <text x="80" y="220" class="hw">Yoylar: katta = 3x,  kichik = x</text>

    <text x="80" y="290" class="hw">40° = (3x − x) / 2</text>
    <text x="80" y="335" class="hw">40° = 2x / 2</text>
    <text x="80" y="380" class="hw">40° = x</text>

    <text x="80" y="450" class="hwm">Demak:</text>
    <text x="80" y="490" class="hw">kichik yoy x = 40°</text>
    <text x="80" y="535" class="hw">katta yoy 3x = 120°</text>

    <g transform="translate(380, 250)">
      {hand_circle(80, 70, 55, color=PENCIL, seed=51)}
      {hand_line(-30, 70, 130, 30, color=PENCIL, seed=52)}
      {hand_line(-30, 70, 130, 110, color=PENCIL, seed=53)}
      {hand_arc(80, 70, 55, -40, 40, color=INK_LIGHT, width=2.5, seed=54)}
      <text x="-32" y="74" class="hwlabel">P</text>
      <text x="-5" y="76" class="hwlabel" fill="{INK_DARK}">40°</text>
      <text x="135" y="35" class="hwlabel" fill="{INK_LIGHT}">3x</text>
      <text x="22" y="74" class="hwlabel" fill="{INK_LIGHT}">x</text>
    </g>

    <text x="220" y="640" class="hwbig">x = 40°</text>
    {hand_circle_label(285, 632, 80, seed=95)}
    """
    return make_svg(inner, tilt_deg=-0.9)


def rl_q1():
    """Real-Life Q1: ∠P = (150° - 70°) / 2 = 40°"""
    inner = f"""
    <text x="80" y="120" class="hwbig">Metro burchak</text>
    <text x="80" y="160" class="hwl">Katta yoy = 150°, kichik yoy = 70°</text>

    <text x="80" y="220" class="hw">Formulani yozaman:</text>
    <text x="80" y="265" class="hw">∠P = (150° − 70°) / 2</text>

    <text x="80" y="340" class="hw">  = 80° / 2</text>
    <text x="80" y="385" class="hw">  = 40°</text>

    <text x="80" y="455" class="hwm">Yo'lovchilar uchun keng,</text>
    <text x="80" y="490" class="hwm">tirbandlik yo'q ✓</text>

    <g transform="translate(380, 220)">
      {hand_circle(90, 90, 70, color=PENCIL, seed=61)}
      {hand_line(-30, 90, 155, 40, color=PENCIL, seed=62)}
      {hand_line(-30, 90, 155, 140, color=PENCIL, seed=63)}
      {hand_arc(90, 90, 70, -40, 40, color=INK_LIGHT, width=2.5, seed=64)}
      {hand_arc(90, 90, 70, 140, 220, color=INK_LIGHT, width=2.5, seed=65)}
      <text x="-32" y="94" class="hwlabel">P</text>
      <text x="160" y="40" class="hwlabel" fill="{INK_DARK}">150°</text>
      <text x="0" y="94" class="hwlabel" fill="{INK_DARK}">70°</text>
    </g>

    <text x="220" y="600" class="hwbig">∠P = 40°</text>
    {hand_circle_label(305, 592, 95, seed=94)}
    """
    return make_svg(inner, tilt_deg=0.5)


def rl_q2():
    """Real-Life Q2: 30° = (110° - x) / 2 → x = 50°"""
    inner = f"""
    <text x="80" y="120" class="hwbig">Arxitektor xatosi</text>
    <text x="80" y="160" class="hwl">∠Q = 30°, katta = 110°, kichik = ?</text>

    <text x="80" y="220" class="hw">Tenglamani tuzaman:</text>
    <text x="80" y="265" class="hw">30° = (110° − x) / 2</text>

    <text x="80" y="340" class="hw">| · 2</text>
    <text x="80" y="385" class="hw">60° = 110° − x</text>

    <text x="80" y="455" class="hw">x = 110° − 60°</text>
    <text x="80" y="500" class="hw">x = 50°</text>

    <text x="80" y="570" class="hwm">Loyiha amalga oshadi —</text>
    <text x="80" y="605" class="hwm">kichik yoy = 50° ✓</text>

    <g transform="translate(380, 240)">
      {hand_circle(90, 80, 55, color=PENCIL, seed=71)}
      {hand_line(-30, 80, 145, 35, color=PENCIL, seed=72)}
      {hand_line(-30, 80, 145, 125, color=PENCIL, seed=73)}
      {hand_arc(90, 80, 55, -30, 30, color=INK_LIGHT, width=2.5, seed=74)}
      <text x="-32" y="84" class="hwlabel">Q</text>
      <text x="-3" y="84" class="hwlabel" fill="{INK_DARK}">30°</text>
      <text x="148" y="40" class="hwlabel" fill="{INK_DARK}">110°</text>
      <text x="35" y="84" class="hwlabel" fill="{INK_LIGHT}">x</text>
    </g>

    <text x="220" y="700" class="hwbig">x = 50°</text>
    {hand_circle_label(285, 692, 80, seed=93)}
    """
    return make_svg(inner, tilt_deg=-1.4)


def rl_q3():
    """Real-Life Q3: katta yoy +20% → ∠P = 55°, ∆ = 15°"""
    inner = f"""
    <text x="80" y="120" class="hwbig">What-if ssenariy</text>
    <text x="80" y="160" class="hwl">Katta yoy +20%, kichik = 70° o'zgarmas</text>

    <text x="80" y="220" class="hw">Yangi katta yoy:</text>
    <text x="80" y="265" class="hw">150° · 1.2 = 180°</text>

    <text x="80" y="340" class="hw">Yangi ∠P:</text>
    <text x="80" y="385" class="hw">∠P' = (180° − 70°) / 2</text>
    <text x="80" y="430" class="hw">    = 110° / 2</text>
    <text x="80" y="475" class="hw">    = 55°</text>

    <text x="80" y="550" class="hwm">Farq:</text>
    <text x="80" y="590" class="hw">Δ = 55° − 40° = 15°</text>

    <g transform="translate(380, 240)">
      {hand_circle(90, 90, 65, color=PENCIL, seed=81)}
      {hand_line(-30, 90, 155, 30, color=PENCIL, seed=82)}
      {hand_line(-30, 90, 155, 150, color=PENCIL, seed=83)}
      {hand_arc(90, 90, 65, -55, 55, color=INK_LIGHT, width=2.5, seed=84)}
      <text x="-32" y="94" class="hwlabel">P'</text>
      <text x="-3" y="94" class="hwlabel" fill="{INK_DARK}">55°</text>
      <text x="158" y="34" class="hwlabel" fill="{INK_DARK}">180°</text>
    </g>

    <text x="220" y="680" class="hwbig">Δ = 15°</text>
    {hand_circle_label(285, 672, 78, seed=92)}
    """
    return make_svg(inner, tilt_deg=1.3)


# ----------------------------------------------------------------------------

GENERATORS = {
    "aq_q1.svg": aq_q1,
    "aq_q2.svg": aq_q2,
    "aq_q3.svg": aq_q3,
    "aq_q4.svg": aq_q4,
    "aq_q5.svg": aq_q5,
    "rl_q1.svg": rl_q1,
    "rl_q2.svg": rl_q2,
    "rl_q3.svg": rl_q3,
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True,
                   help="Output directory (will be created)")
    args = p.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)

    print(f"Writing {len(GENERATORS)} samples to {args.out}/")
    for name, gen in GENERATORS.items():
        svg = gen()
        target = args.out / name
        target.write_text(svg, encoding="utf-8")
        print(f"  [OK] {name}  ({len(svg)} chars)")
    print()
    print("Done. Reference these from homework_data.js as:")
    print("  notebook_sample: '/samples/aq_q1.svg'")


if __name__ == "__main__":
    main()
