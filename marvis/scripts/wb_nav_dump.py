# -*- coding: utf-8 -*-
"""wb_nav_dump.py — dump 顶部导航与用户菜单的 HTML，找「我的收藏」链接。"""
import os
import re
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb import call, navigate

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")

NAV_HTML = r"""(function(){
    var out=[];
    ['header','.header','.nav-list','ul.nav','.user-info','.header-user','.avatar-wrap',
     '[class*="dropdown"]','.menu-list','[class*="user-menu"]'].forEach(function(sel){
        document.querySelectorAll(sel).forEach(function(e){
            var h=(e.outerHTML||'').replace(/\s+/g,' ');
            if(h.length>4000) h=h.slice(0,4000);
            out.push({sel:sel, html:h});
        });
    });
    return out;
})()"""

ALL_HREF = r"""JSON.stringify((function(){
    var out=[];
    document.querySelectorAll('a[href]').forEach(function(a){
        var h=a.getAttribute('href')||'';
        var t=(a.textContent||'').replace(/\s+/g,' ').trim();
        out.push({h:h.slice(0,90), t:t.slice(0,26)});
    });
    return out;
})())"""


def main():
    navigate("https://www.zhipin.com/web/geek/job?query=Java&city=101280100")
    time.sleep(5)
    h = evaluate(NAV_HTML)
    if isinstance(h, str):
        import json
        try:
            h = json.loads(h)
        except Exception:
            h = []
    for x in h or []:
        print(f"\n----- {x['sel']}")
        print(x["html"][:1800])
    print("\n\n===== 页面全部链接（找含 收藏/geek 的）")
    links = evaluate(ALL_HREF)
    import json
    try:
        links = json.loads(links) if isinstance(links, str) else links
    except Exception:
        links = []
    for l in links or []:
        if any(k in l["h"] for k in ("geek", "collect", "like", "favor", "recommend", "mine")):
            print("   ", json.dumps(l, ensure_ascii=False))
    call("screenshot", {"path": os.path.join(WORK, "nav_dump.png"), "format": "png"})


if __name__ == "__main__":
    main()
