# -*- coding: utf-8 -*-
"""wb_fav_find.py — 在职位页/导航里找「我的收藏」入口（含 hover 展开的下拉菜单）。"""
import json
import os
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb import call, navigate

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")

HOVER_NAV = r"""(function(){
    // 悬停顶部「职位」等导航，展开下拉菜单
    var navs=document.querySelectorAll('ul.nav > li, .nav-list > li, li.nav-item');
    var out=[];
    navs.forEach(function(li){
        var r=li.getBoundingClientRect();
        if(r.width<=0) return;
        ['mouseover','mouseenter','mousemove'].forEach(function(t){
            li.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,
                clientX:r.left+r.width/2, clientY:r.top+r.height/2}));
        });
    });
    return 'hovered '+navs.length;
})()"""

FILL = r"""JSON.stringify((function(){
    var out=[];
    document.querySelectorAll('a,li,span,div,p,em,i,button,label').forEach(function(e){
        var t=(e.textContent||'').replace(/\s+/g,'').trim();
        if(!t||t.length>16) return;
        if(t.indexOf('收藏')<0 && t.indexOf('心愿')<0 && t.indexOf('关注')<0) return;
        var r=e.getBoundingClientRect();
        var st=window.getComputedStyle(e);
        if(st.display==='none'||st.visibility==='hidden') return;
        out.push({t:t, tag:e.tagName, cls:(e.className||'').toString().slice(0,50),
                  href:(e.getAttribute&&e.getAttribute('href')||'').slice(0,70),
                  x:Math.round(r.x), y:Math.round(r.y), w:Math.round(r.width), h:Math.round(r.height)});
    });
    return out;
})())"""

URLS = [
    "https://www.zhipin.com/web/geek/job?query=Java&city=101280100",
    "https://www.zhipin.com/job_detail/JOBID013.html",
]


def main():
    for u in URLS:
        navigate(u)
        time.sleep(5)
        print(f"\n===== {u}")
        print("  hover 导航:", evaluate(HOVER_NAV))
        time.sleep(1.5)
        v = evaluate(FILL)
        try:
            v = json.loads(v) if isinstance(v, str) else v
        except Exception:
            v = []
        for x in v or []:
            print("   ", json.dumps(x, ensure_ascii=False))
        call("screenshot", {"path": os.path.join(WORK, f"favfind_{u.split('/')[-1][:18] or 'x'}.png"), "format": "png"})


if __name__ == "__main__":
    main()
