#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_plan2.py — 修正 plan.json 里的会话关键词（示例讯动U等）。"""
import io
import json
import os

PLAN = os.environ.get("BOSS_PLAN", r"YOUR_HOME\output\boss_work\plan.json")

# 招聘方在会话标题里显示的是真实公司名，不是档案里的占位名
FIX = {
    "Java后端开发实习生": dict(conv_kw="示例讯动U", comp="示例讯动U"),
    "AI应用与Agent工程实习生": dict(conv_kw="示例文化B"),
    "java实习生": dict(conv_kw="示例科技V"),
    "产品实习生": dict(conv_kw="示例平台I"),
    "全栈开发实习生": dict(conv_kw="示例科技C"),
    "示例科技D-游戏开发实习生": dict(conv_kw="示例科技D"),
    "后端开发实习生": dict(conv_kw="示例网络E"),
    "示例传媒T-AI智能体研发实习生": dict(conv_kw="示例传媒T"),
    "研发实习生": dict(conv_kw="示例数据科技"),
    "软件实习生": dict(conv_kw="示例软件F"),
    "示例云服务G-AI全栈开发工程师": dict(conv_kw="示例企业69"),
}

with io.open(PLAN, encoding="utf-8") as f:
    plan = json.load(f)

for p in plan:
    f2 = FIX.get(p.get("folder"))
    if f2:
        p.update(f2)

with io.open(PLAN, "w", encoding="utf-8") as f:
    json.dump(plan, f, ensure_ascii=False, indent=1)

for p in plan:
    print(f"{p.get('company',''):<22} conv={p.get('conv_kw',''):<10} comp={p.get('comp',''):<10} {p.get('title','')[:30]}")
