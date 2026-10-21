#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_fav3.py — 打开 BOSS「我的推荐/收藏」页，提取收藏的岗位列表。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate, extract_jobs
from scripts.wb import call, navigate

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")

PAGES = [
    "https://www.zhipin.com/web/geek/recommend",
    "https://www.zhipin.com/web/geek/recommend?tab=favorite",
    "https://www.zhipin.com/web/geek/jobs?query=&city=101280100",
]

LIST_JS = r"""JSON.stringify((function(){
    var out=[];
    document.querySelectorAll('a,li,span,div').forEach(function(e){
        var t=(e.textContent||'').replace(/\s+/g,'').trim();
        if(!t||t.length>10) return;
        if(e.children.length>0 && e.tagName!=='A') return;
        var r=e.getBoundingClientRect();
        if(r.width<=0||r.height<=0) return;
        if(r.y>140) return;
        out.push({t:t, tag:e.tagName, cls:(e.className||'').toString().slice(0,38),
                  href:(e.getAttribute('href')||'').slice(0,70), x:Math.round(r.x), y:Math.round(r.y)});
    });
    return out.slice(0,35);
})())"""

JOBS_ANY = r"""(function(){
    var out=[];
    var sels=['.job-card-wrap','.job-card-wrapper','.job-card-box','li.job-card-wrapper',
              '[class*="job-card"]','[class*="card-wrapper"]'];
    var seen=new Set();
    sels.forEach(function(sel){
        document.querySelectorAll(sel).forEach(function(c){
            var d=null;
            try{ d=c.__vue__ && c.__vue__.$props && c.__vue__.$props.data; }catch(e){}
            if(d && d.encryptJobId && !seen.has(d.encryptJobId)){
                seen.add(d.encryptJobId);
                out.push({jid:d.encryptJobId, title:d.jobName||'', salary:d.salaryDesc||'',
                          city:d.cityName||'', company:d.brandName||'', degree:d.jobDegree||'',
                          exp:d.jobExperience||''});
            }
        });
    });
    if(!out.length){
        document.querySelectorAll('a[href*="job_detail"]').forEach(function(a){
            var t=(a.textContent||'').replace(/\s+/g,' ').trim();
            if(t) out.push({href:(a.href||'').split('?')[0].split('/').pop(), text:t.slice(0,50)});
        });
    }
    return out;
})()"""


def main():
    for u in PAGES:
        navigate(u)
        time.sleep(4.5)
        v = evaluate(r"""(function(){
            var t=(document.body.innerText||'').replace(/\s+/g,' ');
            return {url:location.href, title:document.title, len:t.length, head:t.slice(0,220)};
        })()""")
        print(f"\n=== {u}")
        print(f"    {v}")
        print("    顶部:", evaluate(LIST_JS))
        jobs = evaluate(JOBS_ANY)
        if isinstance(jobs, str):
            try:
                jobs = json.loads(jobs)
            except Exception:
                pass
        print(f"    岗位 {len(jobs) if isinstance(jobs, list) else '?'} 条")
        if isinstance(jobs, list):
            for j in jobs[:25]:
                print("      ", json.dumps(j, ensure_ascii=False)[:170])
        call("screenshot", {"path": os.path.join(WORK, f"fav_{u.split('/')[-1][:18] or 'x'}.png"), "format": "png"})


if __name__ == "__main__":
    raise SystemExit(main())
