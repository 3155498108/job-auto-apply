#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_fav.py — 找 BOSS 收藏夹入口并列出收藏的岗位。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate
from scripts.wb import call, navigate

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")

NAVLINKS = r"""JSON.stringify((function(){
    var out=[];
    document.querySelectorAll('a,li,span,div').forEach(function(e){
        var t=(e.textContent||'').replace(/\s+/g,'').trim();
        if(!t || t.length>8) return;
        if(e.children.length>0 && e.tagName!=='A') return;
        var h=e.getAttribute('href')||'';
        if(t.indexOf('收藏')<0 && t.indexOf('职位')<0 && t.indexOf('我的')<0 && t.indexOf('求职')<0) return;
        var r=e.getBoundingClientRect();
        if(r.width<=0||r.height<=0) return;
        out.push({t:t, tag:e.tagName, href:h.slice(0,90), x:Math.round(r.x), y:Math.round(r.y)});
    });
    return out.slice(0,30);
})())"""

CANDIDATES = [
    "https://www.zhipin.com/web/geek/favorite",
    "https://www.zhipin.com/web/geek/job?tab=favorite",
    "https://www.zhipin.com/web/geek/mine",
]


def main():
    navigate("https://www.zhipin.com/web/geek/job")
    time.sleep(4)
    print("[当前]", evaluate("location.href"))
    print("[导航链接]", evaluate(NAVLINKS))
    print("\n--- 探测收藏夹候选 URL ---")
    for u in CANDIDATES:
        navigate(u)
        time.sleep(3.5)
        v = evaluate(r"""(function(){
            var t=(document.body.innerText||'').replace(/\s+/g,' ');
            return {url:location.href, title:document.title, len:t.length,
                    hasFav:t.indexOf('收藏')>=0, head:t.slice(0,160)};
        })()""")
        print(f"  {u}\n     -> {v}")
    call("screenshot", {"path": os.path.join(WORK, "fav.png"), "format": "png"})


if __name__ == "__main__":
    raise SystemExit(main())
