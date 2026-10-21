# -*- coding: utf-8 -*-
"""wb_probe_state.py — 只读探测浏览器当前状态（不导航、不点击）。"""
import os
import sys

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate

print("URL  ", evaluate("location.href"))
print("TITLE", evaluate("document.title"))
print("卡片", evaluate("document.querySelectorAll('.job-card-wrap').length"))
t = evaluate("(document.body.innerText||'').replace(/\\s+/g,' ').slice(0,300)")
print("正文 ", t)
