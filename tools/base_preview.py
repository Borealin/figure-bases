"""合体底座的预览图：左边俯视图画在 A1 mini 平台上（孔、原厂底座中心、手办朝向），右边立体图。"""
import base64
import math
import tempfile
from pathlib import Path

import render

FONT = 'font-family="Microsoft YaHei, PingFang SC, sans-serif"'


def png_b64(img):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "x.png"
        render.write_png(p, img)
        return base64.b64encode(p.read_bytes()).decode()


def base_svg(out, body, holes, flats, groups, centers=None, fronts=None, bed=180.0, T=11.0):
    """groups: {组名: (颜色, [孔名...])}；centers: {名字: (x, y, r)}；fronts: {组名: (起点, 方向)}。"""
    bb = body.val().BoundingBox()
    cx, cy = bb.center.x, bb.center.y
    S, PAD = 3.0, 30
    half = bed / 2
    X = lambda x: (x - (cx - half)) * S + PAD  # noqa: E731
    Y = lambda y: ((cy + half) - y) * S + PAD  # noqa: E731
    V = bed * S + 2 * PAD
    wire = body.faces("<Z").val().outerWire()
    outline = "M" + " L".join(f"{X(p.x):.1f},{Y(p.y):.1f}" for p in (wire.positionAt(i / 400) for i in range(401))) + " Z"
    top = [f'<rect x="{PAD}" y="{PAD}" width="{bed*S}" height="{bed*S}" fill="#f4f4f2" '
           f'stroke="#999" stroke-width="2" stroke-dasharray="8 6"/>',
           f'<text x="{PAD+8}" y="{PAD+24}" font-size="20" fill="#888">A1 mini 平台 180 × 180</text>',
           f'<path d="{outline}" fill="#c9d6ea" stroke="#5a78a8" stroke-width="2"/>']
    for name, (x, y, r) in (centers or {}).items():
        top.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="{r*S:.1f}" fill="none" stroke="#999" '
                   f'stroke-width="1.5" stroke-dasharray="5 5"/>')
    for g, (start, d) in (fronts or {}).items():
        color = groups[g][0]
        x0, y0 = X(start[0]), Y(start[1])
        x1, y1 = X(start[0] + 18 * d[0]), Y(start[1] + 18 * d[1])
        top.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{color}" stroke-width="4"/>')
        ang = math.atan2(y1 - y0, x1 - x0)
        tip = [(x1 + 10 * math.cos(ang), y1 + 10 * math.sin(ang)),
               (x1 + 8 * math.cos(ang + 2.4), y1 + 8 * math.sin(ang + 2.4)),
               (x1 + 8 * math.cos(ang - 2.4), y1 + 8 * math.sin(ang - 2.4))]
        top.append('<polygon points="' + " ".join(f"{a:.1f},{b:.1f}" for a, b in tip) + f'" fill="{color}"/>')
    for g, (color, names) in groups.items():
        for k in names:
            x, y = holes[k]
            r = flats[k] / math.sqrt(3) * S
            hexp = " ".join(f"{X(x)+r*math.cos(math.radians(60*i)):.1f},{Y(y)-r*math.sin(math.radians(60*i)):.1f}"
                            for i in range(6))
            top.append(f'<polygon points="{hexp}" fill="{color}"/>')
            top.append(f'<text x="{X(x):.1f}" y="{Y(y)-r-8:.1f}" text-anchor="middle" font-size="20" '
                       f'font-weight="700" fill="#222" stroke="#f4f4f2" stroke-width="5" paint-order="stroke">{k}</text>')
    top.append(f'<text x="{V/2}" y="{V-6}" text-anchor="middle" font-size="20" fill="#555">'
               f'底座 {bb.xlen:.0f} × {bb.ylen:.0f} × {T:.0f} mm　箭头 = 手办朝向</text>')
    img, _ = render.render([(body.val(), (120, 150, 200))], width=700, az=-20, el=50, pad=20)
    h, w = img.shape[:2]
    col_w = 600
    sc = min(1.0, (V - 40) / h, col_w / w)
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {V + 30 + col_w} {V}" {FONT}>',
           '<rect width="100%" height="100%" fill="#fafaf8"/>', *top,
           f'<image href="data:image/png;base64,{png_b64(img)}" x="{V + 30 + (col_w - w*sc)/2:.0f}" '
           f'y="{(V - h*sc)/2:.0f}" width="{w*sc:.0f}" height="{h*sc:.0f}"/>', "</svg>"]
    Path(out).write_text("\n".join(svg), encoding="utf-8")
    return out
