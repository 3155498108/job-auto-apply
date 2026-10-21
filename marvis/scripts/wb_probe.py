#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_probe.py — 诊断 BOSS 搜索页的滚动容器与加载行为。"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.wb import evaluate_json, evaluate, navigate, search_url


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else "Java 后端"
    city = sys.argv[2] if len(sys.argv) > 2 else "101280100"

    navigate(search_url(query, city), wait=4)

    diag = evaluate_json(r"""JSON.stringify((function(){
        var out = {url: location.href, title: document.title, bodyH: document.body.scrollHeight,
                   docH: document.documentElement.scrollHeight, winY: window.scrollY, containers: []};
        var sels = ['.job-list-container','.job-list-box','.search-job-result','.job-primary',
                    '.job-list','.job-recommend-list','#wrap .job-list','.content .job-list',
                    '.job-list-container .scroll-box','[class*=scroll]'];
        var seen = {};
        sels.forEach(function(s){
            document.querySelectorAll(s).forEach(function(e){
                if (seen[e.className]) return;
                seen[e.className] = 1;
                out.containers.push({
                    sel: s, cls: e.className,
                    sh: e.scrollHeight, ch: e.clientHeight,
                    oy: getComputedStyle(e).overflowY
                });
            });
        });
        out.cards = document.querySelectorAll('.job-card-wrapper, .job-card-box, .job-list-box li').length;
        return out;
    })())""")

    print(f"URL : {diag.get('url')}")
    print(f"标题: {diag.get('title')}")
    print(f"body.scrollHeight = {diag.get('bodyH')}   documentElement = {diag.get('docH')}")
    print(f"当前卡片数: {diag.get('cards')}\n")
    print("可滚动容器:")
    for c in diag.get("containers", []):
        print(f"  {c['sel']:<28} cls={str(c['cls'])[:34]:<36} scrollH={c['sh']:<7} clientH={c['ch']:<7} overflowY={c['oy']}")

    # 逐个尝试滚动，看卡片数是否增加
    print("\n尝试滚动并观察卡片数:")
    from scripts.wb import list_cards
    for attempt in range(6):
        n_before = len(list_cards())
        for sel in [".job-list-container", ".job-list-box", ".search-job-result", ".job-primary"]:
            evaluate(f"""(function(){{
                var e = document.querySelector('{sel}');
                if (e) {{ e.scrollTop = e.scrollHeight; return 1; }}
                return 0;
            }})()""")
        evaluate("window.scrollTo(0, document.documentElement.scrollHeight);")
        time.sleep(1.8)
        n_after = len(list_cards())
        print(f"  第{attempt+1}次: {n_before} -> {n_after}")
        if n_after == n_before and attempt >= 2:
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
