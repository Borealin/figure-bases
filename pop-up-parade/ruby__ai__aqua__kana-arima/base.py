"""POP UP PARADE Ruby × Ai × Aqua × Kana Arima 合体底座（『【推しの子】』，四人弧形 + 爱的圆台）

孔位（images/holes.svg，IMG_5188 俯拍）：每人只有一只脚有钉，两根钉在同一只鞋上。
  R = 露比（R1 前、R2 后），A = 爱（A1 前、A2 后；另一只踮脚没钉），Q = 阿库亚（Q1 前、Q2 后）
  K = 有马加奈：K1、K2 在右脚上，鞋嵌在 2mm 深的鞋形凹槽里；K3 是抬起的左脚鞋跟下的金属柱
整块放不下 A1 mini：在爱和阿库亚中间切成两块（露比 + 爱 | 阿库亚 + 加奈），燕尾榫拼。

    python base.py [--slice] [--preview]
"""
import math
import sys
from pathlib import Path

import cadquery as cq

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import basekit  # noqa: E402
import setkit  # noqa: E402

# ---------------------------------------------------------------- 实测
PEGS = {
    "R1": (5.05, 6.8), "R2": (4.17, 6.8),
    "A1": (4.15, 7.2), "A2": (3.65, 7.2),
    "Q1": (5.15, 7.0), "Q2": (3.85, 7.0),
    "K1": (3.85, 5.0), "K2": (3.88, 5.0), "K3": (2.46, 6.6),
}   # (钉径, 露出长度)；K1、K2 的长度从鞋底量，K3 是金属柱
# 两根钉圆周上的最远距离（直接量在钉上）：中心距 = 最远距离 - r1 - r2
FAR = {("R1", "R2"): 17.25, ("A1", "A2"): 11.2, ("Q1", "Q2"): 16.12,
       ("K1", "K2"): 13.84, ("K1", "K3"): 17.35, ("K2", "K3"): 12.4}
# 加奈右脚的鞋：长 21.55，鞋头宽 8.3（K2 那头），鞋跟宽 6.2（K1 那头），嵌入 2mm；鞋跟尖在 K1 后 5.4（IMG_5188 估）
SHOE = {"len": 21.55, "toe_w": 8.3, "heel_w": 6.2, "depth": 2.0, "heel_back": 5.4}
K3_SIDE = +1   # K3 在 K1→K2 的左手边（俯拍定的；也正好是左脚在右脚左边）

# ---------------------------------------------------------------- 孔径 / 凹槽（试出来的）
# 第一波垫块孔 = 实测钉径，同盘带 96～104% 档位条；按档位条选的对边距：
HOLE_FLAT = {"R1": 5.06, "R2": 4.17, "A1": 4.17, "A2": 3.56, "Q1": 5.16, "Q2": 3.86,
             "K1": 3.88, "K2": 3.88, "K3": 2.51}
PAD2_FLAT = dict(HOLE_FLAT)     # 量摆位距离用的垫块 v2 就是这组孔径（换算中心距用）
# 正式底座 v1 打印后：阿库亚的钉注塑得不完全平行，孔偏松时最后一点会弹出来 → 再细 1%
HOLE_FLAT.update({"Q1": 5.11, "Q2": 3.82})
SPACING_ADJ = {("R1", "R2"): +0.1}                    # 垫块试装：R1–R2 间距拉大 0.1
SHOE_GROW = 0.4                                       # 鞋形凹槽每边放大
SHOE_EXTRA = {"toe_left": 0.15, "heel_right": 0.10}   # 垫块试装：鞋头往前左（大脚趾）、鞋跟往后右再扩
EXTRA_DEPTH = 1.5   # 孔比钉长多挖的深度
CHAMFER = 0.4       # 孔口倒角

# ---------------------------------------------------------------- 摆位
# 垫块 v2 上量的 15 条孔边距；每组除了量隔壁，再连一条到更远一个人的孔帮着定镜像
LAYOUT_GAPS = {
    ("Q1", "K1"): 30.0, ("Q1", "K2"): 34.6, ("Q2", "K1"): 19.3, ("Q2", "K2"): 24.7, ("Q1", "K3"): 43.6,
    ("A1", "Q1"): 48.0, ("A1", "Q2"): 53.0, ("A2", "Q1"): 51.5, ("A2", "Q2"): 55.5, ("A1", "K1"): 67.5,
    ("R1", "A1"): 77.4, ("R1", "A2"): 81.9, ("R2", "A1"): 77.0, ("R2", "A2"): 80.4, ("R1", "Q1"): 116.7,
}
GROUPS = {"Ruby": ("R1", "R2"), "Ai": ("A1", "A2"), "Aqua": ("Q1", "Q2"), "Kana": ("K1", "K2", "K3")}
ORDER = ["Ruby", "Ai", "Aqua", "Kana"]      # 正面看从左到右
CHAIN = ["Kana", "Aqua", "Ai", "Ruby"]      # 加奈固定，宁远勿近沿这条链依次往外推
# 朝向 = 组内前两个孔连线逆时针转的角度；原厂底座中心 = (起点, 终点, 沿连线, 往右)（都从 IMG_5188 俯拍估）
FRONT = {"Ruby": ("R1", "R2", 149.3), "Ai": ("A1", "A2", -155.4), "Aqua": ("Q1", "Q2", -119.8), "Kana": ("K1", "K2", -44.2)}
ORIG_CENTER = {"Ruby": ("R1", "R2", 6.5, 5.0), "Ai": ("A1", "A2", 7.5, -26.0),
               "Aqua": ("Q1", "Q2", 5.1, -5.5), "Kana": ("K1", "K2", 12.5, -4.0)}
