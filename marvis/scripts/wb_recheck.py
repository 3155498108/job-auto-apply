# -*- coding: utf-8 -*-
"""wb_recheck.py — 重新加载聊天页、滚动会话列表到顶、定位目标会话并导出明细。"""
import json
import os
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb import call, navigate

CHAT = "https://www.zhipin.com/web/geek/chat"

SCROLL_TOP = r"""(function(){
    var lists=document.querySelectorAll('.friend-list, .chat-friend-list, [class*="friend-list"], [class*="conversation"]');
    var n=0;
    lists.forEach(function(l){ if(l.scrollHeight>l.clientHeight+50){ l.scrollTop=0; n++; } });
    var first=document.querySelector('.friend-content');
    if(first && first.scrollIntoView) first.scrollIntoView({block:'start'});
    return 'scrolled:'+n;
})()"""

COUNT = r"""(function(){return document.querySelectorAll('.friend-content').length;})()"""

LIST = r"""JSON.stringify(Array.prototype.map.call(
    document.querySelectorAll('.friend-content'), function(e,i){
        return {i:i, t:(e.textContent||'').replace(/\s+/g,' ').trim().slice(0,90)};
    }))"""


def main():
    navigate(CHAT)
    time.sleep(5)
    for _ in range(6):
        evaluate(SCROLL_TOP)
        time.sleep(1.2)
    n = evaluate(COUNT)
    print("会话 DOM 条数:", n)
    raw = evaluate(LIST)
    try:
        convs = json.loads(raw) if isinstance(raw, str) else (raw or [])
    except Exception:
        print("list failed:", str(raw)[:300]); return
    for c in convs[:25]:
        print(f"  [{c['i']:>3}] {c['t']}")
    call("screenshot", {"path": os.path.join(r"YOUR_HOME\output\boss_work", "chat_top.png"), "format": "png"})


if __name__ == "__main__":
    main()
