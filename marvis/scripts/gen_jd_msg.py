#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_jd_msg.py — 按岗位 JD 正文定制差异化打招呼话术。

与旧的 7 套固定模板（gen_fav.py 的 T_JAVA/T_AI/…）的区别：
  · 旧：按岗位标题套模板 → 同方向的岗位发出的正文几乎一字不差。
  · 新：抓 job_detail 的 JD 全文 → 关键词命中「证据原子」→ 按 JD 排布，
        开头句式 10 选 1、JD 点名句 4 选 1、结尾句 6 选 1、长度按 240/300/360 三档，
        每个岗位的正文由它自己的 JD 决定。

事实边界（全部来自已核验的项目数字，不得夸大）：
  某电商交易后端  Spring Boot + MyBatis + MySQL + Redis
            18 个 Controller / 70 个 RESTful 接口 / 11 张业务表
            SQL 走索引、#{} 占位防注入、MyBatis 拦截器统一分页与字段脱敏
            Redis 缓存菜品与令牌、Session 共享、分布式锁防超卖
  某 AI 客服  Spring AI + DeepSeek，5 个 RESTful 端点
            CompletableFuture 异步 + 30 秒超时 + 持久化异常隔离
            sessionId 隔离 + 5 轮上下文、修复 6 类问题
            单次 AI 响应 1–3 秒、数据库写入 < 50 毫秒
  game      某网页小游戏合集，两百余个 TS 文件 / 数万行，数十个 Vitest 测试文件
            三层架构（站点壳 / 游戏内核 / 渲染层），纯函数 reducer，mulberry32
  某简历生成器  Python + Jinja2：JD 解析 → 覆盖率 → 改写 → 渲染，15 套 A4 主题
  某滚动视频生成器   Python + Flask + Pillow + MoviePy，五类接口，Bootstrap 5 + 原生 JS
  某桌面数据工具     PyQt6 + Node.js 批量歌单抓取与多级排序，200 首取数限制的自建方案
  其他        GitHub 若干个公开仓库、多次提交；每周可实习 5 天，时间可协商

