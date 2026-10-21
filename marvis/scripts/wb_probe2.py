#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_probe2.py — 探测 job_detail 独立页是否可用（绕过右侧详情面板）。"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import extract_jobs
from scripts.wb import navigate, search_url, call

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")


def probe_state(tag):
    code = r"""JSON.stringify((function(){
        var txt=(document.body.innerText||'').replace(/\s+/g,' ');
        return {
            url: location.href,
            title: document.title,
            len: txt.length,
            hasGreet: txt.indexOf('立即沟通')>=0,
            hasChat: txt.indexOf('继续沟通')>=0,
            hasDesc: txt.indexOf('职位描述')>=0 || txt.indexOf('岗位职责')>=0,
            hasLoad: document.querySelectorAll('.job-detail-loading').length,
            head: txt.slice(0,200)
        };
    })())"""
    from scripts.webbridge_client import evaluate
    raw = evaluate(code)
    print(f"[{tag}] {raw}")
    return raw


def main():
    # 1) 搜索示例科技Y的岗位，拿 jobId
    navigate(search_url("Java 后端开发", "101280100"))
    time.sleep(4)
    jobs = extract_jobs()
    target = None
    for j in jobs:
        if j.get("city") == "广州" and "JAVA" in j["title"].upper() and "示例科技Y" in j["company"]:
            target = j
            break
    if not target:
        print("!! 搜索结果里没找到示例科技Y JAVA")
        for j in jobs[:20]:
            print("   ", j["title"][:28], "|", j["salary"], "|", j["company"], "|", j["city"])
        return 2
    print(f"[命中] {target['title']} | {target['salary']} | {target['company']} | jobId={target['jobId']}")

    # 2) 打开 job_detail 独立页
    jd_url = f"https://www.zhipin.com/job_detail/{target['jobId']}.html"
    print(f"[导航] {jd_url}")
    navigate(jd_url)
    time.sleep(5)
    probe_state("job_detail")

    for i in range(6):
        time.sleep(2)
        probe_state(f"t+{i*2+5}s")

    call("screenshot", {"path": os.path.join(WORK, "probe_detail.png"), "format": "png"})
    print(f"[截图] {os.path.join(WORK, 'probe_detail.png')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
