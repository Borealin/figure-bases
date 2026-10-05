"""POP UP PARADE Panty & Stocking Set 合体底座（背靠背）
（Good Smile Company，『Panty & Stocking with Garterbelt』）

孔位编号（见 docs/hole-labels.svg，IMG_5147 俯拍）：
  S = Stocking（原厂左边底座）：S1、S2 同一只脚，S3 另一只脚
  P = Panty（原厂右边底座）：P1、P2 各一只脚
原厂底座都是 Ø99 圆底座，孔是六边形。

第一步：验证垫块（每只脚一个）
第二步：试摆底座 = 0.8mm 薄底板 + 每个孔一个桩 + 加强筋
第三步：正式底座 = 11mm 实心整板

坐标系：S1 为原点，S2 在 +X；从 S1 看向 S2，左手边为 +Y（俯视），S3 在左手边。

用法：python figure_base.py  →  输出到 out/
"""
import math
from pathlib import Path

import cadquery as cq

# ---------------------------------------------------------------- 实测数据
# 手办脚底圆钉：(直径, 露出长度) mm；长度每个手办按最长的那根算
PEGS = {
    "S1": (6.0, 7.4), "S2": (6.0, 7.4), "S3": (6.0, 7.4),
    "P1": (5.2, 8.1), "P2": (6.0, 8.1),
}
# 原厂底座上两孔的近边距（六边形孔）：中心距 = 近边距 + (r1 + r2) * K
GAPS = {("S1", "S2"): 12.1, ("S1", "S3"): 22.1, ("S2", "S3"): 25.7, ("P1", "P2"): 36.5}
K = 1.05

# ---------------------------------------------------------------- 摆放（验证垫块试摆，背靠背）
# 垫块上量的跨手办近边距（垫块孔都是六边形 → 按 K 换算）。P2–S2 当时记成 104.9，
# 用 P1–P2 固定距离交叉检查发现差 10mm，复量确认是 114.9
CROSS_GAPS = {("P1", "S1"): 64.3, ("P1", "S2"): 73.7, ("P1", "S3"): 42.4,
              ("P2", "S1"): 103.6, ("P2", "S2"): 114.9, ("P2", "S3"): 83.6}
# 原厂底座中心（Ø99，照片 IMG_5147 按直径 99 定比例估）：(起点, 终点, 沿连线, 往右)
ORIG_CENTER = {"Stocking": ("S1", "S2", -3.05, -8.13), "Panty": ("P1", "P2", 18.77, -2.24)}
# 试摆底座 v1 试装：Panty 整体往"后"挪 1mm。前后按 Stocking 定：S2、S3 在前、S1 在后，
# "往后" = 垂直于 S2–S3 连线、指向 S1 的方向
PANTY_NUDGE = 1.0
# Stocking 头发重、容易往后倒 → 底座在 Stocking 身后多伸出一段：
# 把 Stocking 原厂底座中心的 COG 圆沿"往后"方向再复制一份，挪 STOCKING_BACK
STOCKING_BACK = 15.0
# 正式底座 v1 试装：两人还是贴得有点近 → Panty 再沿"Stocking 三孔中心 → Panty 两孔中心"方向平移 2mm
PANTY_APART = 2.0

# ---------------------------------------------------------------- 打印参数
# 打印机：Bambu A1 mini（FDM，平台 180 x 180）
# 六边形孔对边距 = (钉径 + CLEARANCE[孔]) * HOLE_SCALE；沿用 2B × A2 那套的最终经验（x1.01）
CLEARANCE = {k: 0.0 for k in PEGS}
HOLE_SCALE = 1.01
# 个别孔直接指定对边距（试装结果）：
#   P1：v1 垫块 5.252 略松 → v2 补打 5.20 仍松 → v3 补打 5.10 → 定为 5.12
HOLE_FLAT = {"P1": 5.12}
EXTRA_DEPTH = 1.5   # 孔比钉长多挖的深度
CHAMFER = 0.4       # 孔口倒角
PAD_T = 11.0        # 垫块厚度（和正式底座一样），保证鞋底在同一高度
PAD_WALL = 2.2      # 垫块在孔外留的壁厚
assert PAD_T - max(L for _, L in PEGS.values()) - EXTRA_DEPTH >= 1.0, "孔底太薄"

