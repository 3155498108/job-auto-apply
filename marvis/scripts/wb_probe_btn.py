#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_probe_btn.py — 探测一个岗位详情页上到底有哪些可点元素（只读）。

用法: python wb_probe_btn.py <jobId>
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate
from scripts.wb import navigate

JS = r"""JSON.stringify((function(){
    var out=[];
    var sels='a,button,span.btn,div.btn,.btn,.op-btn-chat,.btn-startchat,.job-btn,input[type=submit],input[type=button]';
    document.querySelectorAll(sels).forEach(function(e){
        var r=e.getBoundingClientRect();
        if(r.width<=0||r.height<=0) return;
        var t=(e.textContent||'').replace(/\s+/g,' ').trim();
        if(!t || t.length>24) return;
        if(/^(首页|职位|公司|校园|海归|APP|消息|简历|新|更多|地图|搜索|清空|我|登录|注册|隐私|协议)/.test(t)) return;
        out.push({t:t, cls:(e.className||'').toString().slice(0,50), tag:e.tagName});
    });
    var seen={}, uniq=[];
    out.forEach(function(x){ var k=x.t+'|'+x.cls; if(!seen[k]){seen[k]=1; uniq.push(x);} });
    return {url:location.href, title:document.title, n:uniq.length, items:uniq.slice(0,40),
            bodyLen:(document.body.innerText||'').length};
})())"""


def main():
    jid = sys.argv[1]
    navigate(f"https://www.zhipin.com/job_detail/{jid}.html")
    time.sleep(10)
    raw = evaluate(JS)
    try:
        v = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        print("raw:", str(raw)[:400])
        return
    print("URL:", v.get("url"))
    print("标题:", v.get("title"), "| 正文字数:", v.get("bodyLen"))
    print(f"可点元素 {v.get('n')} 个：")
    for x in v.get("items", []):
        print(f"   [{x['tag']:<6}] {x['t']:<22} class={x['cls']}")


if __name__ == "__main__":
    main()
