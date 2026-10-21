# -*- coding: utf-8 -*-
"""check_crosscity.py — 校验跨城话术（长度/行数）+ 回归检查既有 12 个岗位取值未变。"""
import json
import os
import re
import sys

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.recruit_greetings import load_index, pick_by_company

RECRUIT = r"YOUR_HOME\招聘"
WORK = r"YOUR_HOME\output\boss_work"

OLD12 = ["示例科技A-后端JAVA开发实习生", "示例文化B", "示例讯动U", "示例科技V", "示例平台I",
         "示例科技C", "示例科技D-游戏开发实习生", "后端开发实习生", "示例传媒T-AI智能体研发实习生",
         "研发实习生", "软件实习生", "示例云服务G-AI全栈开发工程师", "AI应用与Agent工程实习生",
         "Java后端开发实习生", "java实习生", "产品实习生", "全栈开发实习生",
         "示例大厂J-后端开发实习生", "示例网络P-实施工程师", "示例网络P-开发工程师",
         "示例科技Q-AI应用开发", "示例企业66-JAVA后端实习", "示例企业27-AI应用工程师",
         "AI Coding全栈工程师"]


def main():
    targets = json.load(open(os.path.join(WORK, "crosscity_targets.json"), encoding="utf-8"))
    idx = load_index()
    print(f"招聘目录索引 {len(idx)} 个岗位\n")
    ok = True
    for t in targets:
        f = t["folder"]
        if f not in idx:
            print(f"!! {f} 不在索引里")
            ok = False
            continue
        main_text = idx[f]["main"]
        n = len(re.sub(r"\s+", "", main_text))
        lines = main_text.count("\n") + 1
        flag = "" if 250 <= n <= 340 else "  ⚠️ 超出 250-340"
        print(f"  {f:<40} {n:>4} 字 {lines} 行{flag}")
        if flag:
            ok = False
        if "38 款" in main_text or "38款" in main_text:
            print(f"     ⚠️ 含过时的 38 款")
            ok = False
        for l in main_text.split("\n"):
            if l.startswith("说明") or "不要改" in l:
                print(f"     ⚠️ 正文混入内部说明: {l[:40]}")
                ok = False

    print("\n--- 回归：既有岗位取值是否仍指向原文件夹 ---")
    for f in OLD12:
        if f not in idx:
            continue
        text, src, meta = pick_by_company(f)
        got = meta.get("folder")
        mark = "OK " if got == f else "!! "
        if got != f:
            ok = False
        print(f"  {mark}{f:<34} → {got}")

    print("\n结果:", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
