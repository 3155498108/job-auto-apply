#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_dumpconv.py — 导出指定会话的完整聊天记录（用于写回复话术）。

用法: python wb_dumpconv.py <关键词1> [关键词2] ...
不带参数 = 导出全部会话摘要
"""
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
        out.push({i:i, y:Math.round(r.top), cls:(e.className||''),
                  t:(e.textContent||'').replace(/\s+/g,' ').trim().slice(0,70)});
    });
    return out;
})())"""

DUMP_JS = r"""JSON.stringify((function(){
    var head='';
    var h=document.querySelector('.name-box,.name-content');
    if(h) head=(h.textContent||'').replace(/\s+/g,' ').trim();
    var pos='';
    var p=document.querySelector('.position-name');
    if(p) pos=(p.textContent||'').replace(/\s+/g,' ').trim();
    var msgs=[];
    document.querySelectorAll('.message-item,.chat-item,.msg-item,.message-content').forEach(function(e){
        var t=(e.textContent||'').replace(/\s+/g,' ').trim();
        if(t) msgs.push(t.slice(0,200));
    });
    if(!msgs.length){
        // 兜底：抓消息区全文
        var box=document.querySelector('.chat-record,.message-list,.chat-content,.chat-box');
        if(box) msgs.push(((box.textContent||'').replace(/\s+/g,' ').trim()).slice(0,600));
    }
    return {head:head, pos:pos, msgs:msgs};
})())"""


def main():
    kws = sys.argv[1:]
    raw = evaluate(LIST_JS)
    convs = json.loads(raw) if raw else []
    if not kws:
        for c in convs:
            print(f"[{c['i']:>2}] {c['t']}")
        return 0

    for c in convs:
        if not any(k in c["t"] for k in kws):
            continue
        r = evaluate(r"""(function(){
            var list=document.querySelectorAll('.friend-content');
            var e=list[%d]; if(!e) return 'gone';
            e.scrollIntoView({block:'center'}); e.click(); return 'clicked';
        })()""" % c["i"])
        time.sleep(2.2)
        d = evaluate(DUMP_JS)
        try:
            d = json.loads(d)
        except Exception:
            d = {"_raw": str(d)[:400]}
        print(f"\n{'='*70}")
        print(f"[{c['i']}] {c['t']}  ({r})")
        print(f"对方: {d.get('head')}   岗位: {d.get('pos')}")
        for m in d.get("msgs", []):
            print(f"  · {m}")

    call("screenshot", {"path": os.path.join(WORK, "dumpconv.png"), "format": "png"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
