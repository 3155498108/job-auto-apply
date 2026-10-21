# -*- coding: utf-8 -*-
"""check_targets.py — 校验任意目标清单的话术长度/行数/合规性。

用法: python check_targets.py <targets.json>
"""
import json
import os
import re
import sys

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.recruit_greetings import load_index

BAD = ["说明：", "说明:", "不要改", "不要再改", "归档", "内部", "本节", "这是发给",
       "注：", "（附", "38 款", "38款", "57070"]


def main():
    path = sys.argv[1]
    targets = json.load(open(path, encoding="utf-8"))
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
        if not (250 <= n <= 350):
            flag += "  ⚠️长度"
            ok = False
        bad = [w for w in BAD if w in m]
        if bad:
            flag += f"  ⚠️{bad}"
            ok = False
        if lines < 4 or lines > 7:
            flag += "  ⚠️行数"
            ok = False
        print(f"  {f:<54} {n:>4} 字 {lines} 行{flag}")
    print(f"\n共 {len(targets)} 个，结果:", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
