"""【推しの子】 露比 × 爱 × 阿库亚 × 有马加奈 合体底座（商品名待补，确定后挪到对应系列文件夹）

孔位编号（见 docs/hole-labels.svg，IMG_5188 俯拍）：
  R = 露比 Ruby：R1 前桩、R2 后桩（同一只鞋）
  A = 爱 Ai：A1 前桩、A2 后桩（同一只靴子；另一只踮脚，没有钉）
  Q = 阿库亚 Aqua：Q1 前桩、Q2 后桩（同一只鞋）
  K = 有马加奈 Kana：K1、K2 在同一只鞋上，鞋嵌在原厂底座的鞋形凹槽里（深 2mm）；
      K3 是另一只脚抬起的鞋跟下的金属柱
原厂底座：爱 Ø≈98，其余三个 Ø≈64（照片估，按孔距标定比例）。

第一步：验证垫块 + 孔径档位条（python figure_base.py --trial）
  垫块的孔按实测钉径 100% 开；粗细接近的钉合用一根档位条，每根钉都有自己的 96 / 98 / 100 / 102 / 104% 五档
"""
import math
import sys
from pathlib import Path

import cadquery as cq

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import basekit  # noqa: E402
import fit_samples as fs  # noqa: E402

# ---------------------------------------------------------------- 实测数据
# 脚底的钉：(直径, 露出长度) mm；长度每个手办量最长的那根。K1、K2 的长度从鞋底量
PEGS = {
    "R1": (5.05, 6.8), "R2": (4.17, 6.8),
    "A1": (4.15, 7.2), "A2": (3.65, 7.2),
    "Q1": (5.15, 7.0), "Q2": (3.85, 7.0),
    "K1": (3.85, 5.0), "K2": (3.88, 5.0), "K3": (2.46, 6.6),   # K3 是金属柱
}
# 两根钉圆周上的最远距离（直接量在钉上）：中心距 = 最远距离 - r1 - r2
FAR = {("R1", "R2"): 17.25, ("A1", "A2"): 11.2, ("Q1", "Q2"): 16.12,
       ("K1", "K2"): 13.84, ("K1", "K3"): 17.35, ("K2", "K3"): 12.4}
# 加奈的鞋：长 21.55，鞋头宽 8.3（K2 那头），鞋跟宽 6.2（K1 那头），嵌入原厂凹槽 2mm
SHOE = {"len": 21.55, "toe_w": 8.3, "heel_w": 6.2, "depth": 2.0,
        "heel_back": 5.4}   # 鞋跟尖在 K1 后面多远（IMG_5188 估，鞋头尖在 K2 前 21.55 - 5.4 - K1K2）
SHOE_GROW = 0.4             # 凹槽轮廓每边放大（前几套鞋跟凹槽的经验 0.3～0.5）
# K3 在 K1→K2 的左手边（IMG_5188 俯拍定的，距离解不出镜像）
K3_SIDE = +1
# 原厂底座中心（IMG_5188 估）：(起点, 终点, 沿连线, 往右)，正式底座包重心用
ORIG_CENTER = {"Ruby": ("R1", "R2", 6.5, 5.0), "Ai": ("A1", "A2", 7.5, -26.0),
               "Aqua": ("Q1", "Q2", 5.1, -5.5), "Kana": ("K1", "K2", 12.5, -4.0)}

# ---------------------------------------------------------------- 打印参数
PAD_FLAT = {k: d for k, (d, _) in PEGS.items()}   # 验证垫块 v1：孔 = 实测钉径（量摆位距离时换算也用它）
EXTRA_DEPTH = 1.5   # 孔比钉长多挖的深度
CHAMFER = 0.4       # 孔口倒角
PAD_T = 11.0        # 垫块厚度（和正式底座一样）
PAD_WALL = 2.2      # 垫块在孔外留的壁厚
assert PAD_T - SHOE["depth"] - PEGS["K1"][1] - EXTRA_DEPTH >= 1.0, "孔底太薄"
assert PAD_T - max(L for _, L in PEGS.values()) - EXTRA_DEPTH >= 1.0, "孔底太薄"

