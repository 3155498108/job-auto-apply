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
         # 只放我真在项目里写过的东西。「提示词」不放：我写过提示词模板，
         # 但没做过提示词调优/优化，点名这个词会被理解成后者。
         echo=["大模型", "Agent", "Spring AI", "DeepSeek", "多轮对话"],
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

# ── 同一原子的多种真实表述 ───────────────────────────────────────────
# 同一批里好几个岗位会用同一组证据原子（py_web + ai_api 尤其集中）。
# 证据一样、但每句话都一字不差，HR 并排看两条就知道是群发模板。
# 所以给高频原子准备几种**等价但不同措辞**的写法，按批次内使用次数轮换。
#
# ⚠ 硬约束：变体只能换措辞，不能换事实。
#   · 数字必须与已核验事实完全一致（18 Controller / 70 RESTful / 5 端点 /
#     30 秒超时 / 1–3 秒 / < 50 毫秒 / 11 张表 / 某网页小游戏合集 / 两百余个 TS 文件 /
#     数万行 / 数十个测试文件 / 若干个公开仓库 …）
#   · 不能出现原表述里没有的新技术、新项目、新指标
#   · 每条变体都要能被简历/仓库佐证
ATOM_TEXT_VARIANTS = {
    "ai_api": [
        "小组负责人，做 Spring AI + DeepSeek 某 AI 客服：把大模型接成 5 个 RESTful 端点，CompletableFuture 异步调用 + 30 秒超时 + 持久化异常隔离，单次响应 1–3 秒、数据库写入 < 50 毫秒。",
        "带 5 人小组做 Spring AI + DeepSeek 某 AI 客服，按表现 / 控制 / 业务 / 数据 / AI 五层接入大模型，对外 5 个 RESTful 端点；调用走 CompletableFuture 异步，配 30 秒超时与持久化异常隔离，AI 响应稳定在 1–3 秒、入库 < 50 毫秒。",
        "担任 小组负责人，用 Spring AI 把 DeepSeek 接成某 AI 客服，5 个 RESTful 端点对外可用；大模型调用用 CompletableFuture 异步 + 30 秒超时，聊天记录入库失败只记日志、不影响主流程，响应 1–3 秒、写入 < 50 毫秒。",
    ],
    "py_web": [
        "用 Python + Flask + Pillow + MoviePy 独立做出长卷轴滚动视频生成器，后端提供创建 / 列表 / 详情 / 下载 / 删除五类接口，前端 Bootstrap 5 + 原生 JS 支持拖拽批量上传与进度轮询。",
        "独立用 Python + Flask 做出长卷轴滚动视频生成器，配 Pillow 做图像处理、MoviePy 做视频合成；后端给创建 / 列表 / 详情 / 下载 / 删除五类接口，前端 Bootstrap 5 + 原生 JS，支持拖拽批量上传和进度轮询。",
        "Python 侧用 Flask + Pillow + MoviePy 写了长卷轴滚动视频生成器，服务端拆成创建 / 列表 / 详情 / 下载 / 删除五个接口，页面用 Bootstrap 5 + 原生 JS 做拖拽批量上传与进度轮询。",
    ],
    "gen_aicode": [
        "日常用 Claude Code / Codex 协作开发，AI 只做候选试算、规则始终是唯一真相源，生成的代码我自己审、问题自己跟。",
        "写代码基本靠 Claude Code / Codex 协作，但 AI 只负责给候选方案，规则由我定、产出由我审，出了问题自己兜。",
        "日常用 Claude Code / Codex 写代码：我把规则和边界先定死，AI 只做候选试算，生成结果逐行审，逻辑我自己跟。",
    ],
    "gen_full": [
        "前后端能独立闭环：从数据库表设计、接口实现到页面交互和本地部署都自己跑通一遍。",
        "一个人能把前后端闭环：表设计、接口实现、页面交互到本地部署，全部自己跑通。",
        "从建表写接口，到页面交互和本地部署，都是我一个人做完并跑通的。",
    ],
    "game_fe": [
        "用 TypeScript + Canvas 写渲染与交互，同一套状态机同时驱动手机与桌面端，不依赖框架也能把操作手感做细。",
        "前端用 TypeScript + Canvas 实现渲染和交互，一套状态机同时跑手机和桌面浏览器，不依赖框架也把操作手感调到位。",
        "渲染与交互部分用 TypeScript + Canvas 写，同一份状态机适配手机与桌面端，脱离框架也能把手感做细。",
    ],
    "can_stack": [
        "独立完成「某电商交易后端」电商后端：Spring Boot + MyBatis + MySQL + Redis，18 个 Controller、70 个 RESTful 接口，按 Controller / Service / Mapper 分层。",
        "「某电商交易后端」电商后端是我一个人做完的：Spring Boot + MyBatis + MySQL + Redis，分 Controller / Service / Mapper 三层，共 18 个 Controller、70 个 RESTful 接口。",
        "用 Spring Boot + MyBatis + MySQL + Redis 独立做出「某电商交易后端」电商后端，按 Controller / Service / Mapper 分层，18 个 Controller 对应 70 个 RESTful 接口。",
    ],
    "can_sql": [
        "11 张业务表（菜品 / 订单 / 订单明细 / 购物车 / 地址簿等）自己设计，查询走索引、SQL 全部用 `#{}` 占位防注入，MyBatis 拦截器统一做分页与字段脱敏。",
        "菜品 / 订单 / 订单明细 / 购物车 / 地址簿等 11 张表由我自己设计，查询走索引，SQL 全部 `#{}` 占位防注入，分页和字段脱敏交给 MyBatis 拦截器统一处理。",
        "数据库这块：11 张业务表自己设计（菜品 / 订单 / 购物车等），查询用索引，SQL 一律用 `#{}` 占位防注入，分页与脱敏由 MyBatis 拦截器统一做。",
    ],
    "py_doc": [
        "另做过 Python + Jinja2 的简历生成工具：解析岗位 JD、算关键词覆盖率、改写后再渲染成 PDF，内置 15 套 A4 版式主题。",
        "还做过一个 Python + Jinja2 的简历生成工具：先把岗位 JD 解析出来算关键词覆盖率，再改写内容渲染成 PDF，内置 15 套 A4 版式主题。",
        "另外有套 Python + Jinja2 的简历工具：解析 JD → 算关键词覆盖率 → 改写 → 渲染 PDF，配 15 套 A4 版式主题。",
    ],
    "game_arch": [
        "内核按「站点壳 / 游戏内核 / 渲染层」三层拆开，内核零运行时依赖，状态用不可变对象 + 纯函数 reducer 表达，改一处不会牵动全局。",
        "游戏内核拆成站点壳 / 游戏内核 / 渲染层三层，内核本身零运行时依赖，状态用不可变对象和纯函数 reducer 表达，改一处不会牵动全局。",
        "架构上把站点壳、游戏内核、渲染层分开，内核不依赖运行时，状态靠不可变对象 + 纯函数 reducer，改动不会牵一发动全身。",
    ],
    "ai_ctx": [
        "用 sessionId 隔离不同用户的会话并保留 5 轮上下文，让多轮追问能接上前面的信息，而不是每次都从零开始。",
        "每个用户用 sessionId 隔开自己的会话，保留 5 轮上下文，多轮追问能接上前面说过的话，不用每次从头讲。",
        "会话用 sessionId 做隔离，保留最近 5 轮上下文，所以追问时能接上前面聊过什么，而不是每次从零开始。",
    ],
    "ai_stable": [
        "上线后累计修复 6 类问题（超时、串话、输出截断、敏感内容、并发写入等），把大模型的不稳定挡在业务层之外。",
        "上线后修了 6 类问题——超时、串话、输出截断、敏感内容、并发写入这些，大模型的不稳定我都在业务层挡住了。",
        "上线后陆续修掉 6 类问题：超时、串话、输出截断、敏感内容、并发写入等，目标是让大模型的不稳定碰不到主流程。",
    ],
    "gen_deploy": [
        "自己配过 Flask 服务的进程管理与 HTTP 接口暴露，本地跑通前后端并部署上线验证过。",
        "Flask 服务的进程管理和 HTTP 接口暴露我自己配过，前后端在本地跑通后部署上线验证过一遍。",
        "部署这块我独立完成：配好 Flask 服务的进程管理与 HTTP 接口暴露，本地跑通前后端再部署上线验证。",
    ],
    "game_scale": [
        "独立开发 数十款纯静态网页小游戏，同一套代码适配手机与桌面浏览器：游戏内核是纯 TypeScript 状态机，两百余个 TS 文件 / 数万行。",
        "数十款纯静态网页小游戏是我独立写的，同一套代码适配手机和桌面浏览器；内核是纯 TypeScript 状态机，两百余个 TS 文件 / 数万行。",
        "一个人写出 数十款纯静态网页小游戏，代码一套通吃手机与桌面浏览器；内核用纯 TypeScript 状态机实现，两百余个 TS 文件 / 数万行。",
    ],
    "game_test": [
        "用不可变状态与纯函数换可测试、可复现、可回放，随机数用可播种的 mulberry32，每款游戏配 Vitest 单测（共 数十个测试文件）。",
        "状态不可变 + 纯函数，换来的是可测试、可复现、可回放；随机数用可播种的 mulberry32，每款游戏配 Vitest 单测，共 数十个测试文件。",
        "为了让逻辑可测，我把状态做成不可变对象、随机数换成可播种的 mulberry32，每款游戏配 Vitest 单测，一共 数十个测试文件。",
    ],
    "can_cache": [
        "Redis 缓存菜品与令牌、Session 共享登录态，用分布式锁防超卖，把并发下单的重复写入挡在业务层之前。",
        "菜品和令牌走 Redis 缓存，登录态用 Session 共享，并发下单靠分布式锁防超卖，重复写入挡在业务层之前。",
        "缓存这块用 Redis 存菜品和令牌，Session 共享登录态，超卖问题用分布式锁解决，重复写不进业务层。",
    ],
    "can_layer": [
        "后端按 Controller / Service / Mapper 分层，18 个 Controller 对应 70 个 RESTful 接口，接口统一返回包装结构，方便前端按同一套约定接。",
        "后端分 Controller / Service / Mapper 三层，18 个 Controller 对应 70 个 RESTful 接口，返回结构统一包装，前端按同一套约定接。",
        "分层是 Controller / Service / Mapper，18 个 Controller 对应 70 个 RESTful 接口；返回结构统一，前端对接时不用各写一套。",
    ],
    "can_debug": [
        "写接口时靠日志和断点逐个排查参数绑定、事务回滚和缓存一致性问题，踩过的坑都记成文档交给组里复用。",
        "写接口遇到问题，我就靠日志和断点逐个排查参数绑定、事务回滚、缓存一致性这些，踩过的坑整理成文档给组里复用。",
        "参数绑定、事务回滚、缓存不一致这类问题，我是靠日志加断点一个个定位的，排查过程都写成文档留给组里复用。",
    ],
    "py_data": [
        "用 PyQt6 桌面端 + Node.js 客户端做过批量歌单抓取与多级排序，针对命令行单次只能取 200 首的限制，自己搭了一套分批抓取 + 结果合并的分析方案。",
        "批量歌单抓取和分级排序这块，我用 PyQt6 桌面端配 Node.js 客户端做的；命令行一次只能取 200 首，所以自己搭了分批抓取再合并结果的分析流程。",
        "做过一套 PyQt6 桌面端 + Node.js 客户端的批量歌单抓取与多级排序，绕开命令行单次 200 首的限制，用分批抓取加结果合并来完成。",
    ],
    "gen_github": [
        "代表项目都放在 GitHub（github.com/3155498108），若干个公开仓库、多次提交，README 里写清了做法和取舍，可以直接看。",
        "项目都开源在 GitHub（github.com/3155498108），若干个公开仓库、多次提交，README 里把做法和取舍写清楚了，可以直接点进去看。",
        "代表作都在 GitHub 上（github.com/3155498108）：若干个公开仓库、多次提交，每个仓库的 README 都写了实现思路和取舍。",
    ],
    "data_model": [
        "数据库这块自己设计过 11 张业务表并做索引与联表查询优化，熟悉从表结构到慢查询定位这一整套流程。",
        "数据库方面：11 张业务表自己设计过，索引和联表查询也做过优化，从表结构到慢查询定位这套流程我都走过。",
        "表设计和查询优化我都做过——11 张业务表自己建，索引与联表查询也调过，慢查询定位是常规操作。",
    ],
    "data_pipe": [
        "数据流向上做过批量抓取 → 分级排序 → 结果落库的全链路，遇到单次取数上限就自己拆批并补齐结果，不靠手工反复拉。",
        "数据流这块我做过批量抓取 → 分级排序 → 结果落库的完整链路；碰上单次取数上限就自己拆批、补齐结果，不手工反复拉。",
        "从批量抓取到分级排序再到落库，我跑通过整条数据链路；取数有上限的时候自己拆批并把结果合并齐，不靠手动一遍遍拉。",
    ],
    "gen_collab": [
        "习惯先定契约再动手：接口文档、技术方案和模块划分先写清楚再写代码，联调、排错和交接都自己跟。",
        "我的习惯是先定契约再动手——接口文档、技术方案、模块划分先写清楚，然后才写代码，联调、排错、交接都自己跟到底。",
        "开工前先把接口文档、技术方案和模块划分定下来，代码跟着契约走；联调、排错和交接这些我也不假手于人。",
    ],
    "ai_notrain": [
        "模型训练与微调我没做过，做的是把大模型接进业务并处理它的慢与不稳，这点我如实说。",
        "模型训练、微调这些我没碰过；我做过的是把大模型接进业务，再处理它的慢和不稳，这话我得讲在前面。",
        "训练和微调我确实没做过，我的做法是把大模型接进业务链路，并处理它的慢与不稳——这点不糊弄。",
    ],
    "gen_boundary": [
        "RAG / 向量检索、React、Vue 这些我没在项目里实打实用过，来了可以现学，但我不把没做过的说成做过。",
        "RAG、向量检索、React、Vue 这些我没在项目里实打实用过，来了可以现学，但我不把没做过的说成做过。",
        "RAG / 向量检索以及 React、Vue 我都没在项目里真正用过，可以现学，但我不会把没做过的说成做过。",
    ],
}

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
    # ↓ 池长必须 ≥ 批次大小（8 句配 17 个岗位 → 点名句重复，正文相似度冲到 0.6）
    "JD 里的「{kw}」，我做过对应的落地，下面说细节。",
    "看到「{kw}」这条要求，我手上正好有对应的项目。",
    "「{kw}」这块我实际写过，下面展开讲做法。",
    "先拿 JD 里的「{kw}」来对一下。",
    "贵司写的「{kw}」，我的项目里正好覆盖到。",
    "关于「{kw}」这一条，我做过对应的实现，下面是过程。",
    "「{kw}」是我项目里比较实的一块，可以细说。",
    "从 JD 的「{kw}」这条开始对。",
    "JD 提到的「{kw}」，我这边有能对照的实践，下面讲。",
    "「{kw}」这条我做过，下面是具体做法和取舍。",
]

