"""Minimal numpy z-buffer renderer: CadQuery shapes -> shaded PNG (+ optional SVG labels)."""
import math, struct, zlib
import numpy as np


def view_matrix(az=-35, el=50):
    a, e = math.radians(az), -math.radians(el)
    rz = np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])
    rx = np.array([[1, 0, 0], [0, math.cos(e), -math.sin(e)], [0, math.sin(e), math.cos(e)]])
    return rx @ rz


def render(shapes, width=1400, az=-35, el=50, pad=30, tol=0.05, bg=(250, 250, 248)):
    """shapes: list of (cq.Shape, rgb). Returns (img HxWx3 uint8, project fn)."""
    M = view_matrix(az, el)
    tris, cols = [], []
    for shp, rgb in shapes:
        v, t = shp.tessellate(tol, 0.2)
        v = np.array([(p.x, p.y, p.z) for p in v])
        t = np.array(t)
        tris.append(v[t]); cols.append(np.tile(rgb, (len(t), 1)))
    tris = np.concatenate(tris); cols = np.concatenate(cols).astype(float)
    world = tris.copy()
    p = tris @ M.T  # x right, y up(screen), z toward viewer
    lo, hi = p.reshape(-1, 3).min(0), p.reshape(-1, 3).max(0)
    s = (width - 2 * pad) / (hi[0] - lo[0])
    H = int((hi[1] - lo[1]) * s + 2 * pad)
    W = width

    def proj(pt):
        q = np.asarray(pt, float) @ M.T
        return (q[0] - lo[0]) * s + pad, H - ((q[1] - lo[1]) * s + pad)

    sx = (p[..., 0] - lo[0]) * s + pad
    sy = H - ((p[..., 1] - lo[1]) * s + pad)
    sz = p[..., 2]
    n = np.cross(world[:, 1] - world[:, 0], world[:, 2] - world[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    light = np.array([-0.4, -0.6, 0.9]); light /= np.linalg.norm(light)
    shade = 0.35 + 0.65 * np.abs(n @ light)
    zbuf = np.full((H, W), -1e9); img = np.zeros((H, W, 3)); img[:] = bg
    for i in range(len(tris)):
        x, y, z = sx[i], sy[i], sz[i]
        x0, x1 = max(int(x.min()), 0), min(int(x.max()) + 1, W - 1)
        y0, y1 = max(int(y.min()), 0), min(int(y.max()) + 1, H - 1)
        if x1 < x0 or y1 < y0:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        d = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
        if abs(d) < 1e-9:
            continue
        w0 = ((y[1] - y[2]) * (gx - x[2]) + (x[2] - x[1]) * (gy - y[2])) / d
        w1 = ((y[2] - y[0]) * (gx - x[2]) + (x[0] - x[2]) * (gy - y[2])) / d
        w2 = 1 - w0 - w1
        m = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not m.any():
            continue
        zz = w0 * z[0] + w1 * z[1] + w2 * z[2]
        sub = zbuf[y0:y1 + 1, x0:x1 + 1]
        m &= zz > sub
        sub[m] = zz[m]
        img[y0:y1 + 1, x0:x1 + 1][m] = cols[i] * shade[i]
    return np.clip(img, 0, 255).astype(np.uint8), proj


def write_png(path, img):
    h, w, _ = img.shape
    raw = b"".join(b"\x00" + img[r].tobytes() for r in range(h))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))
