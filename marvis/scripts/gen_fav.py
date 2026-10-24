#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_fav.py — 为收藏夹里筛出的目标生成定制话术归档 + 投递目标清单。

数字全部来自实测：某网页小游戏合集、两百余个 TS 文件 / 数万行、数十个 Vitest 测试文件、
18 个 Controller / 70 个 RESTful 接口 / 11 张业务表、5 个 AI 端点 / 1–3 秒 / < 50 毫秒。
"""
import io
import json
import os
import re

RECRUIT = r"YOUR_HOME\招聘"
WORK = r"YOUR_HOME\output\boss_work"

# ── 话术模板（正文用 **【xxx】** 约定，_clean 会去掉粗体标记）──────────────
T_JAVA = """您好，我是后端开发实习生，看到贵司「{pos}」的岗位。
**【Java 后端】**独立完成某电商交易后端全流程：Spring Boot + MyBatis + MySQL + Redis，18 个 Controller / 70 个 RESTful 接口，11 张业务表自己设计，SQL 走索引、全部用 #{} 占位防注入。
**【工程实践】**用 MyBatis 拦截器统一分页与字段脱敏；Redis 缓存菜品与令牌、Session 共享登录态，分布式锁防超卖。
**【AI 协作】**日常用 Claude Code / Codex 协作开发，AI 生成的代码我自己审、问题主动跟进。
可实习，时间可协商。方便发份 JD 吗？"""

T_AI = """您好，我是后端开发实习生，看到贵司「{pos}」的岗位。
**【AI 落地】**小组负责人做 Spring AI + DeepSeek 的 AI 客服系统：接入大模型 API 做成 5 个 RESTful 端点，异步调用 + 30 秒超时 + 异常隔离，单次 AI 响应 1–3 秒、数据库写入 < 50 毫秒。
**【Agent 实践】**某网页小游戏合集里让 AI 与规则共用纯函数 reducer，AI 只做候选试算、不维护第二套逻辑；代码我自己审，每款配 Vitest 单测。
**【边界感】**模型训练与调优我没做过，做的是把大模型接进业务并处理它的慢与不稳，不夸大。
可实习，时间可协商。方便发份 JD 吗？"""

T_AICODE = """您好，我是后端开发实习生，看到贵司「{pos}」的岗位。
**【AI 协作开发】**日常用 Claude Code / Codex / Copilot 做 AI Coding，代码我自己审、问题自己跟进；某网页小游戏合集里 AI 只做候选试算、规则始终是唯一真相源，每款配 Vitest 单测（数十个测试文件）。
**【工程化】**游戏内核 两百余个 TS 文件 / 数万行，三层架构（站点壳 / 游戏内核 / 渲染层），内核是纯 TypeScript 状态机、零运行时依赖，可直接单测。
**【Java 后端】**独立完成某电商交易后端 Spring Boot + MyBatis + MySQL + Redis，18 个 Controller / 70 个 RESTful 接口。
可实习，时间可协商。方便发份 JD 吗？"""

T_FULL = """您好，我是后端开发实习生，看到贵司「{pos}」的岗位。
**【前端/TS】**用 TypeScript + Canvas 做了 某网页小游戏合集，三层架构（站点壳 / 游戏内核 / 渲染层），内核 两百余个 TS 文件、纯函数 reducer 状态机，每款配 Vitest 单测（数十个测试文件）。
**【后端】**独立完成「某电商交易后端」Java 后端 Spring Boot + MyBatis + MySQL + Redis，18 个 Controller / 70 个 RESTful 接口；另有 Flask + JavaScript 前后端闭环并本地部署。
**【AI 协作】**日常用 Claude Code / Codex 协作开发，AI 只做候选试算，规则始终是唯一真相源。
可实习，时间可协商。方便发份 JD 吗？"""

T_PY = """您好，我是后端开发实习生，看到贵司「{pos}」的岗位。
**【Python / 服务端】**用 Python + Flask + Pillow + MoviePy 独立做出「长卷轴滚动视频生成器」：后端提供创建 / 列表 / 详情 / 下载 / 删除五类接口，前端 Bootstrap 5 + 原生 JavaScript 支持拖拽批量上传与进度轮询。
**【工程化】**习惯先定契约再动手，接口文档、技术方案与模块划分都先写清楚；Flask 服务的进程管理与 HTTP 接口暴露自己配过。
**【Java 后端】**另有 Spring Boot + MySQL + Redis 电商后端（18 个 Controller / 70 个 RESTful 接口），日常用 Claude Code / Codex 协作开发。
可实习，时间可协商。方便发份 JD 吗？"""

T_GAME = """您好，我是后端开发实习生，看到贵司「{pos}」的岗位。
**【游戏开发】**独立开发纯静态网页小游戏合集：某网页小游戏合集，同一套代码适配手机与桌面浏览器；游戏内核是纯 TypeScript 状态机、零运行时依赖，共 两百余个 TS 文件 / 数万行。
**【可测性】**用不可变状态与纯函数换可测试、可复现、可回放；实现可播种随机数 mulberry32 由种子驱动对局，每款配 Vitest 单测（数十个测试文件）。
**【Java 后端】**独立完成某电商交易后端 Spring Boot + MyBatis + MySQL + Redis，18 个 Controller / 70 个 RESTful 接口。
可实习，时间可协商。方便发份 JD 吗？"""

T_DATA = """您好，我是后端开发实习生，看到贵司「{pos}」的岗位。
**【数据与 SQL】**某电商交易后端自己设计 11 张 MySQL 业务表（菜品 / 订单 / 订单明细 / 购物车 / 地址簿等）并做索引与联表 SQL 优化，支撑订单查询等高频查表场景；11 个 MyBatis XML 映射文件全部用 #{} 占位防注入。
**【某桌面数据工具】**用 Python + Flask 交付过某桌面数据工具：PyQt6 桌面端 + Node.js 客户端做批量歌单抓取与多级排序，抓取 200 首命令行取数限制的自建分析方案，并批量抓取曲库信息提升数据分析速度。
**【AI 协作】**日常用 Claude Code / Codex 协作开发，代码我自己审。
可实习，时间可协商。方便发份 JD 吗？"""

TPL = {"T_JAVA": T_JAVA, "T_AI": T_AI, "T_AICODE": T_AICODE, "T_FULL": T_FULL,
       "T_PY": T_PY, "T_GAME": T_GAME, "T_DATA": T_DATA}

SHORT = {
    "T_JAVA": "主攻 Java 后端方向。",
    "T_AI": "日常用 Claude Code / Codex 做 AI Coding。",
    "T_AICODE": "日常用 Claude Code / Codex / Copilot 做 AI Coding。",
    "T_FULL": "前后端都能独立交付。",
    "T_PY": "Python 与 Java 后端都做过完整项目。",
    "T_GAME": "做过 某网页小游戏合集的完整作品集。",
    "T_DATA": "SQL 与某桌面数据工具都做过完整项目。",
}
SHORT_TAIL = {
    "T_JAVA": "独立完成「某电商交易后端」Java 后端 Spring Boot + MySQL + Redis（18 个 Controller / 70 个 RESTful 接口）；另有 Spring AI + DeepSeek 的 AI 客服系统。",
    "T_AI": "某网页小游戏合集里让 AI 与规则共用纯函数 reducer，AI 只做候选试算，代码我自己审、每款配 Vitest 单测。",
    "T_AICODE": "某网页小游戏合集全流程用 Claude Code / Codex 协作完成，AI 只做候选试算，代码我自己审、每款配 Vitest 单测。",
    "T_FULL": "TypeScript + Canvas 某网页小游戏合集；Java 后端 Spring Boot + MySQL + Redis（18 个 Controller / 70 个 RESTful 接口）。",
    "T_PY": "Python + Flask + Pillow + MoviePy 独立交付长卷轴视频生成器；Java 后端 Spring Boot + MySQL + Redis。",
    "T_GAME": "某网页小游戏合集，内核纯 TypeScript 状态机，每款配 Vitest 单测（数十个测试文件）。",
    "T_DATA": "自己设计 11 张 MySQL 业务表并做索引与 SQL 优化；用 Python + Flask 交付过某桌面数据工具。",
}
SHORT_END = "GitHub 上若干个公开仓库、多次提交。可实习，时间可协商。方便发份 JD 吗？"

IMGS_GENERIC = [r"研发实习生\shot_全量版_p1.png", r"研发实习生\shot_全量版_p2.png"]
IMGS_AICODE = [r"AI Coding全栈工程师\shot_aicoding_p1.png", r"AI Coding全栈工程师\shot_aicoding_p2.png"]

# 选中的目标：key = jobId，value = (目录名后缀, 模板, 简历图组)
PICK = {
    "JOBID021": ("示例企业95-codex项目设计与测试", "T_AICODE", IMGS_AICODE),
    "JOBID005": ("示例企业06-VibeCoding实习生", "T_AICODE", IMGS_AICODE),
    "JOBID045": ("示例企业11-使用AI写代码", "T_AICODE", IMGS_AICODE),
    "94238d57e22dc7570nN42t6_FlBS": ("示例企业39-AI应用开发实习生", "T_AI", IMGS_AICODE),
    "JOBID026": ("深圳示例科技Q-ai应用开发实习生", "T_AI", IMGS_AICODE),
    "JOBID003": ("示例科技S-AI智能体开发实习生", "T_AI", IMGS_AICODE),
    "JOBID101": ("示例科技T-AI智能体实习生", "T_AI", IMGS_AICODE),
    "9aa33c9337aefb150nBz3dm_F1dS": ("示例企业25-27暑期AI前瞻实习生", "T_AICODE", IMGS_AICODE),
    "c93ef30d5b9b424e1XJ-2tS-E1ZZ": ("示例企业42-Java实习生-上海", "T_JAVA", IMGS_GENERIC),
    "d42279cd31b7e4f60nN73d-7GVZY": ("示例企业97-AI工程师实习生", "T_AI", IMGS_AICODE),
    "JOBID029": ("示例企业35-AI实习生-某城市", "T_AI", IMGS_AICODE),
    "JOBID012": ("某城市华睿数字科技-Java实习生", "T_JAVA", IMGS_GENERIC),
    "JOBID030": ("示例企业03-计算机实习生-某城市", "T_AI", IMGS_GENERIC),
    "9b0e7139b893861503F-2Nq4GVZW": ("某城市市链际科技-java开发实习生", "T_JAVA", IMGS_GENERIC),
    "JOBID006": ("某城市市靖轩投资咨询-程序员实习", "T_JAVA", IMGS_GENERIC),
    "JOBID015": ("示例企业54-Java研发实习生", "T_JAVA", IMGS_GENERIC),
    "JOBID023": ("示例企业53-Java开发实习生", "T_JAVA", IMGS_GENERIC),
    "JOBID033": ("示例企业70-Java开发实习生", "T_JAVA", IMGS_GENERIC),
    "da478ce785fb7b910nNy396_FFJT": ("示例企业10-java后端实习生-汕头", "T_JAVA", IMGS_GENERIC),
    "JOBID009": ("示例科技W-java实习生-深圳", "T_JAVA", IMGS_GENERIC),
    "JOBID042": ("示例互动H-java开发实习生-深圳", "T_JAVA", IMGS_GENERIC),
    "JOBID001": ("示例科技U-软件开发工程师实习-江门", "T_JAVA", IMGS_GENERIC),
    "JOBID002": ("示例科技X-python实习生-佛山", "T_PY", IMGS_GENERIC),
    "JOBID106": ("示例科技AE-全栈java+vue开发实习生", "T_FULL", IMGS_GENERIC),
    "a47ed6c93b58c03203173ti-EFpQ": ("示例企业26-AI全栈开发实习生", "T_AICODE", IMGS_AICODE),
    "JOBID011": ("示例企业41-软件开发实习生", "T_JAVA", IMGS_GENERIC),
    "JOBID043": ("示例科技AM-AiJava开发实习生-东莞", "T_AI", IMGS_GENERIC),
    "3af0fbc389075e2b0ndz3d-5F1JX": ("示例企业51-人工智能实习生-东莞", "T_AI", IMGS_AICODE),
    "JOBID028": ("示例文化C-ai算法实习生-东莞", "T_AI", IMGS_AICODE),
    "JOBID031~": ("示例企业52-实习开发工程师", "T_JAVA", IMGS_GENERIC),
    "JOBID039": ("示例企业22-数据库实习生", "T_DATA", IMGS_GENERIC),
    "238a12c6927de21a0nd_29i-FFVY": ("示例企业96-AI应用开发工程师实习", "T_AI", IMGS_AICODE),
    "JOBID034": ("示例企业76-python开发工程师实习", "T_PY", IMGS_GENERIC),
    "JOBID017": ("示例企业05-软件开发工程师实习生", "T_JAVA", IMGS_GENERIC),
    "JOBID022": ("示例企业40-全栈开发实习生", "T_FULL", IMGS_GENERIC),
    "JOBID040": ("示例企业63-全栈开发实习生", "T_FULL", IMGS_GENERIC),
    "JOBID048": ("示例企业23-游戏开发实习生", "T_GAME", IMGS_GENERIC),
    "JOBID047": ("示例企业31-服务端开发实习", "T_JAVA", IMGS_GENERIC),
    "JOBID008": ("示例科技V-软件研发实习生AI方向", "T_AI", IMGS_AICODE),
    "5172b750744ecc760nx52Ny-FVBQ": ("示例科技AA-Java实习生-深圳", "T_JAVA", IMGS_GENERIC),
    "JOBID036~~": ("示例科技AB-Java开发实习生", "T_JAVA", IMGS_GENERIC),
}
# 主动排除的 3 个（理由写在脚本注释里）：
#   示例企业49「实习生」180-200   —— 岗位名过泛，JD 内容未知，盲投风险高
#   京益数字技术「全栈开发」6-8K —— 经验要求 1-3 年，是社招不是实习
#   示例教育S「前端开发实习生（坐班）」—— 前端非主方向，且该 HR 已在沟通中


def build_txt(comp, title, city, salary, tpl_key):
    tpl = TPL[tpl_key]
    # 注意：模板里有 "#{} 占位防注入" 这种字面花括号，不能用 str.format()，
    # 否则会被当成占位符解析报错 —— 用 replace。
    main = tpl.replace("{pos}", title)
    short = (f"您好，我是后端开发实习生，{SHORT[tpl_key]}\n"
             f"{SHORT_TAIL[tpl_key]}\n{SHORT_END}")
    return f"""{comp} · {title}
