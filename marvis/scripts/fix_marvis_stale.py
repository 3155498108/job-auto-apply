#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix_marvis_stale.py — 更正 marvis/ 里的过时数字。

背景：上一轮「38 款 → 数十款」「若干仓库、数十次提交 → 若干个公开仓库、多次提交」
的全量更正只覆盖了 YOUR_HOME，没覆盖到这个仓库。
marvis/user_profile.json 和 marvis/greetings.json 是**会被自动读取并发出**的活数据，
带着旧数字发出去就是事实错误，必须改。

只改活数据与模板；check_*.py / wb_fix8.py / scan_pdfs_38.py 里出现「38 款」
是故意的（那是检测旧数字用的），不动。
"""
import io
import os

MARVIS = r"YOUR_REPO\marvis"

# (文件, 旧串, 新串)
FIXES = [
    (r"user_profile.json",
     "另有 38 款网页小游戏合集",
     "另有 某网页小游戏合集"),
    (r"user_profile.json",
     "GitHub 公开 8 个仓库、2026 年内提交 50+ 次 commit",
     "GitHub 公开 若干个公开仓库、2026 年内提交 多次提交"),
    (r"greetings.json",
     "GitHub 8 个仓库 50+ commit",
     "GitHub 上若干个公开仓库、多次提交"),
    (r"greetings.json",
     "GitHub 公开 8 个仓库、年内 50+ commit",
     "GitHub 公开 若干个公开仓库、年内 多次提交"),
    (r"scripts\gen_fav.py",
     "GitHub 若干仓库、数十次提交。可实习，时间可协商。方便发份 JD 吗？",
     "GitHub 上若干个公开仓库、多次提交。可实习，时间可协商。方便发份 JD 吗？"),
    (r"scripts\gen_crosscity.py",
     "GitHub 若干仓库、数十次提交。可实习，时间可协商。方便发份 JD 吗？",
     "GitHub 上若干个公开仓库、多次提交。可实习，时间可协商。方便发份 JD 吗？"),
    (r"scripts\gen_jd_msg.py",
     "  其他        GitHub 若干仓库、数十次提交；可实习，时间可协商",
     "  其他        GitHub 上若干个公开仓库、多次提交；可实习，时间可协商"),
]

changed = {}
for rel, old, new in FIXES:
    p = os.path.join(MARVIS, rel)
    if not os.path.isfile(p):
        print("MISS FILE:", rel)
        continue
    s = io.open(p, encoding="utf-8").read()
    if old not in s:
        print("MISS STR :", rel, "|", old[:50])
        continue
    n = s.count(old)
    s = s.replace(old, new)
    io.open(p, "w", encoding="utf-8").write(s)
    changed[rel] = changed.get(rel, 0) + n
    print(f"  ✓ {rel:<26} 改 {n} 处")

print("\n改动汇总：", changed)

# 复查：活数据里不该再出现旧数字
print("\n复查（活数据 + 模板）：")
for rel in ("user_profile.json", "greetings.json",
            r"scripts\gen_fav.py", r"scripts\gen_crosscity.py", r"scripts\gen_jd_msg.py"):
    p = os.path.join(MARVIS, rel)
    s = io.open(p, encoding="utf-8").read()
    hits = []
    if "38 款" in s or "38款" in s:
        hits.append("38 款")
    if "8 个仓库" in s or "8 仓库" in s:
        hits.append("8 仓库")
    if "50+ commit" in s or "50+ 次 commit" in s:
        hits.append("50+ commit")
    print(f"  {'✗ ' if hits else '✓ '}{rel:<26} {hits if hits else '干净'}")
