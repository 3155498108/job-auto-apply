# -*- coding: utf-8 -*-
"""scan_pdfs_38.py — 扫描所有 PDF，找出还写着「38 款」的（以及游戏数量总览）。"""
import glob
import os
import re

import fitz

ROOT = r"YOUR_HOME"
PAT = re.compile(r"(\d+)\s*款")

targets = []
for pat in (r"YOUR_HOME\output\*.pdf", r"YOUR_HOME\招聘\**\*.pdf",
            r"YOUR_HOME\output\tailored\*.pdf", r"YOUR_HOME\output\STAR\*.pdf"):
    targets.extend(glob.glob(pat, recursive=True))

stale = []
ok = []
for p in sorted(set(targets)):
    try:
        doc = fitz.open(p)
    except Exception as e:
        print(f"!! {p} {e}")
        continue
    txt = "".join(pg.get_text() for pg in doc)
    n = doc.page_count
    doc.close()
    nums = sorted({int(m.group(1)) for m in PAT.finditer(txt)})
    if 38 in nums:
        stale.append((p, n, nums))
    else:
        ok.append((p, n, nums))

print(f"共 {len(set(targets))} 个 PDF")
print(f"\n✅ 不含 38 款（{len(ok)} 个）：")
for p, n, nums in ok:
    print(f"   {os.path.basename(p):<46} {n} 页  款数={nums}")
print(f"\n⚠️ 仍含 38 款（{len(stale)} 个）：")
for p, n, nums in stale:
    print(f"   {os.path.basename(p):<46} {n} 页  款数={nums}")
