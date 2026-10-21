# -*- coding: utf-8 -*-
"""wb_fav_top.py — 回到收藏页顶部，列出主区域 tab 与可见条目。"""
import json
import os
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb import call, navigate

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")
FAV = "https://www.zhipin.com/web/geek/recommend?tab=favorite"

TOP_TABS = r"""JSON.stringify((function(){
    var out=[];
    document.querySelectorAll('a,li,span,div,p,em,button').forEach(function(e){
        var t=(e.textContent||'').replace(/\s+/g,'').trim();
        if(!t||t.length>14) return;
        if(e.children.length>2) return;
        var r=e.getBoundingClientRect();
        if(r.width<=0||r.height<=0) return;
        if(r.y>420) return;                       // 只看页面上半部分
        out.push({t:t, tag:e.tagName, cls:(e.className||'').toString().slice(0,52),
                  href:(e.getAttribute&&e.getAttribute('href')||'').slice(0,60),
                  x:Math.round(r.x), y:Math.round(r.y)});
    });
    return out;
})())"""

LINKS = r"""JSON.stringify(Array.prototype.map.call(
    document.querySelectorAll('a[href*="job_detail"]'), function(a,i){
        var m=/job_detail\/([^\.\?]+)\.html/.exec(a.href||'');
        return {i:i, jid:m?m[1]:'', t:(a.textContent||'').replace(/\s+/g,' ').trim().slice(0,50),
                y:Math.round(a.getBoundingClientRect().y)};
    }))"""

ALL_SHORT = r"""(function(){
    var t=(document.body.innerText||'').replace(/\s+/g,' ');
    return t.slice(0,1200);
})()"""


def main():
    navigate(FAV)
    time.sleep(5)
    evaluate("window.scrollTo(0,0)")
    time.sleep(2)
    print("页面文本:\n ", evaluate(ALL_SHORT))
    print("\n上半部分可点元素:")
    tabs = evaluate(TOP_TABS)
    try:
        tabs = json.loads(tabs) if isinstance(tabs, str) else tabs
    except Exception:
        tabs = []
    seen = set()
    for t in tabs or []:
        k = (t["t"], t["x"], t["y"])
        if k in seen:
            continue
        seen.add(k)
        print("   ", json.dumps(t, ensure_ascii=False))
    print("\njob_detail 链接:")
    lk = evaluate(LINKS)
    try:
        lk = json.loads(lk) if isinstance(lk, str) else lk
    except Exception:
        lk = []
    for x in lk or []:
        print("   ", json.dumps(x, ensure_ascii=False))
    call("screenshot", {"path": os.path.join(WORK, "fav_top.png"), "format": "png"})


if __name__ == "__main__":
    main()
