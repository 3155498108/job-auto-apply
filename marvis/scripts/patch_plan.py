#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_plan.py — 用 TARGETS 的最新元数据补齐 plan.json（conv_kw / company 等）。"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.wb_batch import TARGETS, PLAN

with io.open(PLAN, encoding="utf-8") as f:
    plan = json.load(f)

meta = {t["folder"]: t for t in TARGETS}
out = []
for p in plan:
    t = meta.get(p.get("folder"), {})
    p["conv_kw"] = t.get("conv_kw", "")
    p["company"] = t.get("company", p.get("company", ""))
    p["query"] = t.get("query", "")
    p["role"] = t.get("role", "")
    p["comp"] = t.get("comp", "")
    out.append(p)

with io.open(PLAN, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

for p in out:
    print(f"{p.get('company',''):<22} found={str(p.get('found')):<5} conv={p.get('conv_kw',''):<10} "
          f"{p.get('title','')[:30]}")
