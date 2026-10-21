#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_scrolltop.py — 把聊天记录滚到顶部，数清一共有几张图片消息。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate
from scripts.wb import call

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")

SCROLL = r"""(function(){
    var b=document.querySelector('.chat-record');
    if(!b) return 'no_box';
    var sc=b.scrollTop||b.parentElement.scrollTop||0;
    b.scrollTop=0; if(b.parentElement) b.parentElement.scrollTop=0;
    return 'scrolled from '+sc;
})()"""

COUNT = r"""JSON.stringify((function(){
    var b=document.querySelector('.chat-record');
    if(!b) return 'no_box';
    var out=[];
    b.querySelectorAll('.message-image').forEach(function(e,i){
        var imgs=[];
        e.querySelectorAll('img').forEach(function(im){ imgs.push((im.src||'').slice(-40)); });
        var r=e.getBoundingClientRect();
        out.push({i:i, top:Math.round(r.top), h:Math.round(r.height), srcs:imgs});
    });
    var txts=[];
    b.querySelectorAll('.message-text, [class*="message-text"]').forEach(function(e){
        txts.push((e.textContent||'').replace(/\s+/g,' ').trim().slice(0,45));
    });
    return {imgs:out, texts:txts.slice(-6)};
})())"""


def main():
    kw = sys.argv[1]
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from scripts.wb_fiximg import select_conv, log
    sel, i = select_conv(kw)
    log(f"选中[{i}] {sel}")
    time.sleep(1)
    log(f"滚动: {evaluate(SCROLL)}")
    time.sleep(1.5)
    raw = evaluate(COUNT)
    try:
        d = json.loads(raw)
    except Exception:
        d = raw
    log(f"图片消息: {json.dumps(d, ensure_ascii=False)[:1200]}")
    call("screenshot", {"path": os.path.join(WORK, f"top_{kw}.png"), "format": "png"})


if __name__ == "__main__":
    raise SystemExit(main())
