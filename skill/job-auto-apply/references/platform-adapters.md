# 平台适配器 · 现状与轮子清单

> 更新时间 2026-10-23。平台策略会变，接入前先复核本表；带「已验证」的是本机跑通过的。
>
> **本文件的作用**：前两节（各平台现状 + 现成轮子）是**扩展参考**——
> 用来判断「要不要接一个新平台、要不要自己写适配器」；
> 二·六是 **51job 实战手册**（51job 在本 skill 支持范围内，要用的时候翻）。
> **本 skill 只支持 BOSS 直聘 与 前程无忧 51job 这两个平台。**

## 一、各平台现状（2026-10 公开信息）

| 平台 | 支持范围 | 入口 | 投递形态 | 现状 / 限制 | 本机状态 |
|---|---|---|---|---|---|
| BOSS直聘 | ✅ **支持** | `zhipin.com` | 站内「立即沟通」→ 消息页发话术 + 传图 | 打招呼有每日上限（公开信息称约 150 次/日）；高频会被风控踢登录态 | **已验证**，14/14 送达、14/14 核对合格 |
| 前程无忧 51job | ✅ **支持** | `51job.com` | 投简历（在线/附件），**无话术框、无站内聊天** | 投递有上限、限制搜索结果数量；社区评价「已经烂掉了」，但实测产出不差（见二·六）；作者给的土办法是投一页停 10 秒 | **已验证**，28 条投递 + 在线简历填满 + 28 张 HR 沟通二维码 |
| 猎聘 | ❌ 扩展 | `liepin.com` | 站内打招呼 | 默认打招呼无上限、**主动发消息有上限**；需在手机 App 设置打招呼语，否则不发送；只支持微信扫码登录 | 适配器待写 |
| 智联招聘 | ❌ 扩展 | `zhaopin.com` | 投简历（在线/附件） | 上限约 100；**必须先指定默认投递简历**否则投递失败 | 适配器待写（**优先级最低**） |
| 58同城 | ❌ 扩展 | `qy.58.com` | 站内沟通 | 有 Python 实现可参考 | 适配器待写 |
| 牛客网 | ❌ 扩展 | `nowcoder.com/jobs/search` | 站内沟通 / 投递 | **没有现成投递轮子**（只有题目/面经的 MCP）；实习岗位密度低于 BOSS | 适配器待写 |
| 实习僧 | ❌ 扩展 | `shixiseng.com` | 投简历 | 有 Python 实现可参考 | 适配器待写 |
| 脉脉 | ❌ 扩展 | `maimai.cn` | 站内沟通 | 有 Python 实现可参考 | 适配器待写 |

**「支持」= 有适配器、全链路跑通、开箱即用。「扩展」= 没有适配器，接它是新开发任务。**

**排序建议**（2026-10-23 更新）：猎聘 > 牛客 ≈ 58 > 实习僧 ≈ 51job > 智联。
51job 的公开评价很差，但实测是**唯一稳定产出 AI 实习岗**的来源
（单批扫出 76 个候选、投出 28 条、HR 有实际查看/回复动作），已跑通，优先级上调；
智联仍待写。**平台口碑只决定「先做哪个」，不决定「能不能做」。**

## 二、现成轮子（接平台前先看这里，别重复造）

> **顺序提醒**：先翻本地 `marvis\scripts\wb_*.py` —— BOSS 与 51job 的适配器**已经跑通**，
> 投这两个平台根本不需要往下看。**下面这张表是「本地没有的平台」才需要的。**

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

## 二·六、51job 实战适配（2026-10-23 全链路跑通 · **支持范围内，日常按这里做**）

平台 `51job.com`。实现见 `marvis\scripts\wb_51job*.py`（126 个脚本），
独立私有仓 `https://github.com/3155498108/job51-assistant`。

### 平台形态（与 BOSS 完全不同，接之前必须先知道）

| 事实 | 说明 |
|---|---|
| **没有站内文字聊天** | 简历中心 / 旧版简历中心 / 我的51Job / 记录页 / 岗位详情页 / 搜索页 / 投递附件弹窗，7 个入口实测都没有 textarea、contenteditable、iframe |
| **沟通渠道只有微信扫码** | 「立即沟通」= `jobs.51job.com/ajax/getqr_code.php?jobid=…&hruid=…&ctmid=…` |
| **投递是一键直达** | 点「投递」即提交，无话术框、无二次确认；提交后系统自动弹「选择需要同步发送的附件简历」 |
| **在线简历是主简历** | HR 点开后的默认视图。表单是 Element UI 内联卡片，日期下拉必须 CDP 真实鼠标，且「项目时间」必填否则不保存 |
| **校招网申投不了** | 来源字段 `src == "网申"` 的岗位，点「立即投递」只弹「即将跳转应届求职生平台」，要去 `campus.51job.com` |

### 关键 DOM 与接口

