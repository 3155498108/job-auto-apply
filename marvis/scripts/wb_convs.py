#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_convs.py — 列出全部会话及其关联岗位/公司，逐个点开看头部职位卡。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate
from scripts.wb import call

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")

LIST_JS = r"""JSON.stringify((function(){
    var out=[];
    document.querySelectorAll('.friend-content').forEach(function(e,i){
        var r=e.getBoundingClientRect();
        if(r.width<=0||r.height<=0) return;
        out.push({i:i, top:Math.round(r.top), cls:(e.className||''),
                  t:(e.textContent||'').replace(/\s+/g,' ').trim().slice(0,60)});
    });
    return out;
})())"""

HEADER_JS = r"""(function(){
    var t=(document.body.innerText||'').replace(/\s+/g,' ');
    var head=document.querySelector('.chat-info,.info-wrapper,.user-info,.chat-header');
    var h=head?((head.textContent||'').replace(/\s+/g,' ').trim().slice(0,160)):'';
    var job='';
    document.querySelectorAll('a,div,span').forEach(function(e){
        var c=(e.className||'').toString();
        if(c.indexOf('job')>=0 && c.indexOf('name')>=0){
            var tt=(e.textContent||'').replace(/\s+/g,' ').trim();
            if(tt && tt.length<80 && job.indexOf(tt)<0) job=tt;
        }
    });
    var msgs=[];
    document.querySelectorAll('.message-item,.chat-message,.msg-item').forEach(function(e){
        msgs.push((e.textContent||'').replace(/\s+/g,' ').trim().slice(0,80));
    });
    return JSON.stringify({h:h, job:job, msgs:msgs.slice(0,6), head: t.slice(0,260)});
})()"""


def main():
    raw = evaluate(LIST_JS)
    convs = json.loads(raw) if raw else []
    print(f"[会话数] {len(convs)}")
    for c in convs:
        print(f"  [{c['i']:>2}] y={c['top']:>4} {'*' if 'selected' in c['cls'] else ' '} {c['t']}")

    # 逐个点开示例科技Y相关会话
    targets = [c for c in convs if "示例科技Y" in c["t"]]
    print(f"\n[示例科技Y会话] {len(targets)} 个")
    for c in targets:
        idx = c["i"]
        r = evaluate(r"""(function(){
            var list=document.querySelectorAll('.friend-content');
            var e=list[%d];
            if(!e) return 'gone';
            e.scrollIntoView({block:'center'});
            e.click();
            return 'clicked';
        })()""" % idx)
        time.sleep(2.5)
        info = evaluate(HEADER_JS)
        try:
            d = json.loads(info)
        except Exception:
            d = {"_raw": str(info)[:300]}
        print(f"\n--- [{idx}] {c['t'][:40]}  ({r})")
        print(f"    头部: {d.get('h')}")
        print(f"    职位: {d.get('job')}")
        for m in d.get("msgs", []):
            print(f"    消息: {m}")

    call("screenshot", {"path": os.path.join(WORK, "convs.png"), "format": "png"})


if __name__ == "__main__":
    raise SystemExit(main())
