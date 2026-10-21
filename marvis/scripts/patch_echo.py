#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_echo.py — 修掉话术里可能过度承诺的关键词。

背景：话术里出现的每个被点名的技术词，都必须是本人真做过的。
「微服务」「游戏引擎」「数仓」这三个词原本会被引用，但他没做过 → 删掉。
"""
import io

P = r"YOUR_REPO\marvis\scripts\gen_jd_msg.py"

REPS = [
    # 某电商交易后端是单体分层后端，不是微服务 —— 不能点名「微服务」
    ('echo=["Java", "Spring Boot", "后端开发", "RESTful 接口", "微服务"]',
     'echo=["Java", "Spring Boot", "后端开发", "RESTful 接口"]'),
    ('"can_stack": ["java", "spring", "mybatis", "restful", "后端", "接口", "微服务", "服务端"]',
     '"can_stack": ["java", "spring", "mybatis", "restful", "后端", "接口", "服务端"]'),
    # 「提示词工程」不如「提示词」实在
    ('echo=["大模型", "Agent", "Spring AI", "DeepSeek", "提示词工程"]',
     'echo=["大模型", "Agent", "Spring AI", "DeepSeek", "提示词"]'),
    # 没做过数仓
    ('echo=["数据建模", "SQL", "数仓"]', 'echo=["数据建模", "SQL", "表设计"]'),
    # 没用过游戏引擎，做的是纯 TypeScript 内核
    ('echo=["游戏开发", "游戏引擎", "小游戏"]', 'echo=["游戏开发", "网页小游戏", "游戏工程"]'),
]

s = io.open(P, encoding="utf-8").read()
for a, b in REPS:
    if a not in s:
        print("MISS:", a[:70])
    s = s.replace(a, b)
io.open(P, "w", encoding="utf-8").write(s)
print("patched")
