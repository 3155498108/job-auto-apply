# -*- coding: utf-8 -*-
"""backfill_resend_note2.py — 按 jobId 精确回填「第二次触达」标记。

上一版按公司名找条目，同公司多岗位时多段会话会写到同一条目上，
导致另外那些岗位条目没被标记。这版：
  1) 先按 jobId 精确匹配（同一职位页）
  2) jobId 匹配不到，再按公司名匹配（历史手工投递条目 jobId 缺失的情况）
并报告哪些会话没能落到独立条目上。
"""
import io
import json
import os
import re
from datetime import datetime

WORK = r"YOUR_HOME\output\boss_work"
MANIFEST = r"YOUR_HOME\招聘\boss_manifest.json"
STAMP = f"{datetime.now():%Y-%m-%d} 第二次触达已发"


def norm(s):
    return re.sub(r"[\s（）()【】\[\]，,、/·\-—:：~～!！?？]", "", (s or "")).lower()


def main():
    sent = json.load(io.open(os.path.join(WORK, "resend2_send_result.json"), encoding="utf-8"))
    man = json.load(io.open(MANIFEST, encoding="utf-8"))
    jobs = man.setdefault("boss_jobs", [])
    tagged = 0
    by_jid, by_comp = [], []
    for s in sent:
        if s.get("status") != "sent":
            continue
        jid = s.get("jobId", "")
        comp = norm(s.get("company", ""))
        hit = [j for j in jobs if jid and j.get("jobId") == jid]
        how = "jobId"
        if not hit:
            hit = [j for j in jobs if norm(j.get("company", "")) == comp]
            how = "company"
        if not hit:
            by_comp.append((s.get("company"), jid, "NO_ENTRY"))
            continue
        for j in hit:
            note = j.get("note", "") or ""
            if STAMP not in note:
                j["note"] = (note + " ｜ " + STAMP).strip()
                tagged += 1
            else:
                tagged += 1
        by_jid.append((s.get("company"), jid, how, len(hit)))

    man["generated"] = datetime.now().strftime("%Y-%m-%d")
    io.open(MANIFEST, "w", encoding="utf-8").write(json.dumps(man, ensure_ascii=False, indent=1))

    print(f"回填 {tagged} 次（涉及 {len(by_jid)} 段会话）")
    no_entry = [x for x in by_comp]
    print(f"没找到对应 manifest 条目的会话：{len(no_entry)}")
    for x in no_entry:
        print("   ", x)
    multi = [x for x in by_jid if x[3] > 1]
    print(f"命中多条目（同公司多岗位共用 jobId）的会话：{len(multi)}")
    for x in multi[:10]:
        print("   ", x)
    print("manifest 总条数:", len(jobs),
          "带第二次触达标记:", sum(1 for x in jobs if "第二次触达" in (x.get("note") or "")))


if __name__ == "__main__":
    main()