# ---------------------------------------------------------------- 试装结果（验证垫块 + 档位条 v1）
# 垫块基本都合适；孔径按档位条选（对边距，mm）
HOLE_FLAT = {"R1": 5.06, "R2": 4.17, "A1": 4.17, "A2": 3.56, "Q1": 5.16, "Q2": 3.86,
             "K1": 3.88, "K2": 3.88, "K3": 2.51}
# 正式底座 v1 打印后：阿库亚的两根钉注塑得不完全平行（会往外撇或往里收），孔偏松时最后一点会自己弹出来
# → 两个孔再细 1%
HOLE_FLAT.update({"Q1": 5.11, "Q2": 3.82})
SPACING_ADJ = {("R1", "R2"): +0.1}                  # R1–R2 间距再拉大 0.1
# 加奈右脚的鞋形凹槽：前左（大脚趾方向）再扩 0.15，后右再扩 0.1。
# K 坐标系里 +X = 鞋跟→鞋头，+Y = 这只脚的左边（K3 是左脚，正好在 +Y）
SHOE_EXTRA = {"toe_left": 0.15, "heel_right": 0.10}

OUT = Path(__file__).parent / "out"


def center_dist(a, b, final=True):
    """组内中心距；final=False 是验证垫块 v1 用的（没有后来的间距微调）。"""
    far = FAR.get((a, b)) or FAR[(b, a)]
    adj = (SPACING_ADJ.get((a, b)) or SPACING_ADJ.get((b, a)) or 0.0) if final else 0.0
    return far - (PEGS[a][0] + PEGS[b][0]) / 2 + adj


def hole_flat(name, final=True):
    """final=True 正式孔径；"pad2" 垫块 v2 打印时的孔径；False 垫块 v1（实测钉径）。"""
    return (HOLE_FLAT if final is True else PAD2_FLAT if final == "pad2" else PAD_FLAT)[name]


def kana_frame():
    """加奈的三个孔：K1 原点，K2 在 +X，K3 按三边距离算（左手边 = +Y）。"""
    d12, d13, d23 = center_dist("K1", "K2"), center_dist("K1", "K3"), center_dist("K2", "K3")
    x3 = (d13 ** 2 - d23 ** 2 + d12 ** 2) / (2 * d12)
    return {"K1": (0.0, 0.0), "K2": (d12, 0.0), "K3": (x3, K3_SIDE * math.sqrt(d13 ** 2 - x3 ** 2))}


def shoe_outline(k, grow=SHOE_GROW, final=True):
    """加奈鞋形凹槽：鞋跟圆和鞋头圆的外包络（沿 K1→K2），每边放大 grow；
    final 时再把鞋头圆往前左、鞋跟圆往后右各挪一点包进去（SHOE_EXTRA）。"""
    hr, tr = SHOE["heel_w"] / 2 + grow, SHOE["toe_w"] / 2 + grow
    heel_tip = -SHOE["heel_back"] - grow
    toe_tip = -SHOE["heel_back"] + SHOE["len"] + grow
    hc, tc = heel_tip + hr, toe_tip - tr
    circles = basekit.circle_pts((hc, 0), hr, 48) + basekit.circle_pts((tc, 0), tr, 48)
    if final:
        e, f = SHOE_EXTRA["toe_left"] / math.sqrt(2), SHOE_EXTRA["heel_right"] / math.sqrt(2)
        circles += basekit.circle_pts((tc + e, e), tr, 48) + basekit.circle_pts((hc - f, -f), hr, 48)
    pts = basekit.convex_hull(circles)
    ax, ay = k["K1"]
    return [(ax + x, ay + y) for x, y in pts]


# ---------------------------------------------------------------- 第一步：验证垫块
def peg_hole(body, name, x, y, top, final=True):
    return basekit.cut_hex(body, x, y, hole_flat(name, final), PEGS[name][1] + EXTRA_DEPTH, top, CHAMFER)


def engrave(body, text, x, y, size=4.5, depth=0.6, top=PAD_T):
    t = basekit.text_solid(text, size, depth + 0.1)
    bb = t.val().BoundingBox()
    return body.cut(t.translate((x - bb.center.x, y - bb.center.y, top - depth)))


