#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pdf2png.py — 把 PDF 页面渲染成 PNG（用于发简历截图）。

用法: python pdf2png.py <pdf> <输出png> [页码 从1开始]
"""
import os
import sys

import fitz  # PyMuPDF

src = os.path.abspath(sys.argv[1])
out = os.path.abspath(sys.argv[2])
page_no = int(sys.argv[3]) if len(sys.argv) > 3 else 1

doc = fitz.open(src)
if page_no > doc.page_count:
    print(f"!! 只有 {doc.page_count} 页")
    raise SystemExit(2)
page = doc.load_page(page_no - 1)
zoom = 2.0
pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
pix.save(out)
print(f"{src} p{page_no}/{doc.page_count} → {out}  {pix.width}x{pix.height}  {os.path.getsize(out)} B")
