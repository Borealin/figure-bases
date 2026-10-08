"""孔径试样：圆柱试样（一个档位一个）和公差条（同一组钉径接近时，一根条试几根钉）。

档位约定（见根目录 README 的"经验参数"）：
- 新手办第一波：以实测钉径为 100%，出 96 / 98 / 100 / 102 / 104% 五档，对比着试
- 试装后觉得松 / 紧：在试过的孔上 -2% / +2% 出试样，不要按毫米一步调满（0.3mm 一次调到位往往过头）
"""
import math

import cadquery as cq

import basekit

GRADES = (96, 98, 100, 102, 104)        # 第一波：实测钉径的百分比
NUDGE = 2                               # 松 / 紧：在试过的孔上调的百分比
FLOOR = 0.8                             # 孔底厚度（4 层）
EXTRA_DEPTH = 1.5                       # 孔比钉长多挖的深度（和底座一致）
CHAMFER = 0.4


def graded(d, pcts=GRADES):
    """{档位: 对边距}，按实测钉径的百分比。"""
    return {p: d * p / 100 for p in pcts}


def nudge(tried, sign, pct=NUDGE):
    """试过的孔 tried 松（sign < 0，往小调）或紧（sign > 0，往大调）pct%，只看 sign 的正负，返回 (刻字, 对边距)。"""
    sign = math.copysign(1, sign)
    return f"{'+' if sign > 0 else '-'}{pct:g}", tried * (1 + sign * pct / 100)


def tag(p):
    """档位刻字：102 → "102"，97.5 → "975"。"""
    return f"{p:g}".replace(".", "")


def _engrave_at(body, text, size, top, x, y, depth=0.5, below=False):
    """刻字，字的下沿（below=True 时是上沿）贴着 y。"""
    t = basekit.text_solid(text, size, depth + 0.1)
    bb = t.val().BoundingBox()
    dy = (y - bb.ymax) if below else (y - bb.ymin)
    return body.cut(t.translate((x - bb.center.x, dy, top - depth)))


def puck(flat, peg_len, name, grade, dia=20.0, flange=2.0, wall=1.6, size=4.5):
    """圆柱试样（帽子形）：中间一根圆管开六边形孔，底下一圈 flange 厚的圆盘，
    管上方刻钉名、下方刻档位。圆管壁 wall（4 道线）比底座孔周围还结实，松紧有代表性，又比实心圆柱省一半时间。"""
    depth = peg_len + EXTRA_DEPTH
    h = depth + FLOOR
    tube_r = flat / math.sqrt(3) + wall
    body = (cq.Workplane("XY").circle(dia / 2).extrude(flange)
            .union(cq.Workplane("XY").circle(tube_r).extrude(h)))
    body = basekit.cut_hex(body, 0, 0, flat, depth, h, CHAMFER)
    gap = tube_r + 0.6
    body = _engrave_at(body, name, size, flange, 0, gap)
    return _engrave_at(body, grade, size, flange, 0, -gap, below=True)


def strip(rows, grades, pitch=10.0, size=4.0):
    """公差条：rows = [(行刻字, {档位: 对边距}, 钉长)]，每列一个档位，列下方刻档位，行左端刻行名。"""
    n = len(grades)
    row_h = max(f for _, fl, _ in rows for f in fl.values()) + 2 * CHAMFER + 2.6
    w = pitch * n + 10
    hgt = row_h * len(rows) + size + 4
    T = max(L for _, _, L in rows) + EXTRA_DEPTH + FLOOR
    body = cq.Workplane("XY").rect(w, hgt).extrude(T).edges("|Z").fillet(3)
    y0 = hgt / 2 - 1.5 - row_h / 2
    for j, (label, flats, L) in enumerate(rows):
        y = y0 - j * row_h
        for i, g in enumerate(grades):
            x = (i - (n - 1) / 2) * pitch + 3.0
            body = basekit.cut_hex(body, x, y, flats[g], L + EXTRA_DEPTH, T, CHAMFER)
        body = _engrave_at(body, label, size, T, -w / 2 + 4, y - size * 0.36)
    yb = y0 - (len(rows) - 0.5) * row_h - 0.6
    for i, g in enumerate(grades):
        body = _engrave_at(body, tag(g), size * 0.8, T, (i - (n - 1) / 2) * pitch + 3.0, yb, below=True)
    return body