OUT = Path(__file__).parent / "out"


def center_dist(a, b):
    gap = GAPS.get((a, b)) or GAPS[(b, a)]
    return gap + K * (PEGS[a][0] + PEGS[b][0]) / 2


def triangle(a, b, c):
    """a 在原点、b 在 +X 轴；俯视时 c 在 a→b 的左侧（IMG_5147：S3 在 S1→S2 左侧）。"""
    ab, ac, bc = center_dist(a, b), center_dist(a, c), center_dist(b, c)
    x = (ac ** 2 - bc ** 2 + ab ** 2) / (2 * ab)
    return {a: (0.0, 0.0), b: (ab, 0.0), c: (x, math.sqrt(ac ** 2 - x ** 2))}


S = triangle("S1", "S2", "S3")


# ---------------------------------------------------------------- 零件
def hole_flat(name):
    if name in HOLE_FLAT:
        return HOLE_FLAT[name]
    return (PEGS[name][0] + CLEARANCE[name]) * HOLE_SCALE


def cut_hex(body, x, y, flat, depth, top, chamfer=CHAMFER):
    """在顶面 (x, y) 开对边距为 flat 的六边形盲孔，孔口倒角。"""
    r = flat / math.sqrt(3)
    hole = (cq.Workplane("XY").workplane(offset=top - depth)
            .center(x, y).polygon(6, 2 * r).extrude(depth + 1))
    body = body.cut(hole)
    if not chamfer:
        return body
    box = cq.selectors.BoxSelector((x - r - 0.2, y - r - 0.2, top - 0.01),
                                   (x + r + 0.2, y + r + 0.2, top + 0.01))
    return body.edges(box).chamfer(chamfer)


def peg_hole(body, name, x, y, top=PAD_T):
    return cut_hex(body, x, y, hole_flat(name), PEGS[name][1] + EXTRA_DEPTH, top)


def engrave(body, text, x, y, size=4.0, depth=0.6, top=PAD_T):
    txt = (cq.Workplane("XY").workplane(offset=top - depth).center(x, y)
           .text(text, size, depth + 0.1, combine=False,
                 halign="center", valign="center", kind="bold"))
    return body.cut(txt)


def pad_r(name):
    """垫块半宽：六边形外接圆 + 倒角 + 壁厚。"""
    return hole_flat(name) / math.sqrt(3) + CHAMFER + PAD_WALL


def pad_s12():
    """Stocking S1+S2 那只脚：跑道形，两个孔；两孔一样粗，中间刻 1、2 区分。"""
    s = center_dist("S1", "S2")
    r = max(pad_r("S1"), pad_r("S2"))
    body = cq.Workplane("XY").slot2D(s + 2 * r, 2 * r).extrude(PAD_T)
    body = peg_hole(body, "S1", -s / 2, 0)
    body = peg_hole(body, "S2", s / 2, 0)
    body = engrave(body, "1", -2.6, 0)
    return engrave(body, "2", 2.6, 0)


def pad_single(name, label):
    """单钉的脚：圆头长条，孔在一头、另一头刻字。绕钉能转，摆的时候把刻字那头转到不碍事的方向。"""
    r = pad_r(name)
    tail = 8.0
    body = cq.Workplane("XY").center(0, -tail / 2).slot2D(tail + 2 * r, 2 * r, 90).extrude(PAD_T)
    body = peg_hole(body, name, 0, 0)
    return engrave(body, label, 0, -tail)


# ---------------------------------------------------------------- 合体底座
BASE_T = 11.0       # 底座厚度
PLATE = 0.8         # 试摆底座底板厚度（0.2mm 层高的首 4 层）
POST_WALL = 2.5     # 试摆底座：桩在孔外留的壁厚
RIB_W, RIB_H = 2.0, 5.0   # 试摆底座：连接各桩的加强筋宽、高（高出底板）
COG_R = 15.0        # 原厂底座中心周围要包进底座的半径
MARGIN = 10.0       # 外轮廓在孔和 COG 圆外再留的边
TOP_CHAMFER = 1.0   # 正式底座顶面外沿倒角
BED = 180.0         # A1 mini 平台
assert BASE_T - max(L for _, L in PEGS.values()) - EXTRA_DEPTH >= 1.0, "底座孔底太薄"


