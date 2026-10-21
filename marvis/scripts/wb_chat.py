#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_chat.py — BOSS 消息界面的会话与输入框探查 / 发消息。

流程（用户提出的方案）：
    点「立即沟通」建立沟通 → 进消息页找到该 HR 会话 → 在聊天框发定制话术

用法：
    python wb_chat.py probe            # 探查会话列表 + 输入框结构
    python wb_chat.py send <公司关键词> <话术文件>   # 给指定 HR 发消息
"""
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate
from scripts.wb import navigate, call

CHAT_URL = "https://www.zhipin.com/web/geek/chat"

PROBE_JS = r"""JSON.stringify((function(){
    function vis(e){var r=e.getBoundingClientRect();return r.width>0&&r.height>0;}
    var convs=[];
    document.querySelectorAll('.chat-record .user-name, .user-item, .chat-record-item, li').forEach(function(e){
        if(!vis(e)) return;
        var t=(e.textContent||'').replace(/\s+/g,' ').trim();
        if(t && t.length<120) convs.push(t);
    });
    var inputs=[];
    document.querySelectorAll('textarea, input[type=text], [contenteditable=true], .chat-input, .input-box').forEach(function(e){
        if(!vis(e)) return;
        inputs.push({tag:e.tagName, cls:(e.className||'').toString().slice(0,40),
                     ml:e.getAttribute('maxlength')||'',
                     ph:e.getAttribute('placeholder')||'',
                     v:((e.value!==undefined&&e.value!==null)?e.value:(e.textContent||'')).slice(0,60)});
    });
    var btns=[];
    document.querySelectorAll('button,.btn,span[class*=send],a[class*=send],.icon-send').forEach(function(e){
        if(!vis(e)) return;
        var t=(e.textContent||'').trim();
        if(t && t.length<10) btns.push({text:t, cls:(e.className||'').toString().slice(0,40)});
    });
    return {url:location.href, title:document.title, convs:convs.slice(0,12), inputs:inputs, btns:btns.slice(0,18),
            head:document.body.innerText.replace(/\s+/g,' ').slice(0,400)};
})())"""


def probe():
    navigate(CHAT_URL, wait=5)
    raw = evaluate(PROBE_JS)
    try:
        d = json.loads(raw)
    except Exception:
        print(raw)
        return {}
    print("URL :", d.get("url"))
    print("会话列表:")
    for c in d.get("convs", []):
        print("   ", c[:100])
    print("\n输入框:")
    for i in d.get("inputs", []):
        print("   ", i)
    print("\n按钮:")
    for b in d.get("btns", []):
        print("   ", b)
    print("\n页面文本:", d.get("head", "")[:300])
    return d


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "probe"
    if mode == "probe":
        probe()
    elif mode == "send":
        who = sys.argv[2]
        path = sys.argv[3]
        text = io.open(path, encoding="utf-8").read().strip()
        print(f"目标会话含: {who}   消息 {len(text)} 字")
        navigate(CHAT_URL, wait=5)
        # 列出所有会话，找匹配的
        r = evaluate(r"""JSON.stringify((function(){
            var out=[];
            document.querySelectorAll('.chat-record, .user-item, [class*=record-item], .chat-friend-list li').forEach(function(e,i){
                var r=e.getBoundingClientRect();
                if(r.width<=0||r.height<=0) return;
                out.push({i:i, cls:(e.className||'').toString().slice(0,40),
                          text:(e.textContent||'').replace(/\s+/g,' ').trim().slice(0,90)});
            });
            return out;
        })())""")
        print(r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
