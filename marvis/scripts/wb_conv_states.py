#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只读：滚动会话列表，逐屏收集全部会话预览文本 + 消息状态。

背景：BOSS 会话列表是虚拟滚动，DOM 里永远只有 ~40 个 .friend-content，
但列表总高 7000+。要拿到全部已投岗位的状态，必须边滚边收集。
会话预览文本里带 [已读] / [送达] / [投递中] 标记。

用法: python collect_conv_states.py <out.json>
"""
import json
import os
import sys
import time

sys.path.insert(0, r"YOUR_REPO\marvis")
from scripts.wb import evaluate, navigate

WORK = r"YOUR_HOME\output\boss_work"
CHAT = "https://www.zhipin.com/web/geek/chat"

LIST_ALL = r"""JSON.stringify(Array.prototype.map.call(
    document.querySelectorAll('.friend-content'), function(e){
        return {t:(e.textContent||'').replace(/\s+/g,' ').trim()};
    }))"""

SCROLL_STATE = r"""(function(){
    // ⚠ 两个关键点（实测踩出来的）：
    //   1) 滚动容器是 .user-list-content，不是 .friend-list —— 用错元素只拿到头 40 条
    //   2) 直接设 scrollTop **不会**触发懒加载，必须手动派发 scroll 事件；
    //      派发后内容才跟着滚（滚到底时 scrollHeight 从 7842 涨到 15642）
    var el=document.querySelector('.user-list-content');
    var info=[];
    if(el){
        info.push({sh:el.scrollHeight, ch:el.clientHeight, st:Math.round(el.scrollTop)});
        el.scrollTop = el.scrollTop + Math.round(el.clientHeight*0.9);
        el.dispatchEvent(new Event('scroll',{bubbles:true}));
    }
    var lists=document.querySelectorAll('.friend-list, .chat-friend-list, [class*="friend-list"], [class*="conversation"]');
    lists.forEach(function(l){
        info.push({sh:l.scrollHeight, ch:l.clientHeight, st:Math.round(l.scrollTop)});
        l.scrollTop = l.scrollTop + Math.round(l.clientHeight*0.8);
        l.dispatchEvent(new Event('scroll',{bubbles:true}));
    });
    return JSON.stringify(info);
})()"""

RESET = r"""(function(){
    var el=document.querySelector('.user-list-content');
    if(el) el.scrollTop=0;
    var lists=document.querySelectorAll('.friend-list, .chat-friend-list, [class*="friend-list"], [class*="conversation"]');
    lists.forEach(function(l){ l.scrollTop=0; });
    window.scrollTo(0,0);
    return 'reset';
})()"""


def collect(max_steps=90, pause=0.6):
    navigate(CHAT)
    time.sleep(6)
    evaluate(RESET)
    time.sleep(1.0)
    seen = []
    seen_set = set()
    stall = 0
    last_sig = None
    for step in range(max_steps):
        raw = evaluate(LIST_ALL)
        try:
            cur = json.loads(raw) if raw else []
        except Exception:
            cur = []
        added = 0
        for c in cur:
            t = c.get("t", "").strip()
            if not t:
                continue
            # 会话预览：时间 + 名字 + 状态标记 + 正文摘要
            key = t[:110]
            if key not in seen_set:
                seen_set.add(key)
                seen.append(t)
                added += 1
        state = evaluate(SCROLL_STATE)
        sig = state
        if sig == last_sig:
            stall += 1
            if stall >= 4:
                break
        else:
            stall = 0
        last_sig = sig
        time.sleep(pause)
        if added == 0 and stall >= 3:
            break
    return seen


def classify(t):
    if "[已读]" in t:
        return "已读"
    if "[投递中]" in t or "[发送中]" in t:
        return "未送达"
    if "[送达]" in t or "送达" in t:
        return "已送达"
    if "未读" in t:
        return "未读"
    return "无标记"


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "conv_states.json"
    rows = collect()
    recs = [{"t": t, "state": classify(t)} for t in rows]
    with open(os.path.join(WORK, out), "w", encoding="utf-8") as f:
        json.dump(recs, f, ensure_ascii=False, indent=1)
    from collections import Counter
    print(f"收集到 {len(recs)} 条会话（列表可能仍有更早的）")
    print("状态分布:", dict(Counter(r["state"] for r in recs)))
    for st in ("已读", "已送达", "未送达", "未读", "无标记"):
        sel = [r for r in recs if r["state"] == st]
        if not sel:
            continue
        print(f"\n=== {st} ({len(sel)}) ===")
        for r in sel[:40]:
            print("  ", r["t"][:100])
    print(f"\n→ {os.path.join(WORK, out)}")


main()
