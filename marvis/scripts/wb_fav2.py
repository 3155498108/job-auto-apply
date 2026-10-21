#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_fav2.py — 在职位页找「收藏」tab / 用户菜单里的收藏入口。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate
from scripts.wb import call, navigate

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")

TABS = r"""JSON.stringify((function(){
    var out=[];
    document.querySelectorAll('a,li,div,span').forEach(function(e){
        var t=(e.textContent||'').replace(/\s+/g,'').trim();
        if(!t||t.length>10) return;
        if(e.children.length>0 && e.tagName!=='A' && e.tagName!=='LI') return;
        var r=e.getBoundingClientRect();
        if(r.width<=0||r.height<=0) return;
        if(r.y>200) return;
        out.push({t:t, tag:e.tagName, cls:(e.className||'').toString().slice(0,40),
                  href:(e.getAttribute('href')||'').slice(0,80), x:Math.round(r.x), y:Math.round(r.y)});
    });
    return out.slice(0,40);
})())"""

CITY = r"""(function(){
    var t=(document.body.innerText||'').replace(/\s+/g,' ');
    var m=t.match(/搜索\s*([^\s]{2,8})/);
    var chips=[];
    document.querySelectorAll('[class*="recommend"] [class*="item"],[class*="hot"] [class*="item"],[class*="card"]').forEach(function(e,i){
        var tt=(e.textContent||'').replace(/\s+/g,' ').trim();
        if(tt&&tt.length<30&&chips.indexOf(tt)<0) chips.push(tt);
    });
    return {city:m?m[1]:'?', chips:chips.slice(0,20)};
})()"""


def main():
    navigate("https://www.zhipin.com/web/geek/jobs")
    time.sleep(4)
    print("[URL]", evaluate("location.href"))
    print("[城市/推荐]", evaluate(CITY))
    print("[顶部 tab]", evaluate(TABS))
    call("screenshot", {"path": os.path.join(WORK, "jobs_page.png"), "format": "png"})

    # 点开用户头像下拉
    r = evaluate(r"""(function(){
        var els=document.querySelectorAll('a,div,span,img');
        for(var i=0;i<els.length;i++){
            var e=els[i];
            if((e.className||'').toString().indexOf('avatar')>=0 || (e.className||'').toString().indexOf('user-info')>=0){
                var r=e.getBoundingClientRect();
                if(r.width>0&&r.height>0){ e.click(); return 'clicked:'+(e.className||'').toString().slice(0,40); }
            }
        }
        return 'no_avatar';
    })()""")
    print(f"\n[点头像] {r}")
    time.sleep(2)
    print("[下拉菜单]", evaluate(TABS))
    call("screenshot", {"path": os.path.join(WORK, "user_menu.png"), "format": "png"})


if __name__ == "__main__":
    raise SystemExit(main())
