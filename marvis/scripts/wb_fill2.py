#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_fill2.py — 用 WebBridge 原生 fill 动作填聊天框，验证发送按钮是否激活。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate
from scripts.wb import call

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")


def send_state():
    return evaluate(r"""(function(){
        var b=document.querySelector('button.btn-send');
        if(!b) return 'no_btn';
        var cs=getComputedStyle(b);
        return (b.className||'')+' | disabled_prop='+!!b.disabled+' | opacity='+cs.opacity+' | pe='+cs.pointerEvents;
    })()""")


def input_state():
    return evaluate(r"""(function(){
        var e=document.querySelector('#chat-input');
        if(!e) return 'no_input';
        return 'len='+((e.textContent||'').length)+' html='+((e.innerHTML||'').slice(0,60));
    })()""")


def main():
    company = sys.argv[1] if len(sys.argv) > 1 else "示例科技Y"
    from scripts.recruit_greetings import pick_by_company
    text, src, meta = pick_by_company(company)
    if not text:
        print(f"!! 没找到 {company} 的专属话术")
        return 2
    print(f"[话术] {meta.get('folder')} | {len(text)} 字")
    print("[before] input:", input_state())
    print("[before] send :", send_state())

    # 先清空
    evaluate(r"""(function(){
        var e=document.querySelector('#chat-input');
        if(!e) return 'no';
        e.focus();
        document.execCommand('selectAll',false,null);
        document.execCommand('delete',false,null);
        e.textContent='';
        e.dispatchEvent(new Event('input',{bubbles:true}));
        return 'cleared';
    })()""")
    time.sleep(0.6)
    print("[clear] input:", input_state())

    r = call("fill", {"selector": "#chat-input", "value": text})
    print(f"[fill] {json.dumps(r, ensure_ascii=False)[:400]}")
    time.sleep(1.2)
    print("[after] input:", input_state())
    print("[after] send :", send_state())

    call("screenshot", {"path": os.path.join(WORK, "fill2.png"), "format": "png"})
    print(f"[截图] {os.path.join(WORK, 'fill2.png')}")


if __name__ == "__main__":
    raise SystemExit(main())
