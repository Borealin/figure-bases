"""POP UP PARADE 2B（ヨルハ二号B型）× POP UP PARADE A2（ヨルハA型二号）合体底座
（Good Smile Company，『NieR:Automata Ver1.1a』）

孔位编号（见 docs/hole-labels.svg）：
  B = 2B：B1、B2 各一只脚，圆孔，圆孔外面套着放鞋跟的梯形凹槽（深 1.2）。
  H = A2：H1、H2 六边形孔；T = H2 旁边放鞋跟的三角凹槽。

第一步：验证垫块（每只脚一个）+ 公差条（细钉，两排）
第二步：试摆底座 = 0.8mm 薄底板 + 每只脚一个桩 + 加强筋（验证位置和凹槽朝向）
第三步：正式底座 = 11mm 实心整板

坐标系：B1 为原点，B2 在 +X；从 B1 看向 B2，左手边为 +Y（俯视）。

用法：python figure_base.py  →  输出到 out/
"""
import math
from pathlib import Path

import cadquery as cq

# ---------------------------------------------------------------- 实测数据
# 手办脚底圆钉：(直径, 露出长度) mm
# B1、B2 是换电池后重测的；其余是第一次测的读数 x2（卡尺没电时读数约为真值一半，重测的 B1、B2 比值 1.95~2.04）
PEGS = {
    "B1": (3.75, 5.50), "B2": (3.30, 5.65),
    "H1": (3.94, 3.70), "H2": (3.88, 3.70),
}
# 原厂底座上两孔的近边距（x2 换算值，试摆时隔着垫块再量一次）
GAPS = {("B1", "B2"): 80.6, ("H1", "H2"): 87.6}
# 六边形孔：中心距 = 近边距 + (r1 + r2) * K；圆孔不乘
HEX_HOLES = {"H1", "H2"}
K = 1.05
# T：等腰三角形，底边（靠 H2 那条）7.42，两腰 6.6；底边离 H2 孔边 2.2（x2 换算值）
T_BASE, T_SIDE, T_GAP = 7.42, 6.60, 2.20
# 俯视时 H2→T 尖端的方向 = H2→H1 方向逆时针转 T_ANGLE 度（H2、T 底边中点、尖端在一条线上）
# 照片 IMG_4988 估 11°；试摆时 H1 到 T 尖端 79.7（垫块上圆角尖端）反算 13.3° → 取 12°
T_ANGLE = 12.0
# 2B 鞋跟凹槽（梯形，窄头 + 宽头），深 1.2，两个都一样深
# B1（IMG_4992 左槽）实测：总长 9.85、宽头 5.7、窄头 3.1、孔边→宽头边 1.2；
#   形状按 IMG_4992 俯拍：一侧直边（和窄头边垂直）、一侧斜边，宽头边斜约 7.7°，孔中心离直边 2.95
# B2（IMG_4992 右槽）照片估：总长 9.3、宽头 5.6、窄头 2.9、孔边→宽头边 2.0，近似对称梯形
#   v1 垫块试装偏松 → 窄头收窄 0.2、宽头收窄 0.1（窄头 2.7、宽头 5.5）
#   v2 垫块试装仍略松 → 再收窄头 0.1、宽头 0.05（窄头 2.6、宽头 5.45），正式底座用
HEEL_DEPTH = 1.2
# v1 垫块试装：B1 的钉孔要相对凹槽往左 0.2、往上（窄头方向）0.3（窄头朝上俯视），
# 即凹槽相对钉孔往右 0.2、往下 0.3（轮廓以钉孔为原点，所以平移的是轮廓）
HEEL_SHIFT = {"B1": (0.2, -0.3), "B2": (0.0, 0.0)}
# 试摆底座试装：B1 凹槽仍略小 → 宽头那条边往外（背离钉孔）再推 0.2，窄头不动
HEEL_WIDE_EXTEND = {"B1": 0.2, "B2": 0.0}

# ---------------------------------------------------------------- 摆放（v2 垫块试摆）
# 垫块上量的近边距；垫块上的孔全是六边形 → 都按 K 换算
LAYOUT_GAPS = {("B1", "H1"): 16.95, ("B1", "H2"): 99.5, ("B2", "H1"): 96.55, ("B2", "H2"): 132.35,
               ("B1", "B2"): 79.65, ("H1", "H2"): 87.55}
