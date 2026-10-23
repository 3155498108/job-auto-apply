# -*- coding: utf-8 -*-
"""rebuild_record.py — 重建 output\\投递记录.md。

背景（2026-10-23）：并行的 51job 会话用「读全文 → 改 → 写回全文」的方式覆盖了
投递记录.md，把 BOSS 这边的章节整段抹掉了：
  · 备份 投递记录.bak.md（10-22 17:24）覆盖了「附录·BOSS 自动化投递」~「附录九」
  · 「附录十/十一/十二 + 补充说明」（10-22 21:23 写）不在备份里 —— 但可以从
    output/boss_work/ 下的 JSON 产物用 writeback_b3.py 原样重新生成
  · 「附录十三」（51job）与「附录十四/十五」（BOSS 本轮）以当前文件为准

拼装顺序（与原始顺序一致）：
  备份[头 + 岗位明细] + 备份[附录·BOSS ~ 附录九] + 重建[附录十~十二 + 补充说明]
  + 当前[附录十三~十五]

用法: python rebuild_record.py [--write]
不带 --write 只生成到临时文件并打印校验结果。
"""
import io
import importlib.util
import json
import os
import re
import shutil
import sys
from datetime import datetime

WORK = r"YOUR_HOME\output\boss_work"
CUR = r"YOUR_HOME\output\投递记录.md"
BAK = r"YOUR_HOME\output\boss_work\投递记录.bak.md"
TMP = r"YOUR_HOME\output\boss_work\投递记录.rebuilt.md"
WB3 = r"YOUR_REPO\job-auto-apply\marvis\scripts\writeback_b3.py"

# (产物前缀, 附录名, 标题, 扫描描述, 原始候选数)
BATCHES = [
    ("ai", "附录十", "第九轮：AI 方向补投（站内 AI 搜索批）",
     "站内搜索 AI 关键词补扫（`wb_scan3.py` 扫候选池 → `gen_ai_scan.py` 只留 AI 命中的岗位）",
     35),
    ("favai2", "附录十一", "第九轮续：AI 方向补投（收藏夹 AI 批）",
     "收藏夹 tag=4（收藏）+ tag=5（已沟通）合并去重，挑「AI 命中 + 未投 + 技术向」",
     14),
    ("b3bm", "附录十二", "第九轮续：第三批补投（示例科技O）",
     "上一批 32 岗里本轮新投的 1 岗（`make_b3bm.py` 切出子集单独写回）",
     1),
]


def idx(lines, pat, start=0):
    for i in range(start, len(lines)):
        if lines[i].startswith(pat):
            return i
    return -1


def gen_appendix(prefix, appendix, title, scan, candidates):
    """用 writeback_b3.py 重新生成一节附录，输出到临时文件并返回文本。"""
    tmp = os.path.join(WORK, f"_regen_{prefix}.md")
    if os.path.exists(tmp):
        os.remove(tmp)
    os.environ["B3_PREFIX"] = prefix
    os.environ["B3_APPENDIX"] = appendix
    os.environ["B3_TITLE"] = title
    os.environ["B3_SCAN"] = scan
    spec = importlib.util.spec_from_file_location("wb3_" + prefix, WB3)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)      # __name__ != '__main__'，不会自动 main()
    mod.RECORD = tmp
    real_jload = mod.jload

    def patched(name):
        # targets 文件被后续批次覆盖过（ai/favai2 的 targets 已被新一轮扫描重写），
        # 用 kept+dropped 的真实候选数补一个等长的占位列表，只为让「命中候选 N 个」正确
        if name == f"{prefix}_targets.json":
            kept = real_jload(f"{prefix}_kept.json") or []
            dropped = real_jload(f"{prefix}_kept_dropped.json") or []
            n = len(kept) + len(dropped)
            return [{"label": f"__placeholder_{i}__"} for i in range(n or candidates)]
        return real_jload(name)

    mod.jload = patched
    mod.main()
    text = io.open(tmp, encoding="utf-8").read()
    os.remove(tmp)
    # 修正「命中候选 N 个」为真实候选数
    text = re.sub(r"命中候选 \*\*\d+\*\* 个",
                  f"命中候选 **{candidates}** 个", text)
    return text


def main():
    write = "--write" in sys.argv
    cur_lines = io.open(CUR, encoding="utf-8").read().splitlines()
    bak_lines = io.open(BAK, encoding="utf-8").read().splitlines()

    i_bak_boss = idx(bak_lines, "# 附录 · BOSS 直聘自动化投递")
    i_cur_51 = idx(cur_lines, "# 附录十三")
    if i_bak_boss < 0 or i_cur_51 < 0:
        print("!! 定位失败", i_bak_boss, i_cur_51)
        return 1

    head = bak_lines[:i_bak_boss]        # 投递记录 + 岗位明细（含被截断的尾巴）
    boss = bak_lines[i_bak_boss:]        # 附录·BOSS ~ 附录九
    tail = cur_lines[i_cur_51:]          # 附录十三 ~ 附录十五

    print(f"备份头+岗位明细 {len(head)} 行 / 备份附录 {len(boss)} 行 / 当前尾部 {len(tail)} 行")

    gen = []
    for prefix, appendix, title, scan, cand in BATCHES:
        print(f"\n--- 重建 {appendix}（{prefix}）---")
        gen.append(gen_appendix(prefix, appendix, title, scan, cand))

    # 补充说明（附录十二·补）—— 用 append_notes.py 的原文，只取文本不动 manifest
    notes = io.open(os.path.join(WORK, "append_notes.py"), encoding="utf-8").read()
    m = re.search(r"L\.append\(\"\"\)\n(L\.append\(.*?\n)+", notes, re.S)
    seg = notes[notes.index("L = []"):notes.index("with io.open(RECORD")]
    ns = {"datetime": datetime}
    exec(seg, ns)
    notes_text = "\n".join(ns["L"]) + "\n"

    out = []
    out.extend(head)
    out.extend(boss)
    for g in gen:
        out.extend(g.splitlines())
    out.extend(notes_text.splitlines())
    out.extend(tail)

    io.open(TMP, "w", encoding="utf-8").write("\n".join(out).rstrip() + "\n")
    print(f"\n重建完成 → {TMP}（{len(out)} 行）")

    heads = [l for l in out if l.startswith("# ")]
    print("\n章节清单：")
    for h in heads:
        print("   ", h[:80])

    if write:
        shutil.copyfile(CUR, CUR + ".before_rebuild")
        shutil.copyfile(TMP, CUR)
        print(f"\n已写回 {CUR}（原文件备份为 {os.path.basename(CUR)}.before_rebuild）")
    else:
        print("\n（未加 --write，未覆盖原文件）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
