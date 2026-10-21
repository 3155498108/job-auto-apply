#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_scroll2.py — 把 .chat-message 滚到顶部/底部并截图，用于核对历史消息。

用法: python wb_scroll2.py <会话关键词> top|bottom
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate
from scripts.wb import call
from scripts.wb_fiximg import select_conv, log

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")

SCROLL = r"""(function(){
    var b=document.querySelector('.chat-message');
    if(!b) return 'no_box';
    b.scrollTop = __POS__;
    var imgs=[];
    b.querySelectorAll('.message-image img').forEach(function(i,k){
        imgs.push({k:k, src:(i.src||'').slice(-44), w:Math.round(i.getBoundingClientRect().width),
                   top:Math.round(i.getBoundingClientRect().top)});
    });
    return {st:b.scrollTop, sh:b.scrollHeight, ch:b.clientHeight, imgs:imgs};
})()"""


def main():
    kw = sys.argv[1]
    pos = sys.argv[2] if len(sys.argv) > 2 else "top"
    sel, i = select_conv(kw)
    log(f"选中[{i}] {sel}")
    time.sleep(1.5)
    v = evaluate(SCROLL.replace("__POS__", "0" if pos == "top" else "99999"))
    log(f"滚动: {v}")
    time.sleep(1.5)
    out = os.path.join(WORK, f"scroll_{pos}_{kw}.png")
    call("screenshot", {"path": out, "format": "png"})
    log(f"[截图] {out}")


if __name__ == "__main__":
    raise SystemExit(main())
