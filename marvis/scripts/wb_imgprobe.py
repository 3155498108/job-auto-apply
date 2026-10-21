#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_imgprobe.py — 探查 BOSS 聊天工具栏「图片」按钮与文件输入框。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate
from scripts.wb import call

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")

TOOLBAR = r"""JSON.stringify((function(){
    var out=[];
    document.querySelectorAll('button,a,div,span,i,em,label').forEach(function(e){
        var t=(e.textContent||'').replace(/\s+/g,'').trim();
        var c=(e.className||'').toString();
        var hasImg = c.toLowerCase().indexOf('img')>=0 || c.toLowerCase().indexOf('image')>=0
                  || c.toLowerCase().indexOf('photo')>=0 || c.toLowerCase().indexOf('picture')>=0
                  || c.toLowerCase().indexOf('upload')>=0;
        var isIcon = (t==='' || t.length<=4);
        if(!hasImg && !isIcon) return;
        var r=e.getBoundingClientRect();
        if(r.width<=0||r.height<=0) return;
        if(r.y<400) return;                 // 只看底部工具栏
        out.push({tag:e.tagName, cls:c.slice(0,60), t:t.slice(0,20),
                  title:(e.getAttribute('title')||e.getAttribute('aria-label')||'').slice(0,30),
                  x:Math.round(r.x), y:Math.round(r.y), w:Math.round(r.width), h:Math.round(r.height),
                  html:(e.innerHTML||'').slice(0,90)});
    });
    return out.slice(0,25);
})())"""

FILES = r"""JSON.stringify(Array.prototype.slice.call(document.querySelectorAll('input[type=file]')).map(function(e){
    var r=e.getBoundingClientRect();
    return {cls:(e.className||'').toString().slice(0,50), id:e.id||'', accept:e.accept||'',
            multiple:e.multiple, vis:(r.width>0&&r.height>0)};
}))"""

TOOLBAR_TEXT = r"""JSON.stringify((function(){
    var out=[];
    document.querySelectorAll('*').forEach(function(e){
        var t=(e.textContent||'').replace(/\s+/g,'').trim();
        if(['发简历','换电话','换微信'].indexOf(t)<0) return;
        if(e.children.length>0) return;
        var r=e.getBoundingClientRect();
        if(r.width<=0||r.height<=0) return;
        out.push({tag:e.tagName, cls:(e.className||'').toString().slice(0,60), t:t,
                  x:Math.round(r.x), y:Math.round(r.y),
                  parentCls:(e.parentElement?((e.parentElement.className||'').toString().slice(0,60)):''),
                  parentHTML:(e.parentElement?(e.parentElement.innerHTML||'').slice(0,200):'')});
    });
    return out;
})())"""


def main():
    print("[工具栏·图片/图标候选]", evaluate(TOOLBAR))
    print("\n[文件输入框]", evaluate(FILES))
    print("\n[工具栏文本按钮]", evaluate(TOOLBAR_TEXT))
    call("screenshot", {"path": os.path.join(WORK, "imgprobe.png"), "format": "png"})
    print(f"\n[截图] {os.path.join(WORK, 'imgprobe.png')}")


if __name__ == "__main__":
    raise SystemExit(main())
