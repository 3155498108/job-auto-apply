# -*- coding: utf-8 -*-
"""wb_dump_detail.py — dump 指定 jobId 的 job_detail 页面正文，诊断为何「立即沟通」不出现。

用法: python wb_dump_detail.py <jobId> [<jobId> ...]
"""
import json
import os
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb import call, navigate

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")

PROBE = r"""JSON.stringify((function(){
    var btns=[];
    document.querySelectorAll('a,button,div.btn,span.btn,[class*="btn"]').forEach(function(e){
        var t=(e.textContent||'').replace(/\s+/g,' ').trim();
        if(!t||t.length>20) return;
        var r=e.getBoundingClientRect();
        if(r.width<=0||r.height<=0) return;
        btns.push({t:t, cls:(e.className||'').toString().slice(0,50)});
    });
    return {url:location.href, title:document.title,
            body:(document.body.innerText||'').replace(/\s+/g,' ').slice(0,700),
            btns:btns.slice(0,40)};
})())"""


def main():
    for jid in sys.argv[1:]:
        url = f"https://www.zhipin.com/job_detail/{jid}.html"
        navigate(url)
        time.sleep(6)
        raw = evaluate(PROBE)
        try:
            v = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            v = {"raw": str(raw)[:800]}
        print("=" * 70)
        print(f"jobId {jid}")
        print(f"URL   {v.get('url')}")
        print(f"TITLE {v.get('title')}")
        print(f"BODY  {v.get('body')}")
        print("BTNS  " + json.dumps(v.get("btns"), ensure_ascii=False)[:700])
        call("screenshot", {"path": os.path.join(WORK, f"detail_{jid}.png"), "format": "png"})
        print(f"截图  {os.path.join(WORK, f'detail_{jid}.png')}")


if __name__ == "__main__":
    main()
