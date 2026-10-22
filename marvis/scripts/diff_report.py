#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""diff_report.py — 量化这批话术的差异度。

指标：
  · 开头句 / 结尾句 / 标签组合 的去重率
  · 两两相似度（字符 3-gram Jaccard）的最大值与均值
  · 与旧 7 套固定模板的相似度（说明「不再是同一套话」）

环境变量：
  DIFF_OUT   指定后把报告写入 output/boss_work/<该文件名>（UTF-8）
  GD2_REPORT 话术报告文件名（默认 gd2_msg_report.json）
"""
import io
import json
import os
import re
import sys
from itertools import combinations

RECRUIT = r"YOUR_HOME\招聘"
WORK = r"YOUR_HOME\output\boss_work"

sys.path.insert(0, r"YOUR_REPO\marvis")
from scripts.gen_fav import TPL
from scripts.recruit_greetings import _clean


def grams(s, n=3):
    s = re.sub(r"\s+", "", s)
    return {s[i:i + n] for i in range(max(0, len(s) - n + 1))}


def jac(a, b):
    ga, gb = grams(a), grams(b)
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)


def body_of(folder):
    p = os.path.join(RECRUIT, folder, "新建 文本文档.txt")
    txt = io.open(p, encoding="utf-8").read()
    m = re.search(r"【主推版[^\n]*】\s*\n(.*?)(?=\n【|\Z)", txt, re.S)
    return _clean(m.group(1)) if m else ""


def build(tfile):
    """产出报告文本（纯函数，返回 str）。"""
    L = []
    targets = json.load(io.open(os.path.join(WORK, tfile), encoding="utf-8"))
    bodies = {}
    for t in targets:
        bodies[t["label"]] = body_of(t["folder"])

    openers = {v.split("\n")[0] for v in bodies.values()}
    ends = {v.strip().split("\n")[-1] for v in bodies.values()}
    labelsets = {tuple(re.findall(r"【(.+?)】", v)) for v in bodies.values()}
    lens = [len(v) for v in bodies.values()]

    L.append("=" * 84)
    L.append(f"批次差异度报告（{len(bodies)} 份主推版）")
    L.append("=" * 84)
    L.append(f"开头句去重     {len(openers)}/{len(bodies)}")
    L.append(f"结尾句去重     {len(ends)}/{len(bodies)}")
    L.append(f"标签组合去重   {len(labelsets)}/{len(bodies)}")
    L.append(f"字数 min/平均/max   {min(lens)} / {sum(lens)//len(lens)} / {max(lens)}")
    L.append(f"完全相同的两份   {len(bodies) - len(set(bodies.values()))}")

    pairs = []
    for a, b in combinations(bodies.keys(), 2):
        pairs.append((jac(bodies[a], bodies[b]), a, b))
    pairs.sort(reverse=True)
    sims = [p[0] for p in pairs]
    L.append("\n两两相似度（字符 3-gram Jaccard）")
    L.append(f"  均值 {sum(sims)/len(sims):.3f}｜中位 {sorted(sims)[len(sims)//2]:.3f}｜最大 {max(sims):.3f}")
    L.append("  最相似的 5 对：")
    for s, a, b in pairs[:5]:
        L.append(f"    {s:.3f}  {a}")
        L.append(f"           {b}")

    L.append("\n与旧 7 套固定模板的相似度（说明不再是同一套话）")
    old = {k: _clean(v.replace("{pos}", "XX")) for k, v in TPL.items()}
    worst = 0.0
    for k, v in bodies.items():
        m = max(jac(v, ov) for ov in old.values())
        worst = max(worst, m)
    L.append(f"  与旧模板的最大相似度：{worst:.3f}（越低越好）")
    L.append(f"  与旧模板相似度 > 0.5 的份数："
             f"{sum(1 for v in bodies.values() if max(jac(v, ov) for ov in old.values()) > 0.5)}")

    osims = [jac(a, b) for a, b in combinations(old.values(), 2)]
    L.append(f"\n  【基线】旧 7 套模板彼此相似度：均值 {sum(osims)/len(osims):.3f}｜最大 {max(osims):.3f}")
    L.append(f"  【对比】本批 {len(bodies)} 份彼此相似度：均值 {sum(sims)/len(sims):.3f}｜最大 {max(sims):.3f}")

    L.append("\n每份的证据原子与命中关键词：")
    rep = os.path.join(WORK, os.environ.get("GD2_REPORT", "gd2_msg_report.json"))
    if os.path.isfile(rep):
        for r in json.load(io.open(rep, encoding="utf-8")):
            L.append(f"  {r['label'][:42]:<44} {r['main_len']:>3}字  "
                     f"{'/'.join(r['atoms']):<34} {'、'.join(r['kws'][:6])}")
    return "\n".join(L)


def main():
    tfile = sys.argv[1] if len(sys.argv) > 1 else "gd2_kept.json"
    text = build(tfile)
    out = os.environ.get("DIFF_OUT")
    if out:
        p = os.path.join(WORK, out)
        with io.open(p, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"→ {p}")
    print(text)


if __name__ == "__main__":
    main()
