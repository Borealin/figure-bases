"""生成 docs/ 下的预览图：验证垫块、正式底座（俯视 + 立体）。

用法：python preview.py
"""
import base64
import math
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import render  # noqa: E402
import figure_base as fb  # noqa: E402

DOCS = HERE / "docs"
FONT = 'font-family="Microsoft YaHei, PingFang SC, sans-serif"'
PJ, PR, GR = (170, 130, 220), (190, 215, 90), (205, 205, 205)


def png_b64(img):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "x.png"
        render.write_png(p, img)
        return base64.b64encode(p.read_bytes()).decode()


def label(x, y, text, size=24):
    return (f'<text x="{x:.0f}" y="{y:.0f}" text-anchor="middle" font-size="{size}" font-weight="700" '
            f'fill="#222" stroke="#fafaf8" stroke-width="6" paint-order="stroke">{text}</text>')


def pads_preview():
    parts, _ = fb.build_trial()
    colors = {"J1J2": PJ, "J3": PJ, "R1": PR, "R2R3": PR, "tol": GR}
    shapes = [(parts[k].translate((*fb.TRIAL_LAYOUT[k], 0)).val(), colors[k]) for k in parts]
    img, proj = render.render(shapes, width=1300, az=-20, el=55, pad=70)
    H, W = img.shape[:2]
    labels = {
        "J1J2": ("仗助前脚 J1+J2（J2 孔较小）", (-35, 31, fb.T)),
        "R1": ("露伴前脚 R1", (-8, 31, fb.T)),
        "J3": ("仗助后脚 J3", (12, 36, fb.T)),
        "R2R3": ("露伴后脚 R2+R3", (-30, -10, 0)),
        "tol": ("公差条：孔径 +0.0 ~ +0.4", (12, -7, 0)),
    }
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" {FONT}>',
           f'<image href="data:image/png;base64,{png_b64(img)}" width="{W}" height="{H}"/>']
    for text, pt in labels.values():
        x, y = proj(pt)
        svg.append(label(x, y + (-18 if pt[2] > 0 else 34), text))
    svg.append("</svg>")
    (DOCS / "test_pads.svg").write_text("\n".join(svg), encoding="utf-8")


def base_preview():
    holes, _ = fb.solve_layout()
    body, _ = fb.build_solid_base(holes)
    bb = body.val().BoundingBox()
    cx, cy = bb.center.x, bb.center.y

    img, _ = render.render([(body.val(), (120, 150, 200))], width=900, az=-15, el=50, pad=40)
    IH, IW = img.shape[:2]

    # 俯视图画在 A1 mini 平台上（mm -> px）
    S, PAD = 3.0, 30
    half = fb.BED / 2
    X = lambda x: (x - (cx - half)) * S + PAD  # noqa: E731
    Y = lambda y: ((cy + half) - y) * S + PAD  # noqa: E731
    V = fb.BED * S + 2 * PAD
    wire = body.faces("<Z").val().outerWire()
    pts = [wire.positionAt(i / 400) for i in range(401)]
    outline = "M" + " L".join(f"{X(p.x):.1f},{Y(p.y):.1f}" for p in pts) + " Z"
    top = [f'<rect x="{PAD}" y="{PAD}" width="{fb.BED*S}" height="{fb.BED*S}" fill="#f4f4f2" '
           f'stroke="#999" stroke-width="2" stroke-dasharray="8 6"/>',
           f'<text x="{PAD+8}" y="{PAD+24}" font-size="20" fill="#888">A1 mini 平台 180 × 180</text>',
           f'<path d="{outline}" fill="#c9d6ea" stroke="#5a78a8" stroke-width="2"/>']
    for a, b, c in [("J1", "J2", "#a47be0"), ("J3", None, "#a47be0"),
                    ("R1", None, "#9cc43a"), ("R2", "R3", "#9cc43a")]:
        pa = holes[a]
        pb = holes[b] if b else pa
        top.append(f'<line x1="{X(pa[0]):.1f}" y1="{Y(pa[1]):.1f}" x2="{X(pb[0]):.1f}" y2="{Y(pb[1]):.1f}" '
                   f'stroke="{c}" stroke-opacity=".55" stroke-width="{2*fb.POST_R*S:.1f}" stroke-linecap="round"/>')
    for k, (x, y) in holes.items():
        r = fb.PEGS[k][0] / math.sqrt(3) * S
        hexp = " ".join(f"{X(x)+r*math.cos(math.radians(60*i)):.1f},{Y(y)-r*math.sin(math.radians(60*i)):.1f}"
                        for i in range(6))
        top.append(f'<polygon points="{hexp}" fill="#333"/>')
    for k, (dx, dy) in {"J1": (-10, 28), "J2": (10, 28), "J3": (-34, 0),
                        "R1": (-34, 0), "R2": (36, 0), "R3": (36, 6)}.items():
        x, y = holes[k]
        top.append(f'<text x="{X(x)+dx:.1f}" y="{Y(y)+dy+7:.1f}" text-anchor="middle" font-size="20" '
                   f'font-weight="700" fill="#222">{k}</text>')
    top.append(f'<text x="{X(-45):.1f}" y="{Y(-18):.1f}" text-anchor="middle" font-size="22" '
               f'fill="#6a45b0" font-weight="700">仗助</text>')
    top.append(f'<text x="{X(25):.1f}" y="{Y(-80):.1f}" text-anchor="middle" font-size="22" '
               f'fill="#5f8a14" font-weight="700">露伴</text>')
    ax, ay = X(cx), Y(cy + 62)
    top.append(f'<line x1="{ax}" y1="{ay+40}" x2="{ax}" y2="{ay}" stroke="#d05a2a" stroke-width="4"/>'
               f'<polygon points="{ax-9},{ay+4} {ax+9},{ay+4} {ax},{ay-12}" fill="#d05a2a"/>'
               f'<text x="{ax+14}" y="{ay+26}" font-size="20" fill="#d05a2a">手办面朝这边</text>')
    top.append(f'<text x="{V/2}" y="{V-6}" text-anchor="middle" font-size="20" fill="#555">'
               f'底座 {bb.xlen:.0f} × {bb.ylen:.0f} × {fb.T:.0f} mm</text>')

    sc = min(1.0, V / IH)
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {V + 30 + IW*sc:.0f} {V}" {FONT}>',
           '<rect width="100%" height="100%" fill="#fafaf8"/>', *top,
           f'<image href="data:image/png;base64,{png_b64(img)}" x="{V + 30}" y="{(V - IH*sc)/2:.0f}" '
           f'width="{IW*sc:.0f}" height="{IH*sc:.0f}"/>', '</svg>']
    (DOCS / "base.svg").write_text("\n".join(svg), encoding="utf-8")


if __name__ == "__main__":
    DOCS.mkdir(exist_ok=True)
    pads_preview()
    base_preview()
    print("已输出", DOCS / "test_pads.svg", DOCS / "base.svg")
