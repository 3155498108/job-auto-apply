# -*- coding: utf-8 -*-
"""把「已送达未读」的会话跟 manifest 的已投岗位对应起来，按投递时间分层。

输出 resend_targets.json：只含「已投 + 对方未读 + 投递已超过 N 天」的岗位。
"""
import json
import os
import re
from datetime import datetime, timedelta

W = r"YOUR_HOME\output\boss_work"
RECRUIT = r"YOUR_HOME\招聘"
MIN_DAYS = int(os.environ.get("RESEND_MIN_DAYS", "3"))


def norm(s):
    return re.sub(r"[\s（）()【】\[\]，,、/·\-—:：~～!！?？\"'“”‘’*_#`>|-]", "", (s or "")).lower()


def main():
    states = json.load(open(os.path.join(W, "conv_states.json"), encoding="utf-8"))
    man = json.load(open(os.path.join(RECRUIT, "boss_manifest.json"), encoding="utf-8"))
    jobs = man.get("boss_jobs", [])

    # manifest：按公司归一化分组，每条带投递日期
    by_comp = {}
    for j in jobs:
        c = norm(j.get("company", ""))
        if not c:
            continue
        note = j.get("note", "") or ""
        m = re.search(r"(20\d{2}-\d{2}-\d{2})", note)
        d = datetime.strptime(m.group(1), "%Y-%m-%d") if m else None
        by_comp.setdefault(c, []).append({
            "jobId": j.get("jobId", ""), "title": j.get("title", ""),
            "company": j.get("company", ""),
            "city": j.get("city", ""), "salary": j.get("salary", ""),
            "folder": j.get("folder", ""), "date": d, "note": note,
        })

    today = datetime.now()
    rows = []
    matched_comp = set()
    for s in states:
        t = s.get("t", "")
        st = s.get("state", "")
        if st != "已送达":
            continue
        for c, jl in by_comp.items():
            if c and c in norm(t):
                matched_comp.add(c)
                # 取这个公司最早的一条（重发以会话为单位，不按 jobId 多次）
                j = sorted(jl, key=lambda x: (x["date"] or datetime(2026, 10, 20)))[0]
                if j["date"]:
                    age = (today - j["date"]).days
                else:
                    # 最早的手工投递批次（note 里没写日期）→ 按 10-20 起算
                    age = (today - datetime(2026, 10, 20)).days
                rows.append({
                    "label": j["folder"] or f"{j['company']}-{j['title']}",
                    "folder": j["folder"], "jobId": j["jobId"],
                    "company": j["company"], "position": j["title"],
                    "city": j["city"], "salary": j["salary"],
                    "conv": t[:110], "days_since": age,
                    "date": j["date"].strftime("%Y-%m-%d") if j["date"] else "10-20",
                })
                break

    # 同公司多会话去重
    seen = set()
    uniq = []
    for r in rows:
        k = norm(r["conv"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)

    old = [r for r in uniq if r["days_since"] >= MIN_DAYS]
    new = [r for r in uniq if r["days_since"] < MIN_DAYS]
    print(f"「已送达」会话匹配到已投公司 {len(matched_comp)} 个，去重后 {len(uniq)} 个会话")
    print(f"  投递已满 {MIN_DAYS} 天（值得二次触达）：{len(old)}")
    print(f"  投递不足 {MIN_DAYS} 天（太新，先不重发）：{len(new)}")
    print(f"manifest 里的公司有会话的：{len(matched_comp)} / {len(by_comp)}")

    print("\n=== 满 %d 天的未读会话 ===" % MIN_DAYS)
    for r in sorted(old, key=lambda x: -x["days_since"]):
        print("  %3s天  %-16s %-30s %s" % (
            r["days_since"], r["company"][:16], r["position"][:30], r["conv"][:46]))

    json.dump(old, open(os.path.join(W, "resend_targets.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(uniq, open(os.path.join(W, "resend_all.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\n→ resend_targets.json（{len(old)} 条）")


main()