def pad(front, back, label, final=False):
    """两根钉在同一只鞋上：前桩在 -X、后桩在 +X，后桩外侧多留一截刻字。final=False 是打印过的 v1。"""
    s = center_dist(front, back, final)
    r = max(hole_flat(k, final) / math.sqrt(3) for k in (front, back)) + CHAMFER + PAD_WALL
    tail = 7.0
    length = s + 2 * r + tail
    body = cq.Workplane("XY").center(-s / 2 - r + length / 2, 0).slot2D(length, 2 * r).extrude(PAD_T)
    body = peg_hole(body, front, -s / 2, 0, PAD_T, final)
    body = peg_hole(body, back, s / 2, 0, PAD_T, final)
    return engrave(body, label, s / 2 + r + tail / 2 - 1.0, 0)


def pad_kana(final=False):
    """加奈：鞋形凹槽（深 2mm，K1、K2 从槽底往下开）+ K3，外面留 PAD_WALL；在 K3 对面刻 K。"""
    k = kana_frame()
    groove = shoe_outline(k, final=final)
    ring = basekit.convex_hull(
        [(x, y) for x, y in basekit.convex_hull(groove)]
        + basekit.circle_pts(k["K3"], hole_flat("K3", final) / math.sqrt(3) + CHAMFER, 24))
    # 外轮廓 = 凹槽 + K3 外扩 PAD_WALL，再在凹槽另一侧加一块刻字的地方
    label_at = (k["K2"][0] / 2, -(SHOE["toe_w"] / 2 + SHOE_GROW + PAD_WALL + 3.5))
    outer = basekit.convex_hull(
        [p for q in ring for p in basekit.circle_pts(q, PAD_WALL, 12)]
        + basekit.circle_pts(label_at, 4.0, 16))
    body = cq.Workplane("XY").polyline(outer).close().extrude(PAD_T)
    groove_top = PAD_T - SHOE["depth"]
    body = body.cut(cq.Workplane("XY").workplane(offset=groove_top).polyline(groove).close().extrude(SHOE["depth"] + 1))
    for n in ("K1", "K2"):
        body = basekit.cut_hex(body, *k[n], hole_flat(n, final), PEGS[n][1] + EXTRA_DEPTH, groove_top, CHAMFER)
    body = peg_hole(body, "K3", *k["K3"], PAD_T, final)
    return engrave(body, "K", *label_at)


TRIAL_LAYOUT = {"R": (-24, 22), "A": (24, 22), "Q": (-24, 0), "K": (22, -2)}


def build_trial(final=False):
    """验证垫块：final=False 是打印过的 v1（孔 = 实测钉径），True 是按试装结果改过的（v2）。"""
    parts = {"R": pad("R1", "R2", "R", final), "A": pad("A1", "A2", "A", final),
             "Q": pad("Q1", "Q2", "Q", final), "K": pad_kana(final)}
    moved = [p.translate((*TRIAL_LAYOUT[k], 0)).val() for k, p in parts.items()]
    return parts, cq.Workplane().add(cq.Compound.makeCompound(moved))


# 粗细接近的钉合用一根档位条（每根钉都能在条上找到自己的 96～104%），侧面刻对边距 x100
GAUGES = [("A2", "Q2", "K1", "K2"), ("R2", "A1"), ("R1", "Q1"), ("K3",)]


def gauge_map():
    """每根钉的 96～104% 落在哪个孔（刻字）。"""
    out = {}
    for pegs in GAUGES:
        flats = fs.shared_flats([PEGS[k][0] for k in pegs])
        for k in pegs:
            out[k] = [fs.size_tag(min(flats, key=lambda f: abs(f - PEGS[k][0] * g / 100))) for g in fs.GRADES]
    return out


def build_gauges():
    bars = [fs.gauge_bar(fs.shared_flats([PEGS[k][0] for k in pegs]), max(PEGS[k][1] for k in pegs))
            for pegs in GAUGES]
    return fs.grid(bars, 1, (0.0, 14.0))