LABELS = {"Ruby": "Ruby", "Ai": "Ai", "Aqua": "Aqua", "Kana": "Kana"}

# ---------------------------------------------------------------- 底座
BASE_T = 11.0
COG_R = 15.0
MARGIN = 10.0
DOVETAIL = dict(neck=10.0, head=16.0, depth=7.0)   # 阿库亚那块伸出榫头插进爱那块
TAB, SOCKET = 0.025, 0.025   # 总间隙 0.05（试过：0.3 松过头，0.1 略松，0 太紧）
# 爱的圆台：抬高 5mm（再高话筒 / 头发会碰到阿库亚的手肘）；要包住有钉的靴子和踮脚那只（落点按正面照估）
STAGE_H = 5.0
STAGE_PAD = 12.0                                   # 圆台边离两只脚的中心至少这么远
STAGE_LIP = 4.0                                    # 圆台外面底座至少再留这么宽
FREE_FOOT = {"Ai": ("A1", "A2", 10.7, -47.8)}      # 爱踮脚那只的落点 (起点, 终点, 沿连线, 往右)


def center_dist(a, b):
    far = FAR.get((a, b)) or FAR[(b, a)]
    adj = SPACING_ADJ.get((a, b)) or SPACING_ADJ.get((b, a)) or 0.0
    return far - (PEGS[a][0] + PEGS[b][0]) / 2 + adj


def kana_frame():
    """加奈的三个孔：K1 原点，K2 在 +X，K3 按三边距离算。"""
    d12, d13, d23 = center_dist("K1", "K2"), center_dist("K1", "K3"), center_dist("K2", "K3")
    x3 = (d13 ** 2 - d23 ** 2 + d12 ** 2) / (2 * d12)
    return {"K1": (0.0, 0.0), "K2": (d12, 0.0), "K3": (x3, K3_SIDE * math.sqrt(d13 ** 2 - x3 ** 2))}


def shoe_outline():
    """鞋形凹槽（K 坐标系）：鞋跟圆和鞋头圆的外包络，每边放大 SHOE_GROW，再按 SHOE_EXTRA 局部扩一点。"""
    hr, tr = SHOE["heel_w"] / 2 + SHOE_GROW, SHOE["toe_w"] / 2 + SHOE_GROW
    hc = -SHOE["heel_back"] - SHOE_GROW + hr
    tc = -SHOE["heel_back"] + SHOE["len"] + SHOE_GROW - tr
    e, f = SHOE_EXTRA["toe_left"] / math.sqrt(2), SHOE_EXTRA["heel_right"] / math.sqrt(2)
    circles = (basekit.circle_pts((hc, 0), hr, 48) + basekit.circle_pts((tc, 0), tr, 48)
               + basekit.circle_pts((tc + e, e), tr, 48) + basekit.circle_pts((hc - f, -f), hr, 48))
    return basekit.convex_hull(circles)


def solve_layout():
    """四组一起最小二乘（加奈固定），用朝向在镜像解里挑一个，再沿 CHAIN 宁远勿近往外推。
    返回 (holes, 拟合残差, 外推后残差, 外推距离)。"""
    local = {"Kana": kana_frame()}
    for g in ("Aqua", "Ai", "Ruby"):
        a, b = GROUPS[g]
        local[g] = {a: (0.0, 0.0), b: (center_dist(a, b), 0.0)}
    calib = {k: f / math.sqrt(3) for k, f in PAD2_FLAT.items()}
    cands = basekit.solve_groups(local, LAYOUT_GAPS, calib, fixed="Kana")
    _, _, poses = basekit.pick_by_fronts(local, cands, FRONT)
    cd = {k: g + calib[k[0]] + calib[k[1]] for k, g in LAYOUT_GAPS.items()}
    resid = lambda P: {k: math.dist(P[k[0]], P[k[1]]) - d for k, d in cd.items()}  # noqa: E731
    r0 = resid(basekit.place_groups(local, poses))
    poses, push = basekit.push_chain(local, poses, CHAIN, LAYOUT_GAPS, calib)
    holes = basekit.place_groups(local, poses)
    return holes, r0, resid(holes), push


