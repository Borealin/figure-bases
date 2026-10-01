"""POP UP PARADE 東方仗助 × POP UP PARADE 岸辺露伴 合体底座
（Good Smile Company，『ジョジョの奇妙な冒険 ダイヤモンドは砕けない』）

孔位编号：J = 仗助（J1+J2 前脚双钉，J3 后脚单钉），R = 露伴（R1 前脚单钉，R2+R3 后脚双钉）
坐标：J1 为原点，两个手办都面朝 +Y。

第一步：验证垫块 + 公差条
  - 4 个垫块，每只脚一个：J1+J2、J3、R1、R2+R3
  - 公差条：同一根钉，孔依次放大，找出合适的松紧
第二步：试摆底座 = 0.8mm 薄底板 + 每只脚一个凸起的桩 + 加强筋
第三步：正式底座 = 11mm 实心整板，孔直接开在板上

用法：python figure_base.py  →  输出到 out/
"""
import math
from pathlib import Path

import cadquery as cq

# ---------------------------------------------------------------- 实测数据
# 手办脚底圆桩：(直径, 露出长度) mm
PEGS = {
    "J1": (4.52, 7.40), "J2": (3.70, 7.30), "J3": (4.32, 7.70),
    "R1": (4.35, 6.93), "R2": (4.27, 6.80), "R3": (4.30, 6.60),
}
# 原厂底座上两个六边形孔的近边距；中心距 = 近边距 + (r1 + r2) * K
GAPS = {
    ("J1", "J2"): 9.80, ("J1", "J3"): 87.82, ("J2", "J3"): 99.00,
    ("R1", "R2"): 78.00, ("R1", "R3"): 79.54, ("R2", "R3"): 11.80,
}
K = 1.05
# 试摆垫块实测的跨手办近边距（照片 IMG_4945），换算方法同上
CROSS_GAPS = {("J1", "R1"): 43.7, ("J2", "R1"): 54.0, ("J1", "R2"): 65.4, ("J3", "R3"): 116.4}

# ---------------------------------------------------------------- 打印参数
# 打印机：Bambu A1 mini（FDM，平台 180 x 180）
CLEARANCE = 0.0     # 六边形孔对边距 = 桩径 + CLEARANCE；公差条实测：对边距 = 桩径刚好
EXTRA_DEPTH = 1.5   # 孔比桩长多挖的深度
CHAMFER = 0.4       # 孔口倒角，方便对准
T = 11.0            # 垫片和底座统一厚度，保证四只鞋底在同一高度
assert T - max(L for _, L in PEGS.values()) - EXTRA_DEPTH >= 1.0, "孔底太薄"

OUT = Path(__file__).parent / "out"


def center_dist(a, b):
    gaps = {**GAPS, **CROSS_GAPS}
    gap = gaps.get((a, b)) or gaps[(b, a)]
    return gap + K * (PEGS[a][0] + PEGS[b][0]) / 2


def triangle(a, b, c):
    """a 在原点、b 在 +X 轴；俯视时 c 在 a→b 的右侧（照片 IMG_4941 里两组都是这样）。"""
    ab, ac, bc = center_dist(a, b), center_dist(a, c), center_dist(b, c)
    x = (ac**2 - bc**2 + ab**2) / (2 * ab)
    return {a: (0.0, 0.0), b: (ab, 0.0), c: (x, -math.sqrt(ac**2 - x**2))}


# 每个手办自己的孔位坐标（第二步摆放时整体平移旋转）
J = triangle("J1", "J2", "J3")
R = triangle("R1", "R2", "R3")


