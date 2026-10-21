#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""analyze_pool.py — 分析剩余候选池：按城市/方向/薪资统计，确认第二批还有多少可投。"""
import io
import json
import os
import sys
from collections import Counter

sys.path.insert(0, r"YOUR_REPO\marvis")
from scripts.gen_gd import (BAD_TITLE, SOCIAL, OTHER_GRADE, FRONT_ONLY, ALGO_HARD,
                            ALGO_OK_CTX, pick_tpl, norm, score)

RECRUIT = r"YOUR_HOME\招聘"
WORK = r"YOUR_HOME\output\boss_work"


def done_ids():
    d = set()
    try:
        m = json.load(io.open(os.path.join(RECRUIT, "boss_manifest.json"), encoding="utf-8"))
        for j in m.get("boss_jobs", []):
            if j.get("jobId"):
                d.add(j["jobId"])
    except (OSError, ValueError):
        pass
    for fn in ("gd_targets.json", "fav_targets.json", "crosscity_targets.json"):
        try:
            for t in json.load(io.open(os.path.join(WORK, fn), encoding="utf-8")):
                if t.get("jobId"):
                    d.add(t["jobId"])
        except (OSError, ValueError):
            pass
    return d


def main():
    cands = json.load(io.open(os.path.join(WORK, "gd_candidates.json"), encoding="utf-8"))
    done = done_ids()
    print(f"候选 {len(cands)}｜已投 {len(done)}")

    reason = Counter()
    city = Counter()
    tpls = Counter()
    ok = []
    seen = set()
    for j in cands:
        jid = j.get("jobId")
        title = j.get("title") or ""
        comp = j.get("company") or ""
        c = j.get("city") or ""
        if jid in done:
            reason["已投过"] += 1
            continue
        low = title.lower()
        if any(b.lower() in low for b in BAD_TITLE):
            reason["方向不匹配"] += 1
            continue
        if any(s in title for s in SOCIAL):
            reason["社招"] += 1
            continue
        if any(g in title for g in OTHER_GRADE):
            reason["届别不符"] += 1
            continue
        if any(f in low for f in FRONT_ONLY) and "全栈" not in title and "前后端" not in title:
            reason["纯前端"] += 1
            continue
        if "测试" in title and "测试开发" not in title:
            reason["测试岗"] += 1
            continue
        if any(h in comp for h in ("电子", "光电", "半导体", "精密", "科技股份")):
            reason["硬件公司"] += 1
            continue
        if any(h in comp for h in ("分公司", "档案服务", "人力资源", "外包", "劳务")):
            reason["外包分公司"] += 1
            continue
        if "培训生" in title or "培训" in title:
            reason["培训岗"] += 1
            continue
        if any(a in low for a in ALGO_HARD) and not any(o in low for o in ALGO_OK_CTX):
            reason["算法岗"] += 1
            continue
        pair = (norm(comp), norm(title))
        if pair in seen:
            reason["重复"] += 1
            continue
        seen.add(pair)
        tpl = pick_tpl(title)
        tpls[tpl] += 1
        city[c] += 1
        ok.append((score(j, tpl), j, tpl))

    print(f"\n可投 {len(ok)}")
    print("过滤原因：", dict(reason.most_common()))
    print("\n城市分布：", dict(city.most_common()))
    print("方向分布：", dict(tpls.most_common()))
    ok.sort(key=lambda x: -x[0])
    print("\n-- 前 45 名 --")
    for sc, j, tpl in ok[:45]:
        print(f"  [{sc:>3}] {j.get('city',''):<5} {j.get('salary',''):<12} {tpl:<9} "
              f"{j.get('company','')[:16]:<18} {j.get('title','')[:34]}")
    json.dump([{"jobId": j.get("jobId"), "title": j.get("title"), "city": j.get("city"),
                "company": j.get("company"), "salary": j.get("salary"), "tpl": tpl,
                "score": sc, "welfare": j.get("welfare", "")}
               for sc, j, tpl in ok],
              io.open(os.path.join(WORK, "pool_rest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