# ---------------------------------------------------------------- 第二步：摆位 + 底座
# 垫块 v2 上量的跨手办近边距（孔边到孔边），中心距 = 近边距 + 两孔外接圆半径（宁远勿近）
LAYOUT_GAPS = {
    ("Q1", "K1"): 30.0, ("Q1", "K2"): 34.6, ("Q2", "K1"): 19.3, ("Q2", "K2"): 24.7, ("Q1", "K3"): 43.6,
    ("A1", "Q1"): 48.0, ("A1", "Q2"): 53.0, ("A2", "Q1"): 51.5, ("A2", "Q2"): 55.5, ("A1", "K1"): 67.5,
    ("R1", "A1"): 77.4, ("R1", "A2"): 81.9, ("R2", "A1"): 77.0, ("R2", "A2"): 80.4, ("R1", "Q1"): 116.7,
}
# 垫块 v2（量摆位距离用的）上的孔径，换算中心距用；后来正式底座改孔径不影响它
PAD2_FLAT = {"R1": 5.06, "R2": 4.17, "A1": 4.17, "A2": 3.56, "Q1": 5.16, "Q2": 3.86,
             "K1": 3.88, "K2": 3.88, "K3": 2.51}
GROUPS = {"Ruby": ("R1", "R2"), "Ai": ("A1", "A2"), "Aqua": ("Q1", "Q2"), "Kana": ("K1", "K2", "K3")}
ORDER = ["Ruby", "Ai", "Aqua", "Kana"]      # 正面看从左到右
CHAIN = ["Kana", "Aqua", "Ai", "Ruby"]      # 加奈固定，依次往外推（宁远勿近）
# 手办朝向 = 组内前两个孔连线方向逆时针转的角度（IMG_5188 俯拍，照片下方是正面），用来在镜像解里挑一个
FRONT = {"Ruby": ("R1", "R2", 149.3), "Ai": ("A1", "A2", -155.4),
         "Aqua": ("Q1", "Q2", -119.8), "Kana": ("K1", "K2", -44.2)}
RIB_CHAIN = ["R2", "R1", "A1", "A2", "Q2", "Q1", "K1", "K2", "K3"]   # 试摆底座的加强筋
LABELS = {"Ruby": "Ruby", "Ai": "Ai", "Aqua": "Aqua", "Kana": "Kana"}
BASE_T = 11.0
COG_R = 15.0
MARGIN = 10.0
# 整块 210 x 84 放不下 A1 mini：在爱和阿库亚中间切成两块（露比 + 爱 | 阿库亚 + 加奈），燕尾榫拼接
DOVETAIL = dict(neck=10.0, head=16.0, depth=7.0)   # 阿库亚那块伸出榫头插进爱那块
# 试摆 v1 两边各让 0.15（总间隙 0.3）松过头了：右块（榫头）还是 v1 的 0.15，左块（榫眼）改成反过来收 0.05，总间隙 0.1
TAB_SHRINK = 0.15
SOCKET_GROW = -0.05
COUPON_GAPS = (0.0, 0.2)                           # 另出两个小榫眼块对比（总间隙），拿 v1 右块的榫头试
# 试下来：总间隙 0 太紧，0.1 有一点点松 → 正式底座取 0.05，两边各让 0.025
FINAL_TAB, FINAL_SOCKET = 0.025, 0.025
SEAM_BAND = 5.0                                    # 试摆底座接缝附近加厚到这么高，榫头才有劲
# 爱的舞台：抬高 5mm（再高她的话筒 / 头发会碰到阿库亚抬起的手肘）。圆台要包住两只脚：
# 有钉的靴子（A1/A2）和踮脚的那只（没钉，按 IMG_5182 正面照估在原厂底座中心另一侧 22mm）
STAGE_H = 5.0
STAGE_PAD = 12.0                                   # 圆台边离两只脚的中心至少这么远
STAGE_LIP = 4.0                                    # 圆台外面底座至少再留这么宽
FREE_FOOT = {"Ai": ("A1", "A2", 10.7, -47.8)}      # 爱踮脚那只的落点（估），(起点, 终点, 沿连线, 往右)


def local_frames():
    out = {"Kana": kana_frame()}
    for g in ("Aqua", "Ai", "Ruby"):
        a, b = GROUPS[g]
        out[g] = {a: (0.0, 0.0), b: (center_dist(a, b), 0.0)}
    return out


