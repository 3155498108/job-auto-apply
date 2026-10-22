#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_fav_ai.py — 从收藏夹里挑「AI 方向」且未投过的岗位。

用户诉求：专门投 AI 相关（vibe coding / agent / AI Coding / 大模型应用等）。

判定只做**粗筛**，真正的取舍交给 JD 正文（jd_filter）——标题会骗人。
本脚本负责：AI 命中词打分 + 排除已投 + 排除明显非技术/非开发。

输出：output/boss_work/fav_ai_candidates.json
"""
import io
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, r"YOUR_REPO\marvis")
from scripts.wb_scan3 import load_done

WORK = r"YOUR_HOME\output\boss_work"

# ── AI 方向命中词（命中标题或标签即算 AI 岗）─────────────────────────
AI_STRONG = [
    "vibe coding", "vibecoding", "ai coding", "aicoding", "ai coding", "vibe coding",
    "agent", "智能体", "ai agent", "agent方向", "agent 方向",
    "ai全栈", "ai 全栈", "ai应用", "ai 应用", "ai开发", "ai 开发", "ai工程", "ai 工程",
    "ai软件", "ai 软件", "ai研发", "ai 研发", "ai程序", "ai 程序", "ai工程师", "ai 工程师",
    "ai全栈研发", "ai 全栈研发", "ai应用开发", "ai 应用开发", "ai应用研发",
    "大模型", "llm", "aigc", "人工智能", "ai工具", "ai 工具", "ai编程", "ai 编程",
    "使用ai", "使用 ai", "会用ai", "会用 ai", "懂ai", "写代码（前端，后端）",
    "codex", "cursor", "claude", "copilot", "trae", "deepseek", "chatgpt", "gpt",
    "ai应用与agent", "ai应用与 agent", "全栈 ai", "ai 全栈应用", "ai前瞻", "ai 前瞻",
]
# 命中即降权（可能是超纲方向，但要留给 JD 正文判）
AI_WEAK = ["ai算法", "ai 算法", "ai训练", "ai 训练", "提示词", "prompt", "多模态",
           "ai陪伴", "ai 陪伴", "ai数字人", "ai 数字人", "ai安全", "ai 安全",
           "ai数据", "ai 数据", "ai推荐", "ai 推荐", "ai客服", "ai 客服"]

# ── 标题级非技术 / 非开发 ───────────────────────────────────────────
BAD_TITLE = [
    "数据标注", "ai训练师", "ai 训练师", "标注", "产品实习生", "产品助理", "产品经理",
    "运营", "客服", "主播", "剪辑", "人事", "招聘", "销售", "商务", "市场",
    "开发工程师（研发岗）", "老师", "教师", "运营类", "数据采集", "审核",
    "运维", "测试", "硬件", "嵌入式", "前端开发实习生（坐班）",
]

NONDEV_CITY = ["某桌面数据工具工程师"]


def norm(s):
    return re.sub(r"\s+", "", (s or "")).lower()


def text_of(c):
    """把一张收藏卡片的可搜字段拼起来。"""
    parts = [c.get("jobName", ""), c.get("brandName", ""), c.get("nlpTags"),
             c.get("jobLabels"), c.get("highLightLabels"), c.get("industryName"),
             c.get("bossTitle", ""), c.get("positionCategory", "")]
    if isinstance(parts[2], list):
        parts[2] = " ".join(str(x) for x in parts[2])
    if isinstance(parts[3], list):
        parts[3] = " ".join(str(x) for x in parts[3])
    if isinstance(parts[4], list):
        parts[4] = " ".join(str(x) for x in parts[4])
    return " ".join(str(p) for p in parts if p)


def main():
    cards = json.load(io.open(os.path.join(WORK, "favorites_tag4.json"), encoding="utf-8"))
    done = load_done()
    print(f"收藏 {len(cards)}｜已投 jobId {len(done)}")

    hits = Counter()
    out = []
    for c in cards:
        jid = c.get("encryptJobId")
        if not jid:
            continue
        title = c.get("jobName", "") or ""
        hay = text_of(c).lower()
        tl = title.lower()
        if jid in done:
            hits["已投过"] += 1
            continue
        if any(b in tl for b in BAD_TITLE):
            hits["非技术/非开发"] += 1
            continue
        strong = [k for k in AI_STRONG if k in hay]
        weak = [k for k in AI_WEAK if k in hay]
        if not strong and not weak:
            hits["非AI方向"] += 1
            continue
        score = len(strong) * 2 + len(weak)
        out.append(dict(
            jobId=jid, title=title, company=c.get("brandName", ""),
            city=c.get("cityName", ""), salary=c.get("jobSalary", "") or c.get("salaryDesc", ""),
            boss=c.get("bossName", ""), bossTitle=c.get("bossTitle", ""),
            degree=c.get("jobDegree", ""), experience=c.get("jobExperience", ""),
            strong=strong, weak=weak, score=score,
            nlpTags=c.get("nlpTags"), jobLabels=c.get("jobLabels"),
            jobValidStatus=c.get("jobValidStatus"), online=c.get("online"),
            daysPerWeekDesc=c.get("daysPerWeekDesc"), leastMonthDesc=c.get("leastMonthDesc"),
            jobType=c.get("jobType"), positionCategory=c.get("positionCategory"),
        ))

    out.sort(key=lambda x: -x["score"])
    json.dump(out, io.open(os.path.join(WORK, "fav_ai_candidates.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\nAI 候选 {len(out)} → fav_ai_candidates.json")
    print(f"过滤统计：{dict(hits.most_common())}\n")
    for o in out:
        mk = "★" if o["strong"] else "·"
        print(f"{mk}[{o['score']:>2}] {o['city']:<4} {o['salary'][:10]:<11} "
              f"{o['title'][:32]:<34} {o['company'][:18]:<20} {o['boss'][:6]:<8} {o['jobId']}")
        if o["weak"]:
            print(f"      弱信号: {'/'.join(o['weak'][:4])}")


if __name__ == "__main__":
    main()