- 记录页 `i.51job.com/userset/my_apply.php`，行 `.gtbox`；岗位 `a.zhn`、公司 `a.gs`、区域 `span.dq`；
  HR 名 / 职位 / 动态 = `.init_fixed` 内的 `.iname` / `.itag` / `.ilabel`；沟通码 = `img.icode` 的 `src`
- 翻页是普通链接 `?lang=c&type=sh&tagType=all&page=N`（每页 15 条），**没有「下一页」按钮**
- 在线简历走内部 API（比填表单可靠得多）：
  `POST /open/resumes/{id}/self-introduction`（个人优势）、`/open/personal-skill/edit`（技能经验）、
  `/open/resumes/{id}/projects`（项目经历）、`/open/resumes/{id}/school-awards`、
  `/open/resumes/{id}/language`、`/open/resumes/{id}/attachments/url`（作品链接）、
  `/open/resumes/{id}/attachments/file`（作品集）
- 浏览器里调用：`document.querySelector('#app').__vue__` 按 `$options.name` 遍历 `$children`
  定位组件，再 `pc.$api.resumeApi.<method>(...)`（返回 Promise）
- 作品集槽位只收 PDF（5K–20M、仅一份）；它与「附件简历」是两回事：
  附件简历跟投递一起发，作品集在简历页常驻展示

### 十二个实测坑

| # | 坑 | 后果 / 修法 |
|---|---|---|
| 1 | **必须把附件弹窗选对并点「发送」，投递才算真正提交** | 选错（点到弹窗标题）不报错，但记录页里不会出现这条记录 |
| 2 | **弹窗里的附件选项是异步渲染的** | 先出 `<!---->` 占位，必须轮询等待 |
| 3 | 选完要等 **≥2.5s** 再点「发送」 | 等 `cvLogId` 落库，太早会被服务端拒 |
| 4 | **同一岗位只能发一次附件** | 重发返回「发送附件简历失败」——不是没发出去，是重复添加被拒 |
| 5 | **附件简历文件名必须纯 ASCII** | 中文名时 CDP 能挂上文件但组件发不出任何请求（零网络日志），页面毫无反应 |
| 6 | 上传后必须点「确认添加」才入库 | 且要用 JS `.click()`，CDP 坐标点击无效；大小限制 5KB–8MB |
| 7 | **校招判定必须在点之前做** | 只查弹窗文本会把 5 个正常岗位误判成校招，而「立即投递」已经点下去、系统已记为已投 → 脚本说失败、平台说成功，两边账对不上 |
| 8 | 校招弹窗关闭后元素仍留在 DOM 里 | 判断可见性要同时看 `offsetWidth/offsetHeight` 与 computed style |
| 9 | **详情页滑动验证是账号级的** | 连访约 13–15 次触发；`/all/` 与 `/<城市>/` 两种路径都拦，换 session 也可能被关联。**要用户人工过滑块**，不要程序化绕过 |
| 10 | **不要访问 `login.51job.com`** | 会冲掉登录态 |
| 11 | 记录页翻页不是按钮 | 是普通链接 `?page=N`，找「下一页」选择器会白找 |
| 12 | 在线简历表单用 Element UI 日期下拉 | JS `.click()` 展开不了，必须 CDP 真实鼠标；不选「项目时间」点「完成」必填校验不过。**直接调 API 更省事** |

### 投完怎么核对

51job 没有「会话里有没有话术」这回事，核对口径完全不同：

> **送达 = 记录页「我的申请」出现这一条**（`i.51job.com/userset/my_apply.php`）。

- 记录页是**权威口径**，各批次结果文件只用来补「附件简历同步状态」。
- 每条记录上能读到 HR 姓名与动态（`本周查看简历4次`、`27分钟前处理简历`），
  **这能直接证明简历被看到了**，比任何脚本自报成功都硬。
- 附件绑定状态看 `modify-attach-resume` 的回执 `{"status":"1"}`；
  同岗位重复调用会返回「发送附件简历失败」，所以**批量脚本看到这句反而说明第一次已发成功**。

## 二·七、58 同城的额外风险（扩展参考，不在支持范围）

58 的岗位来源杂，自动化前要额外收紧：

- 公司名命中「人力资源 / 劳务派遣 / 招聘中介 / 职介」→ 直接劝退
- JD 命中「无责底薪 / 高提成 / 拉人头 / 日结 / 小时工」→ 直接劝退
- 「熟悉办公软件 / 会基本打字 / 接受小白」→ 非技术岗，劝退
- 「立即沟通 / 投递简历 / 在线聊」三种入口并存，先探测清楚目标岗位走哪条，再写适配器

第一版建议只做**只读采集 + 筛选 + 生成话术**，投递留人工点；猎聘跑顺后再开自动。

## 三、写适配器的统一形状（扩展开发用）

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

## 四、首次接入某平台的探测顺序（扩展开发用）

> 本节只服务于**扩展平台**。BOSS 与 51job 的投递形态都已实测确认，不需要再探。

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