# ---------------------------------------------------------------- 零件
def cut_hex(body, x, y, flat, depth, top=None):
    """在顶面 (x, y) 开对边距为 flat 的六边形盲孔，孔口倒角。"""
    top = T if top is None else top
    r = flat / math.sqrt(3)  # 外接圆半径
    hole = (cq.Workplane("XY").workplane(offset=top - depth)
            .center(x, y).polygon(6, 2 * r).extrude(depth + 1))
    body = body.cut(hole)
    box = cq.selectors.BoxSelector((x - r - 0.2, y - r - 0.2, top - 0.01),
                                   (x + r + 0.2, y + r + 0.2, top + 0.01))
    return body.edges(box).chamfer(CHAMFER)


def peg_hole(body, name, x, y):
    d, length = PEGS[name]
    return cut_hex(body, x, y, d + CLEARANCE, length + EXTRA_DEPTH)


def engrave(body, text, x, y, size=4.5, depth=0.6):
    txt = (cq.Workplane("XY").workplane(offset=T - depth).center(x, y)
           .text(text, size, depth + 0.1, combine=False,
                 halign="center", valign="center", kind="bold"))
    return body.cut(txt)


def pad_pair(a, b, s, r=5.2):
    """紧凑跑道形：a 在 -X，b 在 +X。给挨着另一个手办的那只脚用。"""
    body = cq.Workplane("XY").slot2D(s + 2 * r, 2 * r).extrude(T)
    body = peg_hole(body, a, -s / 2, 0)
    return peg_hole(body, b, s / 2, 0)


def pad_single_small(name, r=5.2):
    """紧凑圆形：给挨着另一个手办的那只脚用。"""
    return peg_hole(cq.Workplane("XY").circle(r).extrude(T), name, 0, 0)


def pad_single_big(name, size=22):
    """大六边形 + 刻字：远离另一个手办的那只脚，面积大更稳。"""
    body = cq.Workplane("XY").polygon(6, size).extrude(T)
    body = peg_hole(body, name, 0, 2.5)
    return engrave(body, name, 0, -4.5, size=4)


def pad_pair_big(a, b, s, w=30, h=19):
    """大圆角矩形 + 刻字。"""
    body = (cq.Workplane("XY").rect(w, h).extrude(T)
            .edges("|Z").fillet(4))
    body = peg_hole(body, a, -s / 2, 2.5)
    body = peg_hole(body, b, s / 2, 2.5)
    body = engrave(body, a, -s / 2, -4.5, size=4)
    return engrave(body, b, s / 2, -4.5, size=4)


def tolerance_strip(name="J3", steps=(0.0, 0.1, 0.2, 0.3, 0.4), pitch=8):
    """同一根桩的孔依次加 steps 的间隙，刻字 = 间隙的十分位（2 表示 +0.2，-1 表示 -0.1）。"""
    d, length = PEGS[name]
    n = len(steps)
    body = (cq.Workplane("XY").rect(pitch * n + 4, 14).extrude(T)
            .edges("|Z").fillet(3))
    for i, c in enumerate(steps):
        x = (i - (n - 1) / 2) * pitch
        body = cut_hex(body, x, 2.5, d + c, length + EXTRA_DEPTH)
        body = engrave(body, str(round(c * 10)), x, -3.8, size=4)
    return body


# 验证件在打印平台上的摆放位置
TRIAL_LAYOUT = {"J1J2": (-35, 25), "R1": (-12, 25), "J3": (10, 25),
                "R2R3": (-30, 0), "tol": (12, 0)}


def build_trial(with_tol=True):
    s_j = center_dist("J1", "J2")
    s_r = center_dist("R2", "R3")
    parts = {
        "J1J2": pad_pair("J1", "J2", s_j),
        "R1": pad_single_small("R1"),
        "J3": pad_single_big("J3"),
        "R2R3": pad_pair_big("R2", "R3", s_r),
    }
    if with_tol:
        parts["tol"] = tolerance_strip()
    moved = [p.translate((*TRIAL_LAYOUT[k], 0)).val() for k, p in parts.items()]
    return parts, cq.Workplane().add(cq.Compound.makeCompound(moved))


