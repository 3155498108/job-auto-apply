# -*- coding: utf-8 -*-
"""wb_probe_search.py — 探测 BOSS 聊天页的搜索入口与会话列表加载方式。

输出：可见输入框、按钮、以及列表容器信息。
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

PROBE = r"""JSON.stringify((function(){
    function vis(e){var r=e.getBoundingClientRect();return r.width>0&&r.height>0;}
    var inputs=[], btns=[];
    document.querySelectorAll('input,textarea,[contenteditable="true"]').forEach(function(e,i){
        if(!vis(e)) return;
        inputs.push({i:i, tag:e.tagName, type:e.type||'', cls:(e.className||'').toString().slice(0,60),
                     ph:e.getAttribute('placeholder')||'', v:(e.value||'').slice(0,30)});
    });
    document.querySelectorAll('button,a[class*="btn"],div[class*="search"],[class*="icon-search"],i[class*="search"]').forEach(function(e){
        var t=(e.textContent||'').replace(/\s+/g,' ').trim();
        var r=e.getBoundingClientRect();
        if(!vis(e)) return;
        if(!t) t='(icon)';
        btns.push({t:t.slice(0,20), cls:(e.className||'').toString().slice(0,50), x:Math.round(r.x), y:Math.round(r.y)});
    });
    var list=document.querySelector('.friend-content');
    var cont=list?list.parentElement:null;
    return {url:location.href, inputs:inputs, btns:btns.slice(0,25),
            convs:document.querySelectorAll('.friend-content').length,
            contCls:cont?(cont.className||'').toString().slice(0,60):'',
            contH:cont?[cont.scrollHeight,cont.clientHeight]:null};
})())"""


def main():
    navigate(CHAT)
    time.sleep(6)
    raw = evaluate(PROBE)
    try:
        v = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        print("raw:", str(raw)[:800]); return
    print("URL ", v.get("url"))
    print("会话数", v.get("convs"), " 列表容器", v.get("contCls"), v.get("contH"))
    print("\n输入框:")
    for i in v.get("inputs", []):
        print(f"  [{i['i']}] {i['tag']} type={i['type']} cls={i['cls']} ph={i['ph']!r} v={i['v']!r}")
    print("\n按钮/搜索:")
    for b in v.get("btns", []):
        print(f"  {b['t']:<22} {b['cls']:<52} ({b['x']},{b['y']})")
    call("screenshot", {"path": os.path.join(WORK, "probe_chat.png"), "format": "png"})
    print("\n截图", os.path.join(WORK, "probe_chat.png"))


if __name__ == "__main__":
    main()
