"""合体底座的通用工具：两组孔的摆放求解、朝向核对、外轮廓、底座建模、上平台。

各套底座的 base.py 只放实测数据和参数，调用这里的函数。
坐标约定：俯视，A 组第一个孔为原点，第二个孔在 +X，+Y 是从 a1 看向 a2 的左手边。
"""
import math

import cadquery as cq
import numpy as np


# ---------------------------------------------------------------- 几何小工具
def rot(v, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return (c * v[0] - s * v[1], s * v[0] + c * v[1])


def unit(p, q):
    d = math.dist(p, q)
    return ((q[0] - p[0]) / d, (q[1] - p[1]) / d)


def angle(v):
    return math.degrees(math.atan2(v[1], v[0]))


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


# ---------------------------------------------------------------- 摆放求解
def solve_two_pairs(a, b, intra, gaps, calib_r, side=+1, weight=None, push_step=0.05):
    """两组各两个孔：A 组 a1 原点、a2 在 +X；B 组 (b1, b2) 作为刚体，用跨组距离最小二乘求位置。

    intra：组内中心距 {(a1, a2): d, (b1, b2): d}
    gaps：跨组近边距（六边形孔边到孔边），中心距 = 近边距 + calib_r[i] + calib_r[j]
    side：+1 = B 组在 a1→a2 的左手边（两组各两个孔时距离解不出镜像，要另外定）
    weight：不太可信的距离给小于 1 的权重（例如超出卡尺量程的）
    宁远勿近：拟合后如果有权重为 1 的距离比实测短，把 B 组沿两组中心连线往外推到都不短。
    返回 (holes, 拟合残差, 外推后残差, 外推距离)。
    """
    a1, a2 = a
    b1, b2 = b
    dA, dB = intra[a], intra[b]
    cd = {k: g + calib_r[k[0]] + calib_r[k[1]] for k, g in gaps.items()}
    w = np.array([(weight or {}).get(k, 1.0) for k in cd])
    A = {a1: np.zeros(2), a2: np.array([dA, 0.0])}

    def place(x):
        p = x[:2]
        return {b1: p, b2: p + dB * np.array([math.cos(x[2]), math.sin(x[2])])}

    def res(x):
        P = {**A, **place(x)}
        return np.array([np.linalg.norm(P[i] - P[j]) - d for (i, j), d in cd.items()])

    best = None
    span = max(cd.values())
    for gx in np.linspace(-span, span + dA, 15):
        for ang in np.linspace(0, 2 * math.pi, 12, endpoint=False):
            x = np.array([gx, side * span / 3, ang])
            for _ in range(60):
                r = res(x) * np.sqrt(w)
                J = np.column_stack([(res(x + e) - res(x)) / 1e-7 for e in np.eye(3) * 1e-7]) * np.sqrt(w)[:, None]
                x = x + np.linalg.lstsq(J, -r, rcond=None)[0]
            P = place(x)
            c = (P[b1] + P[b2]) / 2
            if np.sign(c[1]) != side:
                continue
            cost = float((res(x) ** 2 * w).sum())
            if best is None or cost < best[0] - 1e-9:
                best = (cost, x.copy())
    x = best[1]
    r0 = res(x)
    P = place(x)
    u = (P[b1] + P[b2]) / 2 - (A[a1] + A[a2]) / 2
    u = u / np.linalg.norm(u)
    push = 0.0
    while True:
        r1 = res(np.array([*(x[:2] + push * u), x[2]]))
        if all(v >= -0.02 for v, wk in zip(r1, w) if wk >= 1.0) or push > 20:
            break
        push += push_step
    P = place(np.array([*(x[:2] + push * u), x[2]]))
    holes = {k: (float(v[0]), float(v[1])) for k, v in {**A, **P}.items()}
    return holes, r0, r1, push


def place_groups(local, poses):
    """local = {组: {孔: 局部坐标}}，poses = {组: (tx, ty, 转角弧度)}；没给 pose 的组原样放。"""
    out = {}
    for g, hs in local.items():
        tx, ty, th = poses.get(g, (0.0, 0.0, 0.0))
        c, s = math.cos(th), math.sin(th)
        for k, (x, y) in hs.items():
            out[k] = (tx + c * x - s * y, ty + s * x + c * y)
    return out


def solve_groups(local, gaps, calib_r, fixed, weight=None, starts=300, seed=0):
    """多组孔一起求：fixed 组不动，其余每组 (平移, 转角) 用跨组距离最小二乘（多起点 LM）。
    gaps：跨组近边距，中心距 = 近边距 + calib_r[i] + calib_r[j]。
    两个孔的组可能有镜像解（距离分不出来），所以返回去重后的候选 [(加权残差平方和, poses)]，按残差排序，
    再用 pick_by_fronts 挑。"""
    free = [g for g in local if g != fixed]
    cd = {k: g + calib_r[k[0]] + calib_r[k[1]] for k, g in gaps.items()}
    keys = list(cd)
    w = np.array([(weight or {}).get(k, 1.0) for k in keys])

    def poses_of(p):
        return {g: tuple(p[3 * i:3 * i + 3]) for i, g in enumerate(free)}

    def res(p):
        P = place_groups(local, poses_of(p))
        return np.array([math.dist(P[a], P[b]) - cd[(a, b)] for a, b in keys])

    def lm(p):
        lam = 1e-2
        for _ in range(200):
            f = res(p) * np.sqrt(w)
            J = np.column_stack([(res(p + e) * np.sqrt(w) - f) / 1e-6 for e in np.eye(len(p)) * 1e-6])
            A, g = J.T @ J, J.T @ f
            step = np.linalg.solve(A + lam * np.diag(np.diag(A) + 1e-9), -g)
            if np.sum((res(p + step) ** 2) * w) < np.sum(f ** 2):
                p, lam = p + step, lam * 0.3
            else:
                lam *= 10
            if np.linalg.norm(step) < 1e-10:
                break
        return p

    span = max(cd.values()) * 1.5
    rng = np.random.default_rng(seed)
    found = []
    for _ in range(starts):
        p0 = np.concatenate([[rng.uniform(-span, span), rng.uniform(-span, span), rng.uniform(-math.pi, math.pi)]
                             for _ in free])
        p = lm(p0)
        sse = float(np.sum(res(p) ** 2 * w))
        P = place_groups(local, poses_of(p))
        if any(all(math.dist(P[k], Q[k]) < 0.5 for k in P) for _, _, Q in found):
            continue
        found.append((sse, poses_of(p), P))
    found.sort(key=lambda t: t[0])
    return [(sse, poses) for sse, poses, _ in found]


def fronts_spread(holes, fronts):
    """各手办朝向的离散程度（1 - 平均单位向量的长度），0 = 完全一致。"""
    v = [front_dir(holes, a, b, deg) for a, b, deg in fronts.values()]
    mx, my = sum(x for x, _ in v) / len(v), sum(y for _, y in v) / len(v)
    return 1 - math.hypot(mx, my)


def pick_by_fronts(local, candidates, fronts, sse_factor=4.0):
    """镜像解里挑一个：残差不超过最好解 sse_factor 倍的候选中，选各手办朝向最一致的。"""
    best = candidates[0][0]
    ok = [(fronts_spread(place_groups(local, p), fronts), sse, p) for sse, p in candidates
          if sse <= max(best * sse_factor, best + 0.5)]
    return min(ok, key=lambda t: t[0])


def push_chain(local, poses, chain, gaps, calib_r, weight=None, step=0.05, tol=-0.02):
    """宁远勿近（多组）：沿 chain 从固定组开始，逐个切开 chain[:i] | chain[i:]，
    跨这道切口的距离（权重 1）有比实测短的，就把 chain[i:] 整体沿两组中心连线往外推，直到都不短。
    返回 (poses, {组: 外推距离})。"""
    cd = {k: g + calib_r[k[0]] + calib_r[k[1]] for k, g in gaps.items()}
    poses = dict(poses)
    pushes = {}
    for i in range(1, len(chain)):
        left, right = set(chain[:i]), set(chain[i:])
        gof = {k: g for g, hs in local.items() for k in hs}
        cut = [(a, b) for a, b in cd if (gof[a] in left) != (gof[b] in left) and (weight or {}).get((a, b), 1.0) >= 1.0]
        P = place_groups(local, poses)
        ca = np.mean([P[k] for k in local[chain[i - 1]]], axis=0)
        cb = np.mean([P[k] for k in local[chain[i]]], axis=0)
        u = (cb - ca) / np.linalg.norm(cb - ca)
        push = 0.0
        while push < 20:
            moved = {g: (p[0] + push * u[0], p[1] + push * u[1], p[2]) if g in right else p for g, p in poses.items()}
            P = place_groups(local, moved)
            if all(math.dist(P[a], P[b]) - cd[(a, b)] >= tol for a, b in cut):
                break
            push += step
        poses, pushes[chain[i]] = moved, push
    return poses, pushes


def frame_point(holes, a, b, along, right):
    """以 a→b 为轴：沿轴 along、往右 right 的点。"""
    u = unit(holes[a], holes[b])
    return (holes[a][0] + along * u[0] + right * u[1], holes[a][1] + along * u[1] - right * u[0])


def front_dir(holes, a, b, deg):
    """手办朝向（正面方向）= a→b 方向逆时针转 deg 度（deg 来自原厂底座俯拍照片）。"""
    return rot(unit(holes[a], holes[b]), deg)


def right_angle(fronts):
    """站在正面看时"往右"的方向角（度）；文字沿这个方向排，正面看就是正的。"""
    fx = sum(f[0] for f in fronts) / len(fronts)
    fy = sum(f[1] for f in fronts) / len(fronts)
    return angle((-fy, fx))


def left_to_right(holes, fronts):
    """站在正面看，孔从左到右的顺序（正面方向取各手办朝向的平均）。"""
    fx = sum(f[0] for f in fronts) / len(fronts)
    fy = sum(f[1] for f in fronts) / len(fronts)
    right = (-fy, fx)            # 观众朝 -front 看，右手边 = front 逆时针转 90°（front 朝下时右手边是 +X）
    return sorted(holes, key=lambda k: holes[k][0] * right[0] + holes[k][1] * right[1])


# ---------------------------------------------------------------- 建模
def cut_hex(body, x, y, flat, depth, top, chamfer=0.4):
    """在顶面 (x, y) 开对边距为 flat 的六边形盲孔，孔口倒角。"""
    r = flat / math.sqrt(3)
    hole = (cq.Workplane("XY").workplane(offset=top - depth)
            .center(x, y).polygon(6, 2 * r).extrude(depth + 1))
    body = body.cut(hole)
    if not chamfer:
        return body
    # 按整条边的包围盒选（不是按边的重心），避免选到旁边桩的圆弧外圈
    box = cq.selectors.BoxSelector((x - r - 0.2, y - r - 0.2, top - 0.01),
                                   (x + r + 0.2, y + r + 0.2, top + 0.01), boundingbox=True)
    return body.edges(box).chamfer(chamfer)


def outline_points(holes, flats, centers, cog_r=15.0, chamfer=0.4):
    """外轮廓 = 所有孔 + 每个原厂底座中心周围 cog_r 的圆，取凸包（之后再 offset 留边）。"""
    pts = [p for k, c in holes.items() for p in circle_pts(c, flats[k] / math.sqrt(3) + chamfer)]
    for c in centers:
        pts += circle_pts(c, cog_r)
    return convex_hull(pts)


def build_base(holes, flats, depths, outline, T=11.0, margin=10.0, top_chamfer=1.0, chamfer=0.4,
               thin=False, plate=0.8, post_wall=2.5, rib=(2.0, 5.0), chain=None, recesses=(), hole_tops=None,
               platforms=()):
    """正式底座：T 厚实心 + 顶边倒角；thin=True：试摆底座（薄底板 + 每孔一个桩 + chain 上的加强筋）。
    recesses = [(轮廓点, 深度)]：鞋形之类的凹槽（试摆底座上给它加一圈桩）；
    hole_tops = {孔: 孔口高度}：凹槽里的孔从槽底往下开、舞台上的孔从台面往下开，depths 从孔口算；
    platforms = [(轮廓点, 高度)]：在顶面上再垫高的舞台（正式底座才有，顶边倒角 0.8；试摆底座只把桩加高）。"""
    tops = hole_tops or {}
    shape = cq.Workplane("XY").polyline(outline).close().offset2D(margin)
    if thin:
        body = shape.extrude(plate)
        for k, (x, y) in holes.items():
            r = flats[k] / math.sqrt(3) + chamfer + post_wall
            body = body.union(cq.Workplane("XY").center(x, y).circle(r).extrude(max(T, tops.get(k, T))))
        for p, q in zip(chain or [], (chain or [])[1:]):
            (x0, y0), (x1, y1) = holes[p], holes[q]
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            bar = (cq.Workplane("XY").workplane(offset=plate - 0.01).center(cx, cy)
                   .rect(math.dist(holes[p], holes[q]), rib[0]).extrude(rib[1] + 0.01)
                   .rotate((cx, cy, 0), (cx, cy, 1), math.degrees(math.atan2(y1 - y0, x1 - x0))))
            body = body.union(bar)
        for poly, _ in recesses:
            body = body.union(cq.Workplane("XY").polyline(poly).close().offset2D(post_wall).extrude(T))
    else:
        body = shape.extrude(T)
        if top_chamfer:
            body = body.faces(">Z").chamfer(top_chamfer)
        for poly, h in platforms:
            st = cq.Workplane("XY").workplane(offset=T - 0.01).polyline(poly).close().extrude(h - 0.79)
            st = st.union(cq.Workplane("XY").workplane(offset=T + h - 0.8).polyline(poly).close().extrude(0.8, taper=45))
            body = body.union(st)
    for poly, depth in recesses:
        body = body.cut(cq.Workplane("XY").workplane(offset=T - depth).polyline(poly).close().extrude(depth + 1))
    for k, (x, y) in holes.items():
        body = cut_hex(body, x, y, flats[k], depths[k], tops.get(k, T), chamfer)
    return body


def dovetail_region(p, n, u0, neck=10.0, head=16.0, depth=7.0, L=400.0):
    """分块用的平面区域（右边那块）：过点 p、法向 n（指向右块）的直线右侧，
    再加一个伸进左块的燕尾榫头，榫头中心在接缝上 u0 处。返回多边形点。"""
    nx, ny = n
    tx, ty = -ny, nx
    uv = [(-L, 0), (u0 - neck / 2, 0), (u0 - head / 2, -depth), (u0 + head / 2, -depth), (u0 + neck / 2, 0),
          (L, 0), (L, L), (-L, L)]
    return [(p[0] + u * tx + v * nx, p[1] + u * ty + v * ny) for u, v in uv]


def split_dovetail(body, region, T, gap=0.3, socket=None, tab=None):
    """按 dovetail_region 把底座切成两块，接缝两边各留 gap/2 间隙；
    也可以分别给：socket = 左块（榫眼）往外让多少，tab = 右块（榫头）往里缩多少，总间隙 = 两者之和。返回 (左块, 右块)。"""
    socket = gap / 2 if socket is None else socket
    tab = gap / 2 if tab is None else tab
    tool = lambda off: cq.Workplane("XY").workplane(offset=-1).polyline(region).close().offset2D(off).extrude(T + 60)  # noqa: E731
    return body.cut(tool(socket)), body.intersect(tool(-tab))


def seam_span(outline, p, n, margin=10.0):
    """接缝直线和底座外轮廓（凸包 + margin）相交的那一段，返回沿接缝的 (u 最小, u 最大)。"""
    nx, ny = n
    tx, ty = -ny, nx
    def seg_dist(q, a, b):
        ax, ay, bx, by = *a, *b
        L2 = (bx - ax) ** 2 + (by - ay) ** 2
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((q[0] - ax) * (bx - ax) + (q[1] - ay) * (by - ay)) / L2))
        return math.dist(q, (ax + t * (bx - ax), ay + t * (by - ay)))

    us = []
    for u in np.linspace(-300, 300, 3001):
        q = (p[0] + u * tx, p[1] + u * ty)
        if _inside(outline, q) or min(seg_dist(q, a, b) for a, b in zip(outline, outline[1:] + outline[:1])) <= margin:
            us.append(u)
    return min(us), max(us)


