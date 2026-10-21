#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_jd.py — 抓取目标岗位的 JD 全文（职位描述 + 任职要求）。

数据源：job_detail 独立页 https://www.zhipin.com/job_detail/{jobId}.html
用法: python wb_jd.py <targets.json> [label ...]
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate
from scripts.wb import call, navigate

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")

JD_JS = r"""(function(){
    function vis(e){var r=e.getBoundingClientRect();return r.width>0&&r.height>0;}
    var out=[];
    var sels=['.job-sec-text','.job-detail-section .text','.job-description',
              '.job-detail .text','[class*="job-desc"]','[class*="jobDescription"]',
              '.job-sec-content','.text-cont','.job-detail-section'];
    for(var i=0;i<sels.length;i++){
        document.querySelectorAll(sels[i]).forEach(function(e){
            if(!vis(e)) return;
            var t=(e.innerText||e.textContent||'').replace(/\s+/g,' ').trim();
            if(t && t.length>40) out.push(t);
        });
    }
    // 去重后拼起来
    var seen={}, all=[];
    out.forEach(function(t){ if(!seen[t]){ seen[t]=1; all.push(t); } });
    var body=(document.body.innerText||'').replace(/\s+/g,' ');
    var pos=document.querySelector('.job-banner .name, h1.name, .job-name, .job-title');
    var sal=document.querySelector('.salary, .job-banner .salary');
    var exp=document.querySelector('.tag-list, .job-info .tag');
    return JSON.stringify({
        position: pos?(pos.textContent||'').trim():'',
        salary: sal?(sal.textContent||'').trim():'',
        jd: all.join('\n').slice(0,4000),
        body: body.slice(0,3000)
    });
})()"""


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def main():
    tpath = sys.argv[1]
    only = set(sys.argv[2:])
    targets = json.load(open(tpath, encoding="utf-8"))
    out_path = os.path.join(WORK, "jd_text.json")
    data = {}
    if os.path.isfile(out_path):
        try:
            data = json.load(open(out_path, encoding="utf-8"))
        except Exception:
            data = {}
    for t in targets:
        label = t["label"]
        if only and label not in only:
            continue
        if label in data and len(data[label].get("jd", "")) > 200:
            log(f"跳过（已有） {label}")
            continue
        jid = t["jobId"]
        navigate(f"https://www.zhipin.com/job_detail/{jid}.html")
        time.sleep(4.2)
        raw = evaluate(JD_JS)
        try:
            v = json.loads(raw) if isinstance(raw, str) else (raw or {})
        except Exception:
            v = {}
        jd = v.get("jd") or ""
        if not jd:
            # 回退：从整页正文里截「职位描述」到「职位已关闭/公司介绍」之间
            b = v.get("body", "")
            i = b.find("职位描述")
            j = b.find("公司介绍", i)
            jd = b[i:j] if i >= 0 else b[:1500]
        data[label] = dict(jobId=jid, position=v.get("position", ""),
                           salary=v.get("salary", ""), jd=jd[:3000])
        log(f"  {label:<46} JD {len(jd)} 字")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        time.sleep(1.0)
    log(f"[结果] {out_path} 共 {len(data)} 条")


if __name__ == "__main__":
    main()
