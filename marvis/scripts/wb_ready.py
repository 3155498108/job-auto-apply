#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_ready.py — 开投前体检：登录态 / 页面就绪 / 卡片提取 / 风控计数。

只读，不做任何投递动作。
用法: python wb_ready.py [关键词] [城市码]
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate
from scripts.wb import navigate, search_url, evaluate_json

LOGIN_CHECK = r"""JSON.stringify((function(){
    var u=location.href||'';
    var b=(document.body.innerText||'');
    return {
        url:u, title:document.title,
        login:(u.indexOf('/web/user')>=0)||(u.indexOf('login')>=0),
        hasName:b.indexOf('候选人')>=0,
        len:b.length
    };
})())"""

STATE = r"""JSON.stringify((function(){
    function t(sel){var e=document.querySelector(sel);return e?(e.textContent||'').replace(/\s+/g,' ').trim():'';}
    var body=document.body.innerText||'';
    return {
        title:document.title,
        total:t('.job-count, .result-count, .search-result-count'),
        cards:document.querySelectorAll('.job-card-wrapper, .job-card-box, .job-list-box li, li.job-card-wrapper').length,
        // 风控 / 上限提示
        limitHit: body.indexOf('沟通上限')>=0 || body.indexOf('今天已与')>=0,
        captcha: body.indexOf('验证')>=0 || body.indexOf('安全验证')>=0,
        head: body.replace(/\s+/g,' ').slice(0,160)
    };
})())"""


def main():
    q = sys.argv[1] if len(sys.argv) > 1 else "Java"
    city = sys.argv[2] if len(sys.argv) > 2 else "101280100"
    print(f"== 导航: {q} / {city}")
    navigate(search_url(q, city))
    time.sleep(9)   # Vue SPA 实测需要 8-12s 完整渲染

    lk = evaluate_json(LOGIN_CHECK)
    print(f"== 登录态: {json.dumps(lk, ensure_ascii=False)}")
    if lk.get("login") or not lk.get("hasName"):
        print("!! 登录态无效 —— 停止。需要用户扫码重登。")
        return 2

    st = evaluate_json(STATE)
    print(f"== 页面: {json.dumps(st, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
