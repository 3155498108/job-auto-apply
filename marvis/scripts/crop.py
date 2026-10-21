#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""crop.py — 裁剪并放大截图的指定区域，用来肉眼核对细节。

用法: python crop.py <图片> <x> <y> <w> <h> [放大倍数] [输出]
"""
import os
import sys

try:
    from PIL import Image
except ImportError:
    print("!! 没有 PIL"); raise SystemExit(2)

src = sys.argv[1]
x, y, w, h = (int(v) for v in sys.argv[2:6])
scale = float(sys.argv[6]) if len(sys.argv) > 6 else 2.0
out = sys.argv[7] if len(sys.argv) > 7 else os.path.join(os.path.dirname(src), "_crop.png")

im = Image.open(src)
print(f"原图 {im.size}")
box = (max(0, x), max(0, y), min(im.width, x + w), min(im.height, y + h))
im2 = im.crop(box).resize((int(box[2] - box[0]) * int(scale), int(box[3] - box[1]) * int(scale)),
                          Image.LANCZOS)
im2.save(out)
print(f"裁剪 {box} → {im2.size}  {out}")