def solve_layout():
    """返回 (holes, 拟合残差, 外推后残差, 外推距离, 候选数)。"""
    local = local_frames()
    calib = {k: f / math.sqrt(3) for k, f in PAD2_FLAT.items()}
    cands = basekit.solve_groups(local, LAYOUT_GAPS, calib, fixed="Kana")
    _, _, poses = basekit.pick_by_fronts(local, cands, FRONT)
    cd = {k: g + calib[k[0]] + calib[k[1]] for k, g in LAYOUT_GAPS.items()}
    resid = lambda P: {k: math.dist(P[k[0]], P[k[1]]) - d for k, d in cd.items()}  # noqa: E731
    r0 = resid(basekit.place_groups(local, poses))
    poses, push = basekit.push_chain(local, poses, CHAIN, LAYOUT_GAPS, calib)
    holes = basekit.place_groups(local, poses)
    return holes, r0, resid(holes), push, len(cands)


def fronts(holes):
    return {g: basekit.front_dir(holes, a, b, deg) for g, (a, b, deg) in FRONT.items()}


def orig_centers(holes):
    return {g: basekit.frame_point(holes, a, b, along, right) for g, (a, b, along, right) in ORIG_CENTER.items()}


def kana_recess(holes):
    """加奈鞋形凹槽在总坐标里的轮廓。"""
    k = kana_frame()
    (x1, y1), (x2, y2) = holes["K1"], holes["K2"]
    th = math.atan2(y2 - y1, x2 - x1)
    c, s = math.cos(th), math.sin(th)
    return [(x1 + c * x - s * y, y1 + s * x + c * y) for x, y in shoe_outline(k)]


def check(holes):
    f = fronts(holes)
    angs = {g: round(basekit.angle(v), 1) for g, v in f.items()}
    mx = sum(v[0] for v in f.values()) / len(f); my = sum(v[1] for v in f.values()) / len(f)
    right = (-my, mx)
    cen = {g: (sum(holes[k][0] for k in hs) / len(hs), sum(holes[k][1] for k in hs) / len(hs)) for g, hs in GROUPS.items()}
    order = sorted(cen, key=lambda g: cen[g][0] * right[0] + cen[g][1] * right[1])
    fwd = (mx, my)
    depth = {g: round(cen[g][0] * fwd[0] + cen[g][1] * fwd[1] - cen["Ai"][0] * fwd[0] - cen["Ai"][1] * fwd[1], 1)
             for g in cen}
    print("手办朝向（度）:", angs, " 正面看从左到右:", order, "一致" if order == ORDER else "不一致！")
    print("比爱靠前多少（mm）:", depth)
    return order == ORDER


def seam(holes):
    """接缝：过爱和阿库亚两组孔中心的中点，沿平均正面方向；返回 (点, 指向阿库亚那块的法向)。"""
    f = list(fronts(holes).values())
    mx, my = sum(v[0] for v in f) / len(f), sum(v[1] for v in f) / len(f)
    n = (-my / math.hypot(mx, my), mx / math.hypot(mx, my))
    ca = [sum(holes[k][i] for k in GROUPS["Ai"]) / 2 for i in (0, 1)]
    cb = [sum(holes[k][i] for k in GROUPS["Aqua"]) / 2 for i in (0, 1)]
    return ((ca[0] + cb[0]) / 2, (ca[1] + cb[1]) / 2), n


def stage(holes):
    """爱的圆台：(圆心, 半径, 踮脚落点)。圆心在有钉的靴子和踮脚那只中间，半径包住两只脚再留 STAGE_PAD。"""
    a, b, along, right = FREE_FOOT["Ai"]
    foot = basekit.frame_point(holes, a, b, along, right)
    pm = ((holes["A1"][0] + holes["A2"][0]) / 2, (holes["A1"][1] + holes["A2"][1]) / 2)
    c = ((pm[0] + foot[0]) / 2, (pm[1] + foot[1]) / 2)
    return c, math.dist(pm, foot) / 2 + STAGE_PAD, foot


