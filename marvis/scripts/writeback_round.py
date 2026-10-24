# -*- coding: utf-8 -*-
"""writeback_ai2.py — 本轮（2026-10-23）BOSS 两件事的写回：

  附录十四 · 新投 5 个 AI 岗（广东AI2 / 收藏AI2）
  附录十五 · 未读会话第二次触达（重发）

manifest：
  · 5 个新投岗位各新增一条（含 jobId）
  · 重发不新增条目（同一岗位同一 jobId），只在 note 里追加「第二次触达」记录

用法: python writeback_ai2.py
"""
import io
import json
import os
import re
from collections import Counter
from datetime import datetime

WORK = r"YOUR_HOME\output\boss_work"
RECRUIT = r"YOUR_HOME\招聘"
MANIFEST = os.path.join(RECRUIT, "boss_manifest.json")
RECORD = r"YOUR_HOME\output\投递记录.md"

PDF_DEV = r"研发实习生\候选人-实习.pdf（全量版 3 页 11 项目）"
PDF_AI = r"AI Coding全栈工程师\你的名字-AICoding全栈工程师.pdf"

IMG_NOTE = {
    "研发实习生\\shot_全量版_p1.png": "研发实习生版 p1/p2",
    "AI Coding全栈工程师\\shot_aicoding_p1.png": "AI Coding 版 p1/p2",
}


def jload(p):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return None


def norm(s):
    return re.sub(r"[\s（）()【】\[\]，,、/·\-—:：~～!！?？]", "", (s or "")).lower()


