#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_target.py — 按公司/岗位定位 BOSS 目标岗位。

复用 skill 原生 extract_jobs()（走 Vue $props.data，拿到的是虚拟列表里的
完整数据而非仅 DOM 中的可见卡片），并按 manifest 中的目标做匹配。

用法：
    python wb_target.py <搜索词> [岗位关键词过滤]
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import extract_jobs
from scripts.wb import navigate, search_url


def main():
    if len(sys.argv) < 2:
        print("用法: python wb_target.py <搜索词> [岗位关键词过滤]")
        return 1
    query = sys.argv[1]
    kw = sys.argv[2] if len(sys.argv) > 2 else ""

    url = search_url(query, "101280100")
    print(f"搜索: {query}   过滤: {kw or '(无)'}")
    navigate(url, wait=5)

    jobs = extract_jobs()
    print(f"提取到 {len(jobs)} 条（Vue props 全量，非 DOM 可见数）\n")

    hits = []
    for j in jobs:
        if kw and (kw not in j["title"] and kw not in j["company"]):
            continue
        hits.append(j)

    for j in hits:
        print(f"  {j['title'][:30]:<32} {j['salary'][:12]:<14} {j['company'][:16]:<18} "
              f"{j['city'][:14]:<16} {j['degree']:<8} {j['experience']}")
        print(f"      行业={j['industry'][:16]} 规模={j['scale'][:10]} 融资={j['stage'][:10]} "
              f"福利={j['welfare'][:40]}")
        print(f"      jobId={j['jobId']}")

    print(f"\n命中 {len(hits)} / 共 {len(jobs)} 条")
    if kw and not hits:
        print("→ 本页无命中，全部岗位：")
        for j in jobs:
            print(f"    {j['title'][:34]:<36} {j['salary'][:12]:<14} {j['company'][:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
