"""POP UP PARADE 2B（ヨルハ二号B型）× A2（ヨルハA型二号）合体底座（『NieR:Automata Ver1.1a』，L 形站位）

孔位（images/holes.svg）：
  B = 2B：B1、B2 各一只脚，钉孔外面套着放鞋跟的梯形凹槽（深 1.2）
  H = A2：H1、H2 两个六边形孔；T = H2 旁边放鞋跟的三角凹槽
坐标：B1 原点，B2 在 +X；从 B1 看向 B2，左手边为 +Y（俯视）。

    python base.py [--slice] [--preview]
"""
import math
import sys
from pathlib import Path

import cadquery as cq
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import basekit  # noqa: E402
import setkit  # noqa: E402

# ---------------------------------------------------------------- 实测
# (钉径, 露出长度)；H1、H2 是卡尺没电时的读数 x2（读数约为真值一半，换电池重量的 B1、B2 比值 1.95～2.04）
PEGS = {"B1": (3.75, 5.50), "B2": (3.30, 5.65), "H1": (3.94, 3.70), "H2": (3.88, 3.70)}
HEX_HOLES = {"H1", "H2"}   # 原厂六边形孔：中心距 = 近边距 + (r1 + r2) * K；圆孔不乘
K = 1.05
# T：等腰三角形，底边（靠 H2）7.42、两腰 6.6，底边离 H2 孔边 2.2；尖端 = H2→H1 方向逆时针转 12°
T_BASE, T_SIDE, T_GAP, T_ANGLE = 7.42, 6.60, 2.20, 12.0
HEEL_DEPTH = 1.2   # 2B 鞋跟凹槽深度（照原厂，深了浅了都会改变手办姿态）

# ---------------------------------------------------------------- 孔径 / 凹槽（试出来的）
# 孔对边距 = (钉径 + CLEARANCE) x 1.01：H1 略松收 0.03、H2 略紧放 0.02；试摆底座后所有孔再放大 1%
CLEARANCE = {"H1": -0.03, "H2": 0.02, "B1": 0.0, "B2": 0.0}
HOLE_SCALE = 1.01
EXTRA_DEPTH = 1.5   # 孔比钉长多挖的深度
CHAMFER = 0.4       # 孔口倒角
T_GROW, T_DEPTH = 0.5, 4.0           # 三角凹槽两腰和尖端放大 0.5；宁深勿浅
HEEL_GROW = {"B1": 0.3, "B2": 0.5}   # 鞋跟凹槽每边放大（B2 是照片估的，多放一点）
# B1 凹槽（实测）：钉孔相对凹槽往左 0.2、往窄头 0.3（= 凹槽往右 0.2、往下 0.3）；宽头边再往外推 0.2
HEEL_SHIFT = {"B1": (0.2, -0.3), "B2": (0.0, 0.0)}
HEEL_WIDE_EXTEND = {"B1": 0.2, "B2": 0.0}
# B2 凹槽（照片估）：两次试装偏松，窄头 2.9 → 2.6、宽头 5.6 → 5.45

# ---------------------------------------------------------------- 摆位
# 垫块上量的近边距（垫块上都是六边形孔，按 K 换算）
LAYOUT_GAPS = {("B1", "H1"): 16.95, ("B1", "H2"): 99.5, ("B2", "H1"): 96.55, ("B2", "H2"): 132.35,
               ("B1", "B2"): 79.65, ("H1", "H2"): 87.55}
H_SIDE = +1   # 镜像：从 B1 看向 B2，H2 在左手边（对照实物选的）
HEEL_PHI = {"B1": 97.0, "B2": 96.4}   # 鞋跟凹槽窄头相对 B1→B2 的角度（原厂底座 IMG_4992 俯拍）
# 原厂底座中心（IMG_4988 估）：(起点, 终点, 沿连线, 往右)；2B 圆底座 Ø≈99，A2 六边形底座 ≈166×80
ORIG_CENTER = {"2B": ("B1", "B2", 41.7, 2.8), "A2": ("H1", "H2", 45.9, 4.9)}
FRONT = {"2B": ("B1", "B2", 32.1), "A2": ("H1", "H2", -76.8)}   # 朝向 = 组内两孔连线逆时针转的角度
LABELS = {"2B": "2B", "A2": "A2"}

BASE_T = 11.0       # 底座厚度
COG_R = 15.0        # 原厂底座中心周围要包进底座的半径
MARGIN = 10.0       # 外轮廓在孔、凹槽、COG 圆外再留的边
assert BASE_T - HEEL_DEPTH - max(L for _, L in PEGS.values()) - EXTRA_DEPTH >= 1.0, "孔底太薄"


