# -*- coding: utf-8 -*-
"""probe_tabs.py — 列出 WebBridge 当前所有标签页 + 各会话标签页的 URL/标题。

用于确认并行会话（51job）是否与 BOSS 共用同一个标签页。
"""
import json
import sys

sys.path.insert(0, r"YOUR_REPO\job-auto-apply\marvis")
from scripts.wb import call  # noqa: E402

out = {}
try:
    out["tabs"] = call("list_tabs", {}, "boss-main")
except Exception as e:
    out["tabs_error"] = repr(e)

for sess in ("boss-main", "51job", "job51", "j51", "51-job"):
    try:
        r = call("evaluate", {"code": "JSON.stringify({url:location.href,title:document.title})"}, sess)
        out[sess] = r
    except Exception as e:
        out[sess] = "ERR " + repr(e)[:120]

print(json.dumps(out, ensure_ascii=False, indent=1)[:5000])
