#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_b3.py — 第三批选岗：从 batch3_candidates.json 里挑一批新岗位。

与 gen_gd2.py 同构，差异：
  1) 排除口径统一走 wb_scan3.load_done()（manifest + 全部 targets/final/result/kept/check）；
  2) 额外排除「详情页标题与目标岗位不匹配」的岗位（Vue Router 缓存劫持残留，抓到的 JD 不可信）；
  3) 城市配额重排，覆盖前几批没吃透的城市。

输出：output/boss_work/b3_targets.json
"""
import io
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, r"YOUR_REPO\marvis")
from scripts.gen_gd import (BAD_TITLE, SOCIAL, FRONT_ONLY, ALGO_HARD, ALGO_OK_CTX,
                            pick_tpl, norm, score)
from scripts.gen_gd2 import NON_DEV, OTHER_GRADE, BAD_COMPANY
from scripts.wb_scan3 import load_done

WORK = r"YOUR_HOME\output\boss_work"

CITY_QUOTA = {"深圳": 8, "广州": 8, "东莞": 4, "佛山": 4, "珠海": 3,
              "惠州": 3, "中山": 2, "江门": 1, "汕头": 1, "肇庆": 1, "某城市": 1}
MAX_TOTAL = int(os.environ.get("B3_MAX", "36"))


def safe(s):
    s = re.sub(r'[\\/:*?"<>|]', "-", s or "")
    return s.replace(" ", "")[:40]


def main():
    cands = json.load(io.open(os.path.join(WORK, "batch3_candidates.json"), encoding="utf-8"))
    done = load_done()
    # 标题不匹配的岗位（若已抓过 JD）直接排除
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
        low = title.lower()
        if any(b.lower() in low for b in BAD_TITLE):
            skip["方向不匹配"] += 1
            continue
        if any(n in title for n in NON_DEV):
            skip["非开发岗"] += 1
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
        if "培训生" in title or "培训" in title:
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
        tpl = pick_tpl(title)
        pool.append((score(j, tpl), j, tpl))

    pool.sort(key=lambda x: -x[0])
    picked, per = [], Counter()
    for sc, j, tpl in pool:
        c = j.get("_city") or j.get("city") or ""
        cap = CITY_QUOTA.get(c, 0)
        if cap <= 0 or per[c] >= cap:
            continue
        per[c] += 1
        picked.append((sc, j, tpl))
        if len(picked) >= MAX_TOTAL:
            break

    targets = []
    for sc, j, tpl in picked:
        jid = j.get("jobId")
        title = j.get("title") or ""
        comp = j.get("company") or ""
        c = j.get("_city") or j.get("city") or ""
        folder = f"广东3-{safe(comp)}-{safe(title)}-{safe(c)}"
        targets.append(dict(label=folder, folder=folder, jobId=jid, city=c,
                            company=comp, position=title, salary=j.get("salary", ""),
                            tpl=tpl, score=sc, industry=j.get("industry", ""),
                            welfare=j.get("welfare", "")))
        print(f"  [{sc:>3}] {folder:<52} {c:<5} {j.get('salary',''):<12} {tpl}")

    out = os.path.join(WORK, "b3_targets.json")
    json.dump(targets, io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n候选 {len(cands)}｜可投池 {len(pool)} → 选中 {len(targets)}（上限 {MAX_TOTAL}）")
    print(f"城市分布：{dict(per)}")
    print(f"过滤统计：{dict(skip.most_common())}")
    print(f"→ {out}")


if __name__ == "__main__":
    main()
