"""iPhone HEIC 照片转 JPG（只依赖 ffmpeg / ffprobe）。

iPhone 的 HEIC 是很多 512/640 像素的小块拼成的网格，ffmpeg 不会自动拼，这里按网格信息用 xstack 拼回整图。
注意：没有处理 HEIC 里的旋转标记，竖拍/倒拍的照片可能是转过的，看图时留意方向（不影响镜像）。

用法：python tools/heic2jpg.py IMG_0001.HEIC [更多文件...] [--width 1800] [--out 目录]
"""
import argparse
import json
import subprocess
from pathlib import Path


def convert(src: Path, dst: Path, width: int):
    info = json.loads(subprocess.run(
        ["ffprobe", "-loglevel", "error", "-show_stream_groups", "-of", "json", str(src)],
        capture_output=True, text=True, check=True).stdout)
    grid = info["stream_groups"][0]["components"][0]
    tiles = grid["subcomponents"]
    layout = "|".join(f'{t["tile_horizontal_offset"]}_{t["tile_vertical_offset"]}' for t in tiles)
    inputs = "".join(f'[0:{t["stream_index"]}]' for t in tiles)
    fc = (f'{inputs}xstack=inputs={len(tiles)}:layout={layout}[g];'
          f'[g]crop={grid["width"]}:{grid["height"]}:0:0,scale={width}:-1[o]')
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(src), "-filter_complex", fc,
                    "-map", "[o]", "-frames:v", "1", "-q:v", "3", str(dst)], check=True)
    return grid["width"], grid["height"]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--width", type=int, default=1800)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    for f in a.files:
        out_dir = a.out or f.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        dst = out_dir / (f.stem + ".jpg")
        w, h = convert(f, dst, a.width)
        print(f"{f.name}: {w}x{h} -> {dst}")
