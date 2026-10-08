"""生成 docs/base.svg：俯视图（两块拼起来，正面朝下）+ 试摆底座、正式底座的立体图。"""
import math
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import base_preview  # noqa: E402
import render  # noqa: E402
import figure_base as fb  # noqa: E402

COL = {"Ruby": "#d81b60", "Ai": "#8e24aa", "Aqua": "#1e5bb8", "Kana": "#c62828"}
NAME = {"Ruby": "露比", "Ai": "爱", "Aqua": "阿库亚", "Kana": "加奈"}


def main():
    holes, *_ = fb.solve_layout()
    f = list(fb.fronts(holes).values())
    deg = -(math.degrees(math.atan2(sum(v[1] for v in f), sum(v[0] for v in f))) + 90)   # 转到正面朝 -Y
    rot = lambda p: (p[0] * math.cos(math.radians(deg)) - p[1] * math.sin(math.radians(deg)),  # noqa: E731
                     p[0] * math.sin(math.radians(deg)) + p[1] * math.cos(math.radians(deg)))
    solid = [b.rotate((0, 0, 0), (0, 0, 1), deg) for b in fb.build_base(holes)]
    thin = [b.rotate((0, 0, 0), (0, 0, 1), deg) for b in fb.build_base(holes, thin=True)]
    H = {k: rot(p) for k, p in holes.items()}
    C = {g: rot(c) for g, c in fb.orig_centers(holes).items()}
    F = {g: rot(v) for g, v in fb.fronts(holes).items()}

    S, PAD = 3.6, 40
    xs = [p.X for b in solid for p in b.vertices().vals()]
    ys = [p.Y for b in solid for p in b.vertices().vals()]
    x0, y1 = min(xs) - 10, max(ys) + 10
    W, Hh = (max(xs) - min(xs) + 20) * S + 2 * PAD, (max(ys) - min(ys) + 20) * S + 2 * PAD + 40
    X = lambda x: PAD + (x - x0) * S  # noqa: E731
    Y = lambda y: PAD + (y1 - y) * S  # noqa: E731
    top = []
    for b, fill in zip(solid, ("#ead7e4", "#d6e0ef")):
        wire = b.faces("<Z").val().outerWire()
        d = "M" + " L".join(f"{X(p.x):.1f},{Y(p.y):.1f}" for p in (wire.positionAt(i / 600) for i in range(601))) + " Z"
        top.append(f'<path d="{d}" fill="{fill}" stroke="#777" stroke-width="2"/>')
    for g, c in C.items():
        top.append(f'<circle cx="{X(c[0]):.1f}" cy="{Y(c[1]):.1f}" r="{fb.COG_R * S:.1f}" fill="none" stroke="#999" '
                   f'stroke-width="1.5" stroke-dasharray="5 5"/>')
    for g, hs in fb.GROUPS.items():
        cx = sum(H[k][0] for k in hs) / len(hs)
        cy = sum(H[k][1] for k in hs) / len(hs)
        d = F[g]
        top.append(f'<line x1="{X(cx):.1f}" y1="{Y(cy):.1f}" x2="{X(cx + 16 * d[0]):.1f}" y2="{Y(cy + 16 * d[1]):.1f}" '
                   f'stroke="{COL[g]}" stroke-width="4" marker-end="url(#a{g})"/>')
        top.append(f'<defs><marker id="a{g}" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">'
                   f'<path d="M0,0 L8,4 L0,8 z" fill="{COL[g]}"/></marker></defs>')
        for k in hs:
            x, y = H[k]
            r = fb.HOLE_FLAT[k] / math.sqrt(3) * S
            pts = " ".join(f"{X(x) + r * math.cos(math.radians(60 * i)):.1f},{Y(y) - r * math.sin(math.radians(60 * i)):.1f}"
                           for i in range(6))
            top.append(f'<polygon points="{pts}" fill="{COL[g]}"/>')
        top.append(f'<text x="{X(cx):.1f}" y="{Y(cy) - 34:.1f}" text-anchor="middle" font-size="24" font-weight="700" '
                   f'fill="{COL[g]}" stroke="white" stroke-width="5" paint-order="stroke">{NAME[g]}</text>')
    sizes = []
    for b in fb.build_base(holes):
        _, _, w, h = fb.basekit.fit_on_bed(b)
        sizes.append(f"{w:.0f} × {h:.0f}")
    top.append(f'<text x="{W / 2:.0f}" y="{Hh - 14:.0f}" text-anchor="middle" font-size="20" fill="#555">'
               f'↓ 正面　两块 {sizes[0]}、{sizes[1]} mm　箭头 = 朝向　虚线圆 = 原厂底座中心</text>')

    col_w = 640
    imgs = []
    y = 10
    for parts, title in ((thin, "试摆底座（0.8mm 底板 + 桩 + 凸字）"), (solid, "正式底座（11mm 实心 + 刻字）")):
        img, _ = render.render([(parts[0].val(), (205, 150, 185)), (parts[1].val(), (140, 165, 210))],
                               width=900, az=0, el=50, pad=20)
        h, w = img.shape[:2]
        sc = min(1.0, (Hh / 2 - 50) / h, col_w / w)
        imgs.append(f'<text x="{W + 30 + col_w / 2:.0f}" y="{y + 26}" text-anchor="middle" font-size="22" '
                    f'font-weight="700" fill="#333">{title}</text>')
        imgs.append(f'<image href="data:image/png;base64,{base_preview.png_b64(img)}" x="{W + 30 + (col_w - w * sc) / 2:.0f}" '
                    f'y="{y + 40}" width="{w * sc:.0f}" height="{h * sc:.0f}"/>')
        y += Hh / 2
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W + 30 + col_w:.0f} {Hh:.0f}" {base_preview.FONT}>',
           '<rect width="100%" height="100%" fill="#fafaf8"/>', *top, *imgs, "</svg>"]
    out = HERE / "docs" / "base.svg"
    out.write_text("\n".join(svg), encoding="utf-8")
    print("已输出", out)


if __name__ == "__main__":
    main()