def back_dir():
    """"往后"的单位向量：垂直于 S2–S3 连线、指向 S1（S2、S3 在前，S1 在后）。"""
    (x2, y2), (x3, y3), (x1, y1) = S["S2"], S["S3"], S["S1"]
    ex, ey = x3 - x2, y3 - y2
    L = math.hypot(ex, ey)
    nx, ny = -ey / L, ex / L
    if nx * (x1 - x2) + ny * (y1 - y2) < 0:
        nx, ny = -nx, -ny
    return nx, ny


def solve_layout():
    """Stocking 三孔固定（S1 原点、S2 在 +X、S3 在左侧）；Panty 两孔按刚体（P1–P2 固定）
    用 6 个跨手办距离做最小二乘。Stocking 有 3 个孔，所以没有镜像歧义。"""
    import numpy as np
    Sx = {k: np.array(v) for k, v in S.items()}
    dP = center_dist("P1", "P2")
    cd = {k: g + K * (PEGS[k[0]][0] + PEGS[k[1]][0]) / 2 for k, g in CROSS_GAPS.items()}

    def place(x):
        p1 = x[:2]
        return {"P1": p1, "P2": p1 + dP * np.array([math.cos(x[2]), math.sin(x[2])])}

    def resid(x):
        P = place(x)
        return np.array([np.linalg.norm(P[a] - Sx[b]) - d for (a, b), d in cd.items()])

    best = None
    for a0 in np.linspace(0, 2 * math.pi, 24, endpoint=False):   # 多个初值，取残差最小
        x = np.array([-30.0, 60.0, a0])
        for _ in range(100):
            r = resid(x)
            jac = np.column_stack([(resid(x + e) - r) / 1e-7 for e in np.eye(3) * 1e-7])
            step = np.linalg.lstsq(jac, -r, rcond=None)[0]
            x = x + step
            if abs(step).max() < 1e-12:
                break
        if best is None or (resid(x) ** 2).sum() < (resid(best) ** 2).sum():
            best = x
    # Panty 微调：沿"往后"方向平移 PANTY_NUDGE
    n = np.array(back_dir())
    P = {k: v + PANTY_NUDGE * n for k, v in place(best).items()}
    # 两人拉开：Panty 沿两组孔中心连线方向再平移 PANTY_APART
    a = sum(P.values()) / len(P) - sum(Sx.values()) / len(Sx)
    P = {k: v + PANTY_APART * a / np.linalg.norm(a) for k, v in P.items()}
    holes = {**{k: tuple(v) for k, v in S.items()}, **{k: tuple(float(c) for c in v) for k, v in P.items()}}
    return holes, resid(best)


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


