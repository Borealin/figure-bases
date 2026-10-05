"""POP UP PARADE SP Wise × POP UP PARADE SP Belle 合体底座
（Good Smile Company，『Zenless Zone Zero』，哲 × 铃）

孔位编号（见 docs/hole-labels.svg，IMG_5174 俯拍）：
  W = 哲（Wise）：W1、W2 各一只脚
  B = 铃（Belle）：B1、B2 各一只脚
原厂底座是圆底座，每只脚一个圆孔。

第一步：验证垫块（v1 已打印试装）
第二步：正式底座 = 11mm 实心整板（python figure_base.py）

用法：python figure_base.py  →  输出到 out/
"""
import math
from pathlib import Path

import cadquery as cq

# ---------------------------------------------------------------- 实测数据
# 手办脚底圆钉：(直径, 露出长度) mm；长度每个手办量最长的那根
PEGS = {
    "W1": (4.9, 8.5), "W2": (3.95, 8.5),
    "B1": (4.92, 7.6), "B2": (3.93, 7.6),
}
# 原厂底座两孔圆周上的最远距离：中心距 = 最远距离 - r1 - r2
FAR = {("W1", "W2"): 51.6, ("B1", "B2"): 38.5}

# ---------------------------------------------------------------- 打印参数
# 打印机：Bambu A1 mini（FDM，平台 180 x 180）
# 六边形孔对边距 = (钉径 + CLEARANCE[孔]) * HOLE_SCALE；沿用前几套的经验（x1.01）
CLEARANCE = {k: 0.0 for k in PEGS}
HOLE_SCALE = 1.01
EXTRA_DEPTH = 1.5   # 孔比钉长多挖的深度
CHAMFER = 0.4       # 孔口倒角
PAD_T = 11.0        # 垫块厚度（和正式底座一样）
PAD_WALL = 2.2      # 垫块在孔外留的壁厚
assert PAD_T - max(L for _, L in PEGS.values()) - EXTRA_DEPTH >= 1.0, "孔底太薄"

# ---------------------------------------------------------------- 试装 / 试摆结果（验证垫块 v1）
# 孔松紧：W2、B1 略松 → 各小 0.15；W1、B2 刚好
HOLE_FLAT = {"W2": 3.84, "B1": 4.819}
PAD_FLAT_MEASURED = {"W1": 4.949, "W2": 3.99, "B1": 4.969, "B2": 3.969}
GROUPS = (("W1", "W2"), ("B1", "B2"))
LAYOUT_GAPS = {("W1", "B1"): 30.6, ("W1", "B2"): 59.0, ("W2", "B1"): 39.9, ("W2", "B2"): 73.7}
WEIGHT = {}
ORDER = ["W2", "W1", "B1", "B2"]      # 正面看从左到右（实测）
SIDE = +1                             # 唯一让两人朝向一致、左右顺序对上的解
# 手办朝向 = 组内两孔连线方向逆时针转的角度（IMG_5174 俯拍，照片下方是正面）
FRONT = {"Wise": ("W1", "W2", 63.4), "Belle": ("B1", "B2", -51.8)}
# 原厂圆底座中心（IMG_5174 估）
ORIG_CENTER = {"Wise": ("W1", "W2", 23.5, 1.3), "Belle": ("B1", "B2", 14.6, -2.2)}
# 底座上刻的名字（防止几套搞混）
LABELS = {"Wise": "Wise", "Belle": "Belle"}

OUT = Path(__file__).parent / "out"


def center_dist(a, b):
    far = FAR.get((a, b)) or FAR[(b, a)]
    return far - (PEGS[a][0] + PEGS[b][0]) / 2


def hole_flat(name):
    if name in HOLE_FLAT:
        return HOLE_FLAT[name]
    return (PEGS[name][0] + CLEARANCE[name]) * HOLE_SCALE


# ---------------------------------------------------------------- 零件
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


def pad_single(name):
    """单钉的脚：圆头长条，孔在一头、另一头刻编号。绕钉能转，摆的时候把刻字那头转到不碍事的方向。"""
    r = hole_flat(name) / math.sqrt(3) + CHAMFER + PAD_WALL
    tail = 8.0
    body = cq.Workplane("XY").center(0, -tail / 2).slot2D(tail + 2 * r, 2 * r, 90).extrude(PAD_T)
    body = peg_hole(body, name, 0, 0)
    return engrave(body, name, 0, -tail)


TRIAL_LAYOUT = {"W1": (-21, 0), "W2": (-7, 0), "B1": (7, 0), "B2": (21, 0)}


