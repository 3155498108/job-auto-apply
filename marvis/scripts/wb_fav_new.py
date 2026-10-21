#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_fav_new.py — 抓取 BOSS「收藏」页的完整岗位列表（滚动加载 + Vue props 提取）。

入口：https://www.zhipin.com/web/geek/recommend?tab=favorite
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate, extract_jobs
from scripts.wb import call, navigate

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")
FAV = "https://www.zhipin.com/web/geek/recommend?tab=favorite"

CARDS = r"""(function(){
    var out=[], seen={};
    var sels=['.job-card-wrap','.job-card-wrapper','.job-card-box','li.job-card-wrapper',
              '[class*="job-card"]','[class*="card-wrapper"]'];
    sels.forEach(function(sel){
        document.querySelectorAll(sel).forEach(function(c){
            var d=null;
            try{ d=c.__vue__ && c.__vue__.$props && c.__vue__.$props.data; }catch(e){}
            if(d && d.encryptJobId && !seen[d.encryptJobId]){
                seen[d.encryptJobId]=1;
                out.push({jobId:d.encryptJobId, title:d.jobName||'', salary:d.salaryDesc||'',
                          city:d.cityName||'', area:(d.jobDistrict||d.businessDistrict||''),
                          company:d.brandName||'', industry:d.brandIndustry||'',
                          scale:d.brandScaleName||'', degree:d.jobDegree||'',
                          exp:d.jobExperience||'',
                          tags:((d.jobLabels||d.skills||[])||[]).join('|')});
            }
        });
    });
    if(!out.length){
        document.querySelectorAll('a[href*="job_detail"]').forEach(function(a){
            var m=/job_detail\/([^\.\?]+)\.html/.exec(a.href||'');
            if(m && !seen[m[1]]){ seen[m[1]]=1;
                out.push({jobId:m[1], title:(a.textContent||'').replace(/\s+/g,' ').trim().slice(0,40), href:a.href});}
        });
    }
    return out;
})()"""

TEXT_JS = r"""(function(){
    var t=(document.body.innerText||'').replace(/\s+/g,' ');
    return {url:location.href, title:document.title, len:t.length, head:t.slice(0,400)};
})()"""


def main():
    navigate(FAV)
    time.sleep(5)
    st = evaluate(TEXT_JS)
    print("页面:", st)
    seen = {}
    for i in range(10):
        evaluate(r"""(function(){window.scrollTo(0,document.body.scrollHeight);return 1;})()""")
        time.sleep(1.8)
        cards = evaluate(CARDS)
        if isinstance(cards, str):
            try:
                cards = json.loads(cards)
            except Exception:
                cards = []
        new = 0
        for c in cards or []:
            if c.get("jobId") and c["jobId"] not in seen:
                seen[c["jobId"]] = c
                new += 1
        print(f"  滚动 {i+1}: 卡片 {len(cards or [])} 条，新增 {new}，累计 {len(seen)}")
        if new == 0 and i > 1:
            break

    out = os.path.join(WORK, "favorites.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(list(seen.values()), f, ensure_ascii=False, indent=1)
    print(f"\n===== 收藏 {len(seen)} 个 → {out}")
    for c in seen.values():
        print(f"  {c.get('city',''):<6} {c.get('salary',''):<10} {str(c.get('title',''))[:30]:<32} "
              f"{str(c.get('company',''))[:22]:<24} {c.get('jobId')}")
    call("screenshot", {"path": os.path.join(WORK, "favorites.png"), "format": "png"})


if __name__ == "__main__":
    raise SystemExit(main())
