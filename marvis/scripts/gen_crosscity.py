#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_crosscity.py — 生成跨城市投递的话术文件与 TARGETS 配置。

13 个岗位，覆盖深圳/东莞/佛山/珠海/某城市/惠州/汕头/中山/肇庆/江门 10 个城市。
话术数字全部来自实测：某网页小游戏合集、两百余个 TS 文件、数万行、数十个测试文件。
"""
import io
import json
import os

RECRUIT = r"YOUR_HOME\招聘"
WORK = r"YOUR_HOME\output\boss_work"

# ── 三套基础正文 ──────────────────────────────────────────────
T_JAVA = """您好，我是后端开发实习生。
**【Java 后端】**独立完成某电商交易后端全流程：Spring Boot + MyBatis + MySQL + Redis，18 个 Controller / 70 个 RESTful 接口，11 张业务表自己设计，SQL 走索引、全部用 #{} 占位防注入。
**【工程实践】**用 MyBatis 拦截器统一分页与字段脱敏；Redis 缓存菜品与令牌、Session 共享登录态，分布式锁防超卖。
**【AI 协作】**日常用 Claude Code / Codex 协作开发，AI 生成的代码我自己审、问题主动跟进。
可实习，时间可协商。方便发份 JD 吗？"""

T_AI = """您好，我是后端开发实习生，日常用 Claude Code / Codex / Copilot 做 AI Coding。
**【AI 落地】**小组负责人做 Spring AI + DeepSeek 的 AI 客服系统：接入大模型 API 做成 5 个 RESTful 端点，异步调用 + 30 秒超时 + 异常隔离，单次 AI 响应 1–3 秒、数据库写入 < 50 毫秒。
**【Agent 实践】**某网页小游戏合集里让 AI 与规则共用纯函数 reducer，AI 只做候选试算、不维护第二套逻辑；代码我自己审，每款配 Vitest 单测。
**【边界感】**模型训练与调优我没做过，做的是把大模型接进业务并处理它的慢与不稳，不夸大。
可实习，时间可协商。方便发份 JD 吗？"""

T_FULL = """您好，我是后端开发实习生。
**【前端/TS】**用 TypeScript + Canvas 做了 某网页小游戏合集，三层架构（站点壳 / 游戏内核 / 渲染层），内核 两百余个 TS 文件、纯函数 reducer 状态机，每款配 Vitest 单测（数十个测试文件）。
**【后端】**独立完成「某电商交易后端」Java 后端 Spring Boot + MyBatis + MySQL + Redis，18 个 Controller / 70 个 RESTful 接口；另有 Flask + JavaScript 前后端闭环并本地部署。
**【AI 协作】**日常用 Claude Code / Codex 协作开发，AI 只做候选试算，规则始终是唯一真相源。
可实习，时间可协商。方便发份 JD 吗？"""

# 首行 = 公司 · 岗位（供 _company_aliases 提取公司名）
HEAD = "您好，我是后端开发实习生，看到贵司「{pos}」的岗位。"

IMGS_GENERIC = [r"研发实习生\shot_全量版_p1.png", r"研发实习生\shot_全量版_p2.png"]
IMGS_AICODE = [r"AI Coding全栈工程师\shot_aicoding_p1.png", r"AI Coding全栈工程师\shot_aicoding_p2.png"]

TPL = {"T_JAVA": T_JAVA, "T_AI": T_AI, "T_FULL": T_FULL}

# label, folder, jobId, city, company, position, tpl_key, imgs
JOBS = [
    ("示例大厂JAI全栈", "跨城-示例大厂J-AI全栈开发实习生-深圳", "JOBID102",
     "深圳", "示例大厂J", "AI全栈开发实习生", "T_AI", IMGS_AICODE),
    ("示例科技FJava后端", "跨城-示例科技F-Java后端开发实习生-深圳", "JOBID103",
     "深圳", "示例科技F", "Java 后端开发实习生", "T_JAVA", IMGS_GENERIC),
    ("示例科技GAI应用", "跨城-示例科技G-AI应用开发实习生-深圳", "JOBID024",
     "深圳", "示例科技G", "AI应用开发实习生", "T_AI", IMGS_AICODE),
    ("示例企业55TS全栈", "跨城-示例企业55-TypeScript全栈工程师-东莞", "JOBID032",
     "东莞", "示例企业55", "TypeScript 全栈工程师（实习生）", "T_FULL", IMGS_GENERIC),
    ("示例科技HJava佛山", "跨城-示例科技H-Java开发实习生-佛山", "JOBID104",
     "佛山", "示例科技H", "Java 开发实习生", "T_JAVA", IMGS_GENERIC),
    ("示例科技NAIAgent", "跨城-示例科技N-AIAgent实习生-佛山", "JOBID004",
     "佛山", "示例科技N", "AI Agent 实习生", "T_AI", IMGS_AICODE),
    ("示例科技IJava珠海", "跨城-示例科技I-Java开发实习生-珠海", "JOBID018",
     "珠海", "示例科技I", "Java 开发实习生", "T_JAVA", IMGS_GENERIC),
    ("示例科技J全栈珠海", "跨城-示例科技J-软件全栈开发实习生-珠海", "JOBID105",
     "珠海", "示例科技J", "软件全栈开发实习生", "T_FULL", IMGS_GENERIC),
    ("示例科技KJava某城市", "跨城-示例科技K-JAVA开发实习生-某城市", "JOBID035",
     "某城市", "示例科技K", "JAVA 开发实习生", "T_JAVA", IMGS_GENERIC),
    ("示例企业62全栈惠州", "跨城-示例企业62-全栈开发实习生-惠州", "JOBID038",
     "惠州", "示例企业62", "全栈开发实习生", "T_FULL", IMGS_GENERIC),
    ("示例企业67智能体汕头", "跨城-示例企业67-企业智能体开发实习生-汕头", "JOBID037",
     "汕头", "示例企业67", "企业智能体开发实习生", "T_AI", IMGS_AICODE),
    ("示例科技L中山", "跨城-示例科技L-ai软件实习生-中山", "JOBID010",
     "中山", "示例科技L", "AI 软件实习生", "T_AI", IMGS_AICODE),
    ("示例科技MJava肇庆", "跨城-示例科技M-java软件开发实习生-肇庆", "JOBID025",
     "肇庆", "示例科技M", "Java 软件开发实习生", "T_JAVA", IMGS_GENERIC),
    ("示例企业93开发江门", "跨城-示例企业16-软件开发实习生-江门", "6ae5137d0ee0ce0e0nN_2t21F1VZ",
     "江门", "示例企业16", "软件开发实习生", "T_FULL", IMGS_GENERIC),
]

SHORT = """您好，我是后端开发实习生，{tag}
某网页小游戏合集里让 AI 与规则共用纯函数 reducer，AI 只做候选试算，代码我自己审、每款配 Vitest 单测。
独立完成「某电商交易后端」Java 后端 Spring Boot + MySQL + Redis（18 个 Controller / 70 个 RESTful 接口）；另有 Spring AI + DeepSeek 的 AI 客服系统。
GitHub 上若干个公开仓库、多次提交。可实习，时间可协商。方便发份 JD 吗？"""

SHORT_TAG = {
    "T_JAVA": "主攻 Java 后端方向。",
    "T_AI": "日常用 Claude Code / Codex 做 AI Coding。",
    "T_FULL": "前后端都能独立交付。",
}


def build_txt(label, folder, company, position, city, tpl_key):
    tpl = TPL[tpl_key]
    short = SHORT.replace("{tag}", SHORT_TAG[tpl_key])
    head = HEAD.format(pos=position)
    lines = tpl.split("\n")
    main = "\n".join([head] + lines[1:])
    return f"""{company} · {position}
