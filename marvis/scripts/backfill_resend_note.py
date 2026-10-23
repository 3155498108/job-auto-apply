# -*- coding: utf-8 -*-
"""backfill_resend_note.py — 给 manifest 里已投岗位的 note 补「第二次触达」标记。

按 jobId + 公司名匹配（不靠 label，label 的批次前缀规则各批次不一样）。
幂等：已打过标记的不重复打。
"""
import io
import json
import os
import re
from datetime import datetime

WORK = r"YOUR_HOME\output\boss_work"
MANIFEST = r"YOUR_HOME\招聘\boss_manifest.json"


def norm(s):
    return re.sub(r"[\s（）()【】\[\]，,、/·\-—:：~～!！?？]", "", (s or "")).lower()


def main():
    resend = json.load(io.open(os.path.join(WORK, "resend2_send_result.json"), encoding="utf-8"))
    man = json.load(io.open(MANIFEST, encoding="utf-8"))
    jobs = man.setdefault("boss_jobs", [])
    stamp = f"{datetime.now():%Y-%m-%d} 第二次触达已发"

    by_jid = {}
    for r in resend:
        if r.get("status") != "sent":
            continue
        by_jid.setdefault(r.get("jobId", ""), []).append(r)

    hit, miss = 0, []
    for r in resend:
        if r.get("status") != "sent":
            continue
        jid = r.get("jobId", "")
        comp = norm(r.get("company", ""))
        cands = [j for j in jobs
                 if (jid and j.get("jobId") == jid)
                 or (norm(j.get("company", "")) == comp and jid and j.get("jobId") == jid)]
        if not cands:
            cands = [j for j in jobs if norm(j.get("company", "")) == comp]
        if not cands:
            miss.append((r.get("company", ""), jid))
            continue
        j = cands[0]
        note = j.get("note", "") or ""
        if stamp in note:
            hit += 1
            continue
        j["note"] = (note + " ｜ " + stamp).strip()
        hit += 1

    man["generated"] = datetime.now().strftime("%Y-%m-%d")
    io.open(MANIFEST, "w", encoding="utf-8").write(json.dumps(man, ensure_ascii=False, indent=1))
    print(f"已回填 {hit} 条；未匹配到 manifest 条目的 {len(miss)} 个")
    for m in miss[:10]:
        print("   未匹配:", m)


if __name__ == "__main__":
    main()
