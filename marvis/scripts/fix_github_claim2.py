#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix_github_claim2.py — 补掉剩余两处特殊写法的旧 GitHub 数字。"""
import io

FILES = [
    (r"YOUR_HOME\招聘\AI应用与Agent工程实习生\新建 文本文档.txt",
     [("GitHub 8 仓库，可实习", "GitHub 上若干个公开仓库、多次提交，可实习")]),
    (r"YOUR_HOME\招聘\示例科技A-后端JAVA开发实习生\新建 文本文档.txt",
     [("GitHub 公开 若干仓库、数十次提交 可翻源码", "GitHub 公开 若干个公开仓库、多次提交可翻源码"),
      ("GitHub 公开 8 仓库、2026 年内 50+ commit", "GitHub 公开 若干个公开仓库、2026 年内 多次提交")]),
]

for p, reps in FILES:
    s = io.open(p, encoding="utf-8").read()
    o = s
    for a, b in reps:
        if a not in s:
            print("MISS:", a[:50])
        s = s.replace(a, b)
    if s != o:
        io.open(p, "w", encoding="utf-8").write(s)
        print("fixed", p.split("\\")[-2])
print("done")