def hole_flat(name):
    return (PEGS[name][0] + CLEARANCE[name]) * HOLE_SCALE


def hole_r(name):
    """原厂孔的"半径"：六边形孔按 K 放大。"""
    return PEGS[name][0] / 2 * (K if name in HEX_HOLES else 1.0)


def t_triangle():
    """以 H2 为原点、尖端朝 -X 的三角形。"""
    xb = -(hole_r("H2") + T_GAP)
    h = math.sqrt(T_SIDE ** 2 - (T_BASE / 2) ** 2)
    return [(xb, T_BASE / 2), (xb, -T_BASE / 2), (xb - h, 0.0)]


def heel(name):
    """鞋跟凹槽轮廓（钉孔中心为原点，+Y 指向窄头，已加试装微调）。"""
    if name == "B1":   # 一侧直边、一侧斜边，宽头边斜 7.7°，孔中心离直边 2.95
        L, wb, wt, e, slant, hx = 9.85, 5.7, 3.1, 1.2, math.radians(7.7), 2.95
        L, e = L + HEEL_WIDE_EXTEND["B1"], e + HEEL_WIDE_EXTEND["B1"]
        pts = [(0, 0), (wb * math.cos(slant), wb * math.sin(slant)), (wt, L), (0, L)]
        hy = hx * math.tan(slant) + e + PEGS["B1"][0] / 2
        pts = [(x - hx, y - hy) for x, y in pts]
    else:              # B2：对称梯形
        L, wb, wt, e = 9.3, 5.45, 2.6, 2.0
        y0 = -(e + PEGS["B2"][0] / 2)
        pts = [(-wb / 2, y0), (wb / 2, y0), (wt / 2, y0 + L), (-wt / 2, y0 + L)]
    dx, dy = HEEL_SHIFT[name]
    return [(x + dx, y + dy) for x, y in pts]


def pad_center_dist(a, b):
    gap = LAYOUT_GAPS.get((a, b)) or LAYOUT_GAPS[(b, a)]
    return gap + K * (PEGS[a][0] + PEGS[b][0]) / 2


def solve_layout():
    """B1 原点、B2 在 +X；H1、H2 用 4 个跨手办距离最小二乘，H1–H2 距离固定。"""
    dB, dH = pad_center_dist("B1", "B2"), pad_center_dist("H1", "H2")
    B = {"B1": np.zeros(2), "B2": np.array([dB, 0.0])}
    cross = [k for k in LAYOUT_GAPS if {k[0][0], k[1][0]} == {"B", "H"}]

    def place(x):
        return {**B, "H1": x[:2], "H2": x[:2] + dH * np.array([math.cos(x[2]), math.sin(x[2])])}

    def resid(x):
        P = place(x)
        return np.array([np.linalg.norm(P[a] - P[b]) - pad_center_dist(a, b) for a, b in cross])

    x = np.array([-16.0, 12.0 * H_SIDE, math.radians(83.0 * H_SIDE)])
    for _ in range(100):
        r = resid(x)
        jac = np.column_stack([(resid(x + e) - r) / 1e-7 for e in np.eye(3) * 1e-7])
        step = np.linalg.lstsq(jac, -r, rcond=None)[0]
        x = x + step
        if abs(step).max() < 1e-12:
            break
    return {k: tuple(float(v) for v in p) for k, p in place(x).items()}, resid(x)


def placements(holes):
    """凹槽旋转角：鞋跟凹槽转 (phi - 90)；三角凹槽让尖端指向 H2→H1 再逆时针 T_ANGLE。"""
    h1, h2 = holes["H1"], holes["H2"]
    t_dir = math.degrees(math.atan2(h1[1] - h2[1], h1[0] - h2[0])) + T_ANGLE
    return {"B1": HEEL_PHI["B1"] - 90, "B2": HEEL_PHI["B2"] - 90, "T": t_dir - 180}


