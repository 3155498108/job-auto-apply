# -*- coding: utf-8 -*-
"""wb_msghtml.py — 打印我方消息元素的完整 HTML，寻找隐藏的撤回/删除控件。"""
import json
import os
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb import call

HTML = r"""(function(){
    var b=document.querySelector('.chat-message');
    if(!b) return 'no_box';
    var lis=b.querySelectorAll('li.message-item.item-myself');
    if(!lis.length) return 'no_mine';
    var last=lis[lis.length-1];
    return last.outerHTML.slice(0,3000);
})()"""

CONV_ITEMS = r"""JSON.stringify(Array.prototype.map.call(
    document.querySelectorAll('li.message-item.item-myself'), function(l,i){
        return {i:i, html:l.outerHTML.replace(/\s+/g,' ').slice(0,300)};
    }))"""

RIGHTCLICK = r"""(function(){
    var b=document.querySelector('.chat-message');
    if(!b) return 'no_box';
    var lis=b.querySelectorAll('li.message-item.item-myself');
    if(!lis.length) return 'no_mine';
    var last=lis[lis.length-1];
    var r=last.getBoundingClientRect();
    var x=r.left+r.width/2, y=r.top+20;
    ['contextmenu','mousedown','mouseup'].forEach(function(t){
        last.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,clientX:x,clientY:y,button:2}));
    });
    return 'rightclick dispatched';
})()"""


def main():
    print("--- 我方最后一条消息 outerHTML ---")
    print(evaluate(HTML))
    print("\n--- 所有我方消息 outerHTML 摘要 ---")
    raw = evaluate(CONV_ITEMS)
    try:
        v = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        v = []
    for x in (v or []):
        print(f"  [{x['i']}] {x['html'][:260]}")
    print("\n--- 右键 ---")
    print(evaluate(RIGHTCLICK))
    time.sleep(1.2)
    raw2 = evaluate(r"""JSON.stringify((function(){
        var out=[];
        document.querySelectorAll('body *').forEach(function(e){
            var t=(e.textContent||'').replace(/\s+/g,'').trim();
            if(!t||t.length>8) return;
            if(t.indexOf('撤')<0 && t.indexOf('删')<0 && t.indexOf('复')<0 && t.indexOf('举报')<0) return;
            var r=e.getBoundingClientRect();
            out.push({tag:e.tagName, t:t, cls:(e.className||'').toString().slice(0,50),
                      x:Math.round(r.x), y:Math.round(r.y), w:Math.round(r.width), h:Math.round(r.height),
                      parent:(e.parentElement?(e.parentElement.className||'').toString().slice(0,50):'')});
        });
        return out;
    })())""")
    try:
        m = json.loads(raw2) if isinstance(raw2, str) else (raw2 or [])
    except Exception:
        m = [{"raw": str(raw2)[:300]}]
    for x in m:
        print("   ", json.dumps(x, ensure_ascii=False))
    call("screenshot", {"path": r"YOUR_HOME\output\boss_work\msg_html.png", "format": "png"})


if __name__ == "__main__":
    main()