def circle_pts(c, r, n=24):
    return [(c[0] + r * math.cos(2 * math.pi * i / n), c[1] + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def outline_points(holes):
    pts = [p for k, c in holes.items() for p in circle_pts(c, hole_flat(k) / math.sqrt(3) + CHAMFER)]
    centers = orig_centers(holes)
    for c in centers.values():
        pts += circle_pts(c, COG_R)
    bx, by = back_dir()
    c = centers["Stocking"]
    pts += circle_pts((c[0] + STOCKING_BACK * bx, c[1] + STOCKING_BACK * by), COG_R)
    return convex_hull(pts)


def build_base(holes, thin=False):
    """thin=True：试摆底座（薄底板 + 桩 + 加强筋）；否则正式底座（BASE_T 实心）。"""
    outline = cq.Workplane("XY").polyline(outline_points(holes)).close().offset2D(MARGIN)
    if thin:
        body = outline.extrude(PLATE)
        for k, (x, y) in holes.items():
            r = hole_flat(k) / math.sqrt(3) + CHAMFER + POST_WALL
            body = body.union(cq.Workplane("XY").center(x, y).circle(r).extrude(BASE_T))
        for a, b in (("S2", "S1"), ("S1", "S3"), ("S3", "P1"), ("P1", "P2")):
            (x0, y0), (x1, y1) = holes[a], holes[b]
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            rib = (cq.Workplane("XY").workplane(offset=PLATE - 0.01).center(cx, cy)
                   .rect(math.dist(holes[a], holes[b]), RIB_W).extrude(RIB_H + 0.01)
                   .rotate((cx, cy, 0), (cx, cy, 1), math.degrees(math.atan2(y1 - y0, x1 - x0))))
            body = body.union(rib)
    else:
        body = outline.extrude(BASE_T)
        if TOP_CHAMFER:
            body = body.faces(">Z").chamfer(TOP_CHAMFER)
    for k, (x, y) in holes.items():
        body = peg_hole(body, k, x, y, top=BASE_T)
    return body


# ---------------------------------------------------------------- 名字（防止几套搞混）
import sys as _sys  # noqa: E402
_sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import basekit  # noqa: E402

# 背靠背：Stocking 面朝 S1 的反方向（S2、S3 在前），Panty 面朝相反方向；两个名字各自朝着自己的正面
LABELS = {"Stocking": "Stocking", "Panty": "Panty"}


def add_labels(body, holes, thin=False):
    keep = POST_WALL + 1.5 if thin else 1.5            # 试摆底座要躲开桩
    circles = [(holes[k], hole_flat(k) / math.sqrt(3) + CHAMFER + keep) for k in holes]
    segments = ([((holes[a], holes[b]), RIB_W / 2 + 1.5)
                 for a, b in (("S2", "S1"), ("S1", "S3"), ("S3", "P1"), ("P1", "P2"))] if thin else [])
    bx, by = back_dir()
    front = {"Stocking": (-bx, -by), "Panty": (bx, by)}
    centers = orig_centers(holes)
    for g, text in LABELS.items():
        body, _ = basekit.add_labels(body, [(text, centers[g])], basekit.right_angle([front[g]]),
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
TRIAL_LAYOUT = {"S12": (-24, 0), "S3": (2, 0), "P1": (18, 0), "P2": (34, 0)}


def build_pad(name):
    return pad_s12() if name == "S12" else pad_single(name, name)


def build_trial():
    parts = {k: build_pad(k) for k in TRIAL_LAYOUT}
    moved = [p.translate((*TRIAL_LAYOUT[k], 0)).val() for k, p in parts.items()]
    return parts, cq.Workplane().add(cq.Compound.makeCompound(moved))


if __name__ == "__main__":
    import sys
    OUT.mkdir(exist_ok=True)
    if "--pad" in sys.argv:   # 单独补打一个垫块：python figure_base.py --pad P1
        name = sys.argv[sys.argv.index("--pad") + 1]
        v = 2
        while (OUT / f"pad_{name}_v{v}.stl").exists():   # 不覆盖已经打印过的版本
            v += 1
        out = OUT / f"pad_{name}_v{v}.stl"
        cq.exporters.export(build_pad(name), str(out), tolerance=0.01, angularTolerance=0.1)
        print("已输出", out, "孔对边距", round(hole_flat(name), 3))
        sys.exit()

    def save(wp, name):
        cq.exporters.export(wp, str(OUT / f"{name}.stl"), tolerance=0.01, angularTolerance=0.1)
        print("已输出", OUT / f"{name}.stl")

    if "--trial" in sys.argv:   # 重新生成验证垫块（v1 已打印，平时不覆盖）
        save(build_trial()[1], "trial_v1")
        sys.exit()

    holes, res = solve_layout()
    print("跨手办距离拟合残差 (mm):", [round(float(r), 3) for r in res])
    for k, (x, y) in holes.items():
        print(f"  {k}: ({x:7.2f}, {y:7.2f})")
    for name, thin in (("test_base_thin", True), ("base", False)):
        body, deg, w, h = fit_on_bed(add_labels(build_base(holes, thin=thin), holes, thin=thin))
        ok = "放得下" if max(w, h) <= BED - 4 else "放不下！"
        print(f"{name}：{w:.1f} x {h:.1f} mm，旋转 {deg} 度，A1 mini {ok}")
        cq.exporters.export(body, str(OUT / f"{name}.stl"), tolerance=0.01, angularTolerance=0.1)
        if not thin:
            cq.exporters.export(body, str(OUT / f"{name}.step"))
        print("已输出", OUT / f"{name}.stl")
