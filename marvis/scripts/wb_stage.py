#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_stage.py — 分步投递：定位岗位 → 读 JD → 填话术 → 停在「发送」前。

刻意不点「发送」：那一步对外可见且不可撤回，必须由用户确认后再执行。

用法：
    python wb_stage.py <搜索词> <岗位关键词> <公司关键词>
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import extract_jobs, evaluate
from scripts.jd_reader import read_jd_for_job
from scripts.deliver_engine import fill_greeting, pick_greeting_for_job
from scripts.wb import navigate, search_url

SHOT = os.path.join(os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work"),
                    "stage_shot.png")


def find_job(query, role_kw, company_kw):
    navigate(search_url(query, "101280100"), wait=5)
    jobs = extract_jobs()
    print(f"[搜索] {query}  提取 {len(jobs)} 条")
    best = None
    for j in jobs:
        if role_kw and role_kw not in j["title"]:
            continue
        if company_kw and company_kw not in j["company"]:
            continue
        if best is None:
            best = j
    return best, jobs


def main():
    query = sys.argv[1]
    role_kw = sys.argv[2] if len(sys.argv) > 2 else ""
    company_kw = sys.argv[3] if len(sys.argv) > 3 else ""

    job, jobs = find_job(query, role_kw, company_kw)
    if not job:
        print("!! 未找到匹配岗位")
        for j in jobs:
            print(f"   {j['title'][:32]:<34} {j['salary'][:12]:<14} {j['company'][:18]}")
        return 2

    print(f"[命中] {job['title']} | {job['salary']} | {job['company']} | {job['city']} | {job['degree']}")
    print(f"       jobId={job['jobId']}")

    # 1) 点卡片 + 读 JD
    jd = read_jd_for_job(job["jobId"])
    print(f"[JD] ok={jd.get('ok')} 标题={jd.get('title','')[:40]}")
    full = jd.get("full_text", "")
    print(f"     正文 {len(full)} 字，前 200 字：{full[:200].strip()}")

    # 2) 选话术
    text, meta = pick_greeting_for_job(job)
    print(f"[话术] 来源={meta.get('source')} 命中文件夹={meta.get('folder') or '(通用)'}")
    print(f"       变体={meta.get('variant')}  长度={len(text)} 字")
    print(f"       PDF={os.path.basename(meta.get('pdf') or '(无)')}")
    print(f"       内容: {text[:120]}...")

    # 3) 点「立即沟通」（此时尚未发送，仅打开打招呼弹窗）
    clicked = evaluate(r"""(function(){
        var btn = document.querySelector('.op-btn-chat');
        if (!btn) btn = document.querySelector('.btn-startchat, .job-chat-btn');
        if (!btn) return 'not_found';
        var t = btn.textContent.trim();
        if (t.indexOf('继续沟通') >= 0) return 'already:' + t;
        btn.scrollIntoView({block:'center'});
        btn.click();
        return 'clicked:' + t;
    })()""")
    print(f"[沟通] {clicked}")
    time.sleep(2.5)

    # 4) 填话术（不点发送）
    raw = fill_greeting(text)
    try:
        info = json.loads(raw)
    except Exception:
        info = {"raw": raw}
    print(f"[填充] {info}")

    # 5) 读回输入框真实状态
    state = evaluate(r"""JSON.stringify((function(){
        var sels='textarea, input[type="text"], [contenteditable="true"]';
        var roots=document.querySelectorAll('.dialog-wrap, .greet-pop, .dialog-container, .layer-dialog, .modal, .ant-modal-wrap, .layer-ext');
        var cands=[];
        for(var i=0;i<roots.length;i++){
            var rr=roots[i].getBoundingClientRect();
            if(rr.width>0&&rr.height>0){ var es=roots[i].querySelectorAll(sels); for(var j=0;j<es.length;j++) cands.push(es[j]); }
        }
        if(!cands.length) cands=document.querySelectorAll(sels);
        for(var m=0;m<cands.length;m++){
            var el=cands[m];
            var r2=el.getBoundingClientRect();
            if(r2.width<=0||r2.height<=0) continue;
            var v = (el.value!==undefined&&el.value!==null)?el.value:(el.textContent||'');
            var btn=null;
            var dlg=el.closest('.dialog-wrap, .greet-pop, .dialog-container, .layer-dialog, .modal, .ant-modal-wrap, .layer-ext');
            var scope=dlg||document;
            var bs=scope.querySelectorAll('a,button,.btn,.dialog-btn,.btn-sure');
            for(var b=0;b<bs.length;b++){ var tx=(bs[b].textContent||'').trim(); if(tx==='发送'||tx==='确定'||tx==='发送招呼'||tx==='好'||tx==='发送消息'){ btn=tx; break; } }
            return JSON.stringify({found:true, kind: el.tagName, maxlength: el.getAttribute('maxlength')||'', len: v.length, sample: v.slice(0,60), sendBtn: btn||''});
        }
        return JSON.stringify({found:false});
    })())""")
    print(f"[输入框] {state}")

    # 6) 截图
    r = evaluate("1")
    from scripts.wb import call
    shot = call("screenshot", {"path": SHOT, "format": "png"})
    print(f"[截图] {SHOT}")
    print(shot.get("data", shot))

    print("\n" + "=" * 66)
    print("已停在「发送」按钮前。确认无误后回复『发送』，我再点发送。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
