#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_fiximg.py — 选会话（按 DOM 顺序）+ 查撤回入口 + 发图补发。

用法:
    python wb_fiximg.py sel <关键词>            # 选中并报告
    python wb_fiximg.py hover <关键词>          # 悬停最后一条图片消息，找撤回入口
    python wb_fiximg.py send <关键词> <图片路径> # 补发（幂等）
    python wb_fiximg.py verify                   # 逐个核对 12 个会话的大图数
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate
from scripts.wb import call

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")
IMG_SELECTOR = ".btn-sendimg input[type=file]"

LIST_JS = r"""JSON.stringify((function(){
    var out=[];
    document.querySelectorAll('.friend-content').forEach(function(e,i){
        out.push({i:i, t:(e.textContent||'').replace(/\s+/g,' ').trim().slice(0,70)});
    });
    return out;
})())"""

IMGS_JS = r"""JSON.stringify(Array.prototype.slice.call(
    document.querySelectorAll('.chat-record .message-image')).map(function(e,i){
        var img=e.querySelector('img');
        var r=img?img.getBoundingClientRect():{width:0,height:0};
        return {i:i, w:Math.round(r.width), h:Math.round(r.height),
                src:img?(img.src||'').slice(-42):''};
    }))"""

HOVER_PROBE = r"""JSON.stringify((function(){
    var imgs=document.querySelectorAll('.chat-record .message-image');
    if(!imgs.length) return 'no_img_msg';
    var last=imgs[imgs.length-1];
    var r=last.getBoundingClientRect();
    var x=r.left+r.width/2, y=r.top+r.height/2;
    ['mouseover','mouseenter','mousemove','mousedown','mouseup','click'].forEach(function(t){
        last.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,clientX:x,clientY:y}));
    });
    // 再看看消息容器上有没有出现操作按钮
    var menu=[];
    var box=last.closest('[class*="message"],[class*="item"]')||last;
    box.querySelectorAll('*').forEach(function(e){
        var t=(e.textContent||'').replace(/\s+/g,'').trim();
        if(!t||t.length>6) return;
        if(e.children.length>0) return;
        var rr=e.getBoundingClientRect();
        if(rr.width<=0||rr.height<=0) return;
        menu.push({t:t, cls:(e.className||'').toString().slice(0,45), x:Math.round(rr.x), y:Math.round(rr.y)});
    });
    return {menu:menu.slice(0,12), html:(box.innerHTML||'').replace(/\s+/g,' ').slice(0,400)};
})())"""


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def select_conv(kw):
    """按 DOM 顺序选会话（DOM 顺序 = 最新在前），不用 y 坐标。"""
    raw = evaluate(LIST_JS)
    try:
        convs = json.loads(raw) if raw else []
    except Exception:
        return "list_failed", -1
    hits = [c for c in convs if kw in c["t"]]
    if not hits:
        return "not_found", -1
    best = hits[0]                       # DOM 顺序第一个 = 最新
    evaluate(r"""(function(){
        var list=document.querySelectorAll('.friend-content');
        var e=list[%d]; if(!e) return 'gone';
        e.scrollIntoView({block:'center'}); e.click(); return 'clicked';
    })()""" % best["i"])
    time.sleep(2.5)
    sel = evaluate(r"""(function(){
        var s=document.querySelector('.friend-content.selected');
        return s?((s.textContent||'').replace(/\s+/g,' ').trim().slice(0,60)):'none';
    })()""")
    return sel, best["i"]


def imgs():
    raw = evaluate(IMGS_JS)
    try:
        return json.loads(raw) if raw else []
    except Exception:
        return []


def cmd_sel(kw):
    sel, i = select_conv(kw)
    log(f"选中[{i}] {sel}")
    log(f"大图: {json.dumps(imgs(), ensure_ascii=False)}")
    call("screenshot", {"path": os.path.join(WORK, f"sel_{kw}.png"), "format": "png"})


def cmd_hover(kw):
    sel, i = select_conv(kw)
    log(f"选中[{i}] {sel}")
    log(f"大图: {json.dumps(imgs(), ensure_ascii=False)}")
    log(f"悬停探测: {evaluate(HOVER_PROBE)}")
    time.sleep(1)
    call("screenshot", {"path": os.path.join(WORK, f"hover_{kw}.png"), "format": "png"})


def cmd_send(kw, path):
    sel, i = select_conv(kw)
    log(f"选中[{i}] {sel}")
    before = len(imgs())
    log(f"现有大图 {before}")
    if before >= 1:
        log("已有图，跳过")
        return
    r = call("upload", {"selector": IMG_SELECTOR, "files": [path]})
    if not r.get("ok"):
        log(f"上传失败 {json.dumps(r, ensure_ascii=False)[:200]}")
        return
    after = before
    for _ in range(10):
        time.sleep(2.0)
        after = len(imgs())
        if after > before:
            break
    log(f"大图 {before} → {after}")
    call("screenshot", {"path": os.path.join(WORK, f"img_{kw}.png"), "format": "png"})


def cmd_verify():
    targets = ["候选人F女士示例科技Y", "候选人A女士示例科技Y", "候选人G先生示例文化B", "候选人I女士示例讯动U", "候选人J先生示例科技V",
               "候选人K女士示例平台I", "候选人D女士示例科技C", "候选人H女士示例科技D", "候选人D女士示例网络E",
               "候选人J先生示例传媒T", "候选人N先生示例数据科技", "候选人O广州示例软件F", "候选人E女士广州示例云服务G"]
    for kw in targets:
        sel, i = select_conv(kw)
        ii = imgs()
        log(f"{kw:<16} [{i:>3}] {sel[:40]:<42} 大图 {len(ii)}  {json.dumps(ii, ensure_ascii=False)[:130]}")


def main():
    cmd = sys.argv[1]
    if cmd == "sel":
        cmd_sel(sys.argv[2])
    elif cmd == "hover":
        cmd_hover(sys.argv[2])
    elif cmd == "send":
        cmd_send(sys.argv[2], os.path.abspath(sys.argv[3]))
    elif cmd == "verify":
        cmd_verify()
    else:
        print("用法: sel|hover|send|verify")


if __name__ == "__main__":
    raise SystemExit(main())
