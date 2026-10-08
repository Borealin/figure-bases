"""每套底座 base.py 的收尾：导出 STEP、切片成 A1 mini 的 3mf。

    python base.py            → base.step（多块时 base_<名字>.step）
    python base.py --slice    → 再切片成 base_a1mini.3mf（几块拼一盘）
    python base.py --preview  → 重画 images/preview.svg

切片用的 STL 放在 build/（不进仓库）。
"""
import subprocess
import sys
from pathlib import Path

import cadquery as cq

TOOLS = Path(__file__).resolve().parent
BED = 180.0


def export(here, parts, plate="base"):
    """parts = {文件名: Workplane}；写 STEP 到 here，STL 到 here/build；带 --slice 时切片成一盘。"""
    here = Path(here)
    build = here / "build"
    build.mkdir(exist_ok=True)
    stls = []
    for name, wp in parts.items():
        bb = wp.val().BoundingBox()
        ok = "放得下" if max(bb.xlen, bb.ylen) <= BED - 4 else "放不下！"
        cq.exporters.export(wp, str(here / f"{name}.step"))
        stl = build / f"{name}.stl"
        cq.exporters.export(wp, str(stl), tolerance=0.01, angularTolerance=0.1)
        stls.append(stl)
        print(f"已输出 {name}.step  {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm，A1 mini {ok}")
    if "--slice" in sys.argv:
        out = here / f"{plate}_a1mini.3mf"
        arr = ",".join(f"'{s}'" for s in stls)
        cmd = f"& '{TOOLS / 'slice_a1mini.ps1'}' -Stl {arr} -Out '{out}'"
        subprocess.run(["pwsh", "-NoProfile", "-Command", cmd], check=True)
    return stls


def want_preview():
    return "--preview" in sys.argv
