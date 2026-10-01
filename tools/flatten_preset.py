"""把 Bambu Studio 系统预设的继承链（inherits）展开成一个完整 JSON。

Bambu Studio 命令行只读传进去的那个预设文件本身，不会去读它继承的上级预设，
缺的参数会用程序默认值（例如填充 20%、很慢的速度），切片结果和 GUI 里完全不一样。

用法：python tools/flatten_preset.py <machine|process|filament> "<预设名>" <输出.json>
"""
import json
import sys
from pathlib import Path

ROOT = Path(r"C:\Program Files\Bambu Studio\resources\profiles\BBL")


def flatten(kind, name, root=ROOT):
    idx = {}
    for f in (root / kind).rglob("*.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (ValueError, UnicodeDecodeError):
            continue
        if isinstance(d, dict) and "name" in d:
            idx[d["name"]] = d
    chain, cur = [], name
    while cur:
        chain.append(idx[cur])
        cur = idx[cur].get("inherits", "")
    out = {}
    for d in reversed(chain):
        out.update(d)
    out.pop("inherits", None)
    out["name"] = name
    return out


if __name__ == "__main__":
    kind, name, dst = sys.argv[1:4]
    d = flatten(kind, name)
    Path(dst).write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    keys = ["layer_height", "sparse_infill_density", "wall_loops", "nozzle_temperature", "printable_area"]
    print(name, {k: d[k] for k in keys if k in d})
