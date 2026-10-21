#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_search.py — 按公司名在 BOSS 精准定位目标岗位。

用法：
    python wb_search.py <公司名> [城市码]

输出：当前搜索结果页的岗位卡片（公司/岗位/薪资/区域/沟通按钮状态）。
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.wb import navigate, list_cards, search_url, evaluate_json


def main():
    if len(sys.argv) < 2:
        print("用法: python wb_search.py <公司名> [城市码]")
        return 1
    company = sys.argv[1]
    city = sys.argv[2] if len(sys.argv) > 2 else "101280100"

    url = search_url(company, city)
    print(f"搜索: {company}   城市码: {city}")
    navigate(url, wait=4)

    cards = list_cards()
    print(f"卡片数: {len(cards)}\n")
    hit = 0
    for c in cards:
        mark = ""
        if company and company in c["company"]:
            mark = "  ★匹配"
            hit += 1
        print(f"[{c['idx']:>2}] {c['title'][:26]:<28} {c['salary'][:10]:<12} "
              f"{c['company'][:20]:<22} {c['area'][:16]:<20} btn={c['chatBtn']}{mark}")
    print(f"\n公司名精确匹配: {hit} 条")

    # 页面级状态
    st = evaluate_json(r"""JSON.stringify({
        title: document.title,
        url: location.href,
        total: (document.querySelector('.job-count, .result-count, .search-result-count')||{}).textContent || '',
        filterText: (document.querySelector('.filter-box, .condition-list, .job-filter')||{}).innerText || ''
    })""")
    print(f"\n页面: {st.get('title','')}")
    print(f"地址: {st.get('url','')}")
    if st.get("total"):
        print(f"结果数: {st['total']}")
    if st.get("filterText"):
        print(f"筛选区: {st['filterText'][:200]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