def _engrave_side(body, text, size, x, y_face, zc, depth=0.4):
    """在朝 -Y 的竖直侧面（y = y_face）刻字，从 -Y 方向看是正的。"""
    t = basekit.text_solid(text, size, depth + 0.1).rotate((0, 0, 0), (1, 0, 0), 90)
    bb = t.val().BoundingBox()
    return body.cut(t.translate((x - bb.center.x, y_face + depth - bb.ymax, zc - bb.center.z)))


def shared_flats(diams, grades=GRADES, tol=1.0):
    """几根粗细接近的钉合用一根档位条：各自的 grades 档放在一起，相差不到 tol%（半档）的合成一个孔。"""
    vals = sorted(d * g / 100 for d in diams for g in grades)
    groups = [[vals[0]]]
    for v in vals[1:]:
        (groups[-1] if v <= groups[-1][0] * (1 + tol / 100) else groups.append([v]) or groups[-1]).append(v)
    return [sum(g) / len(g) for g in groups]


def size_tag(f):
    """孔径刻字：对边距 x100，3.86 → "386"。"""
    return f"{f * 100:.0f}"


def gauge_bar(flats, peg_len, labels=None, name=None, pitch=9.0, wall=1.2, size=3.2, tab=10.0):
    """档位条：一排孔按 flats 依次排开，每个孔正对的侧面刻 labels（默认刻对边距 x100），
    有 name 时在一头加一块刻名字的把手。条做得窄：同一只鞋上的另一根钉离得近（7～14mm）时，
    把鞋横过来放，另一根钉垂在条外面，不会顶住（多行公差条就会顶住）。"""
    labels = labels or [size_tag(f) for f in flats]
    n = len(flats)
    w = 2 * (max(flats) / math.sqrt(3) + CHAMFER + wall)
    h = peg_len + EXTRA_DEPTH + FLOOR
    length = n * pitch
    body = cq.Workplane("XY").center(length / 2, 0).rect(length, w).extrude(h)
    if name:
        body = body.union(cq.Workplane("XY").center(-tab / 2, 0).rect(tab, max(w, 11.0)).extrude(h))
    for i, (f, t) in enumerate(zip(flats, labels)):
        x = (i + 0.5) * pitch
        body = basekit.cut_hex(body, x, 0, f, peg_len + EXTRA_DEPTH, h, CHAMFER)
        body = _engrave_side(body, t, size, x, -w / 2, h / 2)
    if name:
        t = basekit.text_solid(name, 4.0, 0.6)
        bb = t.val().BoundingBox()
        body = body.cut(t.translate((-tab / 2 - bb.center.x, -bb.center.y, h - 0.5)))
    return body


def bar(name, d, peg_len, grades=GRADES, **kw):
    """单根钉的档位条：刻名字的那头起按 grades（实测钉径的百分比）排，侧面刻档位。"""
    return gauge_bar([d * g / 100 for g in grades], peg_len, [tag(g) for g in grades], name, **kw)


def grid(parts, cols, pitch):
    """parts 按行排成网格（一行 cols 个），pitch 可以是 (列距, 行距)，返回一个 compound。"""
    px, py = pitch if isinstance(pitch, tuple) else (pitch, pitch)
    out = []
    for i, p in enumerate(parts):
        r, c = divmod(i, cols)
        out.append(p.translate(((c - (cols - 1) / 2) * px, -r * py, 0)).val())
    return cq.Workplane().add(cq.Compound.makeCompound(out))
