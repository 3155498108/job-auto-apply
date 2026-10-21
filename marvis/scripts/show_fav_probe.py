# -*- coding: utf-8 -*-
"""show_fav_probe.py — 打印收藏接口探测结果。"""
import io
import json

p = r"YOUR_HOME\output\boss_work\fav_api_probe.json"
d = json.load(io.open(p, encoding="utf-8"))
for x in d:
    b = " ".join(str(x["body"]).split())[:110]
    print(f"[{x['st']}] {x['u']:<56}{b}")
