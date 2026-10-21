#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_clip.py — 通过「系统剪贴板 + CDP 触发真实粘贴」把图片送进 BOSS 聊天框。

流程:
    1. PowerShell 把图片写入 Windows 剪贴板（System.Windows.Forms.Clipboard）
    2. CDP: Emulation.setFocusEmulationEnabled(true) → 聚焦 #chat-input
    3. CDP: Input.dispatchKeyEvent Ctrl+V，并在 keyUp 带 commands:['paste']

用法: python wb_clip.py <图片路径> [--send]
"""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate
from scripts.wb import call

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")

PS_SET_CLIP = r"""
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$img=[System.Drawing.Image]::FromFile('__PATH__')
[System.Windows.Forms.Clipboard]::SetImage($img)
$img.Dispose()
Write-Output 'clipboard_ok'
"""


def set_clipboard(path):
    ps = PS_SET_CLIP.replace("__PATH__", path.replace("'", "''"))
    r = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-STA", "-Command", ps],
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    return (r.stdout or "").strip(), (r.stderr or "").strip()[:200]


def cdp(method, params=None):
    return call("cdp", {"method": method, "params": params or {}})


def state():
    return evaluate(r"""(function(){
        var input=document.querySelector('#chat-input');
        if(!input) return 'no_input';
        var imgs=input.querySelectorAll('img').length;
        var btn=document.querySelector('button.btn-send');
        return 'input_imgs='+imgs+' btn='+(btn?(btn.className||''):'none')+' html='+(input.innerHTML||'').slice(0,100);
    })()""")


def paste_via_cdp():
    cdp("Emulation.setFocusEmulationEnabled", {"enabled": True})
    evaluate(r"""(function(){
        var e=document.querySelector('#chat-input');
        if(e){ e.focus(); var r=e.getBoundingClientRect(); }
        return document.activeElement ? document.activeElement.className : 'none';
    })()""")
    time.sleep(0.4)
    common = {"key": "v", "code": "KeyV", "windowsVirtualKeyCode": 86,
              "nativeVirtualKeyCode": 86, "modifiers": 2}
    r1 = cdp("Input.dispatchKeyEvent", dict(type="keyDown", **common))
    time.sleep(0.15)
    r2 = cdp("Input.dispatchKeyEvent", dict(type="keyUp", commands=["paste"], **common))
    time.sleep(2.0)
    return r1, r2


def main():
    path = os.path.abspath(sys.argv[1])
    send = "--send" in sys.argv
    if not os.path.isfile(path):
        print("!! 文件不存在", path)
        return 2

    out, err = set_clipboard(path)
    print(f"[剪贴板] {out} {err}")
    print("[before]", state())

    r1, r2 = paste_via_cdp()
    print(f"[CDP] down={json.dumps(r1, ensure_ascii=False)[:120]}")
    print(f"[CDP] up  ={json.dumps(r2, ensure_ascii=False)[:120]}")
    time.sleep(2)
    print("[after ]", state())
    call("screenshot", {"path": os.path.join(WORK, "clip.png"), "format": "png"})
    print(f"[截图] {os.path.join(WORK, 'clip.png')}")

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
        call("screenshot", {"path": os.path.join(WORK, "clip_sent.png"), "format": "png"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
