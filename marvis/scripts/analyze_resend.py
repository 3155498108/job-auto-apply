# -*- coding: utf-8 -*-
"""analyze_resend.py — 检查 resend_targets 与 resend_final 是否一一对齐，
并统计公司重名情况（决定会话定位策略）。"""
import json
import os
import re
from collections import Counter, defaultdict

W = r"YOUR_HOME\output\boss_work"

tg = json.load(open(os.path.join(W, "resend_targets.json"), encoding="utf-8"))
fi = json.load(open(os.path.join(W, "resend_final.json"), encoding="utf-8"))
print(f"targets={len(tg)}  final={len(fi)}")

# 对齐检查
mis = 0
for i, (t, f) in enumerate(zip(tg, fi)):
    if t["company"] != f["company"] or t["position"] != f["position"]:
        mis += 1
        if mis <= 5:
            print(f"  !! 错位 @{i}: {t['company']}/{t['position']}  vs  {f['company']}/{f['position']}")
print(f"逐条对齐不一致：{mis}")

# 公司重名
c = Counter(t["company"] for t in tg)
dups = {k: v for k, v in c.items() if v > 1}
print(f"\n公司数 {len(c)}，其中有多个会话的公司 {len(dups)} 个：")
for k, v in sorted(dups.items(), key=lambda x: -x[1]):
    rows = [t for t in tg if t["company"] == k]
    print(f"  {k} × {v}")
    for r in rows:
        print(f"      {r['position'][:26]:<28} | {r['conv'][:52]}")

# 会话预览唯一性
norm = lambda s: re.sub(r"[\s（）()【】\[\]，,、/·\-—:：~～!！?？\"'“”‘’*_#`>|-]", "", (s or "")).lower()
print("\n会话预览重复检查：")
cc = Counter(norm(t["conv"])[:60] for t in tg)
for k, v in cc.items():
    if v > 1:
        print(f"  重复 ×{v}: {k[:50]}")
