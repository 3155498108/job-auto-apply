# job-auto-apply · 多平台招聘自动投递

把「在招聘平台上批量投递」固化成一条可复用流水线：
**抓 JD → 按 JD 生成差异化话术 → 浏览器投递 → 逐个核对 → 写回记录**。
新接一个平台 = 写一个平台适配器，其余环节复用。

> 公开仓库。脚本与流程公开，个人求职画像、简历、话术归档**不在本仓库内**。

---

## 目录结构

```
job-auto-apply/
├── skill/job-auto-apply/          ← 新写的 skill（多平台版）
│   ├── SKILL.md                       流程 / 输入 / 输出契约 / 失败处理 / Windows 适配
│   └── references/
│       ├── onboarding.md                新人第一次用：前置条件 / 环境自检 / 端到端走查
│       ├── platform-adapters.md        各平台现状 + 现成轮子清单 + 适配器接口
│       ├── greeting-engine.md          证据原子模型 + 差异化量化验收
│       ├── safety-checklist.md         七道安全闸 + DOM 陷阱 + JD 劝退词表 + 上游踩坑六条
│       ├── second-touch.md             第二次触达（未读会话补发）实测手册
│       └── upstream-pitfalls.md        上游 34 条实战坑位全记录（改脚本/换平台时查）
└── marvis/                          ← 自动化脚本工程（上游基座 + 本地演进）
    ├── SKILL.md                        上游原版 skill（v1，单平台）
    ├── references/                     上游文档，含 pitfalls.md（34 条实战坑位）
    ├── scripts/                        164 个脚本
    ├── user_profile.json               求职画像（活数据，会被自动读取）
    ├── greetings.json                  打招呼语模板（活数据）
    └── boss_applied.json               已投记录
```

## 来源与致谢

本工程基于公开仓库 **[taohuajianxian/boss-zhipin-assistant](https://github.com/taohuajianxian/boss-zhipin-assistant)**
（作者提供的基础投递框架与 34 条踩坑记录）演进而来。`marvis/` 下保留了上游的
`SKILL.md` 与 `references/` 原文，本地在此之上做了大批扩展。

本地新增/重写的部分：

| 内容 | 说明 |
|---|---|
| `skill/job-auto-apply/` | 全新 skill。补齐了上游没有的「按 JD 定制话术」「多平台适配」「量化验收」三块 |
| `scripts/wb_jd.py` | 抓 job_detail 的 JD 全文 |
| `scripts/jd_filter.py` | 基于 JD 职责/要求两段做硬性劝退 |
| `scripts/jd_screen.py` | JD 内容风险标签扫描（人工复核用） |
| `scripts/gen_jd_msg.py` | 证据原子 + 确定性组合的话术生成器 |
| `scripts/diff_report.py` | 差异化度量（字符 3-gram Jaccard） |
| `scripts/wb_cross.py` / `wb_fav_check.py` | 通用投递链路 + 送达核对（清单与前缀走环境变量） |
| `scripts/wb_deliver_batch.py` | 按 `final.json` 批量投递（岗位名/公司名双校验 + 简历图上传 + 逐个核对） |
| `scripts/wb_verify_batch.py` | 独立复核：重开消息页逐个点开会话重数话术条数与简历图张数 |
| `scripts/wb_resend.py` | 第二次触达：给「已投但对方未读」的会话补发（四道闸 + 断点续跑 + 登录态守卫） |
| `scripts/wb_conv_states.py` | 会话状态全量收集（虚拟滚动：`.user-list-content` + 派发 scroll 事件） |
| `scripts/match_unread.py` / `gen_resend.py` | 未读候选筛选（含投递天数分层）+ 第二次触达话术生成 |
| `scripts/scan_gd.py` / `gen_gd.py` / `gen_gd2.py` | 按城市扫描与选岗 |
| `scripts/gh_count.py` | 核对 GitHub 仓库数与 commit 数 |
| `scripts/fix_github_claim*.py` | 更正话术里过时的 GitHub 数字 |

上游 `assets/`（作者赞赏码）与 `workbuddy/`（另一智能体平台的变体）**没有**复制进本仓库。

## 安装 skill

把 `skill/job-auto-apply/` 整个目录复制到智能体的 skills 目录下即可：

```
YOUR_HOME\.minimax\skills\job-auto-apply\
```

装完用自然语言触发，例如「猎聘也接上自动投递」「这批投递核对一下」「话术别一套模板」。

## 跑起来需要什么

1. **Chrome/Edge 浏览器 + Kimi WebBridge 扩展**（浏览器操控全部走 WebBridge，不用 Selenium/Playwright）
2. **提前在浏览器里手动登录**目标平台的账号
3. Python 3.14（本机 `python` 即是）
4. 简历与归档目录 `YOUR_HOME\`（简历 PDF、截图、话术三件套、`投递记录.md`）
   —— **不在本仓库内**，属个人材料

## 安全阀（投递是对外可见、不可撤回的操作）

七道闸一道不少，详见 `skill/job-auto-apply/references/safety-checklist.md`：

1. 登录态自检（进详情页、进消息页各查一次；被风控踢到登录页就立即停批）
2. 详情页岗位名校验
3. 消息页岗位名校验
4. 幂等跳过（会话里已有含本人标识的话术就跳过）
5. 正文含内部说明词则拒绝发送
6. 发送键轮询（等 Vue 摘掉 `disabled`）
7. 投递间隔 ≥ 6 秒

外加：Vue Router 缓存劫持每 5 次导航重置、SPA 渲染残留校验、
致命弹窗先检测再关闭、PID 锁防僵尸进程、排除词分 T/C/B 三档。

## 核对口径

> **送达 = 会话内有含本人标识的话术 + ≥2 张简历图**，且头部岗位名与目标对位。
> 岗位名前后缀差异只作备注，不算失败。

## 事实纪律

话术与画像里的每个数字都要能核实。会变的数据（GitHub 仓库数 / commit 数等）
用 `scripts/gh_count.py` 重新实测，不要沿用旧值。当前基准：

- 某网页小游戏合集（目录数与清单条数双向差集为空，双向差集为空）
- 两百余个 TS 文件 / 数万行 / 数十个 Vitest 测试文件（`count_lines.py` 实测）
- 某电商交易后端：18 个 Controller / 70 个 RESTful 接口 / 11 张业务表
- 某 AI 客服：5 个 RESTful 端点 / CompletableFuture 异步 + 30 秒超时 / 异常隔离 / 1–3 秒 / < 50 毫秒
- GitHub：若干个公开仓库 / 多次提交（`gh_count.py` 实测，非 fork 仓库）
