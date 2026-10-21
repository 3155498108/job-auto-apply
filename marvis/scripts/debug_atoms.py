#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""debug_atoms.py — 打印某个岗位的原子排名与得分，用于调参。"""
import io
import json
import os
import sys

sys.path.insert(0, r"YOUR_REPO\marvis")
from scripts.gen_jd_msg import match_atoms, req_section

WORK = r"YOUR_HOME\output\boss_work"

label = sys.argv[1]
tpath = os.path.join(WORK, "gd2_kept.json")
targets = {t["label"]: t for t in json.load(io.open(tpath, encoding="utf-8"))}
jds = json.load(io.open(os.path.join(WORK, "jd_text.json"), encoding="utf-8"))
t = targets[label]
jd = jds[label]["jd"]
print(f"岗位：{t['position']}｜{t['company']}")
print(f"要求段：{req_section(jd)[:260]}\n")
for a, sc, hits in match_atoms(jd, t["position"]):
    hs = "、".join(f"{k}({w:.1f})" for k, w in hits[:6])
    print(f"  {sc:>5.1f}  {a['id']:<12} {hs}")
