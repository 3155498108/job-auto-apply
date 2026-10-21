#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_targets.py — 逐个点开待回会话，读取其岗位卡（公司 + 岗位名）与最后几条消息。"""
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
        out.push({i:i, y:Math.round(r.top), t:(e.textContent||'').replace(/\s+/g,' ').trim().slice(0,60)});
    });
    return out;
})())"""

HEAD_JS = r"""JSON.stringify((function(){
    var who=document.querySelector('.name-box')||document.querySelector('.name-content');
    var pos=document.querySelector('.position-name');
    var sal=document.querySelector('.position-content');
    return {who:(who?who.textContent:'').replace(/\s+/g,' ').trim(),
            pos:(pos?pos.textContent:'').replace(/\s+/g,' ').trim(),
            posall:(sal?sal.textContent:'').replace(/\s+/g,' ').trim().slice(0,120)};
})())"""

MSGS_JS = r"""JSON.stringify((function(){
    var out=[];
    document.querySelectorAll('.chat-record .message-item, .chat-record .item-message, .chat-record [class*="message"]').forEach(function(e){
        var t=(e.textContent||'').replace(/\s+/g,' ').trim();
        if(t && out.indexOf(t)<0) out.push(t.slice(0,220));
    });
    if(!out.length){
        var box=document.querySelector('.chat-record');
        if(box) out=[(box.textContent||'').replace(/\s+/g,' ').trim().slice(0,500)];
    }
    return out;
})())"""


def main():
    kws = sys.argv[1:]
    raw = evaluate(LIST_JS)
    convs = json.loads(raw) if raw else []
    for c in convs:
        if not any(k in c["t"] for k in kws):
            continue
        evaluate(r"""(function(){
            var list=document.querySelectorAll('.friend-content');
            var e=list[%d]; if(!e) return 'gone';
            e.scrollIntoView({block:'center'}); e.click(); return 'clicked';
        })()""" % c["i"])
        time.sleep(4.0)
        h = evaluate(HEAD_JS)
        m = evaluate(MSGS_JS)
        try:
            h = json.loads(h)
        except Exception:
            h = {"_raw": str(h)[:200]}
        try:
            m = json.loads(m)
        except Exception:
            m = [str(m)[:200]]
        print(f"\n{'='*72}")
        print(f"[{c['i']}] {c['t'][:55]}")
        print(f"  对方: {h.get('who')}")
        print(f"  岗位: {h.get('pos')}   | {h.get('posall')}")
        for x in (m or [])[-4:]:
            print(f"   · {x}")
    call("screenshot", {"path": os.path.join(WORK, "targets.png"), "format": "png"})


if __name__ == "__main__":
    raise SystemExit(main())
