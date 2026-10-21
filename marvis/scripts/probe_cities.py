# -*- coding: utf-8 -*-
"""probe_cities.py — 核验 BOSS 城市码（必须实测，不能凭记忆）。

对每个候选 city code 打开搜索页，读 <title> 与页面里的城市名，
把「码 → 实际城市」写成 city_map.json 供扫描脚本使用。
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb import navigate

OUT = r'YOUR_HOME\output\boss_work\city_map.json'

# 候选（码是待核验的猜测，核验后只保留标题里对得上的）
CANDIDATES = [
    ("101280100", "广州"),
    ("101280600", "深圳"),
    ("101280700", "珠海"),
    ("101280800", "佛山"),
    ("101280300", "惠州"),
    ("101281600", "东莞"),
    ("101281700", "中山"),
    ("101281100", "江门"),
    ("101281500", "汕头"),
    ("101281300", "某城市"),
    ("101281200", "肇庆"),
    ("101280900", "江门"),
    ("101281000", "茂名"),
    ("101281400", "梅州"),
    ("101280500", "汕尾"),
    ("101280400", "韶关"),
    ("101281200", "肇庆"),
]


def main():
    results = {}
    for code, guess in CANDIDATES:
        if code in results:
            continue
        url = f"https://www.zhipin.com/web/geek/job?query=%E5%AE%9E%E4%B9%A0&city={code}"
        try:
            navigate(url)
        except Exception as e:
            print(f"{code} 导航失败 {e}")
            continue
        time.sleep(3.2)
        title = evaluate("document.title") or ""
        # 页面里当前选中的城市（城市选择器的高亮项）
        picked = evaluate(r"""(function(){
            var sels=['.city-list .selected','.city-condition .selected','.city-selector .selected',
                      '.condition-city .selected','[class*="city"] .selected','[class*="cityName"]'];
            for(var i=0;i<sels.length;i++){
                var e=document.querySelector(sels[i]);
                if(e) {var t=(e.textContent||'').replace(/\s+/g,' ').trim(); if(t&&t.length<20) return t;}
            }
            var a=document.querySelector('.job-list-box .city, .location');
            return a?(a.textContent||'').trim():'';
        })()""") or ""
        m = re.search(r"[「\[](.+?)[」\]]", title)
        tcity = m.group(1) if m else ""
        # 职位列表里实际出现的城市名（最可信）
        cities = evaluate(r"""JSON.stringify(Array.from(new Set(
            Array.from(document.querySelectorAll('.job-card-wrap .job-area, .job-card-wrap .city, .job-area')).map(function(e){
                return (e.textContent||'').replace(/\s+/g,' ').trim();
            }).filter(function(t){return t && t.length<20;})
        )))""")
        try:
            clist = json.loads(cities) if isinstance(cities, str) else (cities or [])
        except Exception:
            clist = []
        ok = (guess in title) or (guess in clist)
        results[code] = dict(guess=guess, title=title[:60], page_city=picked[:20],
                             list_cities=clist[:6], verified=bool(ok))
        print(f"{code}  猜测={guess:4}  {'OK ' if ok else 'NO '}  title={title[:44]}")
        print(f"        列表城市={clist[:5]}")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    print(f"\n已写入 {OUT}")


if __name__ == "__main__":
    main()