H_SIDE = +1   # 镜像：从 B1 看向 B2，H2 在左手边（方案 A，见 docs/layout-mirror-check.svg）
# 2B 鞋跟凹槽局部 +Y（窄头）相对 B1→B2 方向的角度：窄头都朝左手边（原厂底座 IMG_4992 俯拍）。
# 注：垫块上量的两个窄头角点距离 79.9，按这组角度算是 81.3，差 1.4mm；
#     垫块是圆角凹槽、B2 偏松会晃，先以原厂底座为准，用第二步试摆底座验证
HEEL_PHI = {"B1": 97.0, "B2": 96.4}
# 原厂底座中心（照片 IMG_4988 估），新底座要把它周围 COG_R 的范围包进去，保证重心在底座内
#   2B 圆底座 Ø≈99：中心在 B1→B2 方向 41.7、往右 2.8
#   A2 六边形底座 ≈166×80：中心在 H1→H2 方向 45.9、往右 4.9
ORIG_CENTER = {"2B": ("B1", "B2", 41.7, 2.8), "A2": ("H1", "H2", 45.9, 4.9)}   # (起点, 终点, 沿连线, 往右)

# ---------------------------------------------------------------- 打印参数
# 打印机：Bambu A1 mini（FDM，平台 180 x 180）
# 六边形孔对边距 = 钉径 + CLEARANCE[孔]（v1 垫块 + 公差条试装后的结果）
CLEARANCE = {
    "H1": -0.03,   # 垫块 3.94 略松，公差条 H0（同为 3.94）手感更好 → 稍微收紧
    "H2": 0.02,    # 略紧，放大 0.5%
    "B1": 0.0, "B2": 0.0,
}
HOLE_SCALE = 1.01   # 试摆底座试装后：所有钉孔再放大 1%（在 CLEARANCE 基础上）
EXTRA_DEPTH = 1.5   # 孔比钉长多挖的深度
CHAMFER = 0.4       # 孔口倒角
T_GROW = 0.5        # 三角凹槽每边放大，鞋跟不用对得很准
T_DEPTH = 4.0       # 三角凹槽深度：深了鞋跟只是悬空，浅了会把鞋跟垫高，所以宁深勿浅
HEEL_GROW = {"B1": 0.3, "B2": 0.5}   # 2B 鞋跟凹槽每边放大；B2 是照片估的，多放一点
PAD_T = 10.0        # 垫块厚度，所有垫块一样厚，保证四只鞋底在同一高度
# 2B 的钉从鞋跟凹槽底面往下算
assert PAD_T - HEEL_DEPTH - max(L for _, L in PEGS.values()) - EXTRA_DEPTH >= 1.0, "孔底太薄"
assert PAD_T - T_DEPTH >= 1.0, "三角凹槽底太薄"

BASE_T = 11.0       # 底座厚度（和仗助/露伴那套一样）
PLATE = 0.8         # 试摆底座底板厚度（0.2mm 层高的首 4 层）
POST_WALL = 2.5     # 试摆底座：桩在孔 / 凹槽外留的壁厚
RIB_W, RIB_H = 2.0, 5.0   # 试摆底座：连接各桩的加强筋宽、高（高出底板）
COG_R = 15.0        # 原厂底座中心周围要包进底座的半径
MARGIN = 10.0       # 底座外轮廓在所有孔、凹槽、COG 圆外再留的边
TOP_CHAMFER = 1.0   # 正式底座顶面外沿倒角
BED = 180.0         # A1 mini 平台
assert BASE_T - HEEL_DEPTH - max(L for _, L in PEGS.values()) - EXTRA_DEPTH >= 1.0, "底座孔底太薄"

OUT = Path(__file__).parent / "out"


def hole_r(name):
    """原厂孔的"半径"：六边形孔按 K 放大。"""
    return PEGS[name][0] / 2 * (K if name in HEX_HOLES else 1.0)


