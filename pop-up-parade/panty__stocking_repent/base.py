"""POP UP PARADE Panty & Stocking Set: Repent Ver. L Size 合体底座（『Panty & Stocking with Garterbelt』，天使造型）

孔位（images/holes.svg）：S = Stocking，P = Panty；两人都单脚站，一只脚上一大一小两根钉。
坐标：S1 原点，S2 在 +X；两人并排，正面看从左到右 S1 S2 P2 P1。

    python base.py [--slice] [--preview]
"""
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import basekit  # noqa: E402
import setkit  # noqa: E402

# ---------------------------------------------------------------- 实测
PEGS = {"S1": (5.6, 7.0), "S2": (4.3, 7.0), "P1": (5.05, 7.3), "P2": (4.4, 7.3)}   # (钉径, 露出长度)
FAR = {("S1", "S2"): 13.5, ("P1", "P2"): 14.5}   # 同一只脚两根钉圆周最远距离：中心距 = 最远距离 - r1 - r2

# ---------------------------------------------------------------- 孔径（试出来的）
# 验证垫块的孔 = 钉径 x 1.01：Stocking 两孔偏松、Panty 两孔偏紧，按圆柱试样（±2%）定下在垫块孔上调的百分比
PAD_FLAT = {"S1": 5.656, "S2": 4.343, "P1": 5.101, "P2": 4.444}
FIT_PCT = {"S1": -1.0, "S2": -2.0, "P1": +1.0, "P2": +2.0}
HOLE_FLAT = {k: PAD_FLAT[k] * (1 + p / 100) for k, p in FIT_PCT.items()}
EXTRA_DEPTH = 1.5   # 孔比钉长多挖的深度
CHAMFER = 0.4       # 孔口倒角

# ---------------------------------------------------------------- 摆位
GROUPS = (("S1", "S2"), ("P1", "P2"))
LAYOUT_GAPS = {("S1", "P1"): 50.5, ("S1", "P2"): 50.6, ("S2", "P1"): 46.8, ("S2", "P2"): 45.0}   # 垫块上量的近边距
WEIGHT = {}
ORDER = ["S1", "S2", "P2", "P1"]      # 正面看从左到右
SIDE = +1                             # 唯一让两人朝向一致、左右顺序对上的解
# 朝向 = 组内两孔连线逆时针转的角度；原厂 Ø99 底座中心 = (起点, 终点, 沿连线, 往右)（都从 IMG_5170 俯拍估）
FRONT = {"Stocking": ("S1", "S2", -10.0), "Panty": ("P1", "P2", 6.3)}
ORIG_CENTER = {"Stocking": ("S1", "S2", -22.9, 0.5), "Panty": ("P1", "P2", -21.3, 10.6)}
LABELS = {"Stocking": "Repent Stocking", "Panty": "Repent Panty"}

BASE_T = 11.0       # 底座厚度
COG_R = 15.0        # 原厂底座中心周围要包进底座的半径
MARGIN = 10.0       # 外轮廓在孔和 COG 圆外再留的边


def center_dist(a, b):
    far = FAR.get((a, b)) or FAR[(b, a)]
    return far - (PEGS[a][0] + PEGS[b][0]) / 2


def solve_layout():
    """返回 (holes, 拟合残差, 外推后残差, 外推距离)；近边距按六边形外接圆半径换算（宁远勿近）。"""
    a, b = GROUPS
    intra = {a: center_dist(*a), b: center_dist(*b)}
    calib = {k: f / math.sqrt(3) for k, f in PAD_FLAT.items()}
    return basekit.solve_two_pairs(a, b, intra, LAYOUT_GAPS, calib, side=SIDE, weight=WEIGHT)


def fronts(holes):
    return {g: basekit.front_dir(holes, a, b, deg) for g, (a, b, deg) in FRONT.items()}


def orig_centers(holes):
    return {g: basekit.frame_point(holes, a, b, along, right) for g, (a, b, along, right) in ORIG_CENTER.items()}


def build_base(holes):
    """11mm 实心底座 + 刻字；名字放在各自原厂底座中心附近，正面看是正的。"""
    depths = {k: PEGS[k][1] + EXTRA_DEPTH for k in PEGS}
    centers = orig_centers(holes)
    outline = basekit.outline_points(holes, HOLE_FLAT, centers.values(), COG_R)
    body = basekit.build_base(holes, HOLE_FLAT, depths, outline, T=BASE_T, margin=MARGIN, chain=ORDER)
    circles = [(holes[k], HOLE_FLAT[k] / math.sqrt(3) + CHAMFER + 1.5) for k in holes]
    body, _ = basekit.add_labels(body, [(LABELS[g], centers[g]) for g in LABELS],
                                 basekit.right_angle(list(fronts(holes).values())), outline, circles, top=BASE_T)
    return body


def preview(holes, body):
    import base_preview
    groups = {"Stocking": ("#c2185b", ["S1", "S2"]), "Panty": ("#b8860b", ["P1", "P2"])}
    cs = {g: (*c, COG_R) for g, c in orig_centers(holes).items()}
    fr = {g: (orig_centers(holes)[g], d) for g, d in fronts(holes).items()}
    base_preview.base_svg(HERE / "images" / "preview.svg", body, holes, HOLE_FLAT, groups, cs, fr, T=BASE_T)


if __name__ == "__main__":
    holes, r0, r1, push = solve_layout()
    print("跨手办距离残差:", [round(float(v), 2) for v in r0], f"外推 {push:.2f}mm 后:", [round(float(v), 2) for v in r1])
    order = basekit.left_to_right(holes, list(fronts(holes).values()))
    print("正面看从左到右:", order, "一致" if order == ORDER else "不一致！")
    body = build_base(holes)
    setkit.export(HERE, {"base": basekit.fit_on_bed(body)[0]})
    if setkit.want_preview():
        preview(holes, body)
