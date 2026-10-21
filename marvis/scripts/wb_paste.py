#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_paste.py — 用构造的 paste 事件把本地图片贴进 BOSS 聊天输入框。

绕开扩展「允许访问文件网址」权限与 CDP setFileInputFiles 的 Not allowed。

原理:
    图片 → dataURL → fetch → Blob → File → DataTransfer
    → ClipboardEvent('paste', {clipboardData}) 派发到 #chat-input

用法: python wb_paste.py <图片路径> [--send]
"""
import base64
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate
from scripts.wb import call

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")


def build_js(data_url, filename):
    return r"""(async function(){
        var url = __URL__;
        var name = __NAME__;
        try {
            var resp = await fetch(url);
            var blob = await resp.blob();
            var file = new File([blob], name, {type: blob.type || 'image/png'});
            var dt = new DataTransfer();
            dt.items.add(file);
            var input = document.querySelector('#chat-input') || document.querySelector('div.chat-input');
            if(!input) return 'no_input';
            input.focus();
            var ev = new ClipboardEvent('paste', {
                clipboardData: dt, bubbles: true, cancelable: true
            });
            input.dispatchEvent(ev);
            return 'paste_dispatched:'+file.size;
        } catch(e) {
            return 'err:'+(e && e.message ? e.message : String(e));
        }
    })()""".replace("__URL__", json.dumps(data_url)).replace("__NAME__", json.dumps(filename))


def state():
    return evaluate(r"""(function(){
        var input=document.querySelector('#chat-input');
        var imgs=input?input.querySelectorAll('img').length:-1;
        var html=input?(input.innerHTML||'').slice(0,120):'';
        var btn=document.querySelector('button.btn-send');
        return 'input_imgs='+imgs+' btn='+(btn?(btn.className||''):'none')+' html='+html;
    })()""")


def main():
    path = os.path.abspath(sys.argv[1])
    send = "--send" in sys.argv
    if not os.path.isfile(path):
        print("!! 文件不存在", path)
        return 2
    with open(path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode("ascii")
    data_url = "data:image/png;base64," + b64
    print(f"[文件] {os.path.basename(path)}  {len(data)} B  base64 {len(b64)} chars")

    print("[before]", state())
    r = evaluate(build_js(data_url, os.path.basename(path)))
    print(f"[paste] {r}")
    time.sleep(2.5)
    print("[after ]", state())
    call("screenshot", {"path": os.path.join(WORK, "paste.png"), "format": "png"})
    print(f"[截图] {os.path.join(WORK, 'paste.png')}")

    if send:
        s = evaluate(r"""(function(){
            var b=document.querySelector('button.btn-send');
            if(!b) return 'no_btn';
            if((b.className||'').indexOf('disabled')>=0) return 'disabled';
            b.click(); return 'clicked';
        })()""")
        print(f"[发送] {s}")
        time.sleep(2.5)
        print("[after2]", state())
        call("screenshot", {"path": os.path.join(WORK, "paste_sent.png"), "format": "png"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
