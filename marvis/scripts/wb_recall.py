# -*- coding: utf-8 -*-
"""wb_recall.py — 穷举探查 BOSS 网页版消息撤回/删除入口。

手段：DOM 文本扫描、属性扫描、hover 渲染、右键菜单、SVG 图标 title。
"""
import json
import os
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb import call

WORDS = ["撤回", "删除", "撤銷", "recall", "recallMsg", "delete", "删除消息", "消息删除", "复制", "转发", "举报"]

DOM_SCAN = r"""JSON.stringify((function(){
    var out=[];
    var all=document.querySelectorAll('a,button,span,i,em,div[class*="menu"],li,svg,use');
    for(var i=0;i<all.length;i++){
        var e=all[i];
        var t=(e.textContent||'').replace(/\s+/g,'').trim();
        var tt=e.getAttribute&&(e.getAttribute('title')||'')+'|'+(e.getAttribute('aria-label')||'')+'|'+(e.getAttribute('class')||'');
        if(!t && !tt) continue;
        if(t.length>8) continue;
        out.push({tag:e.tagName, t:t, cls:(e.className||'').toString().slice(0,50), meta:tt.slice(0,90)});
    }
    return out;
})())"""

CTX = r"""(function(){
    var b=document.querySelector('.chat-message');
    if(!b) return 'no_box';
    var lis=b.querySelectorAll('li.message-item.item-myself');
    if(!lis.length) return 'no_mine';
    var last=lis[lis.length-1];
    var r=last.getBoundingClientRect();
    var x=r.left+r.width/2, y=r.top+30;
    ['mouseover','mouseenter','mousemove'].forEach(function(t){
        last.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,clientX:x,clientY:y}));
    });
    var c=last.querySelector('.message-content');
    if(c){ var rc=c.getBoundingClientRect();
        ['mouseover','mouseenter','mousemove'].forEach(function(t){
            c.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,clientX:rc.left+20,clientY:rc.top+10}));
        });}
    return 'hovered at '+Math.round(x)+','+Math.round(y);
})()"""

AFTER_HOVER = r"""JSON.stringify((function(){
    var out=[];
    var all=document.querySelectorAll('a,button,span,i,em,li,div[class*="menu"],div[class*="pop"],div[class*="tool"]');
    for(var i=0;i<all.length;i++){
        var e=all[i];
        var t=(e.textContent||'').replace(/\s+/g,'').trim();
        if(!t||t.length>10) continue;
        var r=e.getBoundingClientRect();
        if(r.width<=0||r.height<=0) continue;
        out.push({t:t, cls:(e.className||'').toString().slice(0,60), x:Math.round(r.x), y:Math.round(r.y)});
    }
    return out;
})())"""

MENUS = r"""JSON.stringify((function(){
    var out=[];
    document.querySelectorAll('[class*="menu"],[class*="pop"],[class*="context"],[class*="dropdown"],[class*="mask"],[class*="modal"]').forEach(function(e){
        var r=e.getBoundingClientRect();
        var t=(e.textContent||'').replace(/\s+/g,' ').trim();
        if(!t) return;
        if(r.width<=0||r.height<=0) return;
        var st=window.getComputedStyle(e);
        if(st.display==='none'||st.visibility==='hidden'||parseFloat(st.opacity||'1')<0.05) return;
        out.push({cls:(e.className||'').toString().slice(0,60), t:t.slice(0,80), x:Math.round(r.x), y:Math.round(r.y)});
    });
    return out;
})())"""


def main():
    raw = evaluate(DOM_SCAN)
    try:
        els = json.loads(raw) if isinstance(raw, str) else (raw or [])
    except Exception:
        els = []
    hits = []
    for e in els:
        blob = (e.get("t") or "") + "|" + (e.get("cls") or "") + "|" + (e.get("meta") or "")
        for w in WORDS:
            if w.lower() in blob.lower():
                hits.append(e)
                break
    print(f"DOM 扫描 {len(els)} 个元素，命中关键词 {len(hits)} 个：")
    for h in hits[:40]:
        print("   ", json.dumps(h, ensure_ascii=False))

    print("\n-- hover 我方最后一条消息 --")
    print(evaluate(CTX))
    time.sleep(1.5)
    raw2 = evaluate(AFTER_HOVER)
    try:
        els2 = json.loads(raw2) if isinstance(raw2, str) else (raw2 or [])
    except Exception:
        els2 = []
    h2 = []
    for e in els2:
        blob = (e.get("t") or "") + "|" + (e.get("cls") or "")
        for w in WORDS:
            if w.lower() in blob.lower():
                h2.append(e)
                break
    print(f"hover 后可见小元素 {len(els2)}，命中 {len(h2)}：")
    for h in h2[:30]:
        print("   ", json.dumps(h, ensure_ascii=False))

    print("\n-- 浮层/菜单 --")
    raw3 = evaluate(MENUS)
    try:
        m = json.loads(raw3) if isinstance(raw3, str) else (raw3 or [])
    except Exception:
        m = []
    for x in m[:25]:
        print("   ", json.dumps(x, ensure_ascii=False))

    call("screenshot", {"path": r"YOUR_HOME\output\boss_work\recall_probe.png", "format": "png"})


if __name__ == "__main__":
    main()
