# -*- coding: utf-8 -*-
"""wb_probe_login.py — 检查 BOSS 登录态是否还在（只读 + 一次导航）。"""
import os
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb import call, navigate

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")

for url in ("https://www.zhipin.com/web/geek/chat",
            "https://www.zhipin.com/web/geek/job?query=java&city=101280100"):
    navigate(url)
    time.sleep(6)
    u = evaluate("location.href")
    t = evaluate("document.title")
    b = evaluate("(document.body.innerText||'').replace(/\\s+/g,' ').slice(0,200)")
    has_input = evaluate("document.querySelectorAll('#chat-input,div.chat-input').length")
    has_card = evaluate("document.querySelectorAll('.job-card-wrap').length")
    print(f"URL {u}")
    print(f"TITLE {t}")
    print(f"chat-input={has_input} job-card={has_card}")
    print(f"正文 {b}")
    print("-" * 60)

call("screenshot", {"path": os.path.join(WORK, "login_probe.png"), "format": "png"})
print("截图", os.path.join(WORK, "login_probe.png"))
