# -*- coding: utf-8 -*-
"""restore_boss_appendix.py — 投递记录.md 被并行会话覆盖后，一键恢复 BOSS 两节附录。

流程：
  1. 若记录里已经没有附录十四/十五 → 从备份整段追加到文件末尾
  2. 若记录里已经有 → 只做校验，不重复追加
"""
import io
import os

RECORD = r"YOUR_HOME\output\投递记录.md"
BACKUP = r"YOUR_HOME\output\boss_work\boss_appendix_1023.md"
MARK_A = "# 附录十四 · 第十轮"
MARK_B = "# 附录十五 · 第十轮续"


def main():
    txt = io.open(RECORD, encoding="utf-8").read()
    have = (MARK_A in txt) and (MARK_B in txt)
    if have:
        print("记录里已有附录十四/十五，不重复追加")
        print("含审计小节:", "## 六、事后审计" in txt)
        return 0
    if not os.path.isfile(BACKUP):
        print("!! 没有备份文件", BACKUP)
        return 1
    seg = io.open(BACKUP, encoding="utf-8").read()
    with io.open(RECORD, "a", encoding="utf-8") as f:
        f.write("\n" + seg)
    print(f"已恢复 {len(seg)} 字符 → {RECORD}")
    return 0


if __name__ == "__main__":
    main()
