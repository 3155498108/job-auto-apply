# -*- coding: utf-8 -*-
"""append_audit_note.py — 给附录十五补一段「事后审计」：

逐条重开 70 个会话复核后，发现 3 个会话本不该补发（判定闸门漏判），
如实写进记录，并把修法写清楚。
"""
import io
import json
import os
from datetime import datetime

WORK = r"YOUR_HOME\output\boss_work"
RECORD = r"YOUR_HOME\output\投递记录.md"

rows = json.load(io.open(os.path.join(WORK, "audit_70.json"), encoding="utf-8"))
sent = json.load(io.open(os.path.join(WORK, "resend2_send_result.json"), encoding="utf-8"))
sent_keys = {(s.get("company", ""), s.get("jobId", "")) for s in sent if s.get("status") == "sent"}


def is_bad(r):
    a = r.get("audit") or {}
    return bool(a.get("anyRead") or (a.get("others") or []))


over = [r for r in rows if (r.get("company", ""), r.get("jobId", "")) in sent_keys and is_bad(r)]
clean = [r for r in rows if (r.get("company", ""), r.get("jobId", "")) in sent_keys and not is_bad(r)]

L = []
L.append("")
L.append("## 六、事后审计：3 个误发（如实记录）")
L.append("")
L.append(f"补发完成后，**重开全部 {len(rows)} 个会话逐条复核**"
         "（读我方每条消息的状态序列、对方说过的话、最后一条是谁发的）：")
L.append("")
L.append(f"- 复核结果：**{len(clean)} 个干净**（全程无一条已读、对方没回过话 → 补发合规）")
L.append(f"- **{len(over)} 个误发**（线上已被读过，不该再发）")
L.append("")
L.append("### 漏判原因")
L.append("")
L.append("发送时的闸门只看**最后一条**我方消息的状态、以及**最后一条**是不是我发的。"
         "这 3 个会话里，对方回话后我方又回过一句，于是最后一条是「送达」、"
         "`lastIsMe` 仍是 true，而**更早的消息早已「已读」**——两道检查同时漏判。")
L.append("")
L.append("### 误发明细")
L.append("")
L.append("| 公司 | 对方说过的话 | 我方消息状态序列 | 现在的状态 |")
L.append("|---|---|---|---|")
for r in over:
    a = r["audit"]
    others = " ／ ".join(o[:40] for o in (a.get("others") or []))
    states = "/".join(a.get("myStates") or [])
    now = "补发已发出，随后会话显示「你撤回了一条消息」→ **已被撤回，HR 侧看不到**" \
        if "撤回" in (a.get("last") or "") else "**补发已发出且 HR 可见**"
    L.append(f"| {r.get('company','')} | {others} | {states} | {now} |")
L.append("")
L.append("### 修法（已落到脚本）")
L.append("")
L.append("闸门从 4 道改成 5 道，其中两条判定换了口径：")
L.append("")
L.append("1. **对方只要回过一句**（任何一条非我方消息）→ 跳过。"
         "不再只看「最后一条是不是我发的」。")
L.append("2. **任意一条**我方消息已读 → 跳过。不再只看最后一条的状态。")
L.append("")
L.append("修改已同步进 `marvis/scripts/wb_resend.py`，")
L.append("并写进 `skill/job-auto-apply/references/second-touch.md` 的「已读判定」一节。")
L.append("")
L.append("### 待人工处理")
L.append("")
for r in over:
    a = r["audit"]
    if "撤回" not in (a.get("last") or ""):
        L.append(f"- **{r.get('company','')}**（{r.get('position','')}）："
                 f"补发的那条「怕您没看到…」在会话里 HR 可见，"
                 f"网页版没有逐条撤回入口，**建议手动删掉**")
L.append("")

with io.open(RECORD, "a", encoding="utf-8") as f:
    f.write("\n".join(L) + "\n")
print(f"已追加审计说明：干净 {len(clean)} / 误发 {len(over)}")
for r in over:
    print("  误发:", r.get("company"), "|", (r["audit"].get("others") or [""])[-1][:50])
