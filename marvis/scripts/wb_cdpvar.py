#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_cdpvar.py — 穷举 DOM.setFileInputFiles 的各种参数组合。"""
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
    return call("cdp", {"method": method, "params": params or {}})


def main():
    path = os.path.abspath(sys.argv[1])
    print(f"[文件] {path}")

    cdp("Emulation.setFocusEmulationEnabled", {"enabled": True})
    cdp("Page.enable", {})
    cdp("Page.setInterceptFileChooserDialog", {"enabled": True})
    time.sleep(0.5)

    r = cdp("DOM.getDocument", {"depth": 1})
    root = (r.get("data") or {}).get("root") or {}
    node_id = root.get("nodeId")
    print(f"[root] nodeId={node_id}")

    r2 = cdp("DOM.querySelector", {"nodeId": node_id, "selector": SEL})
    fid = (r2.get("data") or {}).get("nodeId")
    print(f"[querySelector] nodeId={fid}")

    # backendNodeId
    r3 = cdp("DOM.describeNode", {"nodeId": fid}) if fid else {"ok": False}
    bid = ((r3.get("data") or {}).get("node") or {}).get("backendNodeId")
    print(f"[describeNode] backendNodeId={bid}")

    # objectId 路线：Runtime.evaluate → DOM.requestNode
    r4 = cdp("Runtime.evaluate", {"expression": f"document.querySelector(\"{SEL}\")"})
    oid = ((r4.get("data") or {}).get("result") or {}).get("objectId")
    print(f"[Runtime.evaluate] objectId={oid}")
    r5 = cdp("DOM.requestNode", {"objectId": oid}) if oid else {"ok": False}
    rid = (r5.get("data") or {}).get("nodeId")
    print(f"[DOM.requestNode] nodeId={rid}")

    variants = [
        ("backendNodeId", {"files": [path], "backendNodeId": bid}),
        ("nodeId(requestNode)", {"files": [path], "nodeId": rid}),
        ("objectId", {"files": [path], "objectId": oid}),
        ("nodeId+nodeList", {"files": [path], "nodeId": fid}),
    ]
    for name, params in variants:
        if any(v is None for v in params.values()):
            print(f"  [{name}] 跳过（缺参数）")
            continue
        rr = cdp("DOM.setFileInputFiles", params)
        ok = rr.get("ok")
        print(f"  [{name}] ok={ok} {json.dumps(rr, ensure_ascii=False)[:220]}")
        if ok:
            time.sleep(3)
            print("   [聊天区]", evaluate(r"""(function(){
                var b=document.querySelector('.chat-record');
                return b? ('imgs='+b.querySelectorAll('img').length) : 'no_box';
            })()"""))
            break
        time.sleep(0.5)

    call("screenshot", {"path": os.path.join(WORK, "cdpvar.png"), "format": "png"})
    print(f"[截图] {os.path.join(WORK, 'cdpvar.png')}")


if __name__ == "__main__":
    raise SystemExit(main())
