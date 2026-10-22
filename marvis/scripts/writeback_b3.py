#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""writeback_b3.py — 投递结果写回：manifest 条目 + 投递记录.md 章节。

三态判定（优先用 <prefix>_msgtime.json 的会话指纹比对，回落 result 文件）：
  sent         本轮真实新投（会话里能找到本批生成的话术）
  already_sent 历史已投，本轮正确跳过（会话里最后是我方旧话术）
  not_sent     没能投出去（如「立即网申」形态、详情页超时）

写回规则：
  sent         → manifest 新增条目（含 jobId）
  already_sent → 若 manifest 已有同公司同岗位条目 → 只补 jobId（防重投），不新增
                 否则新增条目并标注「历史已投」
  not_sent     → 不写 manifest（避免污染幂等导致永远不投），只进遗留清单

用法（环境变量参数化，可多批次依次执行）:
  B3_PREFIX=favai B3_APPENDIX=附录八 B3_TITLE=... B3_SCAN=... python writeback_b3.py
"""
import difflib
import io
import json
import os
import re
import sys
from datetime import datetime

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


def norm(s):
    return re.sub(r"[\s（）()【】\[\]，,、/·\-—:：~～!！?？]", "", (s or "")).lower()


def same_job(a_pos, b_pos, a_comp, b_comp):
    """同公司 + 岗位名相似 → 视为同一个岗位的两次记录。"""
    if norm(a_comp) != norm(b_comp):
        return False
    a, b = norm(a_pos), norm(b_pos)
    if not a or not b:
        return False
    if a == b or a in b or b in a:
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.6


def main():
    targets = jload(f"{PREFIX}_targets.json") or []
    kept = jload(f"{PREFIX}_kept.json") or []
    final = jload(f"{PREFIX}_final.json") or []
    result = jload(f"{PREFIX}_result.json") or []
    check = jload(f"{PREFIX}_check.json") or []
    report = jload(f"{PREFIX}_msg_report.json") or []
    mtime = jload(f"{PREFIX}_msgtime.json") or []
    dropped = [(d.get("label", ""), d.get("reason", ""))
               for d in (jload(f"{PREFIX}_kept_dropped.json") or [])
               if isinstance(d, dict)]

    chk_by_label = {c.get("label"): c for c in check if isinstance(c, dict)}
    rep_by_label = {r.get("label"): r for r in report if isinstance(r, dict)}
    res_by_label = {r.get("label"): r for r in result if isinstance(r, dict)}
    mt_by_label = {m.get("label"): m for m in mtime if isinstance(m, dict)}

    def status_of(label, t=None):
        """三态判定。优先级：会话指纹 > manifest 历史条目 > result 文件。"""
        v = (mt_by_label.get(label) or {}).get("verdict")
        if v == "this_batch":
            return "sent"
        if v == "older_batch":
            return "already_sent"
        if t is not None:
            # manifest 里已有同公司同岗位的条目 = 历史投过（只是漏记了 jobId）
            for j in jobs:
                if same_job(j.get("title", ""), t.get("position", ""),
                            j.get("company", ""), t.get("company", "")):
                    return "already_sent"
        if v == "no_my_msg":
            return "not_sent"
        st = (res_by_label.get(label) or {}).get("status")
        if st == "sent":
            return "sent"
        if st in ("already_sent", "already"):
            return "already_sent"
        return "not_sent"

    # ── 1) manifest ────────────────────────────────────────────────
    man = json.load(io.open(MANIFEST, encoding="utf-8"))
    jobs = man.setdefault("boss_jobs", [])
    have = {j.get("folder") for j in jobs}
    added, backfilled, skipped = 0, 0, 0
    state = {}

    for t in final:
        label = t["label"]
        st = status_of(label, t)
        state[label] = st
        if st == "not_sent":
            skipped += 1
            continue
        r = rep_by_label.get(label, {})
        c = chk_by_label.get(label, {})
        atoms = "/".join(r.get("atoms", [])) or "-"
        ok = bool(c.get("ok"))
        tail = "已核对合格" if ok else "核对未达标"
        if st == "already_sent":
            tail = "历史已投，本批正确跳过（会话内为旧话术）"
        note = (f"{datetime.now():%Y-%m-%d} 按 JD 定制话术（证据原子 {atoms}），"
                f"{r.get('main_len', '?')} 字多行话术 + 2 张简历图，"
                f"{tail}（投递状态 {st}）")
        pdf_rel = r.get("pdf") or r"研发实习生\候选人-实习.pdf（全量版 3 页 11 项目）"

        # 已在 manifest 里有同公司同岗位的条目
        hit = None
        for j in jobs:
            if same_job(j.get("title", ""), t.get("position", ""),
                        j.get("company", ""), t.get("company", "")):
                hit = j
                break
        if hit is not None:
            if hit.get("jobId") == t.get("jobId"):
                continue                      # 同一职位页，已记录
            if not hit.get("jobId") and t.get("jobId"):
                hit["jobId"] = t["jobId"]
                hit["note"] = (hit.get("note", "") + f" ｜ {datetime.now():%Y-%m-%d} 补记 jobId").strip()
                backfilled += 1
                continue                      # 历史投递，补 jobId 即可，不新增
            # jobId 不同 = BOSS 上不同的职位页 → 走下面的新增分支

        if t.get("folder") in have:
            continue
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
        have.add(t["folder"])
        added += 1

    man["generated"] = datetime.now().strftime("%Y-%m-%d")
    with io.open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=1)

    # ── 2) 投递记录.md ─────────────────────────────────────────────
    ok_n = sum(1 for c in check if isinstance(c, dict) and c.get("ok"))
    sent_n = sum(1 for s in state.values() if s == "sent")
    hist_n = sum(1 for s in state.values() if s == "already_sent")
    miss_n = sum(1 for s in state.values() if s == "not_sent")
    man_n = len(jobs)

    L = []
    L.append("")
    L.append(f"# {APPENDIX} · {ROUND_NAME}（{datetime.now():%Y-%m-%d %H:%M} 写入）")
    L.append("")
    L.append("## 一、这一轮扫了什么")
    L.append("")
    L.append(f"- 扫描方式：{SCAN_NOTE}")
    L.append(f"- 排除口径：`boss_manifest.json`（写回前 {man_n} 条）+ 各批 targets/final/result 全部 jobId")
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
    L.append("证据原子 + JD 匹配 + 开头/结尾句式轮换 + 长度分档，**不是按岗位标题套模板**。")
    L.append("同公司多岗位强制换证据组合（同一 HR 视角下撞车=群发）。")
    L.append("差异度量化验收见下节。")
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
    L.append("| 城市 | 公司 | 岗位 | 薪资 | 话术字数 | 换行 | 图 | 岗位名对位 | 本轮状态 | 结论 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for t in final:
        c = chk_by_label.get(t["folder"], {}) or chk_by_label.get(t["label"], {})
        r = rep_by_label.get(t["label"], {}) or rep_by_label.get(t["folder"], {})
        st = state.get(t["label"], "?")
        st_txt = {"sent": "✅ 本轮新投", "already_sent": "⏭ 历史已投",
                  "not_sent": "❌ 未投出"}.get(st, st)
        L.append(f"| {t.get('city','')} | {t.get('company','')} | {t.get('position','')} | "
                 f"{t.get('salary','')} | {r.get('main_len','?')} | {c.get('brs','?')} | "
                 f"{c.get('images','?')} | {c.get('pos','')[:20]} | {st_txt} | "
                 f"{'✅ 合格' if c.get('ok') else '❌ 未达标'} |")
    L.append("")
    L.append(f"**核对结论**：核对 {len(check)} 个会话，合格 **{ok_n}/{len(check)}**；"
             f"本轮新投 **{sent_n}**、历史已投跳过 **{hist_n}**、未投出 **{miss_n}**")
    L.append("")
    L.append(f"**manifest**：新增 {added} 条、补记 jobId {backfilled} 条、"
             f"未写入 {skipped} 条（当前共 {man_n} 条）")
    L.append("")
    L.append("## 六、遗留待办")
    L.append("")
    for t in final:
        if state.get(t["label"]) == "not_sent":
            L.append(f"- **未投出**：{t.get('company','')} · {t.get('position','')}"
                     f"（{t.get('city','')}）—— 需人工在网页版处理")
    L.append("- 网页版无逐条撤回入口，重复消息只能手删")
    L.append("- 旧模板已投的会话未补发差异化话术（补发更像群发，除非明确要求）")
    L.append("")
    with io.open(RECORD, "a", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

    print(f"manifest 新增 {added} 条 / 补记 jobId {backfilled} 条 / 未写 {skipped} 条"
          f"（现共 {len(jobs)} 条）")
    print(f"投递记录已追加 → {RECORD}")
    print(f"本轮新投 {sent_n} ｜ 历史已投跳过 {hist_n} ｜ 未投出 {miss_n} ｜ 核对合格 {ok_n}/{len(check)}")


if __name__ == "__main__":
    main()
