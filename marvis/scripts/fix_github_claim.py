#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix_github_claim.py — 把话术档案里过时的「若干仓库、数十次提交」更正为实测值。

实测（2026-10-21，`gh_count.py` 跑 GitHub API）：
  公开仓库 11 个 = 自有 10 + fork 1（fork 不算本人作品）
  自有 若干个公开仓库的 commit 合计多次提交
所以正文里写「若干个公开仓库、多次提交」是保守且真实的。
"""
import io
import os
import re

RECRUIT = r"YOUR_HOME\招聘"

# (旧写法, 新写法) —— 覆盖历史模板里的各种变体
REPS = [
    ("GitHub 若干仓库、数十次提交", "GitHub 若干个公开仓库、多次提交"),
    ("若干仓库、数十次提交", "若干个公开仓库、多次提交"),
    ("GitHub 上 若干仓库、数十次提交", "GitHub 上 若干个公开仓库、多次提交"),
    ("GitHub 上 若干仓库、数十次提交", "GitHub 上 若干个公开仓库、多次提交"),
    ("GitHub 8 仓库、50+ commit", "GitHub 若干个公开仓库、多次提交"),
    ("GitHub 若干仓库、数十次提交", "GitHub 若干个公开仓库、多次提交"),
    ("GitHub 若干仓库、数十次提交", "GitHub 若干个公开仓库、多次提交"),
    ("GitHub 上 若干仓库、数十次提交", "GitHub 上 若干个公开仓库、多次提交"),
]

changed = 0
for root, dirs, files in os.walk(RECRUIT):
    for fn in files:
        if not fn.lower().endswith(".txt"):
            continue
        p = os.path.join(root, fn)
        try:
            s = io.open(p, encoding="utf-8").read()
        except (OSError, UnicodeDecodeError):
            continue
        o = s
        for a, b in REPS:
            s = s.replace(a, b)
        # 兜底：任何 "8 仓库" + "50+ commit" 的组合
        s = re.sub(r"8\s*仓库\s*50\+", "若干个公开仓库、80+", s)
        if s != o:
            io.open(p, "w", encoding="utf-8").write(s)
            changed += 1

# 残留检查
left = []
for root, dirs, files in os.walk(RECRUIT):
    for fn in files:
        if not fn.lower().endswith(".txt"):
            continue
        p = os.path.join(root, fn)
        s = io.open(p, encoding="utf-8", errors="ignore").read()
        if re.search(r"8\s*仓库|50\+ commit", s):
            left.append(os.path.relpath(p, RECRUIT))
print(f"已更正 {changed} 个话术文件")
print(f"仍含旧写法的文件：{len(left)}")
for f in left[:20]:
    print("  ", f)
