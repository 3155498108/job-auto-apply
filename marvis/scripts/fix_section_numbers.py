#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix_section_numbers.py — 修掉 merge_upstream_pitfalls.py 留下的错误章节号。"""
import io
import os
import re

P = os.environ.get(
    "SAFETY_CHECKLIST",
    r"YOUR_HOME\.minimax\skills\job-auto-apply\references\safety-checklist.md")

s = io.open(P, encoding="utf-8").read()
before = s

# 「## 三4、xxx」→ 「## 四、xxx」这种错位
s = re.sub(r"^## ([一二三四五六七八九十]+)\d+、", lambda m: "## " + m.group(1) + "、", s, flags=re.M)

# 重新编号：让章节号按出现顺序连续
CN = "一二三四五六七八九十"
heads = list(re.finditer(r"^## ([一二三四五六七八九十]+)、(.+)$", s, re.M))
for i, m in enumerate(heads):
    want = CN[i]
    if m.group(1) != want:
        s = s[:m.start(1)] + want + s[m.end(1):]
        # 位置会因替换长度变化而偏移，重新从头扫
        heads = list(re.finditer(r"^## ([一二三四五六七八九十]+)、(.+)$", s, re.M))
        i = -1
        continue

io.open(P, "w", encoding="utf-8").write(s)
print("修正完成：")
for m in re.finditer(r"^## .+$", s, re.M):
    print("   ", m.group(0))
