#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_core2.py — 第二轮调参：收紧几个原子的核心词，修正匹配优先级。

1. py_web 去掉「接口 / 后端 / 全栈」—— 这三个词太泛（任何后端岗都有），
   留着会让「脚本」在示例企业56那种 AI 岗上误赢；
2. py_data 补上「数据处理 / 预处理 / 收集 / 统计分析」—— 数据分析类 JD 的原话；
3. gen_collab 去掉「文档 / 协作」—— 太泛，会把「工程习惯」顶到具体项目前面。
"""
import io

P = r"YOUR_REPO\marvis\scripts\gen_jd_msg.py"

REPS = [
    ('"py_web": ["python", "flask", "django", "fastapi", "pandas", "numpy", "爬虫", "脚本",\n'
     '               "接口", "后端", "全栈"],',
     '"py_web": ["python", "flask", "django", "fastapi", "pandas", "numpy", "爬虫", "脚本"],'),
    ('"py_data": ["pyqt", "桌面", "抓取", "清洗", "可视化", "统计", "报表", "工具"],',
     '"py_data": ["pyqt", "桌面", "抓取", "清洗", "可视化", "统计", "报表", "工具",\n'
     '                "数据处理", "预处理", "收集", "统计分析", "定量"],'),
    ('"gen_collab": ["代码管理", "工程规范", "复用", "交接", "版本管理", "git", "文档", "协作", "团队"],',
     '"gen_collab": ["代码管理", "工程规范", "复用", "交接", "版本管理", "git", "团队"],'),
]

s = io.open(P, encoding="utf-8").read()
for a, b in REPS:
    if a not in s:
        print("MISS:", a[:70].replace("\n", " "))
    s = s.replace(a, b)
io.open(P, "w", encoding="utf-8").write(s)
print("patched")
