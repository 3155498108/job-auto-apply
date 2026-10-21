# -*- coding: utf-8 -*-
"""wb_net.py — 用 WebBridge 的 network 动作抓请求，找收藏/喜欢相关接口。

用法: python wb_net.py <url> [关键词...]
"""
import json
import os
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.wb import call

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")


def main():
    url = sys.argv[1]
    kws = sys.argv[2:] or ["fav", "collect", "like", "star", "heart", "wish", "favorite"]
    print(call("network", {"cmd": "start"}))
    call("navigate", {"url": url})
    time.sleep(8)
    r = call("network", {"cmd": "list"})
    data = r.get("data")
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            pass
    items = data if isinstance(data, list) else (data or {}).get("requests") or (data or {}).get("entries") or []
    print(f"抓到 {len(items)} 条请求")
    hits = []
    for it in items:
        u = it.get("url") or it.get("request", {}).get("url") or ""
        if any(k.lower() in u.lower() for k in kws):
            hits.append(it)
    print(f"\n命中 {len(hits)} 条：")
    for h in hits:
        u = h.get("url") or h.get("request", {}).get("url") or ""
        st = h.get("status") or h.get("response", {}).get("status")
        print(f"   [{st}] {u[:160]}")
    out = os.path.join(WORK, "net_dump.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    print(f"\n全量 → {out}")


if __name__ == "__main__":
    main()
