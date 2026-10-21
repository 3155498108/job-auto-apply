#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_diag.py — 逐帧诊断：点卡片后详情面板与「立即沟通」的出现时机。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import extract_jobs, evaluate
from scripts.jd_reader import click_card_inplace
from scripts.wb import navigate, search_url

PROBE = r"""JSON.stringify((function(){
    function vis(e){var r=e.getBoundingClientRect();return r.width>0&&r.height>0;}
    var bodyTxt = document.body.innerText || '';
    var box = document.querySelector('.job-detail-box');
    var loading = document.querySelector('.job-detail-loading');
    var btn = null;
    document.querySelectorAll('a,button,span,div').forEach(function(e){
        if(btn) return;
        var t=(e.textContent||'').replace(/\s+/g,'').trim();
        if(t!=='立即沟通' && t!=='继续沟通') return;
        if(!vis(e)) return;
        btn={tag:e.tagName, cls:(e.className||'').toString().slice(0,50),
             text:t, rect:[Math.round(e.getBoundingClientRect().x),Math.round(e.getBoundingClientRect().y),
                           Math.round(e.getBoundingClientRect().width),Math.round(e.getBoundingClientRect().height)]};
    });
    return {
        bodyLen: bodyTxt.length,
        hasChat: bodyTxt.indexOf('立即沟通')>=0,
        boxLen: box ? (box.innerText||'').length : -1,
        boxHasChat: box ? (box.innerText||'').indexOf('立即沟通')>=0 : false,
        loading: !!loading,
        btn: btn,
        tail: bodyTxt.replace(/\s+/g,' ').slice(-260)
    };
})())"""


def main():
    navigate(search_url("Java 后端开发", "101280100"))
    time.sleep(3)
    jobs = extract_jobs()
    job = next((j for j in jobs if j["company"] == "示例科技A" and j["city"] == "广州"), None)
    if not job:
        print("没找到示例科技A(广州)")
        return 1
    print(f"目标 {job['title']}  jobId={job['jobId']}")

    # 先测一次 evaluate 单表达式（不包 IIFE）
    t = evaluate("(document.body.innerText||'').length")
    print(f"[evaluate 单表达式测试] 返回={t!r}  类型={type(t).__name__}")

    cr = click_card_inplace(job["jobId"], verify=True, max_wait=8)
    print(f"[点卡片] ok={cr.get('ok')} detail={cr.get('detail')}")

    for i in range(8):
        time.sleep(2)
        raw = evaluate(PROBE)
        try:
            d = json.loads(raw)
        except Exception:
            print(f"  #{i+1} 解析失败: {str(raw)[:120]}")
            continue
        print(f"  #{i+1} bodyLen={d['bodyLen']:<6} hasChat={str(d['hasChat']):<5} "
              f"boxLen={d['boxLen']:<5} boxHasChat={str(d['boxHasChat']):<5} loading={str(d['loading']):<5} "
              f"btn={d['btn']}")
        if d.get("hasChat"):
            print(f"      命中！tail: {d['tail'][-160:]}")
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
