#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_core3.py — 第三轮：删掉几个会误命中的泛词。

- can_layer 的「领域」「模块」在金融/数据类 JD 里会误命中（"相关领域优先"）；
- gen_collab 的「团队」太泛（"团队合作精神"人人都会写）。
"""
import io

P = r"YOUR_REPO\marvis\scripts\gen_jd_msg.py"

REPS = [
    ('"can_layer": ["分层", "架构", "设计模式", "重构", "模块", "领域", "规范"],',
     '"can_layer": ["分层", "架构", "设计模式", "重构", "规范"],'),
    ('"gen_collab": ["代码管理", "工程规范", "复用", "交接", "版本管理", "git", "团队"],',
     '"gen_collab": ["代码管理", "工程规范", "复用", "交接", "版本管理", "git"],'),
]

s = io.open(P, encoding="utf-8").read()
for a, b in REPS:
    if a not in s:
        print("MISS:", a[:70])
    s = s.replace(a, b)
io.open(P, "w", encoding="utf-8").write(s)
print("patched")
