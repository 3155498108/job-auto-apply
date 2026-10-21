# -*- coding: utf-8 -*-
"""find_png_2480.py — 找出尺寸为 2480x3508 的本地简历图，判断已投的是哪一份。"""
import os
import glob
import struct

ROOT = r'YOUR_HOME\招聘'


def png_size(p):
    with open(p, 'rb') as f:
        head = f.read(33)
    if head[:8] != b'\x89PNG\r\n\x1a\n':
        return None
    w, h = struct.unpack('>II', head[16:24])
    return w, h


rows = []
for p in glob.glob(os.path.join(ROOT, '**', '*.png'), recursive=True):
    try:
        s = png_size(p)
    except Exception:
        continue
    if s:
        rows.append((s[0], s[1], os.path.getsize(p), p))

rows.sort(key=lambda r: (-r[0], -r[1]))
for w, h, sz, p in rows:
    flag = ' <== 2480x3508' if (w, h) == (2480, 3508) else ''
    print(f"{w:>5}x{h:<5} {sz:>9} B  {p}{flag}")
