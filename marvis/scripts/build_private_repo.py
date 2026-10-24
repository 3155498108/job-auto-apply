#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_private_repo.py — 组装私有仓库的工作树。

来源：
  · 上游基座  YOUR_REPO\\marvis   （公开仓库 taohuajianxian/boss-zhipin-assistant）
  · 本地 skill YOUR_HOME\\.minimax\\skills\\job-auto-apply

不带进去的：
  · marvis/assets/（上游作者的赞赏码，不在自有仓库里二次分发）
  · workbuddy/（另一个智能体平台的变体，本项目不用）
  · __pycache__
  · 简历、截图、JD 存档、浏览器会话 —— 这些留在 YOUR_HOME，不进代码仓
"""
import io
import os
import shutil

SRC_BASE = os.environ.get("MARVIS_BASE", r"YOUR_REPO")
SRC_SKILL = os.environ.get(
    "SKILL_DIR", r"YOUR_HOME\.minimax\skills\job-auto-apply")
DST = os.environ.get("DST_REPO", r"YOUR_REPO\job-auto-apply")

SKIP_DIRS = {"__pycache__", "assets", ".git", ".idea", ".vscode"}
SKIP_EXT = {".pyc", ".pyo", ".log", ".tmp"}
# 个人求职画像与话术：属于活数据，绝不能进代码仓（.gitignore 只是兜底，这里再挡一道）
SKIP_NAMES = {"user_profile.json", "greetings.json"}


def copy_tree(src, dst, skip_names=()):
    n = 0
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and d not in skip_names]
        for fn in files:
            if fn in SKIP_NAMES or fn in skip_names:
                continue
            if os.path.splitext(fn)[1].lower() in SKIP_EXT:
                continue
            s = os.path.join(root, fn)
            rel = os.path.relpath(s, src)
            d = os.path.join(dst, rel)
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)
            n += 1
    return n


def main():
    if os.path.isdir(DST):
        shutil.rmtree(DST)
    os.makedirs(DST)

    # 1) skill
    n1 = copy_tree(SRC_SKILL, os.path.join(DST, "skill", "job-auto-apply"))
    print(f"skill：{n1} 个文件")

    # 2) marvis（去掉 assets）
    n2 = copy_tree(os.path.join(SRC_BASE, "marvis"), os.path.join(DST, "marvis"))
    print(f"marvis：{n2} 个文件")

    # 3) 统计
    total = 0
    for root, dirs, files in os.walk(DST):
        total += len(files)
    print(f"合计 {total} 个文件 → {DST}")

    # 4) 打印最终结构（两层）
    print("\n结构：")
    for n in sorted(os.listdir(DST)):
        p = os.path.join(DST, n)
        if os.path.isdir(p):
            sub = len(os.listdir(p))
            print(f"  {n}/  ({sub} 项)")
            if n == "skill":
                for n2 in sorted(os.listdir(os.path.join(p, "job-auto-apply"))):
                    print(f"      {n2}")
            elif n == "marvis":
                for n2 in sorted(os.listdir(p)):
                    q = os.path.join(p, n2)
                    print(f"      {n2}{'/' if os.path.isdir(q) else ''}"
                          f"{'' if os.path.isdir(q) else '  ' + str(os.path.getsize(q)) + 'B'}")
        else:
            print(f"  {n}")


if __name__ == "__main__":
    main()
