"""POP UP PARADE Panty & Stocking Set 合体底座（『Panty & Stocking with Garterbelt』，背靠背）

孔位（images/holes.svg）：S = Stocking（S1、S2 同一只脚，S3 另一只脚），P = Panty（P1、P2 各一只脚）。
坐标：S1 原点，S2 在 +X，S3 在 S1→S2 的左手边。

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
PEGS = {"S1": (6.0, 7.4), "S2": (6.0, 7.4), "S3": (6.0, 7.4), "P1": (5.2, 8.1), "P2": (6.0, 8.1)}   # (钉径, 露出长度)
# 原厂底座上两孔的近边距（六边形孔）：中心距 = 近边距 + (r1 + r2) * K
GAPS = {("S1", "S2"): 12.1, ("S1", "S3"): 22.1, ("S2", "S3"): 25.7, ("P1", "P2"): 36.5}
K = 1.05

# ---------------------------------------------------------------- 孔径（试出来的）
# 孔 = 钉径 x 1.01；P1 单独试了三次：5.25 略松 → 5.20 仍松 → 5.10 偏紧 → 定 5.12
HOLE_FLAT = {k: d * 1.01 for k, (d, _) in PEGS.items()}
HOLE_FLAT["P1"] = 5.12
EXTRA_DEPTH = 1.5   # 孔比钉长多挖的深度
CHAMFER = 0.4       # 孔口倒角

# ---------------------------------------------------------------- 摆位（背靠背）
# 垫块上量的跨手办近边距（P2–S2 当时记成 104.9，用 P1–P2 固定距离交叉检查发现差 10mm，复量是 114.9）
CROSS_GAPS = {("P1", "S1"): 64.3, ("P1", "S2"): 73.7, ("P1", "S3"): 42.4,
              ("P2", "S1"): 103.6, ("P2", "S2"): 114.9, ("P2", "S3"): 83.6}
# 原厂 Ø99 底座中心（IMG_5147 按直径定比例估）：(起点, 终点, 沿连线, 往右)
ORIG_CENTER = {"Stocking": ("S1", "S2", -3.05, -8.13), "Panty": ("P1", "P2", 18.77, -2.24)}
PANTY_NUDGE = 1.0     # 试摆底座试装：Panty 整体往"后"挪 1mm（"后" = 垂直于 S2–S3、指向 S1）
STOCKING_BACK = 15.0  # Stocking 头发重容易往后倒：她身后的底座多伸出 15mm
PANTY_APART = 2.0     # 正式底座 v1 试装：两人还是贴得近，再拉开 2mm
LABELS = {"Stocking": "Stocking", "Panty": "Panty"}

BASE_T = 11.0       # 底座厚度
COG_R = 15.0        # 原厂底座中心周围要包进底座的半径
MARGIN = 10.0       # 外轮廓在孔和 COG 圆外再留的边


def center_dist(a, b):
    gap = GAPS.get((a, b)) or GAPS[(b, a)]
    return gap + K * (PEGS[a][0] + PEGS[b][0]) / 2


def triangle(a, b, c):
    """a 在原点、b 在 +X 轴；俯视时 c 在 a→b 的左侧（IMG_5147）。"""
    ab, ac, bc = center_dist(a, b), center_dist(a, c), center_dist(b, c)
    x = (ac ** 2 - bc ** 2 + ab ** 2) / (2 * ab)
    return {a: (0.0, 0.0), b: (ab, 0.0), c: (x, math.sqrt(ac ** 2 - x ** 2))}


S = triangle("S1", "S2", "S3")


def back_dir():
    """"往后"：垂直于 S2–S3 连线、指向 S1（S2、S3 在前，S1 在后）。"""
    (x2, y2), (x3, y3), (x1, y1) = S["S2"], S["S3"], S["S1"]
    ex, ey = x3 - x2, y3 - y2
    L = math.hypot(ex, ey)
    nx, ny = -ey / L, ex / L
    if nx * (x1 - x2) + ny * (y1 - y2) < 0:
        nx, ny = -nx, -ny
    return nx, ny


def solve_layout():
    """Stocking 三孔固定；Panty 两孔当刚体，用 6 个跨手办距离最小二乘（Stocking 有 3 个孔，没有镜像歧义）。"""
    Sx = {k: np.array(v) for k, v in S.items()}
    dP = center_dist("P1", "P2")
    cd = {k: g + K * (PEGS[k[0]][0] + PEGS[k[1]][0]) / 2 for k, g in CROSS_GAPS.items()}

    def place(x):
        return {"P1": x[:2], "P2": x[:2] + dP * np.array([math.cos(x[2]), math.sin(x[2])])}

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
    P = {k: v + PANTY_NUDGE * np.array(back_dir()) for k, v in place(best).items()}
    a = sum(P.values()) / len(P) - sum(Sx.values()) / len(Sx)
    P = {k: v + PANTY_APART * a / np.linalg.norm(a) for k, v in P.items()}
    holes = {**{k: tuple(v) for k, v in S.items()}, **{k: tuple(float(c) for c in v) for k, v in P.items()}}
    return holes, resid(best)


def orig_centers(holes):
    return {g: basekit.frame_point(holes, a, b, along, right) for g, (a, b, along, right) in ORIG_CENTER.items()}


def outline_points(holes):
    """孔 + 两人原厂底座中心的 COG 圆 + Stocking 身后再挪 STOCKING_BACK 的一个 COG 圆。"""
    centers = orig_centers(holes)
    bx, by = back_dir()
    c = centers["Stocking"]
    extra = [(c[0] + STOCKING_BACK * bx, c[1] + STOCKING_BACK * by)]
    return basekit.outline_points(holes, HOLE_FLAT, list(centers.values()) + extra, COG_R)


def build_base(holes):
    """11mm 实心底座 + 刻字；背靠背，两个名字各自朝着自己的正面。"""
    outline = outline_points(holes)
    depths = {k: PEGS[k][1] + EXTRA_DEPTH for k in PEGS}
    body = basekit.build_base(holes, HOLE_FLAT, depths, outline, T=BASE_T, margin=MARGIN)
    circles = [(holes[k], HOLE_FLAT[k] / math.sqrt(3) + CHAMFER + 1.5) for k in holes]
    bx, by = back_dir()
    front = {"Stocking": (-bx, -by), "Panty": (bx, by)}
    centers = orig_centers(holes)
    for g, text in LABELS.items():
        body, _ = basekit.add_labels(body, [(text, centers[g])], basekit.right_angle([front[g]]),
                                     outline, circles, top=BASE_T)
    return body


def preview(holes, body):
    import base_preview
    groups = {"Stocking": ("#c2185b", ["S1", "S2", "S3"]), "Panty": ("#b8860b", ["P1", "P2"])}
    bx, by = back_dir()
    cs = {g: (*c, COG_R) for g, c in orig_centers(holes).items()}
    fr = {"Stocking": (orig_centers(holes)["Stocking"], (-bx, -by)), "Panty": (orig_centers(holes)["Panty"], (bx, by))}
    base_preview.base_svg(HERE / "images" / "preview.svg", body, holes, HOLE_FLAT, groups, cs, fr, T=BASE_T)


if __name__ == "__main__":
    holes, res = solve_layout()
    print("跨手办距离残差:", [round(float(r), 2) for r in res])
    body = build_base(holes)
    setkit.export(HERE, {"base": basekit.fit_on_bed(body)[0]})
    if setkit.want_preview():
        preview(holes, body)
