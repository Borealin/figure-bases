"""生成 docs/ 下的预览图。

用法：python preview.py
"""
import base64
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import render  # noqa: E402
import figure_base as fb  # noqa: E402

DOCS = HERE / "docs"
FONT = 'font-family="Microsoft YaHei, PingFang SC, sans-serif"'
C2B, CA2, GR = (230, 200, 110), (120, 190, 230), (205, 205, 205)


def png_b64(img):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "x.png"
        render.write_png(p, img)
        return base64.b64encode(p.read_bytes()).decode()


def label(x, y, text, size=24):
    return (f'<text x="{x:.0f}" y="{y:.0f}" text-anchor="middle" font-size="{size}" font-weight="700" '
            f'fill="#222" stroke="#fafaf8" stroke-width="6" paint-order="stroke">{text}</text>')


def trial_preview(name="trial_v2"):
    parts, _ = fb.build_trial()
    colors = {"B1": C2B, "B2": C2B, "H1": CA2, "H2T": CA2, "tol": GR}
    shapes = [(parts[k].translate((*fb.TRIAL_LAYOUT[k], 0)).val(), colors[k]) for k in parts]
    img, proj = render.render(shapes, width=1300, az=-15, el=55, pad=80)
    H, W = img.shape[:2]
    T = fb.PAD_T
    L = fb.TRIAL_LAYOUT
    labels = [("2B B1", (L["B1"][0], L["B1"][1] + 8, T)), ("2B B2", (L["B2"][0], L["B2"][1] + 8, T)),
              ("A2 H1", (L["H1"][0], L["H1"][1] + 7, T)), ("A2 H2 + 鞋跟 T", (L["H2T"][0] - 4, L["H2T"][1] + 7, T))]
    if "tol" in parts:
        labels.append(("公差条：上排 H、下排 B，-0.1 ~ +0.3", (L["tol"][0], L["tol"][1] - 12, 0)))
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" {FONT}>',
           f'<image href="data:image/png;base64,{png_b64(img)}" width="{W}" height="{H}"/>']
    for text, pt in labels:
        x, y = proj(pt)
        svg.append(label(x, y + (-16 if pt[2] > 0 else 34), text))
    svg.append("</svg>")
    out = DOCS / f"{name}.svg"
    out.write_text("\n".join(svg), encoding="utf-8")
    return out


def base_preview():
    """俯视图（画在 A1 mini 平台上）+ 试摆底座和正式底座的立体图。"""
    import math
    holes, _ = fb.solve_layout()
    solid = fb.build_base(holes)
    bb = solid.val().BoundingBox()
    cx, cy = bb.center.x, bb.center.y
    S, PAD = 3.0, 30
    half = fb.BED / 2
    X = lambda x: (x - (cx - half)) * S + PAD  # noqa: E731
    Y = lambda y: ((cy + half) - y) * S + PAD  # noqa: E731
    V = fb.BED * S + 2 * PAD
    wire = solid.faces("<Z").val().outerWire()
    path = lambda pts: "M" + " L".join(f"{X(p[0]):.1f},{Y(p[1]):.1f}" for p in pts) + " Z"  # noqa: E731
    outline = [(p.x, p.y) for p in (wire.positionAt(i / 400) for i in range(401))]
    top = [f'<rect x="{PAD}" y="{PAD}" width="{fb.BED*S}" height="{fb.BED*S}" fill="#f4f4f2" '
           f'stroke="#999" stroke-width="2" stroke-dasharray="8 6"/>',
           f'<text x="{PAD+8}" y="{PAD+24}" font-size="20" fill="#888">A1 mini 平台 180 × 180</text>',
           f'<path d="{path(outline)}" fill="#c9d6ea" stroke="#5a78a8" stroke-width="2"/>']
    ang = fb.placements(holes)
    for k in ("B1", "B2"):
        pts = [(holes[k][0] + q[0], holes[k][1] + q[1]) for q in (fb.rot2(p, ang[k]) for p in fb.heel(k))]
        top.append(f'<path d="{path(pts)}" fill="#f3dfa0" stroke="#b8860b" stroke-width="2"/>')
    tri = [(holes["H2"][0] + q[0], holes["H2"][1] + q[1]) for q in (fb.rot2(p, ang["T"]) for p in fb.t_triangle())]
    top.append(f'<path d="{path(tri)}" fill="#bfe3f5" stroke="#2c7fb8" stroke-width="2"/>')
    for name, c in fb.orig_centers(holes).items():
        top.append(f'<circle cx="{X(c[0]):.1f}" cy="{Y(c[1]):.1f}" r="{fb.COG_R*S:.1f}" fill="none" '
                   f'stroke="#999" stroke-width="1.5" stroke-dasharray="5 5"/>')
        top.append(f'<text x="{X(c[0]):.1f}" y="{Y(c[1])+6:.1f}" text-anchor="middle" font-size="16" fill="#888">'
                   f'{name} 原厂底座中心</text>')
    for k, (x, y) in holes.items():
        r = fb.PEGS[k][0] / math.sqrt(3) * S
        hexp = " ".join(f"{X(x)+r*math.cos(math.radians(60*i)):.1f},{Y(y)-r*math.sin(math.radians(60*i)):.1f}"
                        for i in range(6))
        top.append(f'<polygon points="{hexp}" fill="#333"/>')
    for k, (dx, dy) in {"B1": (8, 46), "B2": (0, 46), "H1": (-40, 6), "H2": (40, -16)}.items():
        x, y = holes[k]
        top.append(f'<text x="{X(x)+dx:.1f}" y="{Y(y)+dy:.1f}" text-anchor="middle" font-size="22" '
                   f'font-weight="700" fill="#222">{k}</text>')
    top.append(f'<text x="{V/2}" y="{V-6}" text-anchor="middle" font-size="20" fill="#555">'
               f'底座 {bb.xlen:.0f} × {bb.ylen:.0f} × {fb.BASE_T:.0f} mm</text>')

    thin = fb.build_base(holes, thin=True)
    imgs = []
    for body, color, title in ((thin, (200, 170, 120), "试摆底座（0.8mm 底板 + 桩）"),
                               (solid, (120, 150, 200), "正式底座（11mm 实心）")):
        img, _ = render.render([(body.val(), color)], width=700, az=-20, el=50, pad=20)
        imgs.append((img, title))
    col_w = 700
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {V + 30 + col_w} {V}" {FONT}>',
           '<rect width="100%" height="100%" fill="#fafaf8"/>', *top]
    y = 10
    for img, title in imgs:
        h, w = img.shape[:2]
        sc = min(1.0, (V / 2 - 40) / h)
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
    import sys
    DOCS.mkdir(exist_ok=True)
    if "--trial" in sys.argv:
        print("已输出", trial_preview())
    print("已输出", base_preview())
