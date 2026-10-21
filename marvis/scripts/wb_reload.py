# -*- coding: utf-8 -*-
"""wb_reload.py — 重新加载当前页并等聊天区就绪（WebBridge 没有 reload 动作，用 JS 触发）。"""
import os
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb import call

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")
CHAT = "https://www.zhipin.com/web/geek/chat"

for i in range(1, 4):
    print(f"--- 第 {i} 次尝试")
    try:
        evaluate("location.reload()")
    except Exception as e:
        print("  reload 异常", e)
    time.sleep(6)
    body = evaluate(r"""(document.body.innerText||'').replace(/\s+/g,' ').slice(0,160)""")
    n = evaluate(r"""document.querySelectorAll('.friend-content').length""")
    print(f"  body={body}")
    print(f"  会话条目={n}")
    if int(n or 0) > 0:
        call("screenshot", {"path": os.path.join(WORK, "chat_reload_ok.png"), "format": "png"})
        print("  OK")
        break
    time.sleep(4)
