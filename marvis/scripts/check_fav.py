# -*- coding: utf-8 -*-
"""check_fav.py — 校验收藏岗位话术长度/行数 + 确认没有内部说明、没有过时数字。"""
import json
import os
import re
import sys

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.recruit_greetings import load_index

WORK = r"YOUR_HOME\output\boss_work"
BAD = ["说明：", "不要改", "归档", "内部", "本节", "38 款", "38款"]


def main():
    targets = json.load(open(os.path.join(WORK, "fav_targets.json"), encoding="utf-8"))
    idx = load_index()
    ok = True
    for t in targets:
        f = t["folder"]
        item = idx.get(f)
        if not item or not item["main"]:
            print(f"!! {f} 不在索引里")
            ok = False
            continue
        m = item["main"]
        n = len(re.sub(r"\s+", "", m))
        lines = m.count("\n") + 1
        flag = ""
        if not (250 <= n <= 345):
            flag = "  ⚠️长度"
            ok = False
        bad = [w for w in BAD if w in m]
        if bad:
            flag += f"  ⚠️{bad}"
            ok = False
        if lines < 4 or lines > 7:
            flag += "  ⚠️行数"
            ok = False
        print(f"  {f:<40} {n:>4} 字 {lines} 行{flag}")
    print(f"\n共 {len(targets)} 个，结果:", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