# 点名句优先从这张表里挑「该 JD 独有且足够具体」的词，
# 而不是用原子的固定 echo 词（固定的会让同方向的岗位点名同一个词）。
#
# ⚠ 这张表是**「点名句里可以声称我做过」的技术白名单**，不是 JD 关键词表。
# 点名句的句式是「JD 里的「X」我也做过」——一旦把没做过的技术放进来，
# 就是当场编经历（实测：LangChain 被点名后说「我做过」）。
# 边界技术（RAG / 向量库 / LangChain / MCP / 微服务 / 模型训练）只能出现在
# ECHOES_BOUNDARY 那组「我没做过」的句式里，不能进这张表。
ECHO_POOL = [
    # 后端 / 数据
    "spring boot", "mybatis", "mysql", "redis", "docker", "flask", "fastapi",
    "异步", "超时", "异常隔离", "缓存", "分布式锁", "索引",
    # 前端 / TS
    "typescript", "canvas", "单元测试", "vitest", "交互", "响应式",
    # AI 应用（我真做过的部分）
    "spring ai", "deepseek", "大模型", "多轮对话", "上下文", "某 AI 客服", "问答",
    # AI Coding / 工程习惯
    # 只放「天天用、并且有产出」的：Claude Code / Codex 是主力；
    # Cursor / Copilot / Trae 只是「打开用过」，不点它们的名——点名句的句式是
    # 「JD 里的「X」我也做过对应的落地」，对只用过的东西说这句话是夸大。
    "ai coding", "claude code", "codex", "vibe coding",
    "开源", "从 0 到 1", "独立交付", "全栈", "前后端联调", "需求拆解",
    "自动化脚本", "批量", "图像", "视频", "pyqt",
]

