#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_dupcheck.py — 检查各目标会话的最后一条消息，判断是否已发过定制话术。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate
from scripts.wb import call

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")
MARKER = "我是计算机专业"

LIST_JS = r"""JSON.stringify((function(){
    var out=[];
    document.querySelectorAll('.friend-content').forEach(function(e,i){
        var r=e.getBoundingClientRect();
        if(r.width<=0||r.height<=0) return;
        out.push({i:i, y:Math.round(r.top), t:(e.textContent||'').replace(/\s+/g,' ').trim().slice(0,90)});
    });
    return out;
})())"""

# 找页面里所有「含我们话术」的元素，用来反推真实的消息节点 class
DOM_PROBE = r"""JSON.stringify((function(){
    var hits=[];
    document.querySelectorAll('*').forEach(function(e){
        if(e.children.length>0) return;              // 只看叶子节点
        var t=(e.textContent||'').replace(/\s+/g,' ').trim();
        if(t.indexOf('__MARK__')>=0 && t.length<400){
            hits.push({cls:(e.className||'').toString().slice(0,60), tag:e.tagName, t:t.slice(0,60)});
        }
    });
    return hits.slice(0,8);
})())"""

# 选中会话的聊天区结构
CHAT_DOM = r"""JSON.stringify((function(){
    var out=[];
    document.querySelectorAll('div,li,p,span').forEach(function(e){
        var t=(e.textContent||'').replace(/\s+/g,' ').trim();
        if(!t || t.length>300) return;
        if(t.indexOf('__MARK__')<0) continue;
        out.push({tag:e.tagName, cls:(e.className||'').toString().slice(0,70), len:t.length, t:t.slice(0,50)});
    });
    return out.slice(0,20);
})())"""


def main():
    print("=== 当前页面结构探测 ===")
    for js, name in ((DOM_PROBE, "叶子节点"), (CHAT_DOM, "全部节点")):
        raw = evaluate(js.replace("__MARK__", MARKER))
        print(f"[{name}] {raw[:1200]}")

    print("\n=== 会话列表状态 ===")
    raw = evaluate(LIST_JS)
    convs = json.loads(raw) if raw else []
    for c in convs:
        mark = "★已发" if MARKER in c["t"] else ("·默认" if "我对您发布的职位" in c["t"] else "  ")
        print(f"[{c['i']:>2}] {mark} {c['t']}")
    call("screenshot", {"path": os.path.join(WORK, "dupcheck.png"), "format": "png"})


if __name__ == "__main__":
    raise SystemExit(main())
