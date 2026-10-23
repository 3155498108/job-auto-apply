# -*- coding: utf-8 -*-
"""backup_boss_appendix.py — 把 BOSS 两节附录从投递记录.md 里切出来单独存一份。

并行会话（51job）会用「读全文→改→写回全文」的方式覆盖投递记录.md，
把别的会话追加的内容整段抹掉。这里留一份独立备份，
被覆盖时用 restore_boss_appendix.py 一键恢复，不用重新跑写回。
"""
import io
import os
import re

RECORD = r"YOUR_HOME\output\投递记录.md"
BACKUP = r"YOUR_HOME\output\boss_work\boss_appendix_1023.md"
MARK_A = "# 附录十四 · 第十轮"
MARK_B = "# 附录十五 · 第十轮续"


def main():
    txt = io.open(RECORD, encoding="utf-8").read()
    ia = txt.find(MARK_A)
    ib = txt.find(MARK_B)
    if ia < 0 or ib < 0:
        print("!! 没找到附录十四/十五（可能被覆盖了）")
        return 1
    seg = txt[ia:].rstrip() + "\n"
    io.open(BACKUP, "w", encoding="utf-8").write(seg)
    print(f"已备份 {len(seg)} 字符 → {BACKUP}")
    print(f"含审计小节: {'## 六、事后审计' in seg}")
    return 0


if __name__ == "__main__":
    main()