def center_dist(a, b):
    gap = GAPS.get((a, b)) or GAPS[(b, a)]
    return gap + hole_r(a) + hole_r(b)


def t_triangle():
    """以 H2 为原点、尖端朝 -X 的三角形三个顶点。"""
    xb = -(hole_r("H2") + T_GAP)                     # 底边
    h = math.sqrt(T_SIDE ** 2 - (T_BASE / 2) ** 2)   # 高
    return [(xb, T_BASE / 2), (xb, -T_BASE / 2), (xb - h, 0.0)]


def heel_b1():
    """B1 鞋跟凹槽轮廓，钉孔中心为原点，+Y 指向窄头，+X 指向斜边（IMG_4992 俯视方向）。"""
    L, wb, wt, e, slant, hx = 9.85, 5.7, 3.1, 1.2, math.radians(7.7), 2.95
    L, e = L + HEEL_WIDE_EXTEND["B1"], e + HEEL_WIDE_EXTEND["B1"]   # 宽头边外推，窄头相对钉孔不动
    pts = [(0, 0), (wb * math.cos(slant), wb * math.sin(slant)), (wt, L), (0, L)]  # 直边在 x=0
    hy = hx * math.tan(slant) + e + PEGS["B1"][0] / 2
    return [(x - hx, y - hy) for x, y in pts]


def heel_b2():
    """B2 鞋跟凹槽轮廓（对称梯形），坐标约定同 heel_b1。"""
    L, wb, wt, e = 9.3, 5.45, 2.6, 2.0
    L, e = L + HEEL_WIDE_EXTEND["B2"], e + HEEL_WIDE_EXTEND["B2"]
    y0 = -(e + PEGS["B2"][0] / 2)
    return [(-wb / 2, y0), (wb / 2, y0), (wt / 2, y0 + L), (-wt / 2, y0 + L)]


def heel(name):
    """鞋跟凹槽轮廓（已加试装微调的偏移）。"""
    dx, dy = HEEL_SHIFT[name]
    return [(x + dx, y + dy) for x, y in {"B1": heel_b1, "B2": heel_b2}[name]()]


# ---------------------------------------------------------------- 零件
def cut_hex(body, x, y, flat, depth, top, chamfer=CHAMFER):
    """在顶面 (x, y) 开对边距为 flat 的六边形盲孔，孔口倒角（chamfer=0 不倒角）。"""
    r = flat / math.sqrt(3)
    hole = (cq.Workplane("XY").workplane(offset=top - depth)
            .center(x, y).polygon(6, 2 * r).extrude(depth + 1))
    body = body.cut(hole)
    if not chamfer:
        return body
    box = cq.selectors.BoxSelector((x - r - 0.2, y - r - 0.2, top - 0.01),
                                   (x + r + 0.2, y + r + 0.2, top + 0.01))
    return body.edges(box).chamfer(chamfer)


def peg_hole(body, name, x, y, top=PAD_T, chamfer=CHAMFER):
    d, length = PEGS[name]
    return cut_hex(body, x, y, (d + CLEARANCE[name]) * HOLE_SCALE, length + EXTRA_DEPTH, top, chamfer)


def cut_t(body, top=PAD_T, at=(0.0, 0.0), angle=0.0):
    """三角凹槽：两腰和尖端放大 T_GROW，靠 H2 的底边不动（留住和 H2 孔之间的隔墙）；
    再绕原点转 angle 度、平移到 at。"""
    xb = t_triangle()[0][0]
    pocket = (cq.Workplane("XY").workplane(offset=top - T_DEPTH)
              .polyline(t_triangle()).close().offset2D(T_GROW).extrude(T_DEPTH + 1))
    keep = (cq.Workplane("XY").workplane(offset=top - T_DEPTH - 1)
            .center(xb - 25, 0).rect(50, 50).extrude(T_DEPTH + 3))
    pocket = pocket.intersect(keep).rotate((0, 0, 0), (0, 0, 1), angle).translate((*at, 0))
    return body.cut(pocket)


def engrave(body, text, x, y, size=4.5, depth=0.6, top=PAD_T):
    txt = (cq.Workplane("XY").workplane(offset=top - depth).center(x, y)
           .text(text, size, depth + 0.1, combine=False,
                 halign="center", valign="center", kind="bold"))
    return body.cut(txt)


