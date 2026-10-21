#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_msglist.py — 按顺序 dump 聊天记录区每个消息节点的内容，确定 HR 实际看到几条。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate
from scripts.wb import call
from scripts.wb_fiximg import select_conv, log

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")

DUMP = r"""JSON.stringify((function(){
    var b=document.querySelector('.chat-record');
    if(!b) return 'no_box';
    var out=[];
    // 找出所有直接承载消息的节点
    var nodes=b.querySelectorAll('.message-item, [class*="message-"], [class*="item-message"]');
    nodes.forEach(function(e,i){
        var r=e.getBoundingClientRect();
        var t=(e.textContent||'').replace(/\s+/g,' ').trim();
        out.push({i:i, cls:(e.className||'').toString().slice(0,44),
                  top:Math.round(r.top), h:Math.round(r.height),
                  imgs:e.querySelectorAll('img').length,
                  msgImgs:e.querySelectorAll('.message-image').length,
                  t:t.slice(0,60)});
    });
    // 同时给出 chat-record 的直接子节点
    var kids=[];
    for(var k=0;k<b.children.length;k++){
        var c=b.children[k];
        var r=c.getBoundingClientRect();
        kids.push({cls:(c.className||'').toString().slice(0,40), top:Math.round(r.top),
                   h:Math.round(r.height), imgs:c.querySelectorAll('.message-image').length,
                   t:(c.textContent||'').replace(/\s+/g,' ').trim().slice(0,50)});
    }
    return {nodes:nodes.slice(0,40), kids:kids.slice(0,40)};
})())"""


def main():
    kw = sys.argv[1]
    sel, i = select_conv(kw)
    log(f"选中[{i}] {sel}")
    time.sleep(1.5)
    raw = evaluate(DUMP)
    try:
        d = json.loads(raw)
    except Exception:
        print(raw)
        return
    log("--- 消息节点 ---")
    for n in d.get("nodes", []):
        log(f"  [{n['i']:>2}] top={n['top']:>5} h={n['h']:>4} imgs={n['imgs']} msgImg={n['msgImgs']} "
            f"cls={n['cls']:<40} | {n['t']}")
    log("--- 直接子节点 ---")
    for n in d.get("kids", []):
        log(f"  top={n['top']:>5} h={n['h']:>4} msgImg={n['imgs']} cls={n['cls']:<38} | {n['t']}")


if __name__ == "__main__":
    raise SystemExit(main())