地址：{city}
薪资：{salary}

【主推版 · 目标 280-340 字（不计空格）】
{main}

【精简版 · 目标 180-230 字】
{short}

【已核验】
- 某网页小游戏合集（目录数与清单条数双向差集为空，双向差集为空）
- 两百余个 TS 文件 / 数万行 / 数十个 Vitest 测试文件（`count_lines.py` 实测）
- 某电商交易后端：18 个 Controller / 70 个 RESTful 接口 / 11 张业务表
- 某 AI 客服：5 个 RESTful 端点 / CompletableFuture 异步 + 30 秒超时 / 异常隔离 / 1–3 秒 / < 50 毫秒
"""


def main():
    faves = json.load(open(os.path.join(WORK, "favorites_fresh.json"), encoding="utf-8"))
    byid = {f.get("encryptJobId"): f for f in faves}
    targets = []
    for jid, (suffix, tpl_key, imgs) in PICK.items():
        f = byid.get(jid)
        if not f:
            print(f"  !! 收藏里没有 {jid}（{suffix}），跳过")
            continue
        folder = f"收藏-{suffix}"
        d = os.path.join(RECRUIT, folder)
        os.makedirs(d, exist_ok=True)
        txt = build_txt(f.get("brandName", ""), f.get("jobName", ""),
                        f.get("cityName", ""), f.get("jobSalary", ""), tpl_key)
        with io.open(os.path.join(d, "新建 文本文档.txt"), "w", encoding="utf-8") as fp:
            fp.write(txt)
        src = (r"AI Coding全栈工程师\你的名字-AICoding全栈工程师.pdf（AI Coding 方向 2 页）"
               if imgs is IMGS_AICODE else r"研发实习生\候选人-实习.pdf（全量版 3 页 11 项目）")
        with io.open(os.path.join(d, "新建 文本文档.txt"), "a", encoding="utf-8") as fp:
            fp.write(f"简历：{src}\n")
        targets.append(dict(label=folder, folder=folder, jobId=jid,
                            city=f.get("cityName", ""), company=f.get("brandName", ""),
                            position=f.get("jobName", ""), salary=f.get("jobSalary", ""),
                            tpl=tpl_key, imgs=imgs))
        print(f"  {folder:<42} {f.get('cityName',''):<6} {f.get('jobSalary',''):<10} {tpl_key}")
    out = os.path.join(WORK, "fav_targets.json")
    with io.open(out, "w", encoding="utf-8") as f:
        json.dump(targets, f, ensure_ascii=False, indent=1)
    print(f"\n共 {len(targets)} 个目标 → {out}")


if __name__ == "__main__":
    main()
