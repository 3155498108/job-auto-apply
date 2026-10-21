#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""show_plan.py — 打印 batch plan.json 摘要。"""
import io
import json
import os
import sys

PLAN = os.environ.get("BOSS_PLAN", r"YOUR_HOME\output\boss_work\plan.json")

with io.open(PLAN, encoding="utf-8") as f:
    d = json.load(f)

print(f"计划条目 {len(d)} 条\n")
for p in d:
    print(f"{p.get('company','?'):<22} found={str(p.get('found')):<5} "
          f"{p.get('reason','-'):<18} conv={p.get('conv_kw',''):<8}")
    if p.get("title"):
        print(f"{'':<26}→ {p['title'][:36]} | {p.get('salary','')} | {p.get('company','')} | {p.get('city','')}")
    for a in p.get("alt", []):
        print(f"{'':<26}  备选: {a['title'][:30]} | {a['salary']} | {a['company']}")
print()
ok = [p for p in d if p.get("found") and p.get("reason") == "ok"]
print(f"已校验命中 {len(ok)}/{len(d)}: " + ", ".join(p["company"] for p in ok))