def build_trial():
    parts = {k: pad_single(k) for k in TRIAL_LAYOUT}
    moved = [p.translate((*TRIAL_LAYOUT[k], 0)).val() for k, p in parts.items()]
    return parts, cq.Workplane().add(cq.Compound.makeCompound(moved))


# ---------------------------------------------------------------- 第二步：正式底座
import sys as _sys  # noqa: E402
_sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import basekit  # noqa: E402

BASE_T = 11.0       # 底座厚度
COG_R = 15.0        # 原厂底座中心周围要包进底座的半径
MARGIN = 10.0       # 外轮廓在孔和 COG 圆外再留的边
assert BASE_T - max(L for _, L in PEGS.values()) - EXTRA_DEPTH >= 1.0, "底座孔底太薄"


def solve_layout():
    """返回 (holes, 拟合残差, 外推后残差, 外推距离)。"""
    a, b = GROUPS
    intra = {a: center_dist(*a), b: center_dist(*b)}
    calib = {k: f / math.sqrt(3) for k, f in PAD_FLAT_MEASURED.items()}   # 六边形外接圆半径：宁远勿近
    return basekit.solve_two_pairs(a, b, intra, LAYOUT_GAPS, calib, side=SIDE, weight=WEIGHT)


def fronts(holes):
    return {g: basekit.front_dir(holes, a, b, deg) for g, (a, b, deg) in FRONT.items()}


def orig_centers(holes):
    return {g: basekit.frame_point(holes, a, b, along, right) for g, (a, b, along, right) in ORIG_CENTER.items()}


def build_base(holes, thin=False):
    """正式底座（刻字）或试摆底座（凸字）；每个手办的名字放在它原厂底座中心附近，正面看是正的。"""
    flats = {k: hole_flat(k) for k in PEGS}
    depths = {k: PEGS[k][1] + EXTRA_DEPTH for k in PEGS}
    centers = orig_centers(holes)
    outline = basekit.outline_points(holes, flats, centers.values(), COG_R)
    body = basekit.build_base(holes, flats, depths, outline, T=BASE_T, margin=MARGIN, thin=thin, chain=ORDER)
    keep = 2.5 + 1.5 if thin else 1.5                     # 试摆底座要躲开桩
    circles = [(holes[k], flats[k] / math.sqrt(3) + CHAMFER + keep) for k in holes]
    segments = [((holes[p], holes[q]), 2.5) for p, q in zip(ORDER, ORDER[1:])] if thin else []
    body, _ = basekit.add_labels(body, [(LABELS[g], centers[g]) for g in LABELS],
                                 basekit.right_angle(list(fronts(holes).values())), outline, circles, segments,
                                 top=0.8 if thin else BASE_T, raised=thin)
    return body


def check(holes):
    """打印朝向和左右顺序，用来核对镜像。"""
    f = fronts(holes)
    angs = {g: round(basekit.angle(v), 1) for g, v in f.items()}
    order = basekit.left_to_right(holes, list(f.values()))
    print("手办朝向（度）:", angs, " 正面看从左到右:", order, " 实测:", ORDER,
          "一致" if order == ORDER else "不一致！")
    return order == ORDER


if __name__ == "__main__":
    import sys
    OUT.mkdir(exist_ok=True)
    if "--trial" in sys.argv:   # 按当前孔径重新生成验证垫块（v1 已打印，不覆盖）
        cq.exporters.export(build_trial()[1], str(OUT / "trial_v2.stl"), tolerance=0.01, angularTolerance=0.1)
        print("已输出", OUT / "trial_v2.stl")
        sys.exit()
    for a, b in FAR:
        print(f"{a}-{b} 中心距 {center_dist(a, b):.2f} mm")
    print("孔对边距:", {k: round(hole_flat(k), 3) for k in PEGS})
    holes, r0, r1, push = solve_layout()
    print("跨手办距离拟合残差:", [round(float(v), 3) for v in r0], f" 外推 {push:.2f}mm 后:", [round(float(v), 3) for v in r1])
    for k, (x, y) in holes.items():
        print(f"  {k}: ({x:7.2f}, {y:7.2f})")
    check(holes)
    for name, thin in (("base", False), ("test_base_thin", True)):
        body, deg, w, h = basekit.fit_on_bed(build_base(holes, thin=thin))
        print(f"{name}：{w:.1f} x {h:.1f} mm，旋转 {deg} 度，A1 mini {'放得下' if max(w, h) <= 176 else '放不下！'}")
        cq.exporters.export(body, str(OUT / f"{name}.stl"), tolerance=0.01, angularTolerance=0.1)
        if not thin:
            cq.exporters.export(body, str(OUT / f"{name}.step"))
        print("已输出", OUT / f"{name}.stl")