def fronts(holes):
    return {g: basekit.front_dir(holes, a, b, deg) for g, (a, b, deg) in FRONT.items()}


def orig_centers(holes):
    return {g: basekit.frame_point(holes, a, b, along, right) for g, (a, b, along, right) in ORIG_CENTER.items()}


def kana_recess(holes):
    (x1, y1), (x2, y2) = holes["K1"], holes["K2"]
    th = math.atan2(y2 - y1, x2 - x1)
    c, s = math.cos(th), math.sin(th)
    return [(x1 + c * x - s * y, y1 + s * x + c * y) for x, y in shoe_outline()]


def seam(holes):
    """接缝：过爱和阿库亚两组孔中心的中点，沿平均正面方向；返回 (点, 指向阿库亚那块的法向)。"""
    f = list(fronts(holes).values())
    mx, my = sum(v[0] for v in f) / len(f), sum(v[1] for v in f) / len(f)
    n = (-my / math.hypot(mx, my), mx / math.hypot(mx, my))
    ca = [sum(holes[k][i] for k in GROUPS["Ai"]) / 2 for i in (0, 1)]
    cb = [sum(holes[k][i] for k in GROUPS["Aqua"]) / 2 for i in (0, 1)]
    return ((ca[0] + cb[0]) / 2, (ca[1] + cb[1]) / 2), n


def stage(holes):
    """爱的圆台：(圆心, 半径, 踮脚落点)。"""
    a, b, along, right = FREE_FOOT["Ai"]
    foot = basekit.frame_point(holes, a, b, along, right)
    pm = ((holes["A1"][0] + holes["A2"][0]) / 2, (holes["A1"][1] + holes["A2"][1]) / 2)
    c = ((pm[0] + foot[0]) / 2, (pm[1] + foot[1]) / 2)
    return c, math.dist(pm, foot) / 2 + STAGE_PAD, foot


def build_base(holes):
    """11mm 实心底座 + 鞋形凹槽 + 爱的圆台 + 刻字，切成两块。返回 (露比 + 爱, 阿库亚 + 加奈)。"""
    recess = kana_recess(holes)
    groove_top = BASE_T - SHOE["depth"]
    sc, sr, _ = stage(holes)
    top_stage = BASE_T + STAGE_H
    tops = {"K1": groove_top, "K2": groove_top, "A1": top_stage, "A2": top_stage}
    depths = {k: PEGS[k][1] + EXTRA_DEPTH for k in PEGS}
    centers = orig_centers(holes)
    hull = basekit.outline_points(holes, HOLE_FLAT, centers.values(), COG_R) + recess
    outline = basekit.convex_hull(hull + basekit.circle_pts(sc, sr + STAGE_LIP - MARGIN, 96))
    body = basekit.build_base(holes, HOLE_FLAT, depths, outline, T=BASE_T, margin=MARGIN,
                              recesses=[(recess, SHOE["depth"])], hole_tops=tops,
                              platforms=[(basekit.circle_pts(sc, sr, 96), STAGE_H)])
    circles = [(holes[k], HOLE_FLAT[k] / math.sqrt(3) + CHAMFER + 1.5) for k in holes]
    rx = sum(x for x, _ in recess) / len(recess)
    ry = sum(y for _, y in recess) / len(recess)
    circles.append(((rx, ry), max(math.dist((rx, ry), p) for p in recess) + 1.5))
    sp, n = seam(holes)
    t = (-n[1], n[0])
    seam_band = [(((sp[0] - 300 * t[0], sp[1] - 300 * t[1]), (sp[0] + 300 * t[0], sp[1] + 300 * t[1])),
                  DOVETAIL["depth"] + 3)]
    ang = basekit.right_angle(list(fronts(holes).values()))
    others = [(LABELS[g], centers[g]) for g in LABELS if g != "Ai"]   # 爱的名字刻在台面上，其余的躲开圆台
    body, _ = basekit.add_labels(body, others, ang, outline, circles + [(sc, sr + 1.5)], seam_band, top=BASE_T)
    body, _ = basekit.add_labels(body, [(LABELS["Ai"], centers["Ai"])], ang,
                                 basekit.circle_pts(sc, sr - 3, 96), circles, [], top=top_stage)
    # 榫头位置按不带圆台的轮廓定（试摆时和先打的右块对得上）
    lo, hi = basekit.seam_span(basekit.convex_hull(hull), sp, n, MARGIN)
    region = basekit.dovetail_region(sp, n, (lo + hi) / 2, **DOVETAIL)
    return basekit.split_dovetail(body, region, BASE_T, socket=SOCKET, tab=TAB)