# JD 里没有足够具体的词可点名时，用这几句
# 池长必须 ≥ 批次大小，否则一批里多个岗位用同一句 fallback，正文雷同
ECHOES_FALLBACK = [
    "下面几条是我能对上的地方。",
    "挑几条最能对得上的说。",
    "我的项目里对应的部分大概是这些。",
    "先说我实际做过什么。",
    "有把握的部分我写在下面。",
    "说说我真正落地过的内容。",
    "下面是我能拿出来的实际经历。",
    "把做过的部分摆出来，您看合不合适。",
    "我把这几段相关的经历列一下。",
    "下面这些是我实际动手做过的。",
    "能对上的经历写在这儿。",
    "先把我手上对得上的项目摆出来。",
    "这部分我做过，具体如下。",
    "写下我真正做过的内容。",
    "相关经历整理在下面。",
    "我做过的是这些，展开说一下。",
    "先说我最有把握的几段。",
    "下面这段是我自己的实践。",
]

# 点名句里不能用的泛词：点出来等于没说，还显得像群发模板
# 「ai」是重灾区——示例大厂K「ai实习生」这个岗，JD 里除了 ai 没别的具体词，
# 点名句写成「JD 里提到的『ai』」完全是废话，直接退回 fallback 句。
ECHO_STOP = {
    "ai", "aigc", "ml", "开发", "技术", "代码", "编程", "项目", "需求", "团队",
    "学习", "能力", "实习", "员工", "职责", "工作", "相关", "使用", "熟悉",
    "掌握", "具备", "api", "git", "系统", "平台", "服务", "业务", "问题",
    "优化", "设计", "功能", "方案", "环境", "工具", "效果", "能力", "经验",
    "岗位", "职位", "描述", "要求", "职责", "内容", "方向", "场景", "配合",
    "良好", "较强", "积极", "主动", "沟通", "意识", "习惯", "素质", "能力",
}

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
    # ↓ 池长必须 ≥ 批次大小，否则同一批里结尾句必然重复
    # （17 个岗位配 10 句 → 结尾句去重只有 10/17）
    "实习安排我这边完全没问题：可实习、连续 数月以上都可以。方便的话把岗位说明发我一份？",
    "可实习能到岗，做满 6 个月也没问题。简历已附上，有细节想问我随时说。",
    "我这周起可实习、连续 数月以上都能保证，需要的话把团队情况介绍下？",
    "到岗和周期都不是问题：可实习、数月以上长期做。想先看下具体工作内容吗？",
    "可实习、时间可协商都行。方便的话把 JD 发我，我这边先做功课。",
    "我这边可实习到岗、能连续做 数月以上，后续想聊技术细节也可以。",
    "实习周期我可以保证：可实习、数月以上。岗位还有别的要求吗？",
    "可实习、数月以上没有问题，简历已经附上了。想了解团队分工的话聊聊？",
    "到岗时间没问题，可实习、连续 数月以上都可以。方便聊聊职责边界吗？",
    "我每周能实习 5 天，数月以上持续做也没问题。有具体的技术要求吗？",
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
    "ai_api": ["ai", "llm", "大模型", "agent", "智能体", "aigc", "提示词", "prompt",
               "spring ai", "deepseek", "ai应用", "ai 应用"],
    # ⚠ 「ai」必须进 CORE：短词按「非 ASCII 字母数字」判边界后，
    #   「AI实习生」这种标题能命中了。缺了它，AI 岗的 lead 会掉到
    #   gen_deploy 这类通用工程化原子身上（示例大厂K那个岗就是这么选错的）。
    # 能力边界：JD 要求里有「模型训练/微调」时，用这条如实说「训练我没做过」
    # （CORE 里漏了它 → 这类岗位永远选不上边界原子，只能硬凑一段假经历）
    "ai_notrain": ["模型训练", "训练", "微调", "调优", "sft", "lora", "预训练", "蒸馏", "量化"],
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


