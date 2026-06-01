"""
Minimal SVG dimension sketch template.
"""

from pathlib import Path


OUT = Path(__file__).resolve().parent / "output" / "dimensioned_section.svg"
W = 720
H = 420
SCALE = 12.0
MARGIN = 60.0

MODEL_X_MIN = -25.0
MODEL_Z_MIN = -10.0


def sx(x):
    return MARGIN + (x - MODEL_X_MIN) * SCALE


def sy(z):
    return H - MARGIN - (z - MODEL_Z_MIN) * SCALE


def line(x1, z1, x2, z2, cls="solid"):
    return f'<line class="{cls}" x1="{sx(x1):.1f}" y1="{sy(z1):.1f}" x2="{sx(x2):.1f}" y2="{sy(z2):.1f}"/>'


def text(x, z, value, cls="label"):
    return f'<text class="{cls}" x="{sx(x):.1f}" y="{sy(z):.1f}" text-anchor="middle">{value}</text>'


def main():
    body = f'<rect class="body" x="{sx(-20):.1f}" y="{sy(10):.1f}" width="{40*SCALE:.1f}" height="{20*SCALE:.1f}"/>'
    bore = line(-22, 0, 22, 0, "void")
    label = text(0, 13, "Example section, dimensions in mm", "title")

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <style>
    .body {{ fill:#9fc5e8; stroke:#1f4e79; stroke-width:1.5; }}
    .void {{ stroke:#111; stroke-width:3; fill:none; }}
    .label {{ font: 12px Arial, sans-serif; fill:#111; }}
    .title {{ font: bold 16px Arial, sans-serif; fill:#111; }}
  </style>
  <rect width="{W}" height="{H}" fill="#fff"/>
  {label}
  {body}
  {bore}
</svg>
'''
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(svg, encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
