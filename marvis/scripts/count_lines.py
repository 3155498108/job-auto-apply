# -*- coding: utf-8 -*-
"""count_lines.py — 核实 game/src 的 TS 文件数与总行数（简历里写 两百余个 TS 文件 / 数万行）。"""
import os
import re

ROOT = r"YOUR_ROOT\game\src"
EXTS = (".ts", ".tsx")

files = []
for dp, dn, fn in os.walk(ROOT):
    for f in fn:
        if f.endswith(EXTS):
            files.append(os.path.join(dp, f))

total = 0
nonblank = 0
per_dir = {}
for p in files:
    try:
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.read().split("\n")
    except OSError:
        continue
    n = len(lines)
    # 若文件以换行结尾，split 会多出一个空串
    if n and lines[-1] == "":
        n -= 1
    total += n
    nonblank += sum(1 for x in lines if x.strip())
    rel = os.path.relpath(p, ROOT)
    per_dir[rel] = n

print(f"TS/TSX 文件数 = {len(files)}")
print(f"总行数(含空行) = {total}")
print(f"非空行数       = {nonblank}")
print(f"游戏目录数     = {len([d for d in os.listdir(os.path.join(ROOT,'games')) if os.path.isdir(os.path.join(ROOT,'games',d))])}")

# 测试文件
tests = [p for p in files if re.search(r"\.test\.tsx?$", p) or "__tests__" in p]
print(f"测试文件数     = {len(tests)}")
print(f"非游戏目录行数 = {total - sum(v for k,v in per_dir.items() if k.startswith('games'+os.sep))}")
