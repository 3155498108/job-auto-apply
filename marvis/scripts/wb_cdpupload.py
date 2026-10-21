#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_cdpupload.py — 用 CDP 的 DOM.setFileInputFiles 给 BOSS 聊天上传简历截图。

绕开 WebBridge upload 动作需要的扩展「允许访问文件网址」权限。

用法: python wb_cdpupload.py <图片路径>
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.wb import call
from scripts.webbridge_client import evaluate

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")

SEL = "input[type=file][accept*='image/png']"


def cdp(method, params=None):
    r = call("cdp", {"method": method, "params": params or {}})
    return r


def main():
    path = os.path.abspath(sys.argv[1])
    if not os.path.isfile(path):
        print("!! 文件不存在", path)
        return 2
    print(f"[文件] {path}  {os.path.getsize(path)} B")

    r = cdp("DOM.getDocument", {"depth": 1})
    if not r.get("ok"):
        print("[DOM.getDocument] 失败:", json.dumps(r, ensure_ascii=False)[:400])
        return 3
    root = (r.get("data") or {}).get("root") or {}
    node_id = root.get("nodeId")
    print(f"[root] nodeId={node_id} baseURL={root.get('baseURL')}")
    if not node_id:
        print("[raw]", json.dumps(r, ensure_ascii=False)[:300])
        return 3

    r2 = cdp("DOM.querySelector", {"nodeId": node_id, "selector": SEL})
    if not r2.get("ok"):
        print("[querySelector] 失败:", json.dumps(r2, ensure_ascii=False)[:400])
        return 4
    fid = (r2.get("data") or {}).get("nodeId")
    print(f"[file input] nodeId={fid}")
    if not fid:
        print("!! 没找到图片 file input")
        return 5

    r3 = cdp("DOM.setFileInputFiles", {"files": [path], "nodeId": fid})
    print(f"[setFileInputFiles] {json.dumps(r3, ensure_ascii=False)[:400]}")

    time.sleep(3)
    print("[聊天区图片]", evaluate(r"""(function(){
        var box=document.querySelector('.chat-record');
        if(!box) return 'no_chat_record';
        var n=box.querySelectorAll('img').length;
        var t=(box.textContent||'').replace(/\s+/g,' ').trim().slice(0,160);
        return 'imgs='+n+' | '+t;
    })()"""))
    call("screenshot", {"path": os.path.join(WORK, "cdpupload.png"), "format": "png"})
    print(f"[截图] {os.path.join(WORK, 'cdpupload.png')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
