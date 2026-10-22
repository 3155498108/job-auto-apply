#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_fav_ai2.py — 修好 AI 命中规则后的收藏夹 AI 岗全量扫描（v2）。

v1 的 bug：词表只写了「ai应用/ai开发/ai工程师…」这类组合，**没有裸 `ai`**，
于是「ai实习生」「Java+AI(实习)」「全栈开发实习生(AI方向)」全被判成非 AI 岗。
v2 改成正则 + 英文词边界，能命中裸 ai / AI方向 / Java+AI / ai实习 等。

同时不再用 BAD_TITLE 直接一票否决产品岗（产品岗仍单独标出来人工看），
改为分层输出：
  strong  明确技术 AI 岗 → 进候选
  product 产品/运营向 AI 岗 → 单独列，不自动投
  weak    超纲方向（算法/训练/多模态/数据）→ 进候选但标注，交给 JD 正文判

输出：output/boss_work/fav_ai2_candidates.json
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

# ── v2：正则 + 英文词边界 ─────────────────────────────────────────
AI_RE = re.compile(
    r"(?:^|[^a-z0-9])ai(?:[^a-z0-9]|$)"          # 裸 ai（含中文两侧）
    r"|智能体|智能助手|大模型|人工智能|生成式"
    r"|llm|aigc|agent|vibe\s*cod|ai\s*cod"
    r"|codex|cursor|claude|copilot|trae|deepseek|chatgpt"
    r"|提示词|prompt|多模态|数字人|知识图谱|向量|rag",
    re.I,
)
# 技术岗向：明确是写代码/做系统的 AI 岗
TECH_HINT = re.compile(
    r"开发|研发|工程|程序|全栈|后端|前端|架构|工程师|实习"
    r"|dev|engineer|program|swe|coding|code", re.I)
# 非开发向：产品/运营/标注/训练师
PRODUCT_HINT = re.compile(
    r"产品|运营|标注|训练师|策划|助理|顾问|销售|商务|市场|客服|讲师|教师|课程", re.I)
# 超纲方向：正文大概率要求模型训练/算法研究
WEAK_DIR = re.compile(
    r"算法|训练|微调|大模型研究|多模态研究|视觉|语音识别|nlp|cv|数据挖掘|特征工程|数据标注", re.I)


def text_of(c):
    parts = [c.get("jobName", ""), c.get("brandName", ""), c.get("nlpTags"),
             c.get("jobLabels"), c.get("highLightLabels"), c.get("industryName"),
             c.get("bossTitle", ""), c.get("positionCategory", "")]
    for i in (2, 3, 4):
        if isinstance(parts[i], list):
            parts[i] = " ".join(str(x) for x in parts[i])
    return " ".join(str(p) for p in parts if p)


def main():
    cards = json.load(io.open(os.path.join(WORK, "favorites_tag4.json"), encoding="utf-8"))
    done = load_done()
    print(f"收藏 {len(cards)}｜已投 jobId {len(done)}")

    hits = Counter()
    strong, product, weak = [], [], []
    for c in cards:
        jid = c.get("encryptJobId")
        if not jid:
            continue
        title = c.get("jobName", "") or ""
        hay = text_of(c)
        if jid in done:
            hits["已投过"] += 1
            continue
        if not AI_RE.search(hay):
            hits["非AI方向"] += 1
            continue
        is_product = bool(PRODUCT_HINT.search(title))
        is_weak = bool(WEAK_DIR.search(title))
        item = dict(
            jobId=jid, title=title, company=c.get("brandName", ""),
            city=c.get("cityName", ""), salary=c.get("jobSalary", "") or c.get("salaryDesc", ""),
            boss=c.get("bossName", ""), bossTitle=c.get("bossTitle", ""),
            degree=c.get("jobDegree", ""), experience=c.get("jobExperience", ""),
            nlpTags=c.get("nlpTags"), jobLabels=c.get("jobLabels"),
            jobValidStatus=c.get("jobValidStatus"), online=c.get("online"),
            daysPerWeekDesc=c.get("daysPerWeekDesc"), leastMonthDesc=c.get("leastMonthDesc"),
            jobType=c.get("jobType"), positionCategory=c.get("positionCategory"),
        )
        if is_product:
            hits["AI但产品/非开发向"] += 1
            product.append(item)
        elif is_weak:
            hits["AI但超纲方向"] += 1
            weak.append(item)
        else:
            hits["AI技术岗"] += 1
            strong.append(item)

    for name, arr in (("strong", strong), ("weak", weak), ("product", product)):
        json.dump(arr, io.open(os.path.join(WORK, f"fav_ai2_{name}.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    json.dump(strong + weak, io.open(os.path.join(WORK, "fav_ai2_candidates.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print(f"\n过滤统计：{dict(hits.most_common())}")
    print(f"strong(AI技术岗) {len(strong)}｜weak(超纲方向) {len(weak)}｜product(产品向) {len(product)}")
    for tag, arr in (("STRONG", strong), ("WEAK", weak), ("PRODUCT", product)):
        print(f"\n===== {tag} =====")
        for o in arr:
            print(f"  {o['city']:<4} {str(o['salary'])[:10]:<11} {o['title'][:34]:<36} "
                  f"{o['company'][:18]:<20} {o['jobId']}")


if __name__ == "__main__":
    main()
