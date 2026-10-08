"""POP UP PARADE SP Wise × POP UP PARADE SP Belle 合体底座（『Zenless Zone Zero』，哲 × 铃）

孔位（images/holes.svg）：W = 哲，B = 铃，每只脚一个钉。
坐标：W1 原点，W2 在 +X；两人并排，正面看从左到右 W2 W1 B1 B2。

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
PEGS = {"W1": (4.9, 8.5), "W2": (3.95, 8.5), "B1": (4.92, 7.6), "B2": (3.93, 7.6)}   # (钉径, 露出长度)
FAR = {("W1", "W2"): 51.6, ("B1", "B2"): 38.5}   # 原厂底座两孔圆周最远距离：中心距 = 最远距离 - r1 - r2

# ---------------------------------------------------------------- 孔径（试出来的）
# 验证垫块的孔 = 钉径 x 1.01：W1、B2 刚好；W2、B1 偏松，按圆柱试样（±2%）定下在垫块孔上收的百分比
# （W2 先收 1%，正式底座 v1 上还是偏紧，改成 0.5%）
PAD_FLAT = {"W1": 4.949, "W2": 3.99, "B1": 4.969, "B2": 3.969}
FIT_PCT = {"W2": -0.5, "B1": -1.0}
HOLE_FLAT = {k: d * 1.01 for k, (d, _) in PEGS.items()}
HOLE_FLAT.update({k: PAD_FLAT[k] * (1 + p / 100) for k, p in FIT_PCT.items()})
EXTRA_DEPTH = 1.5   # 孔比钉长多挖的深度（哲的钉 8.5mm，孔底刚好剩 1mm）
CHAMFER = 0.4       # 孔口倒角

# ---------------------------------------------------------------- 摆位
GROUPS = (("W1", "W2"), ("B1", "B2"))
LAYOUT_GAPS = {("W1", "B1"): 30.6, ("W1", "B2"): 59.0, ("W2", "B1"): 39.9, ("W2", "B2"): 73.7}   # 垫块上量的近边距
WEIGHT = {}
ORDER = ["W2", "W1", "B1", "B2"]      # 正面看从左到右
SIDE = +1                             # 唯一让两人朝向一致、左右顺序对上的解
# 朝向 = 组内两孔连线逆时针转的角度；原厂圆底座中心 = (起点, 终点, 沿连线, 往右)（都从 IMG_5174 俯拍估）
FRONT = {"Wise": ("W1", "W2", 63.4), "Belle": ("B1", "B2", -51.8)}
ORIG_CENTER = {"Wise": ("W1", "W2", 23.5, 1.3), "Belle": ("B1", "B2", 14.6, -2.2)}
LABELS = {"Wise": "Wise", "Belle": "Belle"}

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
    groups = {"Wise": ("#3b5ba5", ["W1", "W2"]), "Belle": ("#d2691e", ["B1", "B2"])}
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