def _count_kw(hay, c):
    """词条出现次数。两字母词条必须按词边界计数。

    「ci」「cd」这种词条直接用 `in` 会命中 "efficiency"、"procedure" 里的字母对，
    让「部署运维」原子在毫不相干的 JD 上刷高分（示例大厂K那个岗就是这么选错的）。

    ⚠ 边界不能用 `\\b`：Python 的 `\\b` 是 Unicode 感知的，中文属于 word 字符，
    所以「AI实习生」里的 ai 前后都挨着中文字符 → `\\bai\\b` **匹配不上**。
    实测示例大厂K「ai实习生」这个岗，ai_api 原子压根没进候选，只剩「服务器」把
    gen_deploy 顶成 lead。改用「非 ASCII 字母数字」作边界才符合中文 JD 的实际。
    """
    if len(c) <= 2:
        return len(re.findall(r"(?<![a-z0-9])" + re.escape(c) + r"(?![a-z0-9])", hay))
    return hay.count(c)


def _has_kw(text, c):
    if len(c) <= 2:
        return re.search(r"(?<![a-z0-9])" + re.escape(c) + r"(?![a-z0-9])", text) is not None
    return c in text


def match_atoms(jd_text, title):
    """在 JD 正文里匹配证据原子。

    打分口径（按重要性）：
      · 核心技术词出现在「任职要求」段 → 3.0；出现在「岗位职责」段 → 1.5；
      · 出现在岗位标题里 → 再 +2.0（标题点明 Java 的岗就该主推 Java 那条）；
      · 命中的技术词越多、重复出现越多，分数越高。

    **标题也要进检索范围**：只搜正文的话，「软件开发实习生 AI 辅助开发 / Vibe Coding」
    这种只在标题里出现的强信号会被整个跳过，原子退化成「排错/前端」这类弱相关项。
    """
    hay = norm_lower(jd_text + " " + (title or ""))
    req = norm_lower(req_section(jd_text))
    ttl = norm_lower(title)
    out = []
    for a in ATOMS:
        best = 0.0
        distinct = 0
        occ = 0
        matched = []
        for c in CORE.get(a["id"], []):
            n = _count_kw(hay, c)
            if n == 0:
                continue
            distinct += 1
            occ += min(n, 2)
            w = 3.0 if _has_kw(req, c) else 1.5
            if _has_kw(ttl, c):
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

    ⚠ 第一轮必须用 **lead 原子自己的 echo 词**，保证「点名什么，正文就讲什么」。
    实测踩过的坑：示例企业98「后端开发实习生AI+编程开发」这个岗，
    lead 是 py_web（Python + AI 编程），但 ECHO_POOL 里先命中了「mysql」，
    点名句写成「mysql 是我项目里比较实的一块」——正文讲的却是 Python + Flask，
    HR 一眼就看出是套模板。点名词和正文必须自洽。

    第二轮才退回 ECHO_POOL：这张表是「具体技术词」，能保证同方向的岗位
    点名的词不一样（都用原子的固定 echo 词的话，5 个 Python+AI 岗会一起点名
    「Python」，正文就长得一模一样）。
    第三轮兜底用「JD 里命中过的词」时，必须过 ECHO_STOP 泛词黑名单：
    「ai」这种词点出来是废话，会让整句看起来像群发模板。
    泛词全被过滤掉就返回 None，调用方走 ECHOES_FALLBACK。
    """
    for e in atom.get("echo", []):
        if e.lower() in jd_low:
            return e
    best = None
    for e in ECHO_POOL:
        if e in jd_low:
            if best is None or len(e) > len(best):
                best = e
    if best:
        return best
    for kw, w in hits:
        if w >= 1.2 and kw.lower() not in ECHO_STOP and len(kw) > 1:
            return kw
    return None


def _is_ai_title(title):
    """岗位标题是不是 AI 方向。"""
    t = norm_lower(title or "")
    for k in ("ai", "aigc", "大模型", "agent", "智能体", "llm", "gpt", "aicoding",
              "ai coding", "ai应用", "ai 应用", "ai开发", "ai 开发", "vibe coding",
              "提示词", "prompt", "chatgpt", "claude"):
        if k in t:
            return True
    return False


# AI 落地类原子：我真做过、且正是 AI 岗最想听的
AI_LEAD_OK = ("ai_api", "ai_ctx", "ai_stable", "gen_aicode")


def _ai_lead_fix(atoms, title, forced=None):
    """AI 方向岗：把「AI 落地」证据顶成 lead。

    为什么需要：
    示例大厂K「ai实习生」这个岗，JD 里只零星提到「服务器」「模型训练」，
    通用打分让 gen_deploy（部署运维）拿了 3.3 分当 lead，正文第一句就成了
    「看到 JD 里写着『部署』」——跟「参与 AI 开发 / 协助模型训练」八竿子打不着。
    HR 一看就知道是拿通用模板套的。

    规则：
      · 标题是 AI 方向、且候选里有 AI 落地类原子 → 最好的那个提到 lead；
      · 阈值取当前 lead 的 55%，太低（不相关）不动手，太高（AI 命中更强）不动手；
      · ai_notrain（能力边界）**永远不当 lead**——开场就说「这条我没做过」
        太消极，边界声明放在正文第二段更合适；
      · 已有 force_atoms（JD 写死主语言）时不插手，语言的优先级更高。
    """
    if forced or not atoms or not _is_ai_title(title):
        return atoms
    cands = [a for a in atoms if a[0]["id"] in AI_LEAD_OK]
    if not cands:
        return atoms
    best_ai = max(cands, key=lambda x: x[1])
    lead = atoms[0]
    if lead[0]["id"] in AI_LEAD_OK:
        return atoms  # 本来就是 AI 落地打头，不用动
    if best_ai[1] < lead[1] * 0.55:
        return atoms
    rest = [a for a in atoms if a is not best_ai]
    return [best_ai] + rest


def _jd_body(jd):
    """取 JD 的「职责 + 要求」正文，排除公司介绍 / 竞争力分析等无关段落。

    示例大厂K那个岗写的是「岗位职责：1. 参与AI相关技术的开发与实现，协助完成
    模型训练与测试」——「模型训练」在**职责段**而不在要求段，
    只看要求段会漏掉（实测漏过一次）。
    """
    low = jd
    start = 0
    for mark in ("岗位职责", "职位描述", "工作内容"):
        i = low.find(mark)
        if i >= 0:
            start = i
            break
    end = len(low)
    for mark in ("公司介绍", "微信扫码分享", "竞争力分析", "BOSS 安全提示",
                 "查看全部", "工商信", "该公司其他"):
        i = low.find(mark, start)
        if i >= 0:
            end = min(end, i)
    return low[start:end]


# JD 里出现这些词 = 对方要我做模型训练/微调，而我确实没做过
TRAIN_REQ = ("模型训练", "微调", "预训练", "训练模型", "sft", "lora", "蒸馏", "精调")


def _ensure_boundary(atoms, jd):
    """JD 要求里写了「模型训练/微调」，正文就必须有一段如实说明没做过。

    这是**真实性硬规则**，不是差异化技巧：
    示例大厂K「ai实习生」JD 写的是「参与AI相关技术的开发与实现，协助完成模型训练与测试」——
    我没做过模型训练，正文里不写清楚就是隐瞒，HR 技术面一问就穿。

    插到第 2 位（lead 之后）：组装时「第 2 段」是无条件保留的（超长也留，
    规则是 `used >= 2` 才跳过），保证边界声明一定发得出去。
    """
    if any(a[0]["id"] == "ai_notrain" for a in atoms[:2]):
        return atoms
    body = _jd_body(jd).lower()
    if not any(k in body for k in TRAIN_REQ):
        return atoms
    by_id = {a["id"]: a for a in ATOMS}
    na = by_id.get("ai_notrain")
    if not na:
        return atoms
    matched = [(c, 1.0) for c in na["kws"] if c.lower() in jd.lower()] or [("模型训练", 1.0)]
    item = (na, 3.0, matched)
    if len(atoms) < 2:
        return [item] + atoms
    return [atoms[0], item] + atoms[1:]


def build_main(target, jd, idx, avoid_lead=None, used_pairs=None, variant_ctr=None):
    """生成主推版正文（多行）。

    avoid_lead：同一公司前面已经用过的 lead 原子 id。
    同一批里同一个 HR 挂了多个岗位时（如「示例文旅W」三个 AI 全栈岗都是同一个人），
    如果证据组合撞车，HR 会收到几条几乎一样的招呼话——直接看着像群发。
    所以把已用过的 lead 原子压到最后，逼它换一个证据组合。

    used_pairs：整批已用过的「lead+次要原子」组合（批次级去撞车）。
    17 个岗位里有 4 个都是 py_web+ai_api，话术两两相似度最高冲到 0.66——
    同一个 HR 同时收到两条不同岗位的招呼，会觉得是群发。
    所以同一组证据组合在一批里只用一次，后面遇到就顺位往后挑。

    target['force_atoms']：指定必须出现在话术里的证据原子 id。
    通用打分按「命中词多的原子」取胜，但 JD 写死主语言时（如「熟悉 Python 语言」）
    会输给「排错/异常」这类原子——这时用 force_atoms 把语言证据顶上来。

    variant_ctr：各原子在整批里已被采用过的次数，用来轮换同一原子的
    不同真实表述（见 ATOM_TEXT_VARIANTS）。
    """
    jd_low = jd.lower()
    if variant_ctr is None:
        variant_ctr = Counter()
    atoms = match_atoms(jd, target.get("position", ""))
    forced = target.get("force_atoms") or []
    if not forced and target.get("req_lang"):
        # JD 写死了单一主语言 → 把该语言的证据顶上来
        aid = {"python": "py_web", "java": "can_stack",
               "typescript": "game_fe"}.get(target["req_lang"])
        if aid:
            forced = [aid]
    if forced:
        by_id = {a["id"]: a for a in ATOMS}
        f_atoms = []
        for fid in forced:
            a = by_id.get(fid)
            if not a:
                continue
            matched = [(c, 1.0) for c in a["kws"] if c.lower() in jd_low] or [(a["kws"][0], 1.0)]
            f_atoms.append((a, 9.0, matched))
        if f_atoms:
            atoms = f_atoms + [a for a in atoms if a[0]["id"] not in forced]
    atoms = _ai_lead_fix(atoms, target.get("position", ""), forced=forced)
    if avoid_lead:
        atoms = sorted(atoms, key=lambda x: (x[0]["id"] == avoid_lead, -x[1]))
    if used_pairs:
        # 整批去撞车：把「组合已用过」的原子往后压。
        # 只在得分接近时才换（阈值取 lead 的 80%）——匹配度优先。
        # 实测：示例企业64 ai_api 5.90 / gen_aicode 5.70（并列，换谁都贴）；
        #       示例企业48 ai_api 6.90 / gen_boundary 5.70（边界证据也贴，正好错开）。
        def _pair_key(a, b):
            return (a[0]["id"], b[0]["id"])
        n = len(atoms)
        # 强制原子（语言硬要求）被打到 9.0 分，不能拿它当阈值基准，
        # 否则阈值被抬到 7.2，所有次要原子都被挡在门外，一批同方向的岗位只能撞车。
        forced_ids = set(forced)
        real_sc = max((a[1] for a in atoms if a[0]["id"] not in forced_ids),
                       default=atoms[0][1])
        limit = real_sc * 0.80
        # 第二原子的门槛比第一原子宽：正文第一段（lead）才是重点，
        # 第二段只要别太离谱就行。原来两个原子用同一个 0.80 门槛，
        # 结果 5 个 py_web/ai_api 岗位的 (lead, second) 全被判成「没有可用组合」，
        # 只能原样保留 → 正文两段一字不差。
        limit_b = real_sc * 0.50
        # 第一轮：找「(lead, second) 没用过」的组合
        picked = None
        for k in range(n):
            a = atoms[k]
            b = atoms[(k + 1) % n]
            # 注意这里用 continue 不是 break：某个位置的分数偏低不代表后面就没有
            # 更合适的位置（原来 break 会直接放弃，5 个 py_web/ai_api 岗位因此撞车）。
            if a[1] < limit or b[1] < limit_b:
                continue
            if _pair_key(a, b) not in used_pairs:
                picked = k
                break
        if picked is not None:
            if picked:
                atoms = atoms[picked:] + atoms[:picked]
        else:
            # 第二轮：所有 (lead, second) 组合都撞过车 → 保持 lead 不动，
            # 换一个第二原子。前提是这个组合本身在批次里已经出现过 ≥2 次
            # （第 1、2 次允许重复：匹配度比差异度重要）。
            lead = atoms[0]
            rest = [a for a in atoms[1:] if a is not lead]
            for cand in sorted(rest, key=lambda x: -x[1]):
                if cand[1] < limit_b:
                    break
                key = _pair_key(lead, cand)
                if used_pairs.get(key, 0) >= 2:
                    atoms = [lead, cand] + [a for a in atoms[1:] if a is not cand]
                    break
    # 边界声明放在去撞车之后插入：插入会改变 (lead, second) 组合，
    # 如果放在前面，会把去撞车的结果搅乱。
    atoms = _ensure_boundary(atoms, jd)
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
        # 同一原子的多种真实表述轮换：证据一样，但说法不一样。
        # 5 个 py_web/ai_api 岗位用同一套原子时，正文两段一字不差就太像群发。
        texts = ATOM_TEXT_VARIANTS.get(a["id"]) or [a["text"]]
        vi = variant_ctr[a["id"]] % len(texts)
        variant_ctr[a["id"]] += 1
        line = f"**【{lbl}】**{texts[vi]}"
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
    used_pairs = Counter()  # 整批已用过的「lead+次要」原子组合 → 次数（批次级去撞车）
    company_n = Counter()  # 公司 → 已生成份数
    variant_ctr = Counter()  # 各证据原子已被采用次数（轮换同义表述）
    start_idx = int(os.environ.get("GD2_START_IDX", "0"))
    no_overwrite = os.environ.get("GD2_NO_OVERWRITE", "") == "1"
    for i0, t in enumerate(targets):
        i = i0 + start_idx
        jd = (jds.get(t["label"]) or {}).get("jd", "")
        if len(jd) < 120:
            missing.append(t["label"])
            continue
        comp = t.get("company", "")
        avoid = company_lead.get(comp)
        main_txt, used, atom_ids = build_main(t, jd, i, avoid, used_pairs, variant_ctr)
        short_txt = build_short(t, jd, i)
        if atom_ids:
            company_lead.setdefault(comp, atom_ids[0])
            _k = (atom_ids[0], atom_ids[1] if len(atom_ids) > 1 else "")
            used_pairs[_k] = used_pairs.get(_k, 0) + 1
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
        # 密度阈值 2 会漏掉「熟练使用 AI 编程工具，并对生成结果进行独立验证」这类
        # 只有一处提到、但明显是硬要求的写法（示例科技P AI应用开发）——单独判一次。
        aic_hard = bool(re.search(
            r"(熟练使用|熟练运用|能够使用|必须会|会用|使用)\s*"
            r"(ai\s*编程工具|ai\s*开发工具|claude\s*code|cursor|codex|copilot|trae)",
            jd_low))
        imgs = IMGS_AICODE if (aic >= 2 or aic_hard) else IMGS_GENERIC
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
        if no_overwrite and os.path.isfile(os.path.join(d, "新建 文本文档.txt")):
            # 已投递批次的话术归档不能被覆盖：归档必须等于实际发出去的内容
            print(f"  = {folder[:44]:<46} 已存在，跳过（不覆盖）")
            continue
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
    print(f"→ {os.path.join(WORK, report_name)}")
    print(f"→ {os.path.join(WORK, final_name)}（投递用）")


if __name__ == "__main__":
    main()
