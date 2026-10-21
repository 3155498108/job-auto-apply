#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_imgfix.py — 找「撤回」入口 + 精确核对每个会话的图片消息数。

用法:
    python wb_imgfix.py probe <会话关键词>   # 悬停图片消息，找撤回/删除按钮
    python wb_imgfix.py verify               # 逐个精确核对
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate
from scripts.wb import call
from scripts.wb_fiximg import select_conv, log

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")

ACCURATE = r"""JSON.stringify((function(){
    var b=document.querySelector('.chat-record');
    if(!b) return 'no_box';
    var imgs=[];
    b.querySelectorAll('.message-image').forEach(function(e,i){
        var r=e.getBoundingClientRect();
        var srcs=[];
        e.querySelectorAll('img').forEach(function(im){ srcs.push((im.src||'').slice(-34)); });
        imgs.push({i:i, top:Math.round(r.top), h:Math.round(r.height), srcs:srcs});
    });
    return imgs;
})())"""

HOVER = r"""JSON.stringify((function(){
    var b=document.querySelector('.chat-record');
    if(!b) return 'no_box';
    var list=b.querySelectorAll('.message-image');
    var target=list[__IDX__] || list[0];
    if(!target) return 'no_img';
    var r=target.getBoundingClientRect();
    var x=r.left+r.width/2, y=r.top+r.height/2;
    ['mouseover','mouseenter','mousemove'].forEach(function(t){
        target.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,clientX:x,clientY:y}));
    });
    var found=[];
    var scope=target.parentElement ? target.parentElement.parentElement : b;
    scope.querySelectorAll('*').forEach(function(e){
        var t=(e.textContent||'').replace(/\s+/g,'').trim();
        if(!t||t.length>8) return;
        if(e.children.length>0) return;
        var rr=e.getBoundingClientRect();
        if(rr.width<=0||rr.height<=0) return;
        found.push({t:t, tag:e.tagName, cls:(e.className||'').toString().slice(0,50),
                    x:Math.round(rr.x), y:Math.round(rr.y)});
    });
    return {scopeCls:(scope.className||'').toString().slice(0,60), found:found.slice(0,18),
            html:(scope.innerHTML||'').replace(/\s+/g,' ').slice(0,600)};
})())"""

# 消息容器上可能出现的图标按钮（无文字）
ICONS = r"""JSON.stringify((function(){
    var b=document.querySelector('.chat-record');
    if(!b) return 'no_box';
    var out=[];
    b.querySelectorAll('[class*="message"],[class*="item"]').forEach(function(m){
        var r=m.getBoundingClientRect();
        if(r.width<=0||r.height<=0) return;
        m.querySelectorAll('i,em,span[class*="icon"],div[class*="icon"],svg,use,img[class*="icon"]').forEach(function(e){
            var rr=e.getBoundingClientRect();
            if(rr.width<=0||rr.height<=0) return;
            if(rr.width>40) return;
            out.push({cls:(e.className||'').toString().slice(0,45), tag:e.tagName,
                      href:(e.getAttribute('href')||e.getAttribute('xlink:href')||'').slice(-40),
                      x:Math.round(rr.x), y:Math.round(rr.y), w:Math.round(rr.width)});
        });
    });
    return out.slice(0,20);
})())"""


def cmd_probe(kw):
    sel, i = select_conv(kw)
    log(f"选中[{i}] {sel}")
    time.sleep(1)
    log(f"图片: {evaluate(ACCURATE)}")
    for idx in (0, 1):
        log(f"\n--- 悬停第 {idx} 张 ---")
        log(f"hover: {evaluate(HOVER.replace('__IDX__', str(idx)))}")
        time.sleep(0.8)
    log(f"\nicons: {evaluate(ICONS)}")
    call("screenshot", {"path": os.path.join(WORK, f"probe_{kw}.png"), "format": "png"})


TARGETS = ["候选人D女士示例科技Y", "候选人A女士示例科技Y", "候选人G先生示例文化B", "候选人I女士示例讯动U", "候选人J先生示例科技V",
           "候选人F女士示例平台I", "候选人B女士示例科技C", "候选人H女士示例科技D", "候选人B女士示例网络E",
           "候选人E先生示例传媒T", "候选人N先生示例数据科技", "候选人O广州示例软件F", "候选人C女士广州示例云服务G"]


def cmd_verify():
    summary = []
    for kw in TARGETS:
        sel, i = select_conv(kw)
        raw = evaluate(ACCURATE)
        try:
            d = json.loads(raw) if raw else []
        except Exception:
            d = []
        tops = [x.get("top") for x in d] if isinstance(d, list) else d
        log(f"{kw:<16} 大图 {len(d) if isinstance(d,list) else '?'}  tops={tops}")
        summary.append(dict(conv=kw, n=len(d) if isinstance(d, list) else -1, tops=tops))
    out = os.path.join(WORK, "img_verify.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    log(f"[结果] {out}")


def main():
    cmd = sys.argv[1]
    if cmd == "probe":
        cmd_probe(sys.argv[2])
    elif cmd == "verify":
        cmd_verify()


if __name__ == "__main__":
    raise SystemExit(main())