def main():
    final = jload(os.path.join(WORK, "ai2_final.json")) or []
    verify = jload(os.path.join(WORK, "ai2_verify.json")) or []
    result = jload(os.path.join(WORK, "ai2_result.json")) or []
    rep = jload(os.path.join(WORK, "ai2_msg_report.json")) or []
    resend = jload(os.path.join(WORK, "resend2_send_result.json")) or []
    rtg = jload(os.path.join(WORK, "resend_targets.json")) or []

    ver_by = {v.get("folder"): v for v in verify}
    rep_by = {r.get("label"): r for r in rep}
    res_by = {r.get("folder"): r for r in result}

    # ── 1) manifest ────────────────────────────────────────────────
    man = json.load(io.open(MANIFEST, encoding="utf-8"))
    jobs = man.setdefault("boss_jobs", [])
    have = {j.get("folder") for j in jobs}
    added = 0
    for t in final:
        if t["folder"] in have:
            continue
        r = rep_by.get(t["label"], {}) or rep_by.get(t["folder"], {})
        v = ver_by.get(t["folder"], {})
        rs = res_by.get(t["folder"], {})
        pdf = PDF_DEV if "研发实习生" in (t.get("imgs") or [""])[0] else PDF_AI
        atoms = "/".join(r.get("atoms", [])) or "-"
        note = (f"{datetime.now():%Y-%m-%d} 按 JD 定制话术（证据原子 {atoms}），"
                f"{r.get('main_len', '?')} 字多行话术 + 2 张简历图，"
                f"独立复核：话术 {v.get('my_text', '?')} 条 / 简历图 {v.get('imgs_in_conv', '?')} 张"
                f"（投递状态 {rs.get('status', '?')}）")
        jobs.append({
            "folder": t["folder"],
            "channel": "boss",
            "company": t.get("company", ""),
            "title": t.get("position", ""),
            "salary": t.get("salary", ""),
            "city": t.get("city", ""),
            "jobId": t.get("jobId", ""),
            "greeting_file": os.path.join(RECRUIT, t["folder"], "新建 文本文档.txt"),
            "pdf": os.path.join(RECRUIT, pdf),
            "note": note,
        })
        have.add(t["folder"])
        added += 1

    # 重发：同一 jobId 的条目追加「第二次触达」note，不新增
    touched = 0
    if resend:
        by_label = {x.get("label"): x for x in resend}
        for tg in rtg:
            lab = tg.get("label", "")
            row = by_label.get(f"重发AI-{lab}") or by_label.get(lab)
            if not row or row.get("status") != "sent":
                continue
            for j in jobs:
                if norm(j.get("company", "")) == norm(tg.get("company", "")) and \
                   j.get("jobId") == tg.get("jobId"):
                    stamp = f"{datetime.now():%Y-%m-%d} 第二次触达已发"
                    if stamp not in (j.get("note") or ""):
                        j["note"] = (j.get("note", "") + " ｜ " + stamp).strip()
                    touched += 1
                    break

    man["generated"] = datetime.now().strftime("%Y-%m-%d")
    io.open(MANIFEST, "w", encoding="utf-8").write(
        json.dumps(man, ensure_ascii=False, indent=1))

    # ── 2) 投递记录.md ─────────────────────────────────────────────
    L = []
    L.append("")
    L.append(f"# 附录十四 · 第十轮：新投 5 个 AI 岗（站内 AI 搜索 + 收藏夹合并批）"
             f"（{datetime.now():%Y-%m-%d %H:%M} 写入）")
    L.append("")
    L.append("## 一、这一轮扫了什么")
    L.append("")
    L.append("- 站内 AI 搜索补扫 9 城（广州/深圳/东莞/佛山/珠海/惠州/中山/汕头/某城市）"
             "× 10 词 × 2 页 = 180 次导航，候选 51 个")
    L.append("- 收藏夹重拉：tag=4 → 124 条（原 119，+5）、tag=5 → 210 条")
    L.append("- 两批合并候选 **39** 个 → JD 硬规则劝退 **34** 个 → 保留 **5** 个")
    L.append("")
    L.append("## 二、JD 正文硬规则劝退（修过的三条）")
    L.append("")
    L.append("| 规则 | 作用 | 拦下的例子 |")
    L.append("|---|---|---|")
    L.append("| `TITLE_NO_INTERN` | 标题里出现「不考虑实习生/非实习/坐班」直接劝退 | 示例企业37 |")
    L.append("| `TITLE_BOUNDARY` | coze / dify / n8n / langchain 等我没做过的框架 | 大白熊 |")
    L.append("| `NONDEV_DUTY`（补 AIGC 内容评测类） | 音色/发音/短剧配乐/评测标准等非开发岗 | 示例科技R |")
    L.append("")
    L.append("## 三、投递与独立核对明细")
    L.append("")
    L.append("| 城市 | 公司 | 岗位 | 薪资 | 话术字数 | 会话话术条数 | 简历图张数 | 面板岗位名 | 结论 |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for t in final:
        v = ver_by.get(t["folder"], {})
        r = rep_by.get(t["label"], {}) or rep_by.get(t["folder"], {})
        ok = v.get("status") == "verified"
        L.append(f"| {t.get('city','')} | {t.get('company','')} | {t.get('position','')} | "
                 f"{t.get('salary','')} | {r.get('main_len','?')} | {v.get('my_text','?')} | "
                 f"{v.get('imgs_in_conv','?')} | {v.get('pos','')[:22]} | "
                 f"{'✅ 已投且核对通过' if ok else '❌ 未达标'} |")
    L.append("")
    L.append("**核对方式**：投递脚本自报结果不算数，另写 `verify_ai2.py` 重开消息页、"
             "逐个点开会话重新数「我的文字条数」和「简历图张数」，"
             "同时比对会话面板上的岗位名与目标岗位是否一致。")
    L.append("")
    L.append(f"**manifest**：新增 {added} 条（现共 {len(jobs)} 条）")
    L.append("")
    L.append("## 四、遗留")
    L.append("")
    L.append("- 示例大厂K东莞岗的页面公司名在详情页 DOM 里被 `detail_company()` 取成了别的元素"
             "（取到西安示例公司AC/示例网络Y等），实际公司以**会话头**为准（候选人L先生示例大厂K招聘者）——"
             "校验逻辑已改为「页面正文含公司名 + 会话头二次确认」")
    L.append("- 示例科技Q「AI应用开发（校招，广州）」入口是「立即网申」，需在 BOSS 网页版完善在线简历")
    L.append("")
    L.append("")
    L.append(f"# 附录十五 · 第十轮续：对「已投但对方未读」的会话补发第二次触达"
             f"（{datetime.now():%Y-%m-%d %H:%M} 写入）")
    L.append("")
    L.append("## 一、判定口径")
    L.append("")
    L.append("用户口径：**线上已读的不再新投**；已投但对方仍未读的，重发一次话术。")
    L.append("")
    L.append("- 「已读」= 对方看过我方消息。列表里的 `[送达]` 标记不够用——"
             "带 `[送达]` 但后面跟着对方文字的，说明对方已回过、我的消息必已被读。")
    L.append("- 所以最终判定在**会话内部**做，逐个点开会话读三件事："
             "`state` 是不是已读、最后一条是不是我发的、对方有没有回过话。")
    L.append("- 分层：投递不足 2 天的（昨晚 21:00 那批 23 个）一律不重发，"
             "留到满 2 天再说。")
    L.append("")
    L.append("## 二、候选规模")
    L.append("")
    L.append("- 会话列表全量收集 **218** 条（已送达/已读/无标记）")
    L.append("- 与 `boss_manifest.json` 已投公司匹配后去重 **121** 个会话")
    L.append("- 满 2 天的 **70** 个 → 逐个进会话做精确判定")
    L.append("")
    L.append("## 三、第二次触达话术怎么写的")
    L.append("")
    L.append("**不是重发原文**。结构固定为四段：")
    L.append("")
    L.append("1. 一句开场（不重复「我是谁」，改成「怕您没看到关键信息」这类）")
    L.append("2. 一条最硬证据（按首次投递话术的**段落标签**映射，只挑一条）")
    L.append("3. 一句到岗承诺（可实习 / 数月以上）")
    L.append("4. 一句低门槛收尾（「回一句也行，我不纠缠」）")
    L.append("")
    L.append("- 长度 105–155 字，**不带简历图**（第一次已经带过，再带变刷屏）")
    L.append("- 证据只取首次话术里已经出现过的原子，**不新增任何技术或数字**")
    L.append("- 档案单独存 `招聘/重发AI-*`（70 个目录），不覆盖首次话术目录")
    L.append("")
    L.append("## 四、发送结果")
    L.append("")
    cnt = Counter(r.get("status") for r in resend)
    L.append("| 结果 | 数量 |")
    L.append("|---|---|")
    for k, v in cnt.most_common():
        L.append(f"| {k} | {v} |")
    L.append("")
    sent_rows = [r for r in resend if r.get("status") == "sent"]
    L.append(f"**实际发出 {len(sent_rows)} 条**，每条间隔 ≥6 秒，每 15 条歇 25 秒，"
             "全程带登录态守卫（被风控踢到 `/web/user/` 立即停）。")
    L.append("")
    if sent_rows:
        L.append("### 已发出的会话")
        L.append("")
        L.append("| # | 公司 | 岗位 | 字数 | 会话头 |")
        L.append("|---|---|---|---|---|")
        for i, r in enumerate(sent_rows, 1):
            L.append(f"| {i} | {r.get('company','')} | {r.get('position','')} | "
                     f"{r.get('chars','')} | {r.get('conv_head','')[:30]} |")
        L.append("")
    skipped = [r for r in resend if r.get("status") not in ("sent",)]
    if skipped:
        L.append("### 跳过明细（各自动作的原因）")
        L.append("")
        L.append("| 公司 | 会话头 | 跳过原因 | 现场信息 |")
        L.append("|---|---|---|---|")
        for r in skipped:
            info = (r.get("last") or "")[:40] if r.get("status") == "hr_replied" else (r.get("state") or "")[:20]
            L.append(f"| {r.get('company','')} | {r.get('conv_head','')[:26]} | "
                     f"{r.get('status')} | {info} |")
        L.append("")
    L.append("## 五、遗留")
    L.append("")
    L.append("- 本轮**只动未读**的会话；已读的一个都没碰")
    L.append("- 用旧模板投递的历史会话没有补发差异化话术（补发更像群发）")
    L.append("- 网页版没有逐条撤回入口，历史重复消息/图仍需手删")
    L.append("")

    with io.open(RECORD, "a", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

    print(f"manifest 新增 {added} 条、重发补注 {touched} 条（现共 {len(jobs)} 条）")
    print(f"投递记录已追加 附录十四 + 附录十五 → {RECORD}")
    print("重发结果:", dict(cnt))


if __name__ == "__main__":
    main()
