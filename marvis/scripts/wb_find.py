#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_find.py — 搜索并滚动加载全部岗位卡片，解密薪资，按关键词过滤。

用法：
    python wb_find.py <公司名> [过滤关键词] [城市码]
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.wb import navigate, evaluate_json, search_url


# 加载全部卡片：反复滚动
LOAD_JS = r"""JSON.stringify((function(){
    var cards = document.querySelectorAll('.job-card-wrapper, .job-card-box, .job-list-box li');
    return {n: cards.length, h: document.body.scrollHeight, y: window.scrollY};
})())"""


def scroll_load(times=10, pause=1.6):
    last = -1
    stable = 0
    for i in range(times):
        evaluate_js = r"""(function(){
            var el = document.querySelector('.job-list-container, .job-list-box, .search-job-result, .job-primary');
            var target = el || document.scrollingElement;
            var before = target.scrollTop;
            target.scrollTop = target.scrollHeight;
            return before;
        })()"""
        from scripts.wb import evaluate
        evaluate(evaluate_js)
        time.sleep(pause)
        st = evaluate_json(LOAD_JS)
        n = st.get("n", 0)
        if n == last:
            stable += 1
            if stable >= 3:
                break
        else:
            stable = 0
        last = n
    return last


# 卡片 + 薪资解密
CARDS_JS = r"""JSON.stringify((function(){
    function dec(t){
        if(!t) return '';
        var out='';
        for(var i=0;i<t.length;i++){
            var cp=t.charCodeAt(i);
            if(cp>=0xE031 && cp<=0xE03A) out += String(cp-0xE031);
            else out += t[i];
        }
        return out;
    }
    var cards = document.querySelectorAll('.job-card-wrapper, .job-card-box, .job-list-box li');
    var out = [];
    for (var i=0;i<cards.length;i++){
        var c = cards[i];
        function txt(sel){ var e=c.querySelector(sel); return e ? e.textContent.trim() : ''; }
        var sal = txt('.salary, .job-salary, .salary-area');
        out.push({
            idx: i,
            title: txt('.job-name, .job-title'),
            salaryRaw: sal,
            salary: dec(sal),
            company: txt('.company-name, .company-info a, .boss-name'),
            area: txt('.job-area .workplace, .company-location'),
            tag: txt('.tag-list, .job-info .tag'),
            href: (c.querySelector('a.job-name, a.job-card-left, a.job-card-right')||{}).href || ''
        });
    }
    return out;
})())"""


def main():
    if len(sys.argv) < 2:
        print("用法: python wb_find.py <公司名> [过滤关键词] [城市码]")
        return 1
    company = sys.argv[1]
    kw = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].isdigit() else ""
    city = sys.argv[3] if len(sys.argv) > 3 else ("101280100" if len(sys.argv) < 3 or not sys.argv[2].isdigit() else sys.argv[2])

    url = search_url(company, city)
    print(f"搜索: {company}   城市码: {city}   过滤: {kw or '(无)'}")
    navigate(url, wait=4)
    n = scroll_load()
    print(f"滚动加载后卡片数: {n}\n")

    cards = evaluate_json(CARDS_JS)
    if isinstance(cards, dict):
        print("解析异常:", cards)
        return 1

    hits = 0
    for c in cards:
        if kw and (kw not in c["title"] and kw not in c["company"]):
            continue
        hits += 1
        print(f"[{c['idx']:>2}] {c['title'][:30]:<32} {c['salary'][:14]:<16} "
              f"{c['company'][:18]:<20} {c['area'][:16]:<18}")
        print(f"      标签: {c['tag'][:60]}")
    print(f"\n命中: {hits} 条 / 共 {len(cards)} 条")
    if kw and hits == 0:
        print("→ 没命中，列出全部岗位名供选择：")
        for c in cards:
            print(f"    [{c['idx']:>2}] {c['title'][:34]:<36} {c['salary'][:12]:<14} {c['company'][:18]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
