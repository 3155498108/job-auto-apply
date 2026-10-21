#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_chatprobe.py — 等消息页加载完，定位聊天输入框 + 会话列表。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate
from scripts.wb import call

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")


def main():
    print("[tabs]", json.dumps(call("list_tabs", {}), ensure_ascii=False)[:800])
    for i in range(12):
        url = evaluate("location.href") or ""
        txt = (evaluate(r"""(document.body.innerText||'').replace(/\s+/g,' ')""") or "")
        n_ta = evaluate(r"""document.querySelectorAll('textarea').length""")
        n_ce = evaluate(r"""document.querySelectorAll('[contenteditable="true"]').length""")
        n_in = evaluate(r"""document.querySelectorAll('input').length""")
        print(f"[t+{i*3}s] url={url[-45:]} len={len(txt)} ta={n_ta} ce={n_ce} in={n_in} | {txt[:110]}")
        if ("发送" in txt) and (n_ce or n_ta):
            print(">>> 聊天界面已就绪")
            break
        time.sleep(3)

    probe = r"""JSON.stringify((function(){
        function vis(e){var r=e.getBoundingClientRect();return r.width>0&&r.height>0;}
        var out=[];
        document.querySelectorAll('textarea,input,[contenteditable="true"]').forEach(function(e){
            if(!vis(e)) return;
            var r=e.getBoundingClientRect();
            out.push({tag:e.tagName, cls:(e.className||'').toString().slice(0,60),
                      ph:e.getAttribute('placeholder')||'', id:e.id||'',
                      x:Math.round(r.x), y:Math.round(r.y), w:Math.round(r.width), h:Math.round(r.height)});
        });
        var convs=[];
        document.querySelectorAll('li,div').forEach(function(e){
            var t=(e.textContent||'').replace(/\s+/g,'').trim();
            if(t.indexOf('示例科技Y')>=0 && t.length>0 && t.length<80){
                var r=e.getBoundingClientRect();
                if(r.width<=0||r.height<=0) return;
                convs.push({cls:(e.className||'').toString().slice(0,50), t:t.slice(0,40),
                            x:Math.round(r.x), y:Math.round(r.y)});
            }
        });
        var sends=[];
        document.querySelectorAll('button,a,span,div,i').forEach(function(e){
            var t=(e.textContent||'').replace(/\s+/g,'').trim();
            if(t!=='发送') return;
            var r=e.getBoundingClientRect();
            if(r.width<=0||r.height<=0) return;
            sends.push({tag:e.tagName, cls:(e.className||'').toString().slice(0,50),
                        x:Math.round(r.x), y:Math.round(r.y)});
        });
        return {inputs:out, convs:convs.slice(0,10), sends:sends.slice(0,6)};
    })())"""
    print("[probe]", evaluate(probe))
    call("screenshot", {"path": os.path.join(WORK, "chatprobe.png"), "format": "png"})
    print(f"[截图] {os.path.join(WORK, 'chatprobe.png')}")


if __name__ == "__main__":
    raise SystemExit(main())
