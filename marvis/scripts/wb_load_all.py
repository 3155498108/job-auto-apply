#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_load_all.py — 滚动加载聊天页的全部会话，直到不再增长。

BOSS 聊天列表是懒加载的（DOM 默认只渲染 40 条），
真正的滚动容器是 .user-list-content（默认 clientHeight 610 / scrollHeight 7764）。
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate
from scripts.wb import call, navigate

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")
CHAT = "https://www.zhipin.com/web/geek/chat"

COUNT = r"""(function(){return document.querySelectorAll('.friend-content').length;})()"""

SCROLL = r"""(function(){
    var l=document.querySelector('.user-list-content');
    if(!l) return 'no_container';
    l.scrollTop=l.scrollHeight;
    l.dispatchEvent(new Event('scroll',{bubbles:true}));
    return l.scrollTop+'/'+l.scrollHeight+'/'+l.clientHeight;
})()"""

LIST = r"""JSON.stringify(Array.prototype.map.call(
    document.querySelectorAll('.friend-content'), function(e,i){
        return {i:i, t:(e.textContent||'').replace(/\s+/g,' ').trim().slice(0,110)};
    }))"""


def load_all(max_rounds=30):
    navigate(CHAT)
    time.sleep(6)
    prev = -1
    for i in range(max_rounds):
        n = int(evaluate(COUNT) or 0)
        if n == prev:
            break
        prev = n
        evaluate(SCROLL)
        time.sleep(1.6)
    n = int(evaluate(COUNT) or 0)
    # 再滚回顶部
    evaluate(r"""(function(){
        var l=document.querySelector('.user-list-content');
        if(l) l.scrollTop=0;
        var f=document.querySelector('.friend-content');
        if(f && f.scrollIntoView) f.scrollIntoView({block:'start'});
        return 1;
    })()""")
    time.sleep(1.0)
    return n


def main():
    n = load_all()
    print(f"加载后会话数 {n}")
    raw = evaluate(LIST)
    try:
        convs = json.loads(raw) if raw else []
    except Exception:
        convs = []
    p = os.path.join(WORK, "all_convs.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(convs, f, ensure_ascii=False, indent=1)
    print(f"落盘 {p}")
    for c in convs:
        print(f"  [{c['i']:>3}] {c['t']}")
    call("screenshot", {"path": os.path.join(WORK, "all_convs.png"), "format": "png"})


if __name__ == "__main__":
    main()
