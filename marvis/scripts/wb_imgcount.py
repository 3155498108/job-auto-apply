#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_imgcount.py — 精确统计当前会话里的大图（简历图）数量，并寻找「撤回」入口。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate
from scripts.wb import call

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")

BIG = r"""JSON.stringify((function(){
    var b=document.querySelector('.chat-record');
    if(!b) return 'no_box';
    var out=[];
    b.querySelectorAll('img').forEach(function(i){
        var r=i.getBoundingClientRect();
        if(r.width<80) return;
        var m=i.closest('[class*="message"],[class*="item"],[class*="msg"]');
        out.push({w:Math.round(r.width), h:Math.round(r.height),
                  src:(i.src||'').slice(-46),
                  msgCls:(m?(m.className||'').toString().slice(0,46):'none'),
                  parentCls:(i.parentElement?(i.parentElement.className||'').toString().slice(0,46):'')});
    });
    return out;
})())"""

WITHDRAW = r"""JSON.stringify((function(){
    var out=[];
    document.querySelectorAll('*').forEach(function(e){
        var t=(e.textContent||'').replace(/\s+/g,'').trim();
        if(t!=='撤回' && t!=='删除' && t!=='重新编辑') return;
        if(e.children.length>0) return;
        var r=e.getBoundingClientRect();
        if(r.width<=0||r.height<=0) return;
        out.push({t:t, tag:e.tagName, cls:(e.className||'').toString().slice(0,50),
                  x:Math.round(r.x), y:Math.round(r.y)});
    });
    return out;
})())"""

# 消息气泡上的 hover 菜单/更多按钮
MENUS = r"""JSON.stringify((function(){
    var out=[];
    document.querySelectorAll('.chat-record [class*="menu"],[class*="more"],[class*="operation"],[class*="action"],[class*="tool"]').forEach(function(e){
        var r=e.getBoundingClientRect();
        if(r.width<=0||r.height<=0) return;
        out.push({cls:(e.className||'').toString().slice(0,55), x:Math.round(r.x), y:Math.round(r.y),
                  w:Math.round(r.width), h:Math.round(r.height),
                  html:(e.innerHTML||'').replace(/\s+/g,' ').slice(0,110)});
    });
    return out.slice(0,14);
})())"""


def main():
    print("[大图]", evaluate(BIG))
    print("\n[撤回/删除元素]", evaluate(WITHDRAW))
    print("\n[消息区菜单]", evaluate(MENUS))


if __name__ == "__main__":
    raise SystemExit(main())
