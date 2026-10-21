# -*- coding: utf-8 -*-
"""wb_fav_probe.py — 在 BOSS 找「我的收藏」入口（找 tab / 菜单项）。"""
import json
import os
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb import call, navigate

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")

TABS = r"""JSON.stringify((function(){
    var out=[];
    document.querySelectorAll('a,li,span,div,p,em,i,button').forEach(function(e){
        var t=(e.textContent||'').replace(/\s+/g,'').trim();
        if(!t||t.length>12) return;
        if(e.children.length>2) return;
        var r=e.getBoundingClientRect();
        if(r.width<=0||r.height<=0) return;
        out.push({t:t, tag:e.tagName, cls:(e.className||'').toString().slice(0,46),
                  href:(e.getAttribute&&e.getAttribute('href')||'').slice(0,60),
                  x:Math.round(r.x), y:Math.round(r.y)});
    });
    return out;
})())"""

URLS = [
    "https://www.zhipin.com/web/geek/recommend?tab=favorite",
    "https://www.zhipin.com/web/geek/recommend?tab=collect",
    "https://www.zhipin.com/web/geek/favorite",
    "https://www.zhipin.com/web/geek/mine?tab=favorite",
]


def main():
    for u in URLS:
        navigate(u)
        time.sleep(4.5)
        st = evaluate(r"""(function(){return {url:location.href,title:document.title,
            body:(document.body.innerText||'').replace(/\s+/g,' ').slice(0,200)};})()""")
        print(f"\n=== {u}\n    {st}")
        tabs = evaluate(TABS)
        try:
            tabs = json.loads(tabs) if isinstance(tabs, str) else tabs
        except Exception:
            tabs = []
        kw = ("收藏", "喜欢", "心愿", "感兴趣", "投递", "岗位", "推荐", "看我的", "附件")
        hit = [x for x in tabs if any(k in x["t"] for k in kw)]
        for h in hit[:25]:
            print("    ", json.dumps(h, ensure_ascii=False))
        call("screenshot", {"path": os.path.join(WORK, f"favprobe_{u.split('/')[-1][:20] or 'x'}.png"), "format": "png"})


if __name__ == "__main__":
    main()