没做过的事不许出现：模型训练/微调、RAG/向量检索、React、Vue、正式实习。
遇到这类关键词自动插「能力边界」句，而不是硬凑。
"""
import io
import json
import os
import re
import sys
from collections import Counter

RECRUIT = r"YOUR_HOME\招聘"
WORK = r"YOUR_HOME\output\boss_work"

# ── 证据原子 ────────────────────────────────────────────────────────────
# kws: 在 JD 里命中的关键词；labels: 段落标签（轮换，避免全场同一个标签）
# echo: 出现在「JD 点名句」里的展示写法；text: 正文句子（全部为已核验事实）
ATOMS = [
    # ── 某电商交易后端 / Java 后端 ──
    dict(id="can_stack", kws=["java", "spring", "springboot", "spring boot", "后端", "backend",
                              "服务端", "接口", "api", "微服务", "中间件", "分布式", "restful"],
         labels=["Java 后端", "后端服务", "服务端开发"],
         echo=["Java", "Spring Boot", "后端开发", "RESTful 接口"],
         text="独立完成「某电商交易后端」电商后端：Spring Boot + MyBatis + MySQL + Redis，18 个 Controller、70 个 RESTful 接口，按 Controller / Service / Mapper 分层。"),
    dict(id="can_sql", kws=["sql", "数据库", "mysql", "索引", "注入", "分页", "事务", "查询", "性能优化", "慢查询"],
         labels=["数据与 SQL", "数据库", "SQL 优化"],
         echo=["MySQL", "SQL 优化", "数据库设计", "索引"],
         text="11 张业务表（菜品 / 订单 / 订单明细 / 购物车 / 地址簿等）自己设计，查询走索引、SQL 全部用 `#{}` 占位防注入，MyBatis 拦截器统一做分页与字段脱敏。"),
    dict(id="can_cache", kws=["redis", "缓存", "cache", "高并发", "并发", "秒杀", "超卖", "session",
                              "登录态", "锁", "性能", "延迟", "qps", "吞吐"],
         labels=["缓存与并发", "性能优化", "中间件"],
         echo=["Redis", "缓存", "高并发", "分布式锁"],
         text="Redis 缓存菜品与令牌、Session 共享登录态，用分布式锁防超卖，把并发下单的重复写入挡在业务层之前。"),
    dict(id="can_layer", kws=["分层", "架构", "设计模式", "代码规范", "工程", "重构", "模块", "领域驱动", "ddd"],
         labels=["工程分层", "架构设计"],
         echo=["分层架构", "模块划分", "代码规范"],
         text="后端按 Controller / Service / Mapper 分层，18 个 Controller 对应 70 个 RESTful 接口，接口统一返回包装结构，方便前端按同一套约定接。"),
    dict(id="can_debug", kws=["调试", "debug", "日志", "异常", "报错", "排查", "稳定性", "监控"],
         labels=["问题排查", "日志与排错"],
         echo=["日志排查", "异常处理", "问题定位"],
         text="写接口时靠日志和断点逐个排查参数绑定、事务回滚和缓存一致性问题，踩过的坑都记成文档交给组里复用。"),

    # ── 某 AI 客服 / AI 落地 ──
    dict(id="ai_api", kws=["llm", "大模型", "agent", "智能体", "ai", "aigc", "spring ai", "deepseek",
                           "gpt", "提示词", "prompt", "问答", "对话", "chat", "生成", "多模态"],
         labels=["AI 落地", "大模型接入", "智能体应用"],
         echo=["大模型", "Agent", "Spring AI", "DeepSeek", "提示词"],
         text="小组负责人，做 Spring AI + DeepSeek 某 AI 客服：把大模型接成 5 个 RESTful 端点，CompletableFuture 异步调用 + 30 秒超时 + 持久化异常隔离，单次响应 1–3 秒、数据库写入 < 50 毫秒。"),
    dict(id="ai_ctx", kws=["上下文", "context", "会话", "多轮", "session", "记忆", "用户画像"],
         labels=["会话上下文", "多轮对话"],
         echo=["多轮上下文", "会话管理"],
         text="用 sessionId 隔离不同用户的会话并保留 5 轮上下文，让多轮追问能接上前面的信息，而不是每次都从零开始。"),
    dict(id="ai_stable", kws=["幻觉", "兜底", "降级", "限流", "重试", "超时", "稳定", "异常", "安全", "审核"],
         labels=["稳定性", "异常兜底"],
         echo=["异常兜底", "输出稳定性"],
         text="上线后累计修复 6 类问题（超时、串话、输出截断、敏感内容、并发写入等），把大模型的不稳定挡在业务层之外。"),
    dict(id="ai_notrain", kws=["训练", "微调", "调优", "sft", "lora", "精调", "预训练", "蒸馏", "量化", "模型训练", "alignment"],
         labels=["能力边界"],
         echo=["模型训练", "微调"],
         text="模型训练与微调我没做过，做的是把大模型接进业务并处理它的慢与不稳，这点我如实说。"),

    # ── game / 前端 TS ──
    dict(id="game_scale", kws=["游戏", "game", "unity", "ue5", "unreal", "cocos", "小游戏", "互动", "娱乐", "休闲", "关卡", "玩法"],
         labels=["游戏开发", "互动娱乐", "游戏工程"],
         echo=["游戏开发", "网页小游戏", "游戏工程"],
         text="独立开发 数十款纯静态网页小游戏，同一套代码适配手机与桌面浏览器：游戏内核是纯 TypeScript 状态机，两百余个 TS 文件 / 数万行。"),
    dict(id="game_arch", kws=["架构", "分层", "状态管理", "设计模式", "规范", "工程", "性能", "解耦", "可维护"],
         labels=["架构设计", "工程分层"],
         echo=["架构设计", "状态管理"],
         text="内核按「站点壳 / 游戏内核 / 渲染层」三层拆开，内核零运行时依赖，状态用不可变对象 + 纯函数 reducer 表达，改一处不会牵动全局。"),
    dict(id="game_test", kws=["测试", "单测", "单元测试", "junit", "用例", "质量", "vitest", "覆盖率",
                              "自动化测试", "测试开发", "回归", "复现"],
         labels=["可测性", "测试工程"],
         echo=["单元测试", "可测试性"],
         text="用不可变状态与纯函数换可测试、可复现、可回放，随机数用可播种的 mulberry32，每款游戏配 Vitest 单测（共 数十个测试文件）。"),
    dict(id="game_fe", kws=["前端", "typescript", "ts", "javascript", "js", "html", "css", "canvas",
                           "页面", "交互", "组件", "动画", "渲染", "移动端", "响应式", "小程序"],
         labels=["前端/TS", "交互实现"],
         echo=["TypeScript", "Canvas", "前端交互", "响应式"],
         text="用 TypeScript + Canvas 写渲染与交互，同一套状态机同时驱动手机与桌面端，不依赖框架也能把操作手感做细。"),

    # ── Python ──
    dict(id="py_web", kws=["python", "flask", "fastapi", "django", "爬虫", "抓取", "接口", "api", "视频", "图像", "pillow", "moviepy", "批处理", "自动化脚本", "运维脚本"],
         labels=["Python 服务端", "Python 后端"],
         echo=["Python", "Flask", "接口开发", "自动化脚本"],
         text="用 Python + Flask + Pillow + MoviePy 独立做出长卷轴滚动视频生成器，后端提供创建 / 列表 / 详情 / 下载 / 删除五类接口，前端 Bootstrap 5 + 原生 JS 支持拖拽批量上传与进度轮询。"),
    dict(id="py_doc", kws=["jinja", "模板", "解析", "文本处理", "报告", "文档", "word", "pdf", "办公", "生成"],
         labels=["Python 自动化", "文本与文档处理"],
         echo=["文档处理", "模板渲染"],
         text="另做过 Python + Jinja2 的简历生成工具：解析岗位 JD、算关键词覆盖率、改写后再渲染成 PDF，内置 15 套 A4 版式主题。"),
    dict(id="py_data", kws=["数据", "分析", "采集", "清洗", "可视化", "pyqt", "桌面", "工具", "统计", "报表"],
         labels=["某桌面数据工具", "数据处理"],
         echo=["数据处理", "批量采集"],
         text="用 PyQt6 桌面端 + Node.js 客户端做过批量歌单抓取与多级排序，针对命令行单次只能取 200 首的限制，自己搭了一套分批抓取 + 结果合并的分析方案。"),

    # ── 数据 / SQL ──
    dict(id="data_model", kws=["sql", "数据库", "表设计", "数仓", "数据仓库", "etl", "bi", "建模", "指标", "mysql", "oracle", "hive"],
         labels=["数据建模", "SQL"],
         echo=["数据建模", "SQL", "表设计"],
         text="数据库这块自己设计过 11 张业务表并做索引与联表查询优化，熟悉从表结构到慢查询定位这一整套流程。"),
    dict(id="data_pipe", kws=["数据开发", "调度", "采集", "pipeline", "实时", "离线", "数据处理", "任务"],
         labels=["数据工程", "数据链路"],
         echo=["数据开发", "数据链路"],
         text="数据流向上做过批量抓取 → 分级排序 → 结果落库的全链路，遇到单次取数上限就自己拆批并补齐结果，不靠手工反复拉。"),

    # ── 通用工程习惯 ──
    dict(id="gen_collab", kws=["协作", "代码管理", "git", "工程规范", "复用", "交接", "文档", "转正", "带教"],
         labels=["工程习惯", "协作方式"],
         echo=["工程规范", "文档与复用"],
         text="习惯先定契约再动手：接口文档、技术方案和模块划分先写清楚再写代码，联调、排错和交接都自己跟。"),
    dict(id="gen_github", kws=["链接", "仓库", "作品", "开源", "github", "演示", "demo", "个人项目",
                              "代表项目", "简历附", "readme"],
         labels=["开源产出", "项目链接"],
         echo=["代码仓库", "项目链接", "开源贡献", "个人作品"],
         text="代表项目都放在 GitHub（github.com/3155498108），若干个公开仓库、多次提交，README 里写清了做法和取舍，可以直接看。"),
    dict(id="gen_aicode", kws=["ai编程", "ai coding", "aicoding", "codex", "copilot", "claude", "ai工具", "提效", "效率", "cursor", "vibe coding", "vibecoding"],
         labels=["AI 协作", "开发效率"],
         echo=["AI Coding", "Claude Code", "Codex"],
         text="日常用 Claude Code / Codex 协作开发，AI 只做候选试算、规则始终是唯一真相源，生成的代码我自己审、问题自己跟。"),
    dict(id="gen_full", kws=["全栈", "前后端", "独立", "交付", "端到端", "闭环", "落地"],
         labels=["全栈交付", "独立交付"],
         echo=["全栈", "独立交付"],
         text="前后端能独立闭环：从数据库表设计、接口实现到页面交互和本地部署都自己跑通一遍。"),
    dict(id="gen_deploy", kws=["部署", "运维", "linux", "docker", "容器", "ci", "cd", "服务器", "上线", "环境"],
         labels=["部署与运维", "工程化"],
         echo=["部署", "Linux 环境"],
         text="自己配过 Flask 服务的进程管理与 HTTP 接口暴露，本地跑通前后端并部署上线验证过。"),
    dict(id="gen_boundary", kws=["rag", "向量", "embedding", "milvus", "faiss", "pgvector", "react", "vue",
                                 "svelte", "组件库", "小程序开发", "flutter", "android", "ios", "unity3d", "c#", "ue4", "ue5"],
         labels=["能力边界"],
         echo=["该技术栈"],
         text="RAG / 向量检索、React、Vue 这些我没在项目里实打实用过，来了可以现学，但我不把没做过的说成做过。"),
]

# ── 开头句（20 种，按序号轮换）──────────────────────────────────────
# 池子必须 ≥ 批次大小，否则「开头句去重 = 批次大小」这条验收线不可能达标
OPENERS = [
    "您好，我是计算机 本科生候选人，看到贵司「{pos}」这个岗位比较对口，冒昧打扰一下。",
    "您好！我是计算机专业 在校的候选人，刷到贵司在招「{pos}」，我把手上的项目对了一遍你们的要求，有几条正好对得上。",
    "你好，我是候选人，计算机专业 在校。贵司「{pos}」的 JD 我读了一遍，冒昧来说说我能接上的部分。",
    "您好，冒昧打扰。我是候选人，在校计算机本科生，看到「{pos}」想试一下，理由写在下面。",
    "候选人，在校，计算机。翻到贵司「{pos}」时我正好在做类似的东西，所以来说下我做过什么。",
    "您好，我叫候选人，计算机 本科生。贵司「{pos}」里写的技术栈，我有成品项目可以对上，具体是——",
    "您好，我是候选人（计算机专业 在校）。冲着贵司「{pos}」这个岗位来投的，先说我能匹配上的经历。",
    "你好，我是候选人，在校计算机。注意到贵司在招「{pos}」，简单说下我的项目情况和能给到的价值。",
    "您好，我是计算机专业 在校的候选人。贵司「{pos}」的招聘我看到了，先把最能对上要求的几段经历摆出来。",
    "你好呀，我是候选人，计算机 在校。顺着「{pos}」点进来的，想跟您说说我的项目，看看合不合适。",
    "您好，我是候选人，在校计算机本科生。看了贵司「{pos}」的岗位介绍后，觉得自己的项目能对上其中几条，说明如下。",
    "你好，我叫候选人（计算机专业 在校）。贵司「{pos}」我认真读过，冒昧来说明我能接上的部分。",
    "候选人，在校，计算机专业。投递「{pos}」，附上我能对得上要求的几段项目经历。",
    "您好，冒昧打扰。我是计算机专业 在校的候选人，看到「{pos}」这个岗位的要求后，觉得有几条正好是我做过的。",
    "你好呀，我是候选人。贵司「{pos}」在招人，我把手上的项目对了一遍要求，挑能对上的几条说给您听。",
    "您好！我是候选人，计算机 在校。冲着「{pos}」来的，先说我做过什么、您看合不合适。",
    "您好，我是计算机专业 在校的候选人。「{pos}」这个岗位我投了，下面几段是我能直接对上要求的内容。",
    "你好，我是候选人，在校计算机专业本科生。看到贵司「{pos}」，想具体说下我手上的项目。",
    "候选人，在校，计算机。「{pos}」的要求我逐条看过，下面写我能对上的部分。",
    "您好，我叫候选人（计算机专业 在校）。投递贵司「{pos}」，把我做过的东西摆出来，您看是否合适。",
]

# ── JD 点名句（8 种）──────────────────────────────────────────────────
ECHOES = [
    "贵司 JD 里提到的「{kw}」，正好是我实际做过的部分。",
    "看到 JD 里写着「{kw}」，我第一时间想到的就是这个。",
    "JD 里「{kw}」这一条我做过对应的实现，下面是细节。",
    "先说和 JD 里「{kw}」直接对得上的地方。",
    "贵司要求里「{kw}」这一项，我做过对应的，下面展开讲。",
    "JD 中提到的「{kw}」，我这边有可以直接对照的实践。",
    "「{kw}」这条我正好做过，具体做法写在下面。",
    "先从 JD 里「{kw}」这一条说起。",
]

# JD 里没有足够具体的词可点名时，用这几句
ECHOES_FALLBACK = [
    "下面几条是我能对上的地方。",
    "挑几条最能对得上的说。",
    "我的项目里对应的部分大概是这些。",
    "先说我实际做过什么。",
]

# 命中「能力边界」原子时不能用「我做过」句式，否则与正文自相矛盾
ECHOES_BOUNDARY = [
    "先说明一点：JD 里的「{kw}」我没在项目里实打实用过，这话我得讲在前面。",
    "「{kw}」这条我确实没做过，不敢含糊其辞，下面只说我真正做过的部分。",
    "贵司提到的「{kw}」我没有相关实践，可以现学，但我不把没做过的说成做过。",
    "先坦白：「{kw}」我没碰过。下面写的都是我有把握的部分。",
]
BOUNDARY_ATOMS = ("ai_notrain", "gen_boundary")

# ── 结尾句（10 种）────────────────────────────────────────────────────
ENDINGS = [
    "每周可实习 5 天，时间可协商。方便发份 JD 吗？",
    "我每周能到岗 5 天，可以连着做 数月以上，方便的话把详细 JD 发我看看？",
    "可实习、能做 数月以上都没问题，岗位详情方便发我一份吗？",
    "到岗时间可实习，可以实习 数月以上；方便的话把 JD 和团队情况发我一下？",
    "我每周可实习 5 天，长期做（数月以上）没问题，方便聊聊具体职责吗？",
    "可实习、时间可协商，简历已经附上了，后续想聊哪部分都可以。",
    "每周可实习 5 天，时间可协商。岗位还有其它要求的话，欢迎直接问我。",
    "我每周能到岗 5 天，可以连着做 数月以上，方便的话聊聊团队现在的技术栈？",
    "可实习、能做 数月以上没问题，简历已附上，后续想深入哪部分都可以聊。",
    "到岗时间可实习，实习 数月以上没问题。想先了解具体职责和技术选型吗？",
]

# ── 精简版开头 / 结尾 ────────────────────────────────────────────────
SHORT_OPENERS = [
    "您好，我是计算机专业 本科生候选人。",
    "你好，我是候选人，计算机 在校。",
    "您好，冒昧打扰，我是候选人（计算机专业 在校）。",
    "我是候选人，在校计算机专业。",
]

SHORT_END = "GitHub 若干个公开仓库、多次提交。可实习，时间可协商。方便发份 JD 吗？"

# 简历图组：JD 里的 AI 编程工具密度决定发哪份简历
IMGS_GENERIC = [r"研发实习生\shot_全量版_p1.png", r"研发实习生\shot_全量版_p2.png"]
IMGS_AICODE = [r"AI Coding全栈工程师\shot_aicoding_p1.png", r"AI Coding全栈工程师\shot_aicoding_p2.png"]
AI_CODING_KWS = ["ai coding", "aicoding", "ai编程", "ai 编程", "cursor", "claude code", "claude",
                 "codex", "copilot", "vibe coding", "vibecoding", "trae", "windsurf", "ai工具",
                 "ai 工具", "辅助开发", "提效", "大模型辅助"]

# 长度档（主推版目标字数）
TIERS = [260, 310, 360]

BAD_WORDS = ["说明：", "说明:", "不要改", "不要再改", "归档", "内部", "本节", "这是发给", "注："]


def norm_lower(s):
    return (s or "").lower()


# 证据原子分组：同一组（同一个项目 / 同一类能力）在一条话术里最多出现 2 次，
# 避免「某电商交易后端」霸屏、把一段话写成同一个项目复述三遍。
FAMILY = {
    "can_stack": "can", "can_sql": "sql", "can_cache": "can", "can_layer": "can", "can_debug": "can",
    "ai_api": "ai", "ai_ctx": "ai", "ai_stable": "ai", "ai_notrain": "ai",
    "game_scale": "game", "game_arch": "game", "game_test": "game", "game_fe": "game",
    "py_web": "py", "py_doc": "py", "py_data": "py",
    "data_model": "sql", "data_pipe": "pipe",
    "gen_collab": "gen", "gen_github": "gen", "gen_aicode": "gen", "gen_full": "gen",
    "gen_deploy": "gen", "gen_boundary": "gen",
}
FAMILY_CAP = {"can": 2, "sql": 1, "ai": 2, "game": 2, "py": 2, "pipe": 1, "gen": 2}


# 高信息量关键词：命中一个就说明方向真的对口
HIGH_KW = set("""
spring boot springboot springcloud mybatis redis mysql kafka rabbitmq docker nginx maven jvm
并发 多线程 缓存 缓存穿透 缓存击穿 缓存雪崩 分布式锁 微服务 消息队列 幂等 锁机制 事务 索引
慢查询 高并发 性能优化 接口 restful 后端 服务端
python flask django fastapi pandas numpy 爬虫 自动化脚本 定时任务 数据清洗
agent llm 大模型 提示词 prompt 智能体 aigc 微调 spring ai deepseek gpt 上下文 多轮 会话 工作流
rag 向量 检索增强
单元测试 接口测试 自动化测试 pytest vitest junit 测试开发 回归 覆盖率
全栈 前后端 联调 端到端 独立交付
sql 数仓 数据仓库 etl 数据开发 数据分析 bi 建模
typescript canvas 前端 交互 移动端 响应式
git linux 部署 运维 调试 排查
仓库 链接 开源 readme
""".split())


# 每个原子的「核心技术词」——用来判断这个原子跟这个 JD 对不对口。
# 评分：这些词在「任职要求」段出现最值钱，其次是「岗位职责」段，
#      再其次是岗位标题里出现（标题点明 Java 的岗，就该主推 Java 那条）。
CORE = {
    "can_stack": ["java", "spring", "mybatis", "restful", "后端", "接口", "服务端"],
    "can_sql": ["sql", "mysql", "索引", "事务", "数据库", "分页", "orm"],
    "can_cache": ["redis", "缓存", "并发", "高并发", "锁", "session", "性能", "延迟", "qps"],
    "can_layer": ["分层", "架构", "设计模式", "重构", "规范"],
    "can_debug": ["调试", "日志", "排查", "异常", "报错", "bug", "定位"],
    "ai_api": ["llm", "大模型", "agent", "智能体", "aigc", "提示词", "prompt", "spring ai",
               "deepseek", "工作流", "ai应用", "ai 应用"],
    "ai_ctx": ["上下文", "多轮", "会话", "context", "记忆", "用户画像"],
    "ai_stable": ["兜底", "降级", "幻觉", "超时", "重试", "限流", "稳定", "审核", "截断"],
    "game_scale": ["游戏", "game", "小游戏", "unity", "玩法", "关卡", "互动"],
    "game_arch": ["架构", "状态", "解耦", "可维护", "分层", "重构"],
    "game_test": ["单元测试", "单测", "junit", "pytest", "vitest", "自动化测试", "测试开发",
                  "覆盖率", "回归", "测试用例", "质量"],
    "game_fe": ["前端", "typescript", "javascript", "html", "css", "canvas", "交互",
                "移动端", "响应式", "vue", "react", "组件", "渲染", "小程序"],
    "py_web": ["python", "flask", "django", "fastapi", "pandas", "numpy", "爬虫", "脚本"],
    "py_doc": ["jinja", "模板", "解析", "文本", "文档", "pdf", "报告", "办公"],
    "py_data": ["pyqt", "桌面", "抓取", "清洗", "可视化", "统计", "报表", "工具",
                "数据处理", "预处理", "收集", "统计分析", "定量"],
    "data_model": ["sql", "数仓", "数据仓库", "etl", "bi", "建模", "指标", "hive"],
    "data_pipe": ["数据开发", "调度", "采集", "pipeline", "实时", "离线", "数据链路"],
    "gen_collab": ["代码管理", "工程规范", "复用", "交接", "版本管理", "git"],
    "gen_github": ["github", "仓库", "开源", "链接", "作品", "readme", "项目地址", "演示"],
    "gen_aicode": ["ai coding", "ai编程", "ai 编程", "cursor", "claude", "codex", "copilot",
                   "vibe coding", "windsurf", "trae", "提效", "ai工具", "ai 工具"],
    "gen_full": ["全栈", "前后端", "联调", "端到端", "独立交付", "独立负责"],
    "gen_deploy": ["部署", "运维", "linux", "docker", "容器", "服务器", "ci", "环境"],
    "gen_boundary": ["rag", "向量", "embedding", "react", "vue", "flutter", "android", "ios"],
}


def kw_weight(k):
    k = (k or "").lower().strip()
    if not k:
        return 0.0
    if k in HIGH_KW:
        return 3.0
    if len(k) >= 6:          # 较长的中文词，信息量中等
        return 1.2
    return 0.5               # 「团队」「沟通」这类泛词


def req_section(jd_text):
    """取出「任职要求 / 岗位要求」那一段——这才是招聘方真正在筛的东西。"""
    low = jd_text
    for mark in ("任职要求", "岗位要求", "职位要求", "任职资格"):
        i = low.find(mark)
        if i >= 0:
            return low[i:i + 700]
    return low[:700]


def match_atoms(jd_text, title):
    """在 JD 正文里匹配证据原子。

    打分口径（按重要性）：
      · 核心技术词出现在「任职要求」段 → 3.0；出现在「岗位职责」段 → 1.5；
      · 出现在岗位标题里 → 再 +2.0（标题点明 Java 的岗就该主推 Java 那条）；
      · 命中的技术词越多、重复出现越多，分数越高。
    """
    hay = norm_lower(jd_text)
    req = norm_lower(req_section(jd_text))
    ttl = norm_lower(title)
    out = []
    for a in ATOMS:
        best = 0.0
        distinct = 0
        occ = 0
        matched = []
        for c in CORE.get(a["id"], []):
            n = hay.count(c)
            if n == 0:
                continue
            distinct += 1
            occ += min(n, 2)
            w = 3.0 if c in req else 1.5
            if c in ttl:
                w += 2.0
            best = max(best, w)
            matched.append((c, w))
        if not matched:
            continue
        sc = best + 0.5 * (distinct - 1) + 0.3 * (occ - distinct)
        matched.sort(key=lambda x: -x[1])
        out.append((a, sc, matched))
    out.sort(key=lambda x: -x[1])
    return out


def pick_echo_kw(atom, hits, jd_low):
    """挑一个值得在话术里点名的关键词。

    优先选「既在 JD 里出现、又足够具体」的那个（像 Redis、Agent、单元测试）；
    泛词（git、团队）不拿去点名，避免出现「JD 里写着『git』」这种空话。
    """
    best = None
    for e in atom.get("echo", []):
        if e.lower() in jd_low:
            if best is None or len(e) > len(best):
                best = e
    if best:
        return best
    for kw, w in hits:
        if w >= 1.2:
            return kw
    return None


def build_main(target, jd, idx, avoid_lead=None):
    """生成主推版正文（多行）。

    avoid_lead：同一公司前面已经用过的 lead 原子 id。
    同一批里同一个 HR 挂了多个岗位时（如「示例文旅W」三个 AI 全栈岗都是同一个人），
    如果证据组合撞车，HR 会收到几条几乎一样的招呼话——直接看着像群发。
    所以把已用过的 lead 原子压到最后，逼它换一个证据组合。
    """
    jd_low = jd.lower()
    atoms = match_atoms(jd, target.get("position", ""))
    if avoid_lead:
        atoms = sorted(atoms, key=lambda x: (x[0]["id"] == avoid_lead, -x[1]))
    if not atoms:
        atoms = [(a, 1, [(a["kws"][0], 1.0)]) for a in ATOMS if a["id"] in
                 ("can_stack", "gen_collab", "gen_full", "game_fe")]

    tier = TIERS[idx % len(TIERS)]
    opener = OPENERS[idx % len(OPENERS)]
    # 步长必须与池长互质，否则只能轮转到池子的一部分
    ending = ENDINGS[(idx * 3 + 2) % len(ENDINGS)]

    # 「JD 点名句」用得分最高的原子
    lead = atoms[0]
    echo_kw = pick_echo_kw(lead[0], lead[2], jd_low)
    if lead[0]["id"] in BOUNDARY_ATOMS:
        # 能力边界：不能说「我做过」
        echo = (ECHOES_BOUNDARY[idx % len(ECHOES_BOUNDARY)].replace("{kw}", echo_kw)
                if echo_kw else ECHOES_BOUNDARY[idx % len(ECHOES_BOUNDARY)].replace("{kw}", "这块技术"))
    elif echo_kw:
        echo = ECHOES[idx % len(ECHOES)].replace("{kw}", echo_kw)
    else:
        echo = ECHOES_FALLBACK[idx % len(ECHOES_FALLBACK)]

    lines = [opener.replace("{pos}", target.get("position", "")), echo]

    used = 0
    label_seen = Counter()
    fam_seen = Counter()
    selected_ids = []      # 实际被采用的证据原子（按选用顺序）
    claimed = []           # 已用过的原子 id，避免同一项目反复出现
    reserve = len(ending) + 6      # 给结尾句留位置
    for a, _sc, hits in atoms:
        if used >= 4:
            break
        if a["id"] in claimed:
            continue
        fam = FAMILY.get(a["id"], a["id"])
        if fam_seen[fam] >= FAMILY_CAP.get(fam, 2):
            continue
        cands = a["labels"]
        lbl = None
        for off in range(len(cands)):
            cand = cands[(used + off) % len(cands)]
            if cand not in label_seen:
                lbl = cand
                break
        if lbl is None:
            lbl = cands[used % len(cands)]
        label_seen[lbl] += 1
        line = f"**【{lbl}】**{a['text']}"
        # 超出长度档就跳过这条（后面可能还有更短的原子），但至少保证 2 条证据
        if sum(len(x) for x in lines) + len(line) + reserve > tier and used >= 2:
            label_seen[lbl] -= 1
            continue
        lines.append(line)
        claimed.append(a["id"])
        selected_ids.append(a["id"])
        fam_seen[fam] += 1
        used += 1
    if used == 0:
        lines.append(f"**【Java 后端】**{ATOMS[0]['text']}")

    lines.append(ending)
    body = "\n".join(lines)
    return body, used, selected_ids


def build_short(target, jd, idx):
    """生成精简版正文（1 条证据 + 短开头 + 结尾）。"""
    jd_low = jd.lower()
    atoms = match_atoms(jd, target.get("position", ""))
    if not atoms:
        atoms = [(ATOMS[0], 1, [(ATOMS[0]["kws"][0], 1.0)])]
    a, _sc, hits = atoms[0]
    lbl = a["labels"][idx % len(a["labels"])]
    opener = SHORT_OPENERS[idx % len(SHORT_OPENERS)]
    kw = pick_echo_kw(a, hits, jd_low)
    lines = [opener]
    if kw:
        lines.append(f"JD 里的「{kw}」我也做过：")
    lines.append(f"**【{lbl}】**{a['text']}")
    lines.append(SHORT_END)
    return "\n".join(lines)


def check_body(text):
    bad = [w for w in BAD_WORDS if w in text]
    if bad:
        raise ValueError(f"正文含内部词 {bad}")
    if not (text.startswith("您好") or text.startswith("你好") or text.startswith("候选人")
            or text.startswith("我是") or text.startswith("您好！") or text.startswith("你好呀")):
        raise ValueError("正文首行不是打招呼开头")
    return True


def main():
    tfile = os.environ.get("GD2_TARGETS", "gd2_targets.json")
    tpath = os.path.join(WORK, tfile)
    targets = json.load(io.open(tpath, encoding="utf-8"))
    jdpath = os.path.join(WORK, "jd_text.json")
    jds = {}
    if os.path.isfile(jdpath):
        jds = json.load(io.open(jdpath, encoding="utf-8"))

    out = []
    missing = []
    company_lead = {}      # 公司 → 该公司前面已用过的 lead 原子（同 HR 多岗位去撞车）
    company_n = Counter()  # 公司 → 已生成份数
    for i, t in enumerate(targets):
        jd = (jds.get(t["label"]) or {}).get("jd", "")
        if len(jd) < 120:
            missing.append(t["label"])
            continue
        comp = t.get("company", "")
        avoid = company_lead.get(comp)
        main_txt, used, atom_ids = build_main(t, jd, i, avoid)
        short_txt = build_short(t, jd, i)
        if atom_ids:
            company_lead.setdefault(comp, atom_ids[0])
        company_n[comp] += 1
        try:
            check_body(main_txt)
            check_body(short_txt)
        except ValueError as e:
            print(f"  !! {t['label']} {e}")
            continue

        folder = t["folder"]
        d = os.path.join(RECRUIT, folder)
        os.makedirs(d, exist_ok=True)
        kws = []
        for _a, _sc, hits in match_atoms(jd, t.get("position", ""))[:6]:
            for kw, w in hits:
                if w >= 1.2 and kw not in kws:
                    kws.append(kw)
        kws = kws[:8]
        # 简历图：JD 里的 AI 编程工具密度高 → 发 AI Coding 版，否则发全量版
        jd_low = jd.lower()
        aic = sum(1 for k in AI_CODING_KWS if k in jd_low)
        imgs = IMGS_AICODE if aic >= 2 else IMGS_GENERIC
        src_pdf = (r"AI Coding全栈工程师\你的名字-AICoding全栈工程师.pdf（AI Coding 方向 2 页）"
                   if imgs is IMGS_AICODE else r"研发实习生\候选人-实习.pdf（全量版 3 页 11 项目）")
        t["imgs"] = imgs
        t["tpl"] = "JD定制"
        t["aicoding_hits"] = aic
        content = f"""{t['company']} · {t['position']}