地址：{city}
简历：{company} 定制（见上级文件夹 PDF/截图）

【主推版 · 目标 260-330 字】
{main}

【精简版 · 目标 180-220 字】
{short}

【已核验】
- 数字来源：某网页小游戏合集（目录数与清单条数双向差集为空，双向差集为空）、
  两百余个 TS 文件 / 数万行、数十个 Vitest 测试文件（`count_lines.py` 实测）
- 某电商交易后端：18 个 Controller / 70 个 RESTful 接口 / 11 张业务表（`data-github.json`）
- 某 AI 客服：5 个 RESTful 端点 / CompletableFuture 异步 + 30 秒超时 / 异常隔离 / 1–3 秒 / < 50 毫秒
"""


def main():
    os.makedirs(WORK, exist_ok=True)
    targets = []
    for label, folder, jobId, city, company, position, tpl, imgs in JOBS:
        d = os.path.join(RECRUIT, folder)
        os.makedirs(d, exist_ok=True)
        txt = build_txt(label, folder, company, position, city, tpl)
        with io.open(os.path.join(d, "新建 文本文档.txt"), "w", encoding="utf-8") as f:
            f.write(txt)
        targets.append(dict(label=label, folder=folder, jobId=jobId, city=city,
                            company=company, position=position, imgs=imgs))
        print(f"  {folder:<44} {city}  {company}")
    out = os.path.join(WORK, "crosscity_targets.json")
    with io.open(out, "w", encoding="utf-8") as f:
        json.dump(targets, f, ensure_ascii=False, indent=1)
    print(f"\n共 {len(targets)} 个目标 → {out}")


if __name__ == "__main__":
    main()
