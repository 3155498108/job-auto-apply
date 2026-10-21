# 平台适配器 · 现状与轮子清单

> 更新时间 2026-10-21。平台策略会变，接入前先复核本表；带「已验证」的是本机跑通过的。

## 一、各平台现状（2026-10 公开信息）

| 平台 | 入口 | 投递形态 | 现状 / 限制 | 本机状态 |
|---|---|---|---|---|
| BOSS直聘 | `zhipin.com` | 站内「立即沟通」→ 消息页发话术 + 传图 | 打招呼有每日上限（公开信息称约 150 次/日）；高频会被风控踢登录态 | **已验证**，14/14 送达、14/14 核对合格 |
| 猎聘 | `liepin.com` | 站内打招呼 | 默认打招呼无上限、**主动发消息有上限**；需在手机 App 设置打招呼语，否则不发送；只支持微信扫码登录 | 适配器待写 |
| 前程无忧 51job | `51job.com` | 投简历（在线/附件） | 投递有上限、限制搜索结果数量；社区评价「已经烂掉了」；作者给的土办法是投一页停 10 秒 | 适配器待写（**优先级最低**） |
| 智联招聘 | `zhaopin.com` | 投简历（在线/附件） | 上限约 100；**必须先指定默认投递简历**否则投递失败 | 适配器待写（**优先级最低**） |
| 58同城 | `qy.58.com` | 站内沟通 | 有 Python 实现可参考 | 适配器待写 |
| 牛客网 | `nowcoder.com/jobs/search` | 站内沟通 / 投递 | **没有现成投递轮子**（只有题目/面经的 MCP）；实习岗位密度低于 BOSS | 适配器待写 |
| 实习僧 | `shixiseng.com` | 投简历 | 有 Python 实现可参考 | 适配器待写 |
| 脉脉 | `maimai.cn` | 站内沟通 | 有 Python 实现可参考 | 适配器待写 |

**排序建议**：猎聘 > 牛客 ≈ 58 > 实习僧 > 51job ≈ 智联。
51job/智联的公开评价都很差，投递量与回复率都低，先做猎聘和 58 的性价比更高。

## 二、现成轮子（接平台前先看这里，别重复造）