地址：{t['city']}
薪资：{t['salary']}

【主推版 · 按 JD 定制 · {len(main_txt)} 字】
{main_txt}

【精简版 · {len(short_txt)} 字】
{short_txt}

【按 JD 命中的证据点】
- 命中关键词：{'、'.join(kws) if kws else '（无，回退到通用项目）'}
- 采用证据原子：{'、'.join(atom_ids)}
- 长度档：{TIERS[i % len(TIERS)]} 字档（轮换）
- 开头句式 #{i % len(OPENERS) + 1} / 结束句式 #{(i * 3 + 2) % len(ENDINGS) + 1}
- 简历图组：{src_pdf}
- GitHub：https://github.com/3155498108（若干个公开仓库 / 多次提交，2026-10-21 实测）

【已核验】
- 某网页小游戏合集（目录数与清单条数双向差集为空，双向差集为空）
- 两百余个 TS 文件 / 数万行 / 数十个 Vitest 测试文件（`count_lines.py` 实测）
- 某电商交易后端：18 个 Controller / 70 个 RESTful 接口 / 11 张业务表
- 某 AI 客服：5 个 RESTful 端点 / CompletableFuture 异步 + 30 秒超时 / 异常隔离 / 1–3 秒 / < 50 毫秒
- GitHub：若干个公开仓库 / 多次提交（`gh_count.py` 实测，非 fork 仓库）
"""
        with io.open(os.path.join(d, "新建 文本文档.txt"), "w", encoding="utf-8") as fp:
            fp.write(content)
        out.append(dict(label=folder, jobId=t["jobId"], company=t["company"],
                        position=t["position"], city=t["city"], salary=t["salary"],
                        main_len=len(main_txt), short_len=len(short_txt),
                        atoms=atom_ids, opener=i % len(OPENERS), tier=TIERS[i % len(TIERS)],
                        jd_len=len(jd), kws=kws, pdf=src_pdf, imgs=imgs,
                        aicoding_hits=aic, company_seq=company_n[comp]))
        print(f"  {len(main_txt):>3}字 {folder[:44]:<46} 原子 {'/'.join(atom_ids) or '-'}")

    report_name = os.environ.get("GD2_REPORT", "gd2_msg_report.json")
    with io.open(os.path.join(WORK, report_name), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    # 投递用最终清单（wb_cross.py 读 BOSS_TARGETS_FILE）
    final_name = os.environ.get("GD2_FINAL", "gd2_final.json")
    json.dump(out and targets or [], io.open(os.path.join(WORK, final_name), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\n生成 {len(out)} 份差异化话术")
    if missing:
        print(f"!! JD 未就绪 {len(missing)} 个：{missing}")
    print(f"→ {os.path.join(WORK, 'gd2_msg_report.json')}")
    print(f"→ {os.path.join(WORK, final_name)}（投递用）")


if __name__ == "__main__":
    main()
