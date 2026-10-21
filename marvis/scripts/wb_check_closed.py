# -*- coding: utf-8 -*-
"""wb_check_closed.py — 批量检查 jobId 详情页是否显示「职位已关闭」。"""
import json
import os
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb import navigate

PROBE = r"""(function(){
    var b=(document.body.innerText||'').replace(/\s+/g,' ');
    var hasChat=b.indexOf('立即沟通')>=0 || b.indexOf('继续沟通')>=0;
    return JSON.stringify({closed:b.indexOf('职位已关闭')>=0, chat:hasChat,
        title:document.title.slice(0,50)});
})()"""


def main():
    for jid in sys.argv[1:]:
        navigate(f"https://www.zhipin.com/job_detail/{jid}.html")
        time.sleep(5)
        raw = evaluate(PROBE)
        try:
            v = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            v = {"raw": str(raw)[:200]}
        tag = "职位已关闭" if v.get("closed") else ("可沟通" if v.get("chat") else "无按钮")
        print(f"{jid}  {tag:<8} {v.get('title')}")


if __name__ == "__main__":
    main()
