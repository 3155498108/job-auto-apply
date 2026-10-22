#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_fav_ai.py — 收藏夹 AI 批次：从 fav_ai_candidates.json 生成投递目标清单。

本批只做标题层粗筛（AI 方向 + 未投过 + 非明显非技术），
真正的取舍交给 jd_filter 按 JD 正文硬筛。

输出：output/boss_work/favai_targets.json
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, r"YOUR_REPO\marvis")

WORK = r"YOUR_HOME\output\boss_work"

# 标题层再压一刀：明显不是开发岗的
DROP = ["产品实习生", "产品助理", "产品经理", "运营", "客服", "主播", "剪辑",
        "数据标注", "ai训练师", "ai 训练师", "标注员", "见习", "数据采集",
        "算法实习生", "ai算法", "ai 算法", "训练生"]


def safe(s):
    s = re.sub(r'[\\/:*?"<>|]', "-", s or "")
    s = s.replace(" ", "")
    return s[:40]


def main():
    cands = json.load(io.open(os.path.join(WORK, "fav_ai_candidates.json"), encoding="utf-8"))
    targets = []
    skip = []
    for c in cands:
        title = c.get("title", "") or ""
        low = title.lower()
        if any(d in low for d in DROP):
            skip.append((title, "标题层排除"))
            continue
        comp = c.get("company", "") or ""
        city = c.get("city", "") or ""
        folder = f"收藏AI-{safe(comp)}-{safe(title)}-{safe(city)}"
        targets.append(dict(label=folder, folder=folder, jobId=c["jobId"],
                            city=city, company=comp, position=title,
                            salary=c.get("salary", ""), boss=c.get("boss", ""),
                            degree=c.get("degree", ""), experience=c.get("experience", ""),
                            ai_hits=c.get("strong", [])))
        print(f"  {folder:<56} {city:<4} {str(c.get('salary',''))[:11]:<12} "
              f"{'/'.join(c.get('strong', [])[:3])}")

    out = os.path.join(WORK, "favai_targets.json")
    json.dump(targets, io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nAI 候选 {len(cands)} → 目标 {len(targets)}（排除 {len(skip)}）")
    for t, why in skip:
        print(f"  ✗ {t}  ({why})")
    print(f"→ {out}")


if __name__ == "__main__":
    main()
