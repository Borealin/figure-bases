"""POP UP PARADE Byleth (Male) × Byleth (Female) 合体底座（『Fire Emblem: Three Houses』）

孔位（images/holes.svg）：M = 贝雷特（男），F = 贝雷丝（女），每只脚一个钉。
坐标：M1 原点，M2 在 +X；两人并排，正面看从左到右 M2 M1 F1 F2。

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
PEGS = {"M1": (5.05, 6.9), "M2": (4.55, 6.9), "F1": (4.8, 7.0), "F2": (3.65, 7.0)}   # (钉径, 露出长度)
FAR = {("M1", "M2"): 120.0, ("F1", "F2"): 94.5}   # 原厂底座两孔圆周最远距离：中心距 = 最远距离 - r1 - r2

# ---------------------------------------------------------------- 孔径（试出来的）
# 验证垫块的孔 = 钉径 x 1.01；四个都偏松，按圆柱试样（±2%）定下在垫块孔上收的百分比
PAD_FLAT = {"M1": 5.101, "M2": 4.596, "F1": 4.848, "F2": 3.687}
FIT_PCT = {"M1": -1.5, "M2": -1.0, "F1": -0.5, "F2": -1.0}
HOLE_FLAT = {k: PAD_FLAT[k] * (1 + p / 100) for k, p in FIT_PCT.items()}
EXTRA_DEPTH = 1.5   # 孔比钉长多挖的深度
CHAMFER = 0.4       # 孔口倒角

# ---------------------------------------------------------------- 摆位
GROUPS = (("M1", "M2"), ("F1", "F2"))
# 垫块上量的跨手办近边距；M2-F2 超出卡尺量程，降低权重
LAYOUT_GAPS = {("M1", "F1"): 39.5, ("M1", "F2"): 117.5, ("M2", "F1"): 94.15, ("M2", "F2"): 171.5}
WEIGHT = {("M2", "F2"): 0.3}
ORDER = ["M2", "M1", "F1", "F2"]      # 正面看从左到右
SIDE = +1                             # 唯一让两人朝向一致、左右顺序对上的解
# 朝向 = 组内两孔连线逆时针转的角度；原厂底座中心 = (起点, 终点, 沿连线, 往右)（都从 IMG_5172 俯拍估）
FRONT = {"Byleth (Male)": ("M1", "M2", 59.8), "Byleth (Female)": ("F1", "F2", -69.3)}
ORIG_CENTER = {"Byleth (Male)": ("M1", "M2", 53.0, -2.9), "Byleth (Female)": ("F1", "F2", 40.9, -7.5)}
LABELS = {"Byleth (Male)": "Byleth M", "Byleth (Female)": "Byleth F"}

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
    groups = {"Byleth (Male)": ("#3b5ba5", ["M1", "M2"]), "Byleth (Female)": ("#2e8b6e", ["F1", "F2"])}
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