def rounded_rect(w, h, cx=0.0, cy=0.0, r=4.0):
    return cq.Workplane("XY").center(cx, cy).rect(w, h).extrude(PAD_T).edges("|Z").fillet(r)


def cut_heel(body, name, top=PAD_T, at=(0.0, 0.0), angle=0.0):
    """2B 鞋跟凹槽 + 槽底的钉孔：轮廓绕钉孔中心转 angle 度后平移到 at。"""
    pocket = (cq.Workplane("XY").workplane(offset=top - HEEL_DEPTH)
              .polyline(heel(name)).close().offset2D(HEEL_GROW[name]).extrude(HEEL_DEPTH + 1))
    body = body.cut(pocket.rotate((0, 0, 0), (0, 0, 1), angle).translate((*at, 0)))
    # B1 的孔几乎贴着凹槽斜边（照片里也是），孔口倒角会碰到槽壁，所以槽底的孔不倒角
    return peg_hole(body, name, *at, top=top - HEEL_DEPTH, chamfer=0)


def pad_b(name, label):
    """2B 的脚：圆角方块 + 鞋跟凹槽，右边刻编号（B1、B2 靠刻字区分）。整体居中到原点。"""
    xs, ys = zip(*heel(name))
    g = HEEL_GROW[name] + 2.0                      # 凹槽外留 2mm 壁
    x0, x1, y0, y1 = min(xs) - g, max(xs) + g + 4.5, min(ys) - g, max(ys) + g   # 右边多留刻字位置
    body = rounded_rect(x1 - x0, y1 - y0, (x0 + x1) / 2, (y0 + y1) / 2, r=3.0)
    body = cut_heel(body, name)
    body = engrave(body, label, x1 - 3.2, (y0 + y1) / 2)
    return body.translate((-(x0 + x1) / 2, -(y0 + y1) / 2, 0))


def pad_h1():
    """A2 不带鞋跟凹槽的那只脚：六边形。"""
    return peg_hole(cq.Workplane("XY").polygon(6, 15).extrude(PAD_T), "H1", 0, 0)


def pad_h2t():
    """A2 带鞋跟的那只脚：H2 孔 + 三角凹槽。垫块绕钉能转，插上后会自己对准鞋跟。"""
    body = peg_hole(rounded_rect(18, 12, cx=-4.0), "H2", 0, 0)
    return cut_t(body)


def tolerance_strip(steps=(-0.1, 0.0, 0.1, 0.2, 0.3), pitch=9):
    """两排孔：上排按 H1 钉，下排按 B2 钉，每列依次加 steps 的间隙。
    刻字 = 间隙的十分位（-1 = -0.1mm，2 = +0.2mm）；左端刻 H / B 区分两排。"""
    n = len(steps)
    w = pitch * n + 12
    body = rounded_rect(w, 23)
    for i, c in enumerate(steps):
        x = (i - (n - 1) / 2) * pitch + 3.0
        for name, y in (("H1", 6.0), ("B2", -1.5)):
            d, length = PEGS[name]
            body = cut_hex(body, x, y, d + c, length + EXTRA_DEPTH, PAD_T)
        body = engrave(body, str(round(c * 10)), x, -8.0, size=4)
    body = engrave(body, "H", -w / 2 + 4, 6.0, size=4)
    return engrave(body, "B", -w / 2 + 4, -1.5, size=4)


