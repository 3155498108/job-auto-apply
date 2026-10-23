#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_fav_ai2.py — 生成「收藏夹漏投的 AI 技术岗」清单。

背景：v1 词表缺裸 `ai`，漏掉 5 个明确带 AI 字样的岗位；
且只拉了 tag=4（收藏）、漏了 tag=5（已沟通）交叉核对。

本脚本从 tag=4 + tag=5 合并去重，挑出「AI 命中 + 未投 + 技术向」，
产品/标注/训练师向的单独列出（不自动投）。

输出：output/boss_work/favai2_targets.json
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, r"YOUR_REPO\marvis")
from scripts.wb_scan3 import load_done
from scripts.wb_fav_ai2 import AI_RE, PRODUCT_HINT, WEAK_DIR, text_of

WORK = r"YOUR_HOME\output\boss_work"
# 归档前缀：每轮用新前缀，避免与旧批次目录撞名
# （`pick_by_company()` 按公司名前缀匹配，folder 名不带批次前缀会串批）
PREFIX = os.environ.get("FAV_PREFIX", "收藏AI2")


def main():
    done = load_done()
    merged = {}
    for tag in (4, 5):
        p = os.path.join(WORK, f"favorites_tag{tag}.json")
        if not os.path.isfile(p):
            continue
        for c in json.load(io.open(p, encoding="utf-8")):
            jid = c.get("encryptJobId")
            if not jid:
                continue
            if jid not in merged:
                merged[jid] = dict(c)
                merged[jid]["_tags"] = []
            if tag not in merged[jid]["_tags"]:
                merged[jid]["_tags"].append(tag)

    targets, products = [], []
    for jid, c in merged.items():
        if jid in done:
            continue
        title = (c.get("jobName") or "").strip()
        hay = text_of(c)
        if not AI_RE.search(hay):
            continue
        hits = sorted(set(m.group(0).strip().lower() for m in AI_RE.finditer(hay) if m.group(0).strip()))
        base = dict(
            jobId=jid, city=c.get("cityName", "") or "",
            company=c.get("brandName", "") or "", position=title,
            salary=c.get("jobSalary", "") or c.get("salaryDesc", "") or "",
            boss=c.get("bossName", "") or "", degree=c.get("jobDegree", "") or "",
            experience=c.get("jobExperience", "") or "",
            ai_hits=hits[:6], weak_dir=bool(WEAK_DIR.search(title)),
            from_tags=c.get("_tags", []),
        )
        if PRODUCT_HINT.search(title):
            products.append(base)
            continue
        safe = re.sub(r'[\\/:*?"<>|]', "", title)[:26]
        comp = re.sub(r'[\\/:*?"<>|]', "", base["company"])[:18]
        label = f"收藏AI2-{comp}-{safe}-{base['city']}"
        item = dict(base)
        item["label"] = label
        item["folder"] = label
        targets.append(item)

    json.dump(targets, io.open(os.path.join(WORK, f"{PREFIX}_targets.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(products, io.open(os.path.join(WORK, f"{PREFIX}_products.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"技术向目标 {len(targets)} 个 → {PREFIX}_targets.json")
    print(f"产品/标注向 {len(products)} 个（不投）")
    for t in targets:
        mark = " ⚠超纲向" if t["weak_dir"] else ""
        print(f"  {t['city']:<4} {t['salary'][:10]:<11} {t['position'][:34]:<36} "
              f"{t['company'][:16]:<18} {t['boss'][:6]:<8}{mark}")


if __name__ == "__main__":
    main()
