# -*- coding: utf-8 -*-
"""wb_health.py — 检查 BOSS 站点是否被限流/拦截。"""
import os
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb import call, navigate

PAGES = [
    ("首页", "https://www.zhipin.com/"),
    ("职位搜索", "https://www.zhipin.com/web/geek/job?query=Java%E5%AE%9E%E4%B9%A0&city=101280100"),
    ("消息页", "https://www.zhipin.com/web/geek/chat"),
]

for name, url in PAGES:
    try:
        navigate(url)
    except Exception as e:
        print(f"{name}: 导航异常 {e}")
        continue
    time.sleep(3)
    body = evaluate(r"""(document.body.innerText||'').replace(/\s+/g,' ').slice(0,220)""")
    n = evaluate(r"""document.querySelectorAll('.friend-content, .job-card-wrap, .card-wrap').length""")
    print(f"[{name}] 元素={n}")
    print(f"   {body}\n")
    call("screenshot", {"path": os.path.join(r"YOUR_HOME\output\boss_work", f"health_{name}.png"), "format": "png"})