def build_base(holes, thin=False, socket=SOCKET_GROW, tab=TAB_SHRINK):
    """返回 (露比 + 爱 那块, 阿库亚 + 加奈 那块)。"""
    flats = dict(HOLE_FLAT)
    recess = kana_recess(holes)
    groove_top = BASE_T - SHOE["depth"]
    sc, sr, foot = stage(holes)
    top_stage = BASE_T + STAGE_H
    tops = {"K1": groove_top, "K2": groove_top, "A1": top_stage, "A2": top_stage}
    depths = {k: PEGS[k][1] + EXTRA_DEPTH for k in PEGS}
    centers = orig_centers(holes)
    disc = basekit.circle_pts(sc, sr, 96)
    outline = basekit.convex_hull(basekit.outline_points(holes, flats, centers.values(), COG_R) + recess
                                  + basekit.circle_pts(sc, sr + STAGE_LIP - MARGIN, 96))
    body = basekit.build_base(holes, flats, depths, outline, T=BASE_T, margin=MARGIN, thin=thin,
                              chain=RIB_CHAIN, recesses=[(recess, SHOE["depth"])], hole_tops=tops,
                              platforms=[(disc, STAGE_H)])
    if thin:   # 试摆底座没有台面：在踮脚那只的落点立一根和台面一样高的桩，看脚落不落在上面
        body = body.union(cq.Workplane("XY").center(*foot).circle(8.0).extrude(top_stage))
    keep = 2.5 + 1.5 if thin else 1.5
    circles = [(holes[k], flats[k] / math.sqrt(3) + CHAMFER + keep) for k in holes]
    rx = sum(x for x, _ in recess) / len(recess); ry = sum(y for _, y in recess) / len(recess)
    circles.append(((rx, ry), max(math.dist((rx, ry), p) for p in recess) + keep))
    if thin:
        circles.append((foot, 8.0 + keep))
    segments = [((holes[p], holes[q]), 2.5) for p, q in zip(RIB_CHAIN, RIB_CHAIN[1:])] if thin else []
    sp, n = seam(holes)
    t = (-n[1], n[0])
    segments.append((((sp[0] - 300 * t[0], sp[1] - 300 * t[1]), (sp[0] + 300 * t[0], sp[1] + 300 * t[1])),
                     DOVETAIL["depth"] + 3))
    ang = basekit.right_angle(list(fronts(holes).values()))
    if thin:
        body, _ = basekit.add_labels(body, [(LABELS[g], centers[g]) for g in LABELS], ang, outline,
                                     circles, segments, top=0.8, raised=True)
    else:      # 爱的名字刻在台面上，其余的刻在底座顶面、躲开圆台
        others = [(LABELS[g], centers[g]) for g in LABELS if g != "Ai"]
        body, _ = basekit.add_labels(body, others, ang, outline, circles + [(sc, sr + 1.5)], segments, top=BASE_T)
        body, _ = basekit.add_labels(body, [(LABELS["Ai"], centers["Ai"])], ang,
                                     basekit.circle_pts(sc, sr - 3, 96), circles, [], top=top_stage)
    lo, hi = basekit.seam_span(outline, sp, n, MARGIN)
    if thin:   # 接缝两边加厚，榫头才拼得住
        w = DOVETAIL["depth"] + 5
        pts = [(sp[0] + u * t[0] + v * n[0], sp[1] + u * t[1] + v * n[1]) for u, v in
               ((lo - 5, -w), (hi + 5, -w), (hi + 5, 5), (lo - 5, 5))]
        shape = cq.Workplane("XY").polyline(outline).close().offset2D(MARGIN).extrude(SEAM_BAND)
        body = body.union(shape.intersect(cq.Workplane("XY").polyline(pts).close().extrude(SEAM_BAND)))
        for k, (x, y) in holes.items():   # 加厚带不能把孔堵住
            body = basekit.cut_hex(body, x, y, flats[k], depths[k], tops.get(k, BASE_T), chamfer=0)
    # 榫头位置按不带圆台的轮廓定（和已经打印的 v1 右块对得上）
    lo1, hi1 = basekit.seam_span(basekit.convex_hull(basekit.outline_points(holes, flats, centers.values(), COG_R) + recess),
                                 sp, n, MARGIN)
    region = basekit.dovetail_region(sp, n, (lo1 + hi1) / 2, **DOVETAIL)
    return basekit.split_dovetail(body, region, BASE_T, socket=socket, tab=tab)


