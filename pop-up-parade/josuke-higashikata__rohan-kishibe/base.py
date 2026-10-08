"""POP UP PARADE 東方仗助 × 岸辺露伴 合体底座（『ジョジョの奇妙な冒険 ダイヤモンドは砕けない』，交叠站位）

孔位（images/holes.svg）：J = 仗助（J1+J2 前脚双钉，J3 后脚），R = 露伴（R1 前脚，R2+R3 后脚双钉）。
坐标：J1 原点，两个手办都面朝 +Y。

    python base.py [--slice] [--preview]
"""
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import basekit  # noqa: E402
import setkit  # noqa: E402

# ---------------------------------------------------------------- 实测
PEGS = {
    "J1": (4.52, 7.40), "J2": (3.70, 7.30), "J3": (4.32, 7.70),
    "R1": (4.35, 6.93), "R2": (4.27, 6.80), "R3": (4.30, 6.60),
}   # (钉径, 露出长度)
# 原厂底座上两个六边形孔的近边距；中心距 = 近边距 + (r1 + r2) * K
GAPS = {
    ("J1", "J2"): 9.80, ("J1", "J3"): 87.82, ("J2", "J3"): 99.00,
    ("R1", "R2"): 78.00, ("R1", "R3"): 79.54, ("R2", "R3"): 11.80,
}
K = 1.05
# 试摆垫块上量的跨手办近边距（IMG_4945）
CROSS_GAPS = {("J1", "R1"): 43.7, ("J2", "R1"): 54.0, ("J1", "R2"): 65.4, ("J3", "R3"): 116.4}

# ---------------------------------------------------------------- 孔径（试出来的）
# 垫块孔 = 钉径 + 0.2 明显偏松；公差条（+0.0 ～ +0.4）试下来对边距 = 钉径刚好
HOLE_FLAT = {k: d for k, (d, _) in PEGS.items()}
EXTRA_DEPTH = 1.5   # 孔比钉长多挖的深度

# ---------------------------------------------------------------- 底座
T = 11.0            # 底座厚度
MARGIN = 12.0       # 底座边缘离孔中心的最小距离
BACK = 10.0         # 底座往手办身后（-Y）多伸出的距离，防止后倒（试摆是 20，实测可缩短）
R_NUDGE = (0.0, -3.0)   # 试摆后微调：露伴整体往后（-Y）挪 3mm
LABELS = {"Josuke": ("J1", "J2", "J3"), "Rohan": ("R1", "R2", "R3")}   # 名字从各自三个孔的中心附近开始找空位
FRONT_DIR = (0.0, 1.0)


def center_dist(a, b):
    gaps = {**GAPS, **CROSS_GAPS}
    gap = gaps.get((a, b)) or gaps[(b, a)]
    return gap + K * (PEGS[a][0] + PEGS[b][0]) / 2


def triangle(a, b, c):
    """a 在原点、b 在 +X 轴；俯视时 c 在 a→b 的右侧（IMG_4941 里两组都是这样）。"""
    ab, ac, bc = center_dist(a, b), center_dist(a, c), center_dist(b, c)
    x = (ac ** 2 - bc ** 2 + ab ** 2) / (2 * ab)
    return {a: (0.0, 0.0), b: (ab, 0.0), c: (x, -math.sqrt(ac ** 2 - x ** 2))}


J = triangle("J1", "J2", "J3")
R = triangle("R1", "R2", "R3")


def solve_layout():
    """露伴三孔相对仗助：4 个跨手办中心距最小二乘（平移 + 旋转），初值来自 IMG_4945；再按试摆结果往后挪。"""
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
    return {**{k: tuple(v) for k, v in Jp.items()}, **nudged}, resid(x)


def build_base(holes):
    """11mm 实心底座：外形 = 孔和孔往后 BACK 的点的凸包，外扩 MARGIN；顶边倒角 1mm；刻名字。"""
    pts = [(x, y) for x, y in holes.values()] + [(x, y - BACK) for x, y in holes.values()]
    outline = basekit.convex_hull(pts)
    depths = {k: L + EXTRA_DEPTH for k, (_, L) in PEGS.items()}
    body = basekit.build_base(holes, HOLE_FLAT, depths, outline, T=T, margin=MARGIN)
    circles = [(holes[k], HOLE_FLAT[k] / math.sqrt(3) + 0.4 + 1.5) for k in holes]
    labels = [(name, (sum(holes[k][0] for k in ks) / 3, sum(holes[k][1] for k in ks) / 3)) for name, ks in LABELS.items()]
    body, _ = basekit.add_labels(body, labels, basekit.right_angle([FRONT_DIR]), outline, circles, top=T)
    return body


def preview(holes, body):
    import base_preview
    groups = {"Josuke": ("#3b5ba5", ["J1", "J2", "J3"]), "Rohan": ("#2e8b6e", ["R1", "R2", "R3"])}
    fr = {g: ((sum(holes[k][0] for k in ks) / 3, sum(holes[k][1] for k in ks) / 3), FRONT_DIR) for g, ks in LABELS.items()}
    base_preview.base_svg(HERE / "images" / "preview.svg", body, holes, HOLE_FLAT, groups, None, fr, T=T)


if __name__ == "__main__":
    holes, res = solve_layout()
    print("跨手办距离残差:", [round(float(r), 2) for r in res])
    body = build_base(holes)
    setkit.export(HERE, {"base": basekit.fit_on_bed(body)[0]})
    if setkit.want_preview():
        preview(holes, body)
