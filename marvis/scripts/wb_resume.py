#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_resume.py — 点聊天工具栏「发简历」，看能不能把已上传的附件简历直接发出去。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate
from scripts.wb import call

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")

BEFORE = r"""(function(){
    var box=document.querySelector('.chat-record');
    var t=box?(box.textContent||'').replace(/\s+/g,' ').trim():'';
    return 'len='+t.length+' tail='+t.slice(-160);
})()"""

DIALOG = r"""JSON.stringify((function(){
    var out=[];
    document.querySelectorAll('[class*="dialog"],[class*="modal"],[class*="popup"],[class*="mask"]').forEach(function(e){
        var r=e.getBoundingClientRect();
        if(r.width<=0||r.height<=0) return;
        var st=getComputedStyle(e);
        if(st.display==='none'||st.visibility==='hidden') return;
        if(st.opacity==='0') return;
        out.push({cls:(e.className||'').toString().slice(0,60),
                  t:(e.textContent||'').replace(/\s+/g,' ').trim().slice(0,200)});
    });
    return out.slice(0,6);
})())"""

FILES = r"""JSON.stringify(Array.prototype.slice.call(document.querySelectorAll('input[type=file]')).map(function(e,i){
    var r=e.getBoundingClientRect();
    return {i:i, accept:(e.accept||'').slice(0,60), vis:(r.width>0&&r.height>0), cls:(e.className||'').toString().slice(0,30)};
}))"""


def main():
    print("[前]", evaluate(BEFORE))
    r = evaluate(r"""(function(){
        var b=null;
        document.querySelectorAll('div,button,span,a').forEach(function(e){
            var t=(e.textContent||'').replace(/\s+/g,'').trim();
            if(t!=='发简历') return;
            if(e.children.length>0) return;
            var r=e.getBoundingClientRect();
            if(r.width<=0||r.height<=0) return;
            b=e;
        });
        if(!b) return 'no_btn';
        b.click();
        return 'clicked:'+(b.className||'').toString().slice(0,50);
    })()""")
    print(f"[点发简历] {r}")
    time.sleep(2.5)
    print("[弹窗]", evaluate(DIALOG))
    print("[file inputs]", evaluate(FILES))
    call("screenshot", {"path": os.path.join(WORK, "resume_btn.png"), "format": "png"})
    print(f"[截图] {os.path.join(WORK, 'resume_btn.png')}")
    time.sleep(1.5)
    print("[后]", evaluate(BEFORE))


if __name__ == "__main__":
    raise SystemExit(main())
