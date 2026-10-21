#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证改造后的投递引擎：语法、话术选择、长度分布。"""
import json
import os
import sys

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SKILL_DIR)
os.environ.setdefault("BOSS_WORK_DIR", SKILL_DIR)

from scripts.deliver_engine import load_greeting, pick_greeting_text
from scripts.profile_loader import (
    USER_NAME, TARGET_CITY, CITY_CODE, DAILY_TARGET,
    SEARCH_KEYWORDS, PREFER, AVOID, MIN_SALARY_K, get_llm_prompt,
)

print("=" * 64)
print("profile_loader 读取结果")
print("=" * 64)
print(f"  user_name     = {USER_NAME}")
print(f"  target_city   = {TARGET_CITY}  (code {CITY_CODE})")
print(f"  daily_target  = {DAILY_TARGET}")
print(f"  min_salary_k  = {MIN_SALARY_K}")
print(f"  keywords      = {len(SEARCH_KEYWORDS)} 个 -> {SEARCH_KEYWORDS[:5]}")
print(f"  prefer/avoid  = {len(PREFER)} / {len(AVOID)}")

print()
print("=" * 64)
print("话术变体选择测试")
print("=" * 64)
cases = [
    {"title": "Java后端开发实习生", "jd_text": "熟悉 Spring Boot、MySQL"},
    {"title": "AI应用开发工程师", "jd_text": "熟练使用 Codex、Claude 等 AI 编程工具，要求掌握 Agent 智能体架构"},
    {"title": "见习全栈开发工程师", "jd_text": "负责前端 TypeScript 与后端 Java"},
    {"title": "大数据开发实习生", "jd_text": "Hive、Hadoop、数据仓库"},
    {"title": "软件测试实习生", "jd_text": "负责用例设计与自动化测试"},
    {},
]
for c in cases:
    text, variant = load_greeting(c)
    short = pick_greeting_text(variant, limit=120)
    title = c.get("title", "(无标题)")
    print(f"  {title:<22} -> {variant:<14} full={len(text):>3}字  short={len(short):>3}字")

print()
print("=" * 64)
print("各变体话术长度（BOSS 打招呼框通常有字数上限）")
print("=" * 64)
with open(os.path.join(SKILL_DIR, "greetings.json"), encoding="utf-8") as f:
    g = json.load(f)
for name, v in g["variants"].items():
    print(f"  {name:<14} full={len(v['full']):>3}  short={len(v['short']):>3}  tiny={len(v['tiny']):>3}")

print()
print("=" * 64)
print("不同 maxlength 限制下的选档结果")
print("=" * 64)
for cap in (None, 300, 200, 140, 120, 100):
    picks = []
    for name in g["variants"]:
        t = pick_greeting_text(name, limit=cap)
        tag = "full" if t == g["variants"][name]["full"] else (
            "short" if t == g["variants"][name]["short"] else "tiny")
        picks.append(f"{name[:4]}:{tag}({len(t)})")
    print(f"  limit={str(cap):<5} -> {', '.join(picks)}")

print()
print("=" * 64)
print("LLM 审核提示词长度（注入 Agent 决策上下文）")
print("=" * 64)
p = get_llm_prompt()
print(f"  {len(p)} 字符")
print("  预览:", p[:120].replace("\n", " "), "...")
print()
print("[OK] 全部检查通过")