# ---------------------------------------------------------------- 第二步：合体底座
PLATE = 0.8         # 底板厚度；0.8 = 0.2mm 层高的首 4 层
RIB_W = 2.0         # 加强筋宽度：每个桩沿前后方向一道，抵抗手办往后倒
RIB_H = 5.0         # 加强筋高出底板的高度；0 = 不要加强筋
POST_R = 6.5        # 桩的半径（孔外围凸台）
POST_FILLET = 1.5   # 桩根部圆角，加强和底板的连接
MARGIN = 12.0       # 底板边缘离孔中心的最小距离
BACK = 10.0         # 底板往手办身后（-Y）多伸出的距离，防止后倒（第二步是 20，实测可缩短）
R_NUDGE = (0.0, -3.0)   # 试摆后微调：露伴整体往后（-Y）挪 3mm
TOP_CHAMFER = 1.0   # 正式底座顶面外沿倒角
BED = 180.0         # A1 mini 平台


def solve_layout():
    """露伴那组孔相对仗助坐标系的位置：用 4 个跨手办中心距做最小二乘（平移 + 旋转）。
    初值来自照片 IMG_4945（俯视，两个手办都朝 +Y）。"""
    import numpy as np
    Jp = {k: np.array(v) for k, v in J.items()}
    Rp = {k: np.array(v) for k, v in R.items()}
    target = {k: center_dist(*k) for k in CROSS_GAPS}

    def place(x):
        c, s = math.cos(x[2]), math.sin(x[2])
        return {k: np.array([[c, -s], [s, c]]) @ v + x[:2] for k, v in Rp.items()}

    def resid(x):
        P = place(x)
        return np.array([np.linalg.norm(Jp[a] - P[b]) - d for (a, b), d in target.items()])

    x = np.array([-28.8, -39.9, math.radians(-3.0)])
    for _ in range(50):
        r = resid(x)
        jac = np.column_stack([(resid(x + e) - r) / 1e-6 for e in np.eye(3) * 1e-6])
        step = np.linalg.lstsq(jac, -r, rcond=None)[0]
        x = x + step
        if abs(step).max() < 1e-10:
            break
    nudged = {k: (v[0] + R_NUDGE[0], v[1] + R_NUDGE[1]) for k, v in place(x).items()}
    holes = {**{k: tuple(v) for k, v in Jp.items()}, **nudged}
    return holes, resid(x)


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
    lower, upper = half(pts), half(reversed(pts))
    return lower[:-1] + upper[:-1]


def seg_dist(p, a, b):
    """点 p 到线段 ab 的距离。"""
    ab = (b[0] - a[0], b[1] - a[1])
    L2 = ab[0] ** 2 + ab[1] ** 2
    t = 0 if L2 == 0 else max(0, min(1, ((p[0] - a[0]) * ab[0] + (p[1] - a[1]) * ab[1]) / L2))
    return math.dist(p, (a[0] + t * ab[0], a[1] + t * ab[1]))


