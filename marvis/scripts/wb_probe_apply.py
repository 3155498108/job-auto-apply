#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_probe_apply.py — 探测「立即网申」类投递入口点击后的去向（只读，不提交表单）。

用法: python wb_probe_apply.py <jobId>
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate
from scripts.wb import navigate, call

JS = r"""(function(){
    var b=document.querySelector('a.btn-online-apply, .btn-online-apply, a.btn-startchat, .op-btn-chat');
    if(!b) return 'not_found';
    b.scrollIntoView({block:'center'});
    return 'found:'+(b.textContent||'').trim();
})()"""

AFTER = r"""JSON.stringify((function(){
    var body=(document.body.innerText||'').replace(/\s+/g,' ').slice(0,900);
    var btns=[];
    document.querySelectorAll('a,button,.btn').forEach(function(e){
        var r=e.getBoundingClientRect();
        if(r.width<=0||r.height<=0) return;
        var t=(e.textContent||'').replace(/\s+/g,' ').trim();
        if(t && t.length<=12 && /投|送|申|确|定|完|简|历|填/.test(t)) btns.push(t);
    });
    var uniq={},u=[]; btns.forEach(function(x){if(!uniq[x]){uniq[x]=1;u.push(x);}});
    return {url:location.href, title:document.title, body:body, btns:u.slice(0,20)};
})())"""


def main():
    jid = sys.argv[1]
    navigate(f"https://www.zhipin.com/job_detail/{jid}.html")
    time.sleep(9)
    r = evaluate(JS)
    print("点击前：", r)
    if not str(r).startswith("found"):
        print("没有网申/沟通入口")
        return
    evaluate(r"""(function(){
        var b=document.querySelector('a.btn-online-apply, .btn-online-apply, a.btn-startchat, .op-btn-chat');
        if(b){ b.click(); return 'clicked'; }
        return 'gone';
    })()""")
    time.sleep(6)
    v = evaluate(AFTER)
    try:
        v = json.loads(v) if isinstance(v, str) else v
    except Exception:
        print("after:", str(v)[:400])
        return
    print("点击后 URL:", v.get("url"))
    print("标题:", v.get("title"))
    print("可见文案:", v.get("body", "")[:600])
    print("相关按钮:", v.get("btns"))
    call("screenshot", {"path": os.path.join(r"YOUR_HOME\output\boss_work", "probe_apply.png"),
                        "format": "png"})


if __name__ == "__main__":
    main()