| 仓库 | 平台 | 技术栈 | 备注 |
|---|---|---|---|
| [loks666/get_jobs](https://github.com/loks666/get_jobs) ★8.4k | BOSS / 猎聘 / 51job / 智联 | Spring Boot + Patchright(Playwright) + SQLite + Next.js | **最值得参考**。一类一文件的平台适配器：`boss/Boss.java`、`liepin/Liepin.java`、`job51/Job51.java`、`zhilian/ZhiLian.java`。作者只维护 BOSS + 猎聘，51job/智联已停维护。AI 自动写打招呼语仅 BOSS 支持 |
| [JasonYANG170/Super_Employee](https://github.com/JasonYANG170/Super_Employee) | 实习僧 / 翼展翅 / BOSS / 脉脉 / 智联 / **58同城** | Python | 58 同城的主要参考。自定义筛选、投到上限、定时投递、通知提醒 |
| [xiaolu1560/Auto-JobHunter](https://github.com/xiaolu1560/Auto-JobHunter) | BOSS / 猎聘 / 51job | FastAPI + LangGraph + DrissionPage | 「抓取 → 入库 → LLM 评估 → 投递」的分层结构可借鉴 |
| [gototrip1/Automated-resume-submission-Agent](https://github.com/gototrip1/Automated-resume-submission-Agent) | BOSS / 实习僧 / 猎聘 | LangGraph，本地部署 | 它的 AGENTS 文档里有两条纪律值得抄：**站点 Adapter 先 mock 后真站**；**投递动作在用户确认前默认 dry_run** |
| [Bochi07/boss_Automatic-resume-submission](https://github.com/Bochi07/boss_Automatic-resume-submission) | BOSS | 油猴脚本 + Python 后端 | 按标题 + JD 内容自动打分筛选，达标自动打招呼 |
| [yangshengzhou03/Jobs_helper](https://github.com/yangshengzhou03/Jobs_helper) | BOSS | 油猴脚本 | XPath 解析 + GM_xmlhttpRequest + localStorage 去重 |
| [joohw/boss-cli](https://github.com/joohw/boss-cli) | BOSS | Node + Puppeteer/CDP | 命令行形态，CDP 驱动本机 Chrome（与本机 WebBridge 思路接近） |
| [goehou/boss-helper](https://github.com/goehou/boss-helper) | BOSS | userscript | 带测试夹具 |
| 牛客 | `nowcoder-mcp-server` | Node + Playwright | **只做题目/面经检索，不是投递**；牛客投递需要从零写适配器 |

**怎么用这些轮子**：
- 它们的浏览器驱动是 Playwright/DrissionPage/Puppeteer，本机走的是 **Kimi WebBridge**，
  不能直接换驱动复用代码，但**页面流程与选择器可以直接照抄**。
- 它们的 AI 写话术是让 LLM 自由生成；本项目用**证据原子 + 确定性组合**（见
  `greeting-engine.md`），可复现、可审计、零幻觉、零 API 成本，**不要换回去**。

## 二·五、本机代码的平台耦合度

2026-10-21 实测：`marvis\scripts\` 下匹配 `zhipin|liepin|58\.com|猎聘|58同城`
共 **118 处 / 72 个文件**；其中 `liepin`、`58` **零命中**（纯新增）。

| 处置 | 内容 |
|---|---|
| 新平台 | 写**独立脚本**（`wb_liepin.py` / `wb_58.py`），不要去改那 72 个文件里的零散分支 |
| 要共用 | 只有四块：话术引擎、JD 归一、核对口径、记录写回。抽出来复用 |
| 不做 | 别为了接新平台去整体重构 `marvis\scripts\`——收益低、回归风险大 |

## 二·七、58 同城的额外风险

58 的岗位来源杂，自动化前要额外收紧：

- 公司名命中「人力资源 / 劳务派遣 / 招聘中介 / 职介」→ 直接劝退
- JD 命中「无责底薪 / 高提成 / 拉人头 / 日结 / 小时工」→ 直接劝退
- 「熟悉办公软件 / 会基本打字 / 接受小白」→ 非技术岗，劝退
- 「立即沟通 / 投递简历 / 在线聊」三种入口并存，先探测清楚目标岗位走哪条，再写适配器

第一版建议只做**只读采集 + 筛选 + 生成话术**，投递留人工点；猎聘跑顺后再开自动。

## 三、写适配器的统一形状

照 `marvis\scripts\wb_cross.py`（BOSS，已验证）写。每个平台一个文件，至少提供：

```python
# 平台标识
BASE = "https://www.<site>.com"
SESSION = "<site>-main"          # WebBridge session 名，与其它平台错开

# 1) 列表：怎么翻页、卡片长什么样
def list_jobs(city, keyword, page) -> list[dict]      # 返回 jobId/company/title/salary/city

# 2) JD 全文：从详情页取正文
def fetch_jd(job_id) -> str                            # 多选择器回退 + 整页截取兜底

# 3) 筛选：能不能投（基于 JD 正文，不基于标题）
def screen(jd_text, title) -> (bool, str)              # (是否可投, 劝退理由)

# 4) 投递：入口在哪、要不要话术、附件怎么传
def apply(job, greeting, attachments) -> dict          # {status, detail}

# 5) 核对：投递后从哪个 DOM 读回执
def verify(selector) -> dict                          # {greeting_count, br, images, position_name}
```

**环境变量统一**（与 BOSS 保持一致，方便同一套脚本跑不同平台）：

```powershell
$env:BOSS_TARGETS_FILE = 'liepin_targets.json'
$env:BOSS_PREFIX = 'liepin'
python "YOUR_REPO\marvis\scripts\wb_liepin.py"
```

## 四、首次接入某平台的探测顺序

**第 0 步：先探「投递形态能不能自动化」——这一步决定后面是全自动还是半自动。**

猎聘的「打招呼语」按官方规则要在手机 App 里设置，网页端可能不允许发自定义文本。
所以第一个要确认的不是选择器，而是：**在网页端点「立即沟通」之后，聊天窗里到底能不能填自定义话术。**

- 能填 → 全自动，话术引擎直接接上去；
- 不能填 → 降级成**半自动**：自动筛 + 自动按 JD 生成话术，发送环节由用户复制到 App 完成。

这一步探错了，后面整套适配器写法都要重做，所以放在最前面。

之后的步骤：

1. 用 WebBridge 打开列表页 → `evaluate` 打印卡片 HTML，**从真实 DOM 里抄选择器**，
   不要照抄网上博客的选择器（站点改版频繁）
2. 打开一个详情页 → 找到 JD 正文容器，打印它的 `innerText` 长度确认抓到了
3. 找到投递入口按钮（文案可能是「立即沟通」「打招呼」「投递简历」「申请该职位」）
4. 打印消息页/投递后的 DOM，找到「我发出的内容」「附件」所在的容器
5. **先只做 1 个岗位的 dry run**：不发消息，只把流程走通并把每步的选择器 dump 出来
6. 确认无误再投 3 个，最后才扩量