# ---------------------------------------------------------------- 合体底座
def rot2(p, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return (c * p[0] - s * p[1], s * p[0] + c * p[1])


def pad_center_dist(a, b):
    """垫块（六边形孔）上量的近边距 → 中心距。"""
    gap = LAYOUT_GAPS.get((a, b)) or LAYOUT_GAPS[(b, a)]
    return gap + K * (PEGS[a][0] + PEGS[b][0]) / 2


def solve_layout():
    """B1 原点、B2 在 +X；H1、H2 用 4 个跨手办距离做最小二乘，H1–H2 距离固定。"""
    import numpy as np
    dB, dH = pad_center_dist("B1", "B2"), pad_center_dist("H1", "H2")
    B = {"B1": np.zeros(2), "B2": np.array([dB, 0.0])}
    cross = [k for k in LAYOUT_GAPS if {k[0][0], k[1][0]} == {"B", "H"}]

    def place(x):
        h1 = x[:2]
        return {**B, "H1": h1, "H2": h1 + dH * np.array([math.cos(x[2]), math.sin(x[2])])}

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
    """每只脚占用的 2D 点（孔、凹槽、三角槽），用来做桩和外轮廓。"""
    ang = placements(holes)

    def circle(c, r):
        return [(c[0] + r * math.cos(i * math.pi / 8), c[1] + r * math.sin(i * math.pi / 8)) for i in range(16)]

    def grown(poly, at, g):
        return [(at[0] + x + dx, at[1] + y + dy) for x, y in poly
                for dx, dy in ((g, g), (g, -g), (-g, g), (-g, -g))]

    pts = {k: grown([rot2(q, ang[k]) for q in heel(k)], holes[k], HEEL_GROW[k]) for k in ("B1", "B2")}
    pts["H1"] = circle(holes["H1"], PEGS["H1"][0] / math.sqrt(3) + CHAMFER)
    pts["H2"] = (circle(holes["H2"], PEGS["H2"][0] / math.sqrt(3) + CHAMFER)
                 + grown([rot2(q, ang["T"]) for q in t_triangle()], holes["H2"], T_GROW))
    return pts


def orig_centers(holes):
    out = {}
    for name, (a, b, along, right) in ORIG_CENTER.items():
        pa, pb = holes[a], holes[b]
        L = math.dist(pa, pb)
        u = ((pb[0] - pa[0]) / L, (pb[1] - pa[1]) / L)
        out[name] = (pa[0] + along * u[0] + right * u[1], pa[1] + along * u[1] - right * u[0])
    return out


def convex_hull(pts):
    pts = sorted(set(pts))

    def half(seq):
        h = []
        for p in seq:
            while len(h) >= 2 and ((h[-1][0] - h[-2][0]) * (p[1] - h[-2][1])
                                   - (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0])) <= 0:
                h.pop()
            h.append(p)
        return h
    return half(pts)[:-1] + half(list(reversed(pts)))[:-1]


def outline_points(holes):
    pts = [p for v in foot_points(holes).values() for p in v]
    for c in orig_centers(holes).values():
        pts += [(c[0] + COG_R * math.cos(i * math.pi / 12), c[1] + COG_R * math.sin(i * math.pi / 12))
                for i in range(24)]
    return convex_hull(pts)


def cut_features(body, holes, top):
    ang = placements(holes)
    for k in ("B1", "B2"):
        body = cut_heel(body, k, top=top, at=holes[k], angle=ang[k])
    for k in ("H1", "H2"):
        body = peg_hole(body, k, *holes[k], top=top)
    return cut_t(body, top=top, at=holes["H2"], angle=ang["T"])


def build_base(holes, thin=False):
    """thin=True：试摆底座（薄底板 + 桩 + 加强筋）；否则正式底座（BASE_T 实心）。"""
    outline = cq.Workplane("XY").polyline(outline_points(holes)).close().offset2D(MARGIN)
    if not thin:
        body = outline.extrude(BASE_T)
        if TOP_CHAMFER:
            body = body.faces(">Z").chamfer(TOP_CHAMFER)
        return cut_features(body, holes, BASE_T)
    body = outline.extrude(PLATE)
    for pts in foot_points(holes).values():
        post = (cq.Workplane("XY").polyline(convex_hull(pts)).close().offset2D(POST_WALL)
                .extrude(BASE_T))
        body = body.union(post)
    for a, b in (("B2", "B1"), ("B1", "H1"), ("H1", "H2")):
        (x0, y0), (x1, y1) = holes[a], holes[b]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        rib = (cq.Workplane("XY").workplane(offset=PLATE - 0.01).center(cx, cy)
               .rect(math.dist(holes[a], holes[b]), RIB_W).extrude(RIB_H + 0.01)
               .rotate((cx, cy, 0), (cx, cy, 1), math.degrees(math.atan2(y1 - y0, x1 - x0))))
        body = body.union(rib)
    return cut_features(body, holes, BASE_T)


