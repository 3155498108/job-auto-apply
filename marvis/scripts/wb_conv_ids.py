# -*- coding: utf-8 -*-
"""wb_conv_ids.py — 从聊天会话里提取每条会话对应的 jobId / 岗位名 / 公司。"""
import json
import os
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb import navigate

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")
CHAT = "https://www.zhipin.com/web/geek/chat"

CONV_DEEP = r"""JSON.stringify((function(){
    var out=[];
    document.querySelectorAll('.friend-content').forEach(function(e,i){
        var t=(e.textContent||'').replace(/\s+/g,' ').trim();
        var attrs={};
        for(var k=0;k<e.attributes.length;k++){
            var a=e.attributes[k];
            if(/job|encrypt|mid|href|data-/i.test(a.name)) attrs[a.name]=a.value.slice(0,80);
        }
        var links=[];
        e.querySelectorAll('a[href]').forEach(function(a){ links.push(a.getAttribute('href').slice(0,80)); });
        out.push({i:i, t:t.slice(0,100), attrs:attrs, links:links});
    });
    return out;
})())"""

HEADER = r"""(function(){
    var out={};
    ['.position-name','.boss-name','.chat-name','.company-name','.chat-title',
     '[class*="position"]','[class*="company"]','[class*="chat-name"]'].forEach(function(s){
        var e=document.querySelector(s);
        if(e){ var t=(e.textContent||'').replace(/\s+/g,' ').trim(); if(t) out[s]=t.slice(0,60); }
    });
    var lk=[];
    document.querySelectorAll('a[href*="job_detail"]').forEach(function(a){ lk.push(a.getAttribute('href').slice(0,90)); });
    out.links=lk;
    return out;
})()"""


def main():
    navigate(CHAT)
    time.sleep(5)
    raw = evaluate(CONV_DEEP)
    try:
        v = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        print("fail", str(raw)[:300]); return
    print(f"会话 {len(v or [])} 条，前 8 条的 DOM 属性：")
    for x in (v or [])[:8]:
        print("   ", json.dumps(x, ensure_ascii=False)[:340])
    print("\n聊天头部信息：")
    print("   ", json.dumps(evaluate(HEADER), ensure_ascii=False)[:700])


if __name__ == "__main__":
    main()
