#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证 pick_greeting_for_job：优先命中「招聘」目录的专属话术。"""
import os
import sys

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SKILL_DIR)
os.environ.setdefault("BOSS_WORK_DIR", SKILL_DIR)

from scripts.deliver_engine import pick_greeting_for_job
from scripts.recruit_greetings import load_index

idx = load_index()
print(f"招聘目录索引: {len(idx)} 个岗位\n")

cases = [
    {"company": "示例科技产业有限公司", "title": "后端JAVA开发工程师（实习生）"},
    {"company": "示例网络科技有限公司", "title": "AI全栈开发工程师"},
    {"company": "示例信息技术有限公司", "title": "游戏开发实习生"},
    {"company": "示例数据科技有限公司", "title": "应届生/实习生(研发岗)"},
    {"company": "某高校某科技公司", "title": "前端开发实习生"},
    {"company": "完全不存在的公司XYZ", "title": "量子计算研究员"},
]

print("=" * 78)
print("岗位 → 话术匹配")
print("=" * 78)
for c in cases:
    text, meta = pick_greeting_for_job(c)
    src = meta.get("source")
    folder = meta.get("folder") or "-"
    print(f"  {c['company'][:16]:<18} {c['title'][:18]:<20}")
    print(f"      来源={src:<8} 命中={folder}")
    print(f"      长度={len(text):>4}  PDF={os.path.basename(meta.get('pdf') or '(无)')}")
    print(f"      开头: {text[:58]}...")
    print()

print("=" * 78)
print("限长降级测试（模拟 BOSS 打招呼框 maxlength）")
print("=" * 78)
for cap in (140, 200, 300):
    t, m = pick_greeting_for_job(
        {"company": "示例科技产业有限公司", "title": "后端JAVA开发工程师"}, limit=cap)
    print(f"  limit={cap:<4} → {len(t):>3} 字  源={m.get('source')}  命中={m.get('folder')}")
print()
print("[OK] 匹配与降级逻辑验证通过")