# ---------------------------------------------------------------- 名字（防止几套搞混）
import sys as _sys  # noqa: E402
_sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import basekit  # noqa: E402

# 手办朝向 = 组内两孔连线方向逆时针转的角度（IMG_4988 俯拍，照片下方是正面）
FRONT = {"2B": ("B1", "B2", 32.1), "A2": ("H1", "H2", -76.8)}
LABELS = {"2B": "2B", "A2": "A2"}


def add_labels(body, holes, thin=False):
    keep = POST_WALL + 1.5 if thin else 1.5            # 试摆底座要躲开桩
    circles = [(p, keep) for pts in foot_points(holes).values() for p in pts]
    segments = ([((holes[a], holes[b]), RIB_W / 2 + 1.5) for a, b in (("B2", "B1"), ("B1", "H1"), ("H1", "H2"))]
                if thin else [])
    fronts = [basekit.front_dir(holes, a, b, deg) for a, b, deg in FRONT.values()]
    centers = orig_centers(holes)
    body, _ = basekit.add_labels(body, [(LABELS[g], centers[g]) for g in LABELS], basekit.right_angle(fronts),
                                 outline_points(holes), circles, segments,
                                 top=PLATE if thin else BASE_T, raised=thin)
    return body


def fit_on_bed(body):
    """放得下就不转；放不下找包围盒最小的角度。移到原点。"""
    bb = body.val().BoundingBox()
    if max(bb.xlen, bb.ylen) <= BED - 4:
        return body.translate((-bb.center.x, -bb.center.y, 0)), 0, bb.xlen, bb.ylen
    best = None
    for deg in range(0, 180):
        b = body.rotate((0, 0, 0), (0, 0, 1), deg).val().BoundingBox()
        if best is None or b.xlen * b.ylen < best[0]:
            best = (b.xlen * b.ylen, deg, b.xlen, b.ylen)
    _, deg, w, h = best
    rotated = body.rotate((0, 0, 0), (0, 0, 1), deg)
    c = rotated.val().BoundingBox().center
    return rotated.translate((-c.x, -c.y, 0)), deg, w, h


# 验证垫块在打印平台上的摆放位置
TRIAL_LAYOUT = {"B1": (-32, 15), "B2": (-15, 15), "H1": (2, 15), "H2T": (25, 15), "tol": (0, -11)}


def build_trial(with_tol=False):
    parts = {"B1": pad_b("B1", "1"), "B2": pad_b("B2", "2"), "H1": pad_h1(), "H2T": pad_h2t()}
    if with_tol:   # v1 带公差条；试装完间隙已定，v2 起不再打
        parts["tol"] = tolerance_strip()
    moved = [p.translate((*TRIAL_LAYOUT[k], 0)).val() for k, p in parts.items()]
    return parts, cq.Workplane().add(cq.Compound.makeCompound(moved))


if __name__ == "__main__":
    import sys
    OUT.mkdir(exist_ok=True)

    def save(wp, name, step=False):
        cq.exporters.export(wp, str(OUT / f"{name}.stl"), tolerance=0.01, angularTolerance=0.1)
        if step:
            cq.exporters.export(wp, str(OUT / f"{name}.step"))
        print("已输出", OUT / f"{name}.stl")

    if "--trial" in sys.argv:   # 重新生成验证垫块（v2 已打印，平时不覆盖）
        save(build_trial()[1], "trial_v2")
        sys.exit()

    holes, res = solve_layout()
    print("跨手办距离拟合残差 (mm):", [round(float(r), 3) for r in res])
    for k, (x, y) in holes.items():
        print(f"  {k}: ({x:7.2f}, {y:7.2f})")
    for name, thin in (("test_base_thin", True), ("base", False)):
        body, deg, w, h = fit_on_bed(add_labels(build_base(holes, thin=thin), holes, thin=thin))
        ok = "放得下" if max(w, h) <= BED - 4 else "放不下！"
        print(f"{name}：{w:.1f} x {h:.1f} mm，旋转 {deg} 度，A1 mini {ok}")
        save(body, name, step=not thin)
