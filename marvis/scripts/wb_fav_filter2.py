#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_fav_filter2.py — 收藏候选过滤（v2：同公司 + 同岗位名才判已沟通）。

同时落盘 output/boss_work/chat_pairs.json = [{conv, pos}]，供后续复用。
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb import call, navigate
from scripts.wb_fiximg import select_conv

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")
CHAT = "https://www.zhipin.com/web/geek/chat"

CONV = r"""JSON.stringify(Array.prototype.map.call(
    document.querySelectorAll('.friend-content'), function(e,i){
        return {i:i, t:(e.textContent||'').replace(/\s+/g,' ').trim().slice(0,140)};
    }))"""

POS = r"""(function(){
    var e=document.querySelector('.position-name');
    return e?(e.textContent||'').replace(/\s+/g,' ').trim():'';
})()"""

BAD_KW = ["数据标注", "AI训练师", "客服", "运营", "营销", "出镜", "达人", "销售",
          "人事", "财务", "会计", "教师", "电工", "普工", "仓管", "导购", "置业",
          "产品实习生", "产品助理", "文案", "剪辑", "主播", "翻译", "精算", "汽修",
          "PCB", "物流", "采购", "外贸", "跟单", "美工", "室内", "置业顾问",
          "某桌面数据工具工程师", "商务", "渠道", "加盟", "校招-AI Agent 工程师",
          "数据采集", "游戏客服", "网络客服"]


def norm(s):
    return re.sub(r"[\s（）()【】\[\]，,、/·\-—:：]", "", (s or "")).lower()


def collect_pairs():
    navigate(CHAT)
    time.sleep(5)
    raw = evaluate(CONV)
    convs = json.loads(raw) if isinstance(raw, str) else (raw or [])
    pairs = []
    for c in convs:
        sel, idx = select_conv(c["t"][:14])
        time.sleep(0.7)
        p = evaluate(POS)
        pairs.append(dict(conv=c["t"], pos=p or ""))
        print(f"  [{idx:>2}] {str(p)[:34]:<36} ← {c['t'][:50]}", flush=True)
    with open(os.path.join(WORK, "chat_pairs.json"), "w", encoding="utf-8") as f:
        json.dump(pairs, f, ensure_ascii=False, indent=1)
    return pairs


def main():
    print("=== 采集会话 → 岗位名 ===")
    pairs = collect_pairs()

    faves = json.load(open(os.path.join(WORK, "favorites_tag4.json"), encoding="utf-8"))
    DONE_IDS = {
        "JOBID013", "5307e75f07a37e1e0nRz2N-4FlVW",
        "JOBID102", "JOBID103",
        "JOBID024", "JOBID032",
        "JOBID104", "JOBID004",
        "JOBID018", "JOBID105",
        "JOBID035", "JOBID038",
        "JOBID037", "JOBID010",
        "JOBID025", "6ae5137d0ee0ce0e0nN_2t21F1VZ",
        "JOBID019", "JOBID027",
        "JOBID046", "JOBID014",
        "JOBID016", "JOBID044",
        "JOBID020",
    }

    fresh, skipped = [], []
    for f in faves:
        jid = f.get("encryptJobId")
        title = f.get("jobName") or ""
        comp = f.get("brandName") or ""
        nc, nt = norm(comp), norm(title)
        if jid in DONE_IDS:
            skipped.append((comp, title, "本轮已投"))
            continue
        # 同公司 + 同岗位名 → 已沟通
        hit = None
        for p in pairs:
            if p["pos"] and norm(p["pos"]) == nt and nc in norm(p["conv"]):
                hit = p["conv"][:40]
                break
        if hit:
            skipped.append((comp, title, f"已沟通：{hit}"))
            continue
        if any(k in title for k in BAD_KW):
            skipped.append((comp, title, "方向不匹配"))
            continue
        fresh.append(f)

    out = os.path.join(WORK, "favorites_fresh.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(fresh, f, ensure_ascii=False, indent=1)
    print(f"\n收藏 {len(faves)} → 可投候选 {len(fresh)}，剔除 {len(skipped)}  → {out}\n")
    for f in fresh:
        print(f"  {f.get('cityName',''):<6} {f.get('jobSalary',''):<10} {f.get('jobName','')[:30]:<32} "
              f"{f.get('brandName','')[:20]:<22} {f.get('bossName',''):<8} {f.get('encryptJobId')}")
    print("\n剔除明细：")
    for c, t, why in skipped:
        print(f"  {c[:20]:<22}{t[:30]:<32}{why}")


if __name__ == "__main__":
    main()
