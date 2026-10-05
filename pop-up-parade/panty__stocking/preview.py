"""生成 docs/ 下的预览图。

用法：python preview.py            → docs/base.svg
      python preview.py --trial    → 另外生成 docs/trial_v1.svg
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
CS, CP = (240, 170, 200), (250, 215, 110)


def png_b64(img):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "x.png"
        render.write_png(p, img)
        return base64.b64encode(p.read_bytes()).decode()


def trial_preview():
    parts, _ = fb.build_trial()
    shapes = [(parts[k].translate((*fb.TRIAL_LAYOUT[k], 0)).val(), CS if k.startswith("S") else CP) for k in parts]
    img, _ = render.render(shapes, width=1100, az=-15, el=55, pad=40)
    H, W = img.shape[:2]
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" {FONT}>',
           f'<image href="data:image/png;base64,{png_b64(img)}" width="{W}" height="{H}"/>', "</svg>"]
    out = DOCS / "trial_v1.svg"
    out.write_text("\n".join(svg), encoding="utf-8")
    return out


def base_preview():
    """俯视图（画在 A1 mini 平台上）+ 试摆底座和正式底座的立体图。"""
    holes, _ = fb.solve_layout()
    solid = fb.add_labels(fb.build_base(holes), holes)
    bb = solid.val().BoundingBox()
    cx, cy = bb.center.x, bb.center.y
    S, PAD = 3.0, 30
    half = fb.BED / 2
    X = lambda x: (x - (cx - half)) * S + PAD  # noqa: E731
    Y = lambda y: ((cy + half) - y) * S + PAD  # noqa: E731
    V = fb.BED * S + 2 * PAD
    wire = solid.faces("<Z").val().outerWire()
    outline = "M" + " L".join(f"{X(p.x):.1f},{Y(p.y):.1f}" for p in (wire.positionAt(i / 400) for i in range(401))) + " Z"
    top = [f'<rect x="{PAD}" y="{PAD}" width="{fb.BED*S}" height="{fb.BED*S}" fill="#f4f4f2" '
           f'stroke="#999" stroke-width="2" stroke-dasharray="8 6"/>',
           f'<text x="{PAD+8}" y="{PAD+24}" font-size="20" fill="#888">A1 mini 平台 180 × 180</text>',
           f'<path d="{outline}" fill="#c9d6ea" stroke="#5a78a8" stroke-width="2"/>']
    for name, c in fb.orig_centers(holes).items():
        top.append(f'<circle cx="{X(c[0]):.1f}" cy="{Y(c[1]):.1f}" r="{fb.COG_R*S:.1f}" fill="none" '
                   f'stroke="#999" stroke-width="1.5" stroke-dasharray="5 5"/>')
        top.append(f'<text x="{X(c[0]) + fb.COG_R*S + 8:.1f}" y="{Y(c[1]) + 5:.1f}" text-anchor="start" '
                   f'font-size="16" fill="#888">{name} 原厂底座中心</text>')
    for k, (x, y) in holes.items():
        r = fb.hole_flat(k) / math.sqrt(3) * S
        color = "#c2185b" if k.startswith("S") else "#b8860b"
        hexp = " ".join(f"{X(x)+r*math.cos(math.radians(60*i)):.1f},{Y(y)-r*math.sin(math.radians(60*i)):.1f}"
                        for i in range(6))
        top.append(f'<polygon points="{hexp}" fill="{color}"/>')
    for k, (dx, dy) in {"S1": (-30, 30), "S2": (30, 30), "S3": (34, 6), "P1": (36, 8), "P2": (-36, -12)}.items():
        x, y = holes[k]
        color = "#c2185b" if k.startswith("S") else "#8a6508"
        top.append(f'<text x="{X(x)+dx:.1f}" y="{Y(y)+dy:.1f}" text-anchor="middle" font-size="22" '
                   f'font-weight="700" fill="{color}">{k}</text>')
    top.append(f'<text x="{V/2}" y="{V-6}" text-anchor="middle" font-size="20" fill="#555">'
               f'底座 {bb.xlen:.0f} × {bb.ylen:.0f} × {fb.BASE_T:.0f} mm</text>')

    thin = fb.build_base(holes, thin=True)
    col_w = 600
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {V + 30 + col_w} {V}" {FONT}>',
           '<rect width="100%" height="100%" fill="#fafaf8"/>', *top]
    y = 10
    for body, color, title in ((thin, CS, "试摆底座（0.8mm 底板 + 桩）"), (solid, (120, 150, 200), "正式底座（11mm 实心）")):
        img, _ = render.render([(body.val(), color)], width=600, az=-20, el=50, pad=20)
        h, w = img.shape[:2]
        sc = min(1.0, (V / 2 - 44) / h, col_w / w)
        svg.append(f'<text x="{V + 30 + col_w/2}" y="{y + 24}" text-anchor="middle" font-size="22" '
                   f'font-weight="700" fill="#333">{title}</text>')
        svg.append(f'<image href="data:image/png;base64,{png_b64(img)}" x="{V + 30 + (col_w - w*sc)/2:.0f}" '
                   f'y="{y + 34}" width="{w*sc:.0f}" height="{h*sc:.0f}"/>')
        y += V / 2
    svg.append("</svg>")
    out = DOCS / "base.svg"
    out.write_text("\n".join(svg), encoding="utf-8")
    return out


if __name__ == "__main__":
    DOCS.mkdir(exist_ok=True)
    if "--trial" in sys.argv:
        print("已输出", trial_preview())
    print("已输出", base_preview())
