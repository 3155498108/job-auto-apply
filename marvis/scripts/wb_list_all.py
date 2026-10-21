# -*- coding: utf-8 -*-
"""wb_list_all.py — 打印会话列表全部条目（含滚动加载后的）。"""
import json
import os
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb import call, navigate

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")
CHAT = "https://www.zhipin.com/web/geek/chat"

LIST = r"""JSON.stringify(Array.prototype.map.call(
    document.querySelectorAll('.friend-content'), function(e,i){
        return {i:i, t:(e.textContent||'').replace(/\s+/g,' ').trim().slice(0,90)};
    }))"""

SCROLL = r"""(function(){
    var lists=document.querySelectorAll('.friend-list, .chat-friend-list, [class*="friend-list"], [class*="conversation"]');
    var n=0;
    lists.forEach(function(l){ if(l.scrollHeight>l.clientHeight+20){ l.scrollTop=l.scrollHeight; n++; } });
    window.scrollTo(0,document.body.scrollHeight);
    return 'scrolled:'+n;
})()"""


def main():
    navigate(CHAT)
    time.sleep(5)
    for _ in range(10):
        evaluate(SCROLL)
        time.sleep(1.2)
    raw = evaluate(LIST)
    try:
        convs = json.loads(raw) if raw else []
    except Exception:
        convs = []
    print(f"共 {len(convs)} 条")
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    for c in convs[start:]:
        print(f"  [{c['i']:>3}] {c['t']}")
    call("screenshot", {"path": os.path.join(WORK, "list_all.png"), "format": "png"})


if __name__ == "__main__":
    main()