def dovetail_coupon(total_gap, h=SEAM_BAND):
    """小榫眼块：拿右块的榫头试松紧；顶上刻总间隙 x100。"""
    region = basekit.dovetail_region((0, 0), (0, 1), 0.0, **DOVETAIL)
    w, d = DOVETAIL["head"] + 10, DOVETAIL["depth"] + 8
    block = cq.Workplane("XY").center(0, -d / 2).rect(w, d).extrude(h)
    sock = total_gap - TAB_SHRINK
    block = block.cut(cq.Workplane("XY").workplane(offset=-1).polyline(region).close().offset2D(sock).extrude(h + 2))
    txt = basekit.text_solid(f"{total_gap * 100:.0f}", 4.0, 0.7)
    bb = txt.val().BoundingBox()
    return block.cut(txt.translate((-bb.center.x, -d + 4 - bb.center.y, h - 0.6)))


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for (a, b) in FAR:
        print(f"{a}-{b} 中心距 {center_dist(a, b):.2f} mm")
    print("加奈孔位:", {n: (round(x, 2), round(y, 2)) for n, (x, y) in kana_frame().items()})
    print("档位条（96 / 98 / 100 / 102 / 104% 对应的孔）:")
    for k, tags in gauge_map().items():
        print(f"  {k}: {' '.join(tags)}")
    if "--pads" in sys.argv:    # 按试装结果更新的垫块（v2），用来摆位置量距离
        _, pads = build_trial(final="pad2")
        cq.exporters.export(pads, str(OUT / "trial_v2_pads.stl"), tolerance=0.01, angularTolerance=0.1)
        print("已输出", OUT / "trial_v2_pads.stl")
    if "--layout" in sys.argv:  # 第二步：解摆位，出正式底座和试摆底座
        holes, r0, r1, push, n = solve_layout()
        print(f"候选解 {n} 个；拟合残差:", {f"{a}-{b}": round(v, 2) for (a, b), v in r0.items()})
        print("外推:", {g: round(v, 2) for g, v in push.items()}, " 外推后残差:", {f"{a}-{b}": round(v, 2) for (a, b), v in r1.items()})
        for k, (x, y) in holes.items():
            print(f"  {k}: ({x:7.2f}, {y:7.2f})")
        check(holes)
        sc, sr, foot = stage(holes)
        print(f"爱的圆台：半径 {sr:.1f}，高 {STAGE_H}；踮脚落点 ({foot[0]:.1f}, {foot[1]:.1f})")
        for name, thin in (("base", False), ("test_base_thin", True)):
            gaps = {} if thin else {"socket": FINAL_SOCKET, "tab": FINAL_TAB}
            for part, piece in zip(("ruby-ai", "aqua-kana"), build_base(holes, thin=thin, **gaps)):
                body, deg, w, h = basekit.fit_on_bed(piece)
                fn = f"{name}_{part}" + ("_v2" if thin else "")
                print(f"{fn}：{w:.1f} x {h:.1f} mm，旋转 {deg} 度，A1 mini {'放得下' if max(w, h) <= 176 else '放不下！'}")
                cq.exporters.export(body, str(OUT / f"{fn}.stl"), tolerance=0.01, angularTolerance=0.1)
                if not thin:
                    cq.exporters.export(body, str(OUT / f"{fn}.step"))
        coupons = [dovetail_coupon(g).translate((i * 32.0, 0, 0)).val() for i, g in enumerate(COUPON_GAPS)]
        cq.exporters.export(cq.Workplane().add(cq.Compound.makeCompound(coupons)),
                            str(OUT / "dovetail_coupons_v2.stl"), tolerance=0.01, angularTolerance=0.1)
    if "--trial" in sys.argv:
        _, pads = build_trial()
        for name, wp in (("trial_v1_pads", pads), ("trial_v1_gauges", build_gauges())):
            cq.exporters.export(wp, str(OUT / f"{name}.stl"), tolerance=0.01, angularTolerance=0.1)
            bb = wp.val().BoundingBox()
            print(f"已输出 {OUT / (name + '.stl')}  {bb.xlen:.0f} x {bb.ylen:.0f} x {bb.zlen:.1f} mm")