# ---------------------------------------------------------------- 文字标签
def text_solid(text, size, height, kind="bold"):
    return (cq.Workplane("XY").text(text, size, height, combine=False,
                                    halign="center", valign="center", kind=kind))


def _inside(poly, p):
    """点是否在凸多边形内（逆时针顶点）。"""
    n = len(poly)
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        if (x1 - x0) * (p[1] - y0) - (y1 - y0) * (p[0] - x0) < 0:
            return False
    return True


def place_label(text, size, c0, angle_deg, region, circles=(), segments=(), pad=1.5, reach=60.0):
    """从 c0 开始螺旋往外找一个位置，让文字（旋转 angle_deg）整块落在 region 凸多边形里，
    并且不碰 circles [(中心, 半径)] 和 segments [((p, q), 半宽)]。找不到返回 None。"""
    bb = text_solid(text, size, 1.0).val().BoundingBox()
    hw, hh = bb.xlen / 2 + pad, bb.ylen / 2 + pad
    ca, sa = math.cos(math.radians(angle_deg)), math.sin(math.radians(angle_deg))

    def to_local(p, c):
        dx, dy = p[0] - c[0], p[1] - c[1]
        return (ca * dx + sa * dy, -sa * dx + ca * dy)

    def ok(c):
        corners = [(c[0] + ca * x - sa * y, c[1] + sa * x + ca * y)
                   for x, y in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh))]
        if not all(_inside(region, q) for q in corners):
            return False
        for cc, r in circles:
            lx, ly = to_local(cc, c)
            dx, dy = max(abs(lx) - hw, 0), max(abs(ly) - hh, 0)
            if math.hypot(dx, dy) < r:
                return False
        for (p, q), hwid in segments:
            n = max(2, int(math.dist(p, q) / 0.5))
            for i in range(n + 1):
                s = (p[0] + (q[0] - p[0]) * i / n, p[1] + (q[1] - p[1]) * i / n)
                lx, ly = to_local(s, c)
                if abs(lx) < hw + hwid and abs(ly) < hh + hwid:
                    return False
        return True

    r = 0.0
    while r <= reach:
        steps = max(1, int(2 * math.pi * r / 1.0))
        for k in range(steps):
            a = 2 * math.pi * k / steps
            c = (c0[0] + r * math.cos(a), c0[1] + r * math.sin(a))
            if ok(c):
                return c
        r += 1.0
    return None


def add_labels(body, labels, angle_deg, region, circles=(), segments=(), size=5.0, top=11.0,
               depth=0.6, raised=False):
    """labels: [(文字, 起始位置)]。raised=False 刻进顶面 depth；raised=True 在 top 上凸起 depth。
    返回 (body, [(文字, 实际位置)])。"""
    placed = []
    for text, c0 in labels:
        c = place_label(text, size, c0, angle_deg, region, circles, segments)
        if c is None:
            raise RuntimeError(f"文字 {text!r} 找不到位置")
        t = text_solid(text, size, depth + 0.1)
        t = t.rotate((0, 0, 0), (0, 0, 1), angle_deg).translate((c[0], c[1], top - 0.1 if raised else top - depth))
        body = body.union(t) if raised else body.cut(t)
        placed.append((text, c))
    return body, placed


def fit_on_bed(body, bed=180.0, clearance=4.0):
    """放得下就不转；放不下找包围盒最小的角度。移到原点。返回 (body, 角度, 宽, 高)。"""
    bb = body.val().BoundingBox()
    if max(bb.xlen, bb.ylen) <= bed - clearance:
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
