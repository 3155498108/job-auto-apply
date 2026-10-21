# -*- coding: utf-8 -*-
"""wb_card_html.py — dump 搜索结果里一张岗位卡片的 HTML，找「已收藏」标记。"""
import json
import os
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb import call, navigate

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")

CARD_HTML = r"""(function(){
    var c=document.querySelector('.job-card-wrap') || document.querySelector('.job-card-wrapper');
    if(!c) return 'no_card';
    return (c.outerHTML||'').replace(/\s+/g,' ').slice(0,2600);
})()"""

LIKE_STATE = r"""JSON.stringify((function(){
    var out=[];
    document.querySelectorAll('.job-card-wrap, .job-card-wrapper').forEach(function(c,i){
        var like=c.querySelector('[class*="like"]');
        var star=c.querySelector('[class*="star"]');
        var collect=c.querySelector('[class*="collect"], [class*="favorite"]');
        var t=(c.textContent||'').replace(/\s+/g,' ').trim().slice(0,44);
        out.push({i:i, t:t,
                  like: like? (like.className||'')+'|'+((like.textContent||'').trim()):'',
                  star: star? (star.className||''):'',
                  collect: collect? (collect.className||''):''});
    });
    return out;
})())"""


def main():
    navigate("https://www.zhipin.com/web/geek/job?query=%E5%AE%9E%E4%B9%A0&city=101280100")
    time.sleep(5)
    print("--- 一张卡片 HTML ---")
    print(evaluate(CARD_HTML))
    print("\n--- 各卡片的 like/star 状态 ---")
    v = evaluate(LIKE_STATE)
    try:
        v = json.loads(v) if isinstance(v, str) else v
    except Exception:
        v = []
    for x in v or []:
        print("   ", json.dumps(x, ensure_ascii=False))
    call("screenshot", {"path": os.path.join(WORK, "card_html.png"), "format": "png"})


if __name__ == "__main__":
    main()
