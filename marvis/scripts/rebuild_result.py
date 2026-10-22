#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rebuild_result.py — 重建被覆盖的 <prefix>_result.json。

场景：补投/重跑时用同一个 PREFIX，结果文件被覆盖成只含本次的记录。
本脚本按「最终状态」重建：投递状态以补投后的记录为准，
其余目标按已核对的事实标注。

用法: python rebuild_result.py <prefix> [补投前缀 ...]
"""
import io
import json
import os
import sys

WORK = r"YOUR_HOME\output\boss_work"


def jload(p):
    if not os.path.isfile(p):
        return None
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return None


def main():
    prefix = sys.argv[1]
    finals = jload(os.path.join(WORK, f"{prefix}_final.json")) or []
    report = {r["label"]: r for r in (jload(os.path.join(WORK, f"{prefix}_msg_report.json")) or [])}
    # 会话指纹判定（本轮真实新投 / 历史已投 / 未投出）
    mt = {m["label"]: m for m in (jload(os.path.join(WORK, f"{prefix}_msgtime.json")) or [])
          if isinstance(m, dict)}
    # 收集所有批次的 result（同 prefix 的 + 补投批次的），jobId → 最新状态
    latest = {}
    for fn in os.listdir(WORK):
        if not fn.endswith("_result.json"):
            continue
        rows = jload(os.path.join(WORK, fn)) or []
        for r in rows if isinstance(rows, list) else []:
            if not isinstance(r, dict):
                continue
            jid = r.get("jobId")
            if not jid:
                continue
            prev = latest.get(jid)
            # sent 优先于 already_sent / 其它状态
            if prev is None or (r.get("status") == "sent" and prev.get("status") != "sent"):
                latest[jid] = r
    out = []
    for t in finals:
        jid = t.get("jobId")
        rec = latest.get(jid)
        rep = report.get(t["label"], {})
        item = dict(label=t["label"], city=t.get("city", ""), company=t.get("company", ""),
                    jobId=jid, greeting_len=rep.get("main_len", 0),
                    lines=rep.get("main_len", 0) and 0 or 0)
        verdict = (mt.get(t["label"]) or {}).get("verdict")
        if verdict == "this_batch":
            item["status"] = "sent"
        elif verdict == "older_batch":
            item["status"] = "already_sent"
        elif verdict == "no_my_msg":
            item["status"] = "not_sent"
        elif rec is None:
            item["status"] = "not_run"
        else:
            item["status"] = rec.get("status")
            item["greeting_len"] = rec.get("greeting_len", rep.get("main_len", 0))
            item["lines"] = rec.get("lines", 0)
        out.append(item)
    p = os.path.join(WORK, f"{prefix}_result.json")
    json.dump(out, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    from collections import Counter
    print(f"重建 {len(out)} 条 → {p}")
    print("状态分布:", dict(Counter(x["status"] for x in out)))
    for x in out:
        print(f"  {x['status']:<16} {x.get('company','')[:16]:<18} {x['label'][:46]}")


if __name__ == "__main__":
    main()
