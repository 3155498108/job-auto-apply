#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_chat2.py — 打开指定 HR 会话 → 填入消息（默认不发送）。

用法：
    python wb_chat2.py open <会话关键词> [话术文件]
        打开会话、填入文本、截图，停在「发送」前
    python wb_chat2.py send <会话关键词> <话术文件>
        填入后直接点发送
"""
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate
from scripts.wb import navigate, call

CHAT_URL = "https://www.zhopin.com"  # 占位，实际用下面的
CHAT_URL = "https://www.zhipin.com/web/geek/chat"
WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")


def open_conv(keyword):
    """点击会话列表里包含 keyword 的会话。"""
    code = r"""(function(){
        var KW = __KW__;
        var cands = document.querySelectorAll('div,li,a,span');
        var best = null;
        for (var i = 0; i < cands.length; i++) {
            var e = cands[i];
            var t = (e.textContent || '').replace(/\s+/g,' ').trim();
            if (t.indexOf(KW) < 0) continue;
            if (t.length > 80) continue;
            if (e.children.length > 4) continue;
            var r = e.getBoundingClientRect();
            if (r.width <= 0 || r.height <= 0) continue;
            if (!best || t.length < best.t.length) best = {el: e, t: t};
        }
        if (!best) return 'not_found';
        best.el.scrollIntoView({block:'center'});
        best.el.click();
        return 'clicked:' + best.el.tagName + ':' + best.t.slice(0,50);
    })()""".replace("__KW__", json.dumps(keyword, ensure_ascii=False))
    return evaluate(code)


def probe_chat():
    code = r"""JSON.stringify((function(){
        function vis(e){var r=e.getBoundingClientRect();return r.width>0&&r.height>0;}
        var ins=[];
        document.querySelectorAll('textarea, [contenteditable="true"], input[type="text"]').forEach(function(e){
            if(!vis(e)) return;
            if((e.className||'').toString().indexOf('search')>=0) return;
            ins.push({tag:e.tagName, cls:(e.className||'').toString().slice(0,44),
                      ml:e.getAttribute('maxlength')||'',
                      ph:e.getAttribute('placeholder')||'',
                      v:((e.value!==undefined&&e.value!==null)?e.value:(e.textContent||'')).slice(0,50)});
        });
        var btns=[];
        document.querySelectorAll('button,.btn,span,div[class*=send],a[class*=send],i[class*=send]').forEach(function(e){
            if(!vis(e)) return;
            var t=(e.textContent||'').trim();
            var c=(e.className||'').toString();
            if(c.indexOf('send')>=0 || t==='发送' || t==='Enter') btns.push({text:t, cls:c.slice(0,46)});
        });
        var panel=document.querySelector('.chat-record, [class*=chat-message], [class*=conversation]');
        return {ins:ins, btns:btns.slice(0,14),
                head:(document.body.innerText||'').replace(/\s+/g,' ').slice(0,300)};
    })())"""
    raw = evaluate(code)
    try:
        return json.loads(raw)
    except Exception:
        print(raw)
        return {}


def fill_text(text):
    code = r"""(function(){
        var G = __TEXT__;
        var cands = document.querySelectorAll('textarea, [contenteditable="true"]');
        for (var i=0;i<cands.length;i++){
            var el=cands[i];
            var r=el.getBoundingClientRect();
            if(r.width<=0||r.height<=0) continue;
            if((el.className||'').toString().indexOf('search')>=0) continue;
            if(el.isContentEditable){
                el.textContent=G;
                el.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:G}));
            } else {
                var setter=Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set;
                setter.call(el,G);
                el.dispatchEvent(new Event('input',{bubbles:true}));
                el.dispatchEvent(new Event('change',{bubbles:true}));
            }
            return 'filled:'+el.tagName+':'+((el.value||el.textContent||'').length);
        }
        return 'no_input';
    })()""".replace("__TEXT__", json.dumps(text, ensure_ascii=False))
    return evaluate(code)


def main():
    mode = sys.argv[1]
    kw = sys.argv[2]
    path = sys.argv[3] if len(sys.argv) > 3 else None
    text = io.open(path, encoding="utf-8").read().strip() if path else ""

    navigate(CHAT_URL, wait=5)
    r = open_conv(kw)
    print(f"[开会话] {r}")
    time.sleep(2.5)

    d = probe_chat()
    print("[输入框]", json.dumps(d.get("ins", []), ensure_ascii=False))
    print("[发送按钮]", json.dumps(d.get("btns", []), ensure_ascii=False))

    if text:
        print(f"[填充] {fill_text(text)}   ({len(text)} 字)")
        time.sleep(0.8)
        shot = call("screenshot", {"path": os.path.join(WORK, "chat_shot.png"), "format": "png"})
        print("[截图]", os.path.join(WORK, "chat_shot.png"))
        if mode == "send":
            s = evaluate(r"""(function(){
                var bs=document.querySelectorAll('button,.btn,span[class*=send],i[class*=send],div[class*=send],a[class*=send]');
                for(var i=0;i<bs.length;i++){
                    var t=(bs[i].textContent||'').trim();
                    var c=(bs[i].className||'').toString();
                    if(t==='发送'||c.indexOf('send')>=0){
                        var r=bs[i].getBoundingClientRect();
                        if(r.width>0&&r.height>0){ bs[i].click(); return 'sent:'+t+':'+c.slice(0,30); }
                    }
                }
                return 'no_send_btn';
            })()""")
            print(f"[发送] {s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