def preview(holes, pieces):
    """images/preview.svg：俯视图（正面朝下，两块拼起来）+ 立体图。"""
    import base_preview
    import render
    col = {"Ruby": "#d81b60", "Ai": "#8e24aa", "Aqua": "#1e5bb8", "Kana": "#c62828"}
    name = {"Ruby": "露比", "Ai": "爱", "Aqua": "阿库亚", "Kana": "加奈"}
    f = list(fronts(holes).values())
    deg = -(math.degrees(math.atan2(sum(v[1] for v in f), sum(v[0] for v in f))) + 90)
    rot = lambda p: basekit.rot(p, deg)  # noqa: E731
    solid = [b.rotate((0, 0, 0), (0, 0, 1), deg) for b in pieces]
    H = {k: rot(p) for k, p in holes.items()}
    C = {g: rot(c) for g, c in orig_centers(holes).items()}
    F = {g: rot(v) for g, v in fronts(holes).items()}
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
    for c in C.values():
        top.append(f'<circle cx="{X(c[0]):.1f}" cy="{Y(c[1]):.1f}" r="{COG_R * S:.1f}" fill="none" stroke="#999" '
                   f'stroke-width="1.5" stroke-dasharray="5 5"/>')
    for g, hs in GROUPS.items():
        cx, cy = sum(H[k][0] for k in hs) / len(hs), sum(H[k][1] for k in hs) / len(hs)
        d = F[g]
        top.append(f'<defs><marker id="a{g}" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">'
                   f'<path d="M0,0 L8,4 L0,8 z" fill="{col[g]}"/></marker></defs>')
        top.append(f'<line x1="{X(cx):.1f}" y1="{Y(cy):.1f}" x2="{X(cx + 16 * d[0]):.1f}" y2="{Y(cy + 16 * d[1]):.1f}" '
                   f'stroke="{col[g]}" stroke-width="4" marker-end="url(#a{g})"/>')
        for k in hs:
            x, y = H[k]
            r = HOLE_FLAT[k] / math.sqrt(3) * S
            pts = " ".join(f"{X(x) + r * math.cos(math.radians(60 * i)):.1f},{Y(y) - r * math.sin(math.radians(60 * i)):.1f}"
                           for i in range(6))
            top.append(f'<polygon points="{pts}" fill="{col[g]}"/>')
        top.append(f'<text x="{X(cx):.1f}" y="{Y(cy) - 34:.1f}" text-anchor="middle" font-size="24" font-weight="700" '
                   f'fill="{col[g]}" stroke="white" stroke-width="5" paint-order="stroke">{name[g]}</text>')
    sizes = [f"{w:.0f} × {h:.0f}" for _, _, w, h in (basekit.fit_on_bed(b) for b in pieces)]
    top.append(f'<text x="{W / 2:.0f}" y="{Hh - 14:.0f}" text-anchor="middle" font-size="20" fill="#555">'
               f'↓ 正面　两块 {sizes[0]}、{sizes[1]} mm　箭头 = 朝向　虚线圆 = 原厂底座中心</text>')
    img, _ = render.render([(solid[0].val(), (205, 150, 185)), (solid[1].val(), (140, 165, 210))],
                           width=900, az=0, el=50, pad=20)
    h, w = img.shape[:2]
    col_w = 640
    sc = min(1.0, (Hh - 40) / h, col_w / w)
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W + 30 + col_w:.0f} {Hh:.0f}" {base_preview.FONT}>',
           '<rect width="100%" height="100%" fill="#fafaf8"/>', *top,
           f'<image href="data:image/png;base64,{base_preview.png_b64(img)}" x="{W + 30 + (col_w - w * sc) / 2:.0f}" '
           f'y="{(Hh - h * sc) / 2:.0f}" width="{w * sc:.0f}" height="{h * sc:.0f}"/>', "</svg>"]
    (HERE / "images" / "preview.svg").write_text("\n".join(svg), encoding="utf-8")


if __name__ == "__main__":
    holes, r0, r1, push = solve_layout()
    print("跨手办距离残差 <", round(max(abs(v) for v in r0.values()), 2), "mm；外推",
          {g: round(v, 2) for g, v in push.items()}, "后最短", round(min(r1.values()), 2))
    pieces = build_base(holes)
    setkit.export(HERE, {f"base_{p}": basekit.fit_on_bed(b)[0] for p, b in zip(("ruby-ai", "aqua-kana"), pieces)})
    if setkit.want_preview():
        preview(holes, pieces)
