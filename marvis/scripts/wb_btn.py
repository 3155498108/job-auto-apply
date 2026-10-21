#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_btn.py — 诊断「立即沟通」按钮与 JD 面板的真实 DOM 结构。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import extract_jobs, evaluate
from scripts.jd_reader import click_card_inplace
from scripts.wb import navigate, search_url

DUMP = r"""JSON.stringify((function(){
    function vis(e){var r=e.getBoundingClientRect();return r.width>0&&r.height>0;}
    var out={buttons:[], panels:[]};

    // 所有含「立即沟通 / 继续沟通 / 发送」文本的可见元素
    var all = document.querySelectorAll('a,button,div,span,i,em');
    for (var i=0;i<all.length;i++){
        var e=all[i];
        if(!vis(e)) continue;
        var t=(e.textContent||'').replace(/\s+/g,' ').trim();
        if(!t || t.length>12) continue;
        if(t.indexOf('立即沟通')<0 && t.indexOf('继续沟通')<0 && t.indexOf('发送')<0) continue;
        out.buttons.push({tag:e.tagName, text:t,
            cls:(e.className||'').toString().slice(0,60),
            id:e.id||'', href:e.getAttribute('href')||'',
            rect: (function(){var r=e.getBoundingClientRect();return [Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)];})()});
    }
    // 右侧详情面板候选
    ['.job-detail','.job-detail-box','[class*=detail]','[class*=job-info]','[class*=job-detail]',
     '.job-banner','.job-sec','.job-detail-content','[class*=right]'].forEach(function(s){
        document.querySelectorAll(s).forEach(function(e){
            if(!vis(e)) return;
            out.panels.push({sel:s, cls:(e.className||'').toString().slice(0,60),
                             text:(e.innerText||'').replace(/\s+/g,' ').slice(0,60)});
        });
    });
    return out;
})())"""


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else "Java 后端开发"
    navigate(search_url(query, "101280100"), wait=5)
    jobs = extract_jobs()
    job = None
    for j in jobs:
        if j["company"] == "示例科技A":
            job = j
            break
    if not job:
        print("没找到示例科技A")
        return 1
    print(f"目标: {job['title']} | {job['jobId']}")
    cr = click_card_inplace(job["jobId"], verify=True, max_wait=6)
    print(f"点卡片 ok={cr.get('ok')}")
    time.sleep(2)

    raw = evaluate(DUMP)
    d = json.loads(raw) if raw else {}
    print("\n=== 含沟通/发送文本的可见元素 ===")
    for b in d.get("buttons", []):
        print(f"  <{b['tag']}> text='{b['text']}' cls='{b['cls']}' id='{b['id']}' href='{b['href']}' rect={b['rect']}")
    print("\n=== 详情面板候选 ===")
    for p in d.get("panels", [])[:14]:
        print(f"  {p['sel']:<24} cls={p['cls']:<44} {p['text'][:40]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
