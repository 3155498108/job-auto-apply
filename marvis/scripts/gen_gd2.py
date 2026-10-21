#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_gd2.py — 第二批选岗：在剩余候选池里挑一批新岗位（第一批已投 29 个）。

与 gen_gd.py 的差异：
  1. 排除所有已投 jobId（manifest + gd/fav/crosscity 三份目标清单）；
  2. 额外过滤：28 届（"28日常实习" 这种无空格的写法第一批漏了）、
     产品/运营岗、招聘/销售类岗位；
  3. 城市配额按「第一批覆盖后剩下的缺口」重新分配；
  4. 本脚本只产出目标清单，不写话术 —— 话术由 gen_jd_msg.py 依 JD 生成。

输出：output/boss_work/gd2_targets.json
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

RECRUIT = r"YOUR_HOME\招聘"
WORK = r"YOUR_HOME\output\boss_work"

# 届别：补上「28日常实习」「28届应届」这类无空格写法
OTHER_GRADE = ["25届", "26届", "28届", "25 届", "26 届", "28 届",
               "25年", "26年", "28年", "25日常", "26日常", "28日常",
               "25应届", "26应届", "28应届"]

# 第一批漏网：非开发岗
NON_DEV = ["产品经理", "产品助理", "产品运营", "项目经理", "产品专员",
           "运营专员", "运营经理", "招聘专员", "招聘实习生", "人事助理",
           "销售代表", "销售经理", "商务专员", "市场专员", "用户运营",
           "游戏运营", "数据运营", "内容运营", "客服专员"]

# 招聘/派遣/中介类公司
BAD_COMPANY = ["人力资源", "劳务派遣", "招聘服务", "人才服务", "中介"]


def safe(s):
    s = re.sub(r'[\\/:*?"<>|]', "-", s or "")
    return s.replace(" ", "")[:40]


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


# 第二批配额：深圳/广州仍是主力，东莞佛山珠海补一轮，汕头惠州各留一个
CITY_QUOTA = {"深圳": 8, "广州": 7, "东莞": 4, "佛山": 3, "珠海": 3, "汕头": 1, "惠州": 1}
MAX_TOTAL = int(os.environ.get("GD2_MAX", "26"))


def main():
    cands = json.load(io.open(os.path.join(WORK, "gd_candidates.json"), encoding="utf-8"))
    done = done_ids()
    seen = set()
    pool = []
    skip = Counter()
    for j in cands:
        jid = j.get("jobId")
        title = j.get("title") or ""
        comp = j.get("company") or ""
        c = j.get("city") or ""
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
        # 算法岗：只保留「AI 应用 / Agent 落地 / 数据开发」，纯模型训练不做
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
    picked = []
    per = Counter()
    for sc, j, tpl in pool:
        c = j.get("city") or ""
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
        c = j.get("city") or ""
        folder = f"广东2-{safe(comp)}-{safe(title)}-{safe(c)}"
        targets.append(dict(label=folder, folder=folder, jobId=jid, city=c,
                            company=comp, position=title, salary=j.get("salary", ""),
                            tpl=tpl, score=sc, industry=j.get("industry", ""),
                            welfare=j.get("welfare", "")))
        print(f"  [{sc:>3}] {folder:<50} {c:<5} {j.get('salary',''):<12} {tpl}")

    out = os.path.join(WORK, "gd2_targets.json")
    json.dump(targets, io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n可投池 {len(pool)} → 选中 {len(targets)}（上限 {MAX_TOTAL}）")
    print(f"城市分布：{dict(per)}")
    print(f"过滤统计：{dict(skip.most_common())}")
    print(f"→ {out}")


if __name__ == "__main__":
    main()