def post(p1, p2=None):
    """桩：单孔是圆柱，双孔是沿两孔连线的跑道形。"""
    wp = cq.Workplane("XY").workplane(offset=PLATE - 0.01)
    if p2 is None:
        return wp.center(*p1).circle(POST_R).extrude(T - PLATE + 0.01)
    ang = math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))
    return (wp.center((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
            .slot2D(math.dist(p1, p2) + 2 * POST_R, 2 * POST_R, ang).extrude(T - PLATE + 0.01))


def build_base(holes):
    pts = [(x, y) for x, y in holes.values()] + [(x, y - BACK) for x, y in holes.values()]
    outline = convex_hull(pts)
    body = cq.Workplane("XY").polyline(outline).close().offset2D(MARGIN).extrude(PLATE)
    groups = [("J1", "J2"), ("J3",), ("R1",), ("R2", "R3")]
    for g in groups:
        body = body.union(post(*[holes[k] for k in g]))
    if POST_FILLET:
        def near_post(e):
            c = e.Center()
            return (abs(c.z - PLATE) < 0.02 and e.BoundingBox().zlen < 0.01 and
                    min(seg_dist((c.x, c.y), holes[g[0]], holes[g[-1]]) for g in groups) < POST_R + 1)
        try:
            body = body.newObject([e for e in body.edges().vals() if near_post(e)]).fillet(POST_FILLET)
        except Exception as ex:  # 圆角失败不影响使用
            print("桩根圆角跳过：", ex)
    if RIB_H > 0:
        inner = cq.Workplane("XY").polyline(outline).close().offset2D(MARGIN - 1.0).extrude(PLATE + RIB_H)
        for g in groups:
            x = sum(holes[k][0] for k in g) / len(g)
            bar = (cq.Workplane("XY").workplane(offset=PLATE - 0.01).center(x, -50)
                   .rect(RIB_W, 400).extrude(RIB_H + 0.01))
            body = body.union(bar.intersect(inner))
    for k, (x, y) in holes.items():
        d, length = PEGS[k]
        body = cut_hex(body, x, y, d + CLEARANCE, length + EXTRA_DEPTH)
    return body, outline


def build_solid_base(holes):
    """正式底座：外形同试摆底座，整块 T 厚，孔直接开在板上。"""
    pts = [(x, y) for x, y in holes.values()] + [(x, y - BACK) for x, y in holes.values()]
    outline = convex_hull(pts)
    body = cq.Workplane("XY").polyline(outline).close().offset2D(MARGIN).extrude(T)
    if TOP_CHAMFER:
        body = body.faces(">Z").chamfer(TOP_CHAMFER)
    for k, (x, y) in holes.items():
        d, length = PEGS[k]
        body = cut_hex(body, x, y, d + CLEARANCE, length + EXTRA_DEPTH)
    return body, outline


def fit_on_bed(body):
    """放得下就不转（方向和摆放照片一致）；放不下再找包围盒最小的角度。移到原点。"""
    bb = body.val().BoundingBox()
    if max(bb.xlen, bb.ylen) <= BED - 4:
        return body.translate((-bb.center.x, -bb.center.y, 0)), 0, bb.xlen, bb.ylen
    best = None
    for deg in range(0, 180):
        bb = body.rotate((0, 0, 0), (0, 0, 1), deg).val().BoundingBox()
        area = bb.xlen * bb.ylen
        if best is None or area < best[0]:
            best = (area, deg, bb.xlen, bb.ylen)
    _, deg, w, h = best
    rotated = body.rotate((0, 0, 0), (0, 0, 1), deg)
    c = rotated.val().BoundingBox().center
    return rotated.translate((-c.x, -c.y, 0)), deg, w, h


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    holes, res = solve_layout()
    print("跨手办距离拟合残差 (mm):", [round(float(r), 3) for r in res])
    for k, (x, y) in holes.items():
        print(f"  {k}: ({x:7.2f}, {y:7.2f})")

    def save(wp, name, step=False):
        cq.exporters.export(wp, str(OUT / f"{name}.stl"), tolerance=0.02, angularTolerance=0.1)
        if step:
            cq.exporters.export(wp, str(OUT / f"{name}.step"))
        print("已输出", OUT / f"{name}.stl")

    # 第三步：正式底座
    body, _ = build_solid_base(holes)
    body, deg, w, h = fit_on_bed(body)
    ok = "放得下" if max(w, h) <= BED - 4 else "放不下！"
    print(f"正式底座：厚 {T} mm，{w:.1f} x {h:.1f} mm，旋转 {deg} 度，A1 mini {ok}")
    save(body, "base", step=True)
    # 第二步：试摆底座（想重新验证摆位时用）
    thin, _ = build_base(holes)
    save(fit_on_bed(thin)[0], "test_base_thin")
    # 第一步：验证垫块 + 公差条
    save(build_trial(with_tol=False)[1], "test_pads")
    save(tolerance_strip(), "tolerance_strip")
