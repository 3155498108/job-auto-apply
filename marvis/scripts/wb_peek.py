# -*- coding: utf-8 -*-
"""wb_peek.py — 打开指定会话，打印我方/对方消息明细（逐条带发送者标记）。

用法: python wb_peek.py <会话关键词> [<会话关键词> ...]
"""
import json
import os
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb import call, navigate

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")
CHAT = "https://www.zhipin.com/web/geek/chat"

LIST = r"""JSON.stringify(Array.prototype.map.call(
    document.querySelectorAll('.friend-content'), function(e,i){
        return {i:i, t:(e.textContent||'').replace(/\s+/g,' ').trim().slice(0,90)};
    }))"""

PEEK = r"""JSON.stringify((function(){
    var b=document.querySelector('.chat-message');
    if(!b) return {err:'no_box'};
    var out=[];
    b.querySelectorAll('li.message-item').forEach(function(l,i){
        var isMe=l.className.indexOf('item-myself')>=0;
        var imgs=l.querySelectorAll('img.message-image').length;
        var c=l.querySelector('.message-content');
        var t=(c?(c.innerText||c.textContent||''):(l.textContent||''))||'';
        var h=c?(c.innerHTML||''):'';
        var brs=(h.match(/<br\s*\/?>/gi)||[]).length;
        var st=document.querySelector('.chat-record .status, .message-status');
        out.push({me:isMe, img:imgs, br:brs, t:t.replace(/\s+/g,' ').trim().slice(0,220)});
    });
    var pos=document.querySelector('.position-name');
    var sel=document.querySelector('.friend-content.selected');
    return {items:out, pos:pos?(pos.textContent||'').trim():'',
            conv:sel?(sel.textContent||'').replace(/\s+/g,' ').trim().slice(0,60):''};
})())"""


def main():
    navigate(CHAT)
    time.sleep(5)
    for kw in sys.argv[1:]:
        raw = evaluate(LIST)
        try:
            convs = json.loads(raw) if raw else []
        except Exception:
            convs = []
        hit = next((c for c in convs if kw in c["t"]), None)
        if not hit:
            print(f"!! {kw} 没找到会话")
            continue
        evaluate(r"""(function(){
            var list=document.querySelectorAll('.friend-content');
            var e=list[%d]; if(!e) return 'gone';
            e.scrollIntoView({block:'center'}); e.click(); return 'clicked';
        })()""" % hit["i"])
        time.sleep(2.5)
        raw = evaluate(PEEK)
        try:
            v = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            v = {"err": str(raw)[:300]}
        print("=" * 72)
        print(f"[{kw}] 会话：{v.get('conv')}  岗位：{v.get('pos')}")
        for it in v.get("items", []):
            who = "我方" if it["me"] else "对方"
            extra = f" 图{it['img']} br{it['br']}" if (it["img"] or it["br"]) else ""
            print(f"  {who}{extra}: {it['t']}")


if __name__ == "__main__":
    main()
