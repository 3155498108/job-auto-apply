# -*- coding: utf-8 -*-
"""rerender_shots.py — 按当前 PDF 重新渲染简历截图（300dpi，与历史图同规格 2480x3508）。

用法: python rerender_shots.py <pdf> <输出前缀> [页数...]
"""
import os
import sys

import fitz

ZOOM = 300 / 72.0   # 300dpi —— 与 招聘\ 下所有 shot_*.png 同规格


def render(pdf, out_prefix, pages):
    doc = fitz.open(pdf)
    out = []
    for pno in pages:
        if pno > doc.page_count:
            print(f"!! {pdf} 只有 {doc.page_count} 页，跳过 p{pno}")
            continue
        page = doc.load_page(pno - 1)
        pix = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM))
        path = f"{out_prefix}_p{pno}.png"
        pix.save(path)
        out.append((path, pix.width, pix.height, os.path.getsize(path)))
    doc.close()
    for p, w, h, sz in out:
        print(f"  {p}  {w}x{h}  {sz} B")
    return out


if __name__ == "__main__":
    pdf = os.path.abspath(sys.argv[1])
    prefix = os.path.abspath(sys.argv[2])
    pages = [int(x) for x in sys.argv[3:]] or [1, 2]
    render(pdf, prefix, pages)
