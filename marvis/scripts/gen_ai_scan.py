#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_ai_scan.py — 站内搜索 AI 关键词补扫的选岗。

输入：output/boss_work/batch3_candidates.json（wb_scan3.py 用 AI 关键词扫出来的候选池）
输出：output/boss_work/ai_targets.json

与 gen_b3.py 的差异：**只有 AI 命中的岗位才进池**（用 wb_fav_ai2.AI_RE 正则 + 英文词边界），
再叠加标题级的方向过滤。真正的取舍仍交给 JD 正文（jd_filter）——标题会骗人。
"""
import io
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, r"YOUR_REPO\marvis")
from scripts.gen_gd import (BAD_TITLE, SOCIAL, FRONT_ONLY, ALGO_HARD, ALGO_OK_CTX,
                            norm, score)
from scripts.gen_gd2 import NON_DEV, OTHER_GRADE, BAD_COMPANY
from scripts.wb_fav_ai2 import AI_RE, PRODUCT_HINT, WEAK_DIR
from scripts.wb_scan3 import load_done

WORK = r"YOUR_HOME\output\boss_work"
MAX_TOTAL = int(os.environ.get("AI_MAX", "30"))
CITY_QUOTA = {"深圳": 10, "广州": 12, "东莞": 5, "佛山": 5, "珠海": 4, "惠州": 3,
              "中山": 3, "汕头": 2, "某城市": 2, "江门": 1, "肇庆": 1}


def safe(s):
    s = re.sub(r'[\\/:*?"<>|]', "-", s or "")
    return s.replace(" ", "")[:40]


def main():
    cands = json.load(io.open(os.path.join(WORK, "batch3_candidates.json"), encoding="utf-8"))
    done = load_done()
    mismatched = set()
    jdpath = os.path.join(WORK, "jd_text.json")
    if os.path.isfile(jdpath):
        try:
            for lab, rec in json.load(io.open(jdpath, encoding="utf-8")).items():
                if isinstance(rec, dict) and rec.get("title_match") is False:
                    mismatched.add(lab)
        except Exception:
            pass

    seen = set()
    pool = []
    skip = Counter()
    for j in cands:
        jid = j.get("jobId")
        title = j.get("title") or ""
        comp = j.get("company") or ""
        c = j.get("_city") or j.get("city") or ""
        if jid in done:
            skip["已投过"] += 1
            continue
        hay = " ".join(str(j.get(k, "")) for k in
                       ("title", "company", "industry", "welfare", "tags", "labels"))
        if not AI_RE.search(hay):
            skip["非AI命中"] += 1
            continue
        low = title.lower()
        if any(b.lower() in low for b in BAD_TITLE):
            skip["方向不匹配"] += 1
            continue
        if any(n in title for n in NON_DEV):
            skip["非开发岗"] += 1
            continue
        if PRODUCT_HINT.search(title):
            skip["产品/标注向"] += 1
            continue
        if any(b in comp for b in BAD_COMPANY):
            skip["中介派遣"] += 1
            continue
        if any(s in title for s in SOCIAL):
            skip["社招"] += 1
            continue
        if any(g in title for g in OTHER_GRADE):
            skip["届别不符"] += 1
            continue
        if any(f in low for f in FRONT_ONLY) and "全栈" not in title and "前后端" not in title:
            skip["纯前端"] += 1
            continue
        if "测试" in title and "测试开发" not in title:
            skip["测试岗"] += 1
            continue
        if any(h in comp for h in ("电子", "光电", "半导体", "精密", "科技股份")):
            skip["硬件公司"] += 1
            continue
        if any(h in comp for h in ("分公司", "档案服务", "外包", "劳务")):
            skip["外包分公司"] += 1
            continue
        if "培训" in title:
            skip["培训岗"] += 1
            continue
        if any(a in low for a in ALGO_HARD) and not any(o in low for o in ALGO_OK_CTX):
            skip["算法岗"] += 1
            continue
        pair = (norm(comp), norm(title))
        if pair in seen:
            skip["重复"] += 1
            continue
        seen.add(pair)
        pool.append((score(j, "JD定制"), j))

    pool.sort(key=lambda x: -x[0])
    picked, per = [], Counter()
    for sc, j in pool:
        c = j.get("_city") or j.get("city") or ""
        cap = CITY_QUOTA.get(c, 0)
        if cap <= 0 or per[c] >= cap:
            continue
        per[c] += 1
        picked.append((sc, j))
        if len(picked) >= MAX_TOTAL:
            break

    targets = []
    for sc, j in picked:
        jid = j.get("jobId")
        title = j.get("title") or ""
        comp = j.get("company") or ""
        c = j.get("_city") or j.get("city") or ""
        folder = f"广东AI-{safe(comp)}-{safe(title)}-{safe(c)}"
        targets.append(dict(label=folder, folder=folder, jobId=jid, city=c,
                            company=comp, position=title, salary=j.get("salary", ""),
                            tpl="JD定制", score=sc, industry=j.get("industry", ""),
                            welfare=j.get("welfare", ""),
                            weak_dir=bool(WEAK_DIR.search(title))))
        mark = " ⚠超纲向" if WEAK_DIR.search(title) else ""
        print(f"  [{sc:>3}] {folder:<52} {c:<5} {j.get('salary',''):<12}{mark}")

    out = os.path.join(WORK, "ai_targets.json")
    json.dump(targets, io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n候选 {len(cands)}｜AI 可投池 {len(pool)} → 选中 {len(targets)}（上限 {MAX_TOTAL}）")
    print(f"城市分布：{dict(per)}")
    print(f"过滤统计：{dict(skip.most_common())}")
    print(f"→ {out}")


if __name__ == "__main__":
    main()
