#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""writeback_b3.py — 第三批投递结果写回：manifest 条目 + 投递记录.md 章节。

输入（output/boss_work/）：
  b3_targets.json  选中岗位（含劝退前的全部）
  b3_kept.json     JD 硬规则保留的岗位
  b3_final.json    实际投递清单
  b3_result.json   投递结果
  b3_check.json    逐会话核对结果
  b3_msg_report.json 话术生成报告

用法: python writeback_b3.py
"""
import io
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, r"YOUR_REPO\marvis")
from scripts.wb_scan3 import load_done  # noqa: F401  (保持依赖路径一致)

WORK = r"YOUR_HOME\output\boss_work"
RECRUIT = r"YOUR_HOME\招聘"
MANIFEST = os.path.join(RECRUIT, "boss_manifest.json")
RECORD = r"YOUR_HOME\output\投递记录.md"
PREFIX = os.environ.get("B3_PREFIX", "b3")
APPENDIX = os.environ.get("B3_APPENDIX", "附录八")
ROUND_NAME = os.environ.get("B3_TITLE", "第七轮：第三批扩投")
SCAN_NOTE = os.environ.get("B3_SCAN", "7 城 × 12 关键词 × 2 页")


def jload(name):
    p = os.path.join(WORK, name)
    if not os.path.isfile(p):
        return None
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return None


def main():
    targets = jload(f"{PREFIX}_targets.json") or []
    kept = jload(f"{PREFIX}_kept.json") or []
    final = jload(f"{PREFIX}_final.json") or []
    result = jload(f"{PREFIX}_result.json") or []
    check = jload(f"{PREFIX}_check.json") or []
    report = jload(f"{PREFIX}_msg_report.json") or []

    # ── 1) manifest ────────────────────────────────────────────────
    man = json.load(io.open(MANIFEST, encoding="utf-8"))
    jobs = man.setdefault("boss_jobs", [])
    have = {j.get("folder") for j in jobs}
    added = 0
    chk_by_label = {c.get("label"): c for c in check if isinstance(c, dict)}
    rep_by_label = {r.get("label"): r for r in report if isinstance(r, dict)}
    res_by_label = {r.get("label"): r for r in result if isinstance(r, dict)}

    for t in final:
        if t.get("folder") in have:
            continue
        c = chk_by_label.get(t["folder"], {})
        ok = bool(c.get("ok"))
        r = rep_by_label.get(t["folder"], {})
        res = res_by_label.get(t["folder"], {})
        atoms = "/".join(r.get("atoms", [])) or "-"
        note = (f"{datetime.now():%Y-%m-%d} 按 JD 定制话术（证据原子 {atoms}），"
                f"{r.get('main_len', '?')} 字多行话术 + 2 张简历图，"
                f"{'已核对合格' if ok else '核对未达标'}"
                f"（投递状态 {res.get('status', '?')}）")
        pdf_rel = r.get("pdf") or r"研发实习生\候选人-实习.pdf（全量版 3 页 11 项目）"
        jobs.append({
            "folder": t["folder"],
            "channel": "boss",
            "company": t.get("company", ""),
            "title": t.get("position", ""),
            "salary": t.get("salary", ""),
            "city": t.get("city", ""),
            "jobId": t.get("jobId", ""),
            "greeting_file": os.path.join(RECRUIT, t["folder"], "新建 文本文档.txt"),
            "pdf": os.path.join(RECRUIT, pdf_rel),
            "note": note,
        })
        added += 1
    man["generated"] = datetime.now().strftime("%Y-%m-%d")
    with io.open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=1)

    # ── 2) 投递记录.md ─────────────────────────────────────────────
    dropped = [(d.get("label", ""), d.get("reason", ""))
               for d in (jload(f"{PREFIX}_kept_dropped.json") or [])
               if isinstance(d, dict)]
    ok_n = sum(1 for c in check if isinstance(c, dict) and c.get("ok"))
    sent_n = sum(1 for r in result if r.get("status") == "sent")

    L = []
    L.append("")
    L.append(f"# {APPENDIX} · {ROUND_NAME}（{datetime.now():%Y-%m-%d %H:%M} 起）")
    L.append("")
    L.append("## 一、这一轮扫了什么")
    L.append("")
    L.append(f"- 扫描方式：{SCAN_NOTE}")
    L.append(f"- 排除口径：`boss_manifest.json`（112 条已投）+ 各批 targets/final/result 全部 jobId")
    L.append(f"- 命中候选 **{len(targets)}** 个 → JD 硬规则劝退 **{len(dropped)}** 个 → 保留 **{len(kept)}** 个")
    L.append("")
    L.append("## 二、JD 正文硬规则劝退清单")
    L.append("")
    L.append("| 岗位 | 劝退理由 |")
    L.append("|---|---|")
    for lab, why in dropped:
        L.append(f"| {lab} | {why} |")
    L.append("")
    L.append("## 三、话术策略")
    L.append("")
    L.append("与第六轮同一套引擎：证据原子 + JD 匹配 + 开头/结尾句式轮换 + 长度分档，")
    L.append("**不是按岗位标题套模板**。差异度量化验收见下节。")
    L.append("")
    L.append("## 四、差异度实测")
    L.append("")
    diff_file = os.path.join(WORK, f"{PREFIX}_diff.txt")
    if os.path.isfile(diff_file):
        with io.open(diff_file, encoding="utf-8") as f:
            L.extend([ln.rstrip() for ln in f])
    else:
        L.append("(未生成差异度报告)")
    L.append("")
    L.append("## 五、投递与核对明细")
    L.append("")
    L.append("| 城市 | 公司 | 岗位 | 薪资 | 话术字数 | 换行 | 图 | 岗位名对位 | 结论 |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for t in final:
        c = chk_by_label.get(t["folder"], {})
        r = rep_by_label.get(t["folder"], {})
        L.append(f"| {t.get('city','')} | {t.get('company','')} | {t.get('position','')} | "
                 f"{t.get('salary','')} | {r.get('main_len','?')} | {c.get('brs','?')} | "
                 f"{c.get('images','?')} | {c.get('pos','')[:20]} | "
                 f"{'✅ 合格' if c.get('ok') else '❌ 未达标'} |")
    L.append("")
    L.append(f"**核对结论**：投递 {len(result)} 个（状态 sent {sent_n}）｜"
             f"核对 {len(check)} 个，合格 **{ok_n}/{len(check)}**")
    L.append("")
    L.append("## 六、遗留待办")
    L.append("")
    L.append("- 网页版无逐条撤回入口，重复消息只能手删")
    L.append("- 旧模板已投的 77 个会话未补发差异化话术（补发更像群发，除非明确要求）")
    L.append("")
    with io.open(RECORD, "a", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

    print(f"manifest 新增 {added} 条（现共 {len(jobs)} 条）")
    print(f"投递记录已追加 → {RECORD}")
    print(f"核对 {ok_n}/{len(check)} 合格")


if __name__ == "__main__":
    main()
