# -*- coding: utf-8 -*-
"""wb_list.py — 列出全部会话（DOM 顺序）与图片 URL，便于定位与核对。"""
import json
import os
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate

LIST = r"""JSON.stringify(Array.prototype.map.call(
    document.querySelectorAll('.friend-content'), function(e,i){
        return {i:i, t:(e.textContent||'').replace(/\s+/g,' ').trim().slice(0,110)};
}))"""

IMGSRC = r"""JSON.stringify(Array.prototype.map.call(
    document.querySelectorAll('.chat-message img.message-image'), function(e,i){
        return {i:i, src:(e.src||'').slice(-70), w:e.naturalWidth, h:e.naturalHeight};
}))"""


def main():
    raw = evaluate(LIST)
    try:
        convs = json.loads(raw) if isinstance(raw, str) else (raw or [])
    except Exception:
        print("list failed:", str(raw)[:300]); return
    print(f"会话总数 {len(convs)}")
    for c in convs:
        print(f"  [{c['i']:>3}] {c['t']}")
    print("\n--- 当前选中会话的图片 ---")
    raw2 = evaluate(IMGSRC)
    try:
        imgs = json.loads(raw2) if isinstance(raw2, str) else (raw2 or [])
    except Exception:
        imgs = [{"raw": str(raw2)[:200]}]
    for m in imgs:
        print("  ", m)


if __name__ == "__main__":
    main()