def foot_points(holes):
    """每只脚占用的 2D 点（孔、凹槽、三角槽），用来定外轮廓和躲开刻字。"""
    ang = placements(holes)

    def circle(c, r):
        return [(c[0] + r * math.cos(i * math.pi / 8), c[1] + r * math.sin(i * math.pi / 8)) for i in range(16)]

    def grown(poly, at, g):
        return [(at[0] + x + dx, at[1] + y + dy) for x, y in poly for dx, dy in ((g, g), (g, -g), (-g, g), (-g, -g))]

    pts = {k: grown([basekit.rot(q, ang[k]) for q in heel(k)], holes[k], HEEL_GROW[k]) for k in ("B1", "B2")}
    pts["H1"] = circle(holes["H1"], PEGS["H1"][0] / math.sqrt(3) + CHAMFER)
    pts["H2"] = (circle(holes["H2"], PEGS["H2"][0] / math.sqrt(3) + CHAMFER)
                 + grown([basekit.rot(q, ang["T"]) for q in t_triangle()], holes["H2"], T_GROW))
    return pts


def orig_centers(holes):
    return {g: basekit.frame_point(holes, a, b, along, right) for g, (a, b, along, right) in ORIG_CENTER.items()}


def outline_points(holes):
    pts = [p for v in foot_points(holes).values() for p in v]
    for c in orig_centers(holes).values():
        pts += [(c[0] + COG_R * math.cos(i * math.pi / 12), c[1] + COG_R * math.sin(i * math.pi / 12)) for i in range(24)]
    return basekit.convex_hull(pts)


def cut_features(body, holes, top):
    ang = placements(holes)
    for k in ("B1", "B2"):   # 鞋跟凹槽 + 槽底的钉孔（B1 的孔几乎贴着凹槽斜边，槽底的孔不倒角）
        pocket = (cq.Workplane("XY").workplane(offset=top - HEEL_DEPTH)
                  .polyline(heel(k)).close().offset2D(HEEL_GROW[k]).extrude(HEEL_DEPTH + 1))
        body = body.cut(pocket.rotate((0, 0, 0), (0, 0, 1), ang[k]).translate((*holes[k], 0)))
        body = basekit.cut_hex(body, *holes[k], hole_flat(k), PEGS[k][1] + EXTRA_DEPTH, top - HEEL_DEPTH, chamfer=0)
    for k in ("H1", "H2"):
        body = basekit.cut_hex(body, *holes[k], hole_flat(k), PEGS[k][1] + EXTRA_DEPTH, top, CHAMFER)
    # 三角凹槽：两腰和尖端放大，靠 H2 的底边不动（留住和 H2 孔之间的隔墙）
    xb = t_triangle()[0][0]
    pocket = (cq.Workplane("XY").workplane(offset=top - T_DEPTH)
              .polyline(t_triangle()).close().offset2D(T_GROW).extrude(T_DEPTH + 1))
    keep = cq.Workplane("XY").workplane(offset=top - T_DEPTH - 1).center(xb - 25, 0).rect(50, 50).extrude(T_DEPTH + 3)
    pocket = pocket.intersect(keep).rotate((0, 0, 0), (0, 0, 1), ang["T"]).translate((*holes["H2"], 0))
    return body.cut(pocket)


def build_base(holes):
    """11mm 实心底座：孔 + 2B 鞋跟凹槽 + A2 三角凹槽 + 刻字。"""
    outline = outline_points(holes)
    body = cq.Workplane("XY").polyline(outline).close().offset2D(MARGIN).extrude(BASE_T).faces(">Z").chamfer(1.0)
    body = cut_features(body, holes, BASE_T)
    circles = [(p, 1.5) for pts in foot_points(holes).values() for p in pts]
    fronts = [basekit.front_dir(holes, a, b, deg) for a, b, deg in FRONT.values()]
    centers = orig_centers(holes)
    body, _ = basekit.add_labels(body, [(LABELS[g], centers[g]) for g in LABELS], basekit.right_angle(fronts),
                                 outline, circles, top=BASE_T)
    return body


def preview(holes, body):
    import base_preview
    groups = {"2B": ("#444444", ["B1", "B2"]), "A2": ("#8a6d3b", ["H1", "H2"])}
    centers = orig_centers(holes)
    cs = {g: (*c, COG_R) for g, c in centers.items()}
    fr = {g: (centers[g], basekit.front_dir(holes, a, b, deg)) for g, (a, b, deg) in FRONT.items()}
    flats = {k: hole_flat(k) for k in PEGS}
    base_preview.base_svg(HERE / "images" / "preview.svg", body, holes, flats, groups, cs, fr, T=BASE_T)


if __name__ == "__main__":
    holes, res = solve_layout()
    print("跨手办距离残差:", [round(float(r), 2) for r in res])
    body = build_base(holes)
    setkit.export(HERE, {"base": basekit.fit_on_bed(body)[0]})
    if setkit.want_preview():
        preview(holes, body)
