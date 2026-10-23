# 新人第一次用这个 skill · 完整走查

> 面向第一次拿到这个 skill、机器上什么都还没有的人。
> 目标：**在不踩坑的前提下，先投出第一批 3 个岗位**，再谈扩量。

---

## 零、先搞清楚这是什么

一句话：**它不是一个「网页脚本」，它是一套「在你自己已登录的浏览器里，替人做投递动作」的流程。**

- **支持范围只有两个平台**：**BOSS 直聘** 和 **前程无忧 51job**（都已跑通全链路）。
  猎聘 / 智联 / 58 / 牛客**没有适配器**，那属于扩展开发，不是开箱即用。
- 浏览器操控走 **Kimi WebBridge**（本机 `http://127.0.0.1:10086`），
  不是 Selenium / Playwright —— 复用你**真实登录态**的浏览器标签页。
- 所以你必须自己装扩展、自己登录账号，脚本**拿不到**你的账号密码。
- 投递是**对外可见、不可撤回**的操作：HR 会真的收到消息。
  **没有明确授权，流程就停在「材料已备好」这一步。**

---

## 一、前置条件清单

| # | 要什么 | 怎么确认 | 缺了会怎样 |
|---|---|---|---|
| 1 | Chrome / Edge | 打开 `chrome://version` | 没有浏览器 = 没有可操控的标签页 |
| 2 | **Kimi WebBridge 扩展** | 浏览器里已安装且已连接 | 脚本连不上，页面全是「加载不出来」 |
| 3 | WebBridge daemon | `kimi-webbridge.exe status` → `running: true` | 同上 |
| 4 | 目标平台**已登录** | 浏览器里能正常打开消息页 | 会被风控踢到登录页 |
| 5 | Python 3.x | `python --version` | 脚本跑不起来 |
| 6 | 本仓库 | `git clone https://github.com/3155498108/job-auto-apply` | 没有脚本 |
| 7 | 个人材料（简历/话术/清单） | 见第二节 | 没有就写不出差异化话术 |

**第 2、3 项只能由人装**，agent 没法替你点浏览器。

---

## 二、环境自检（这一步别跳）

### 2.1 看状态

```powershell
& "$env:USERPROFILE\.kimi-webbridge\bin\kimi-webbridge.exe" status
```

正常长这样：

```json
{"extension_connected":true,"extension_version":"2.0.24","port":10086,
 "running":true,"skills":[...],"tab_id_arg":true,"uptime_seconds":21538,
 "version":"v2.0.26"}
```

### 2.2 逐字段对照

| 字段 | 期望值 | 不对时的动作 |
|---|---|---|
| `running` | `true` | `& "...\kimi-webbridge.exe" start` |
| `extension_connected` | `true` | 见 2.3，**要用户手动修** |
| `port` | `10086` | 端口冲突就换一个，并改 `wb.py` 的 `BASE` |
| `skills` | 数组里能看到**本 agent** | 决定走 A 还是 B 路径（2.4） |
| `tab_id_arg` | `true` | 多标签页时要给每个 action 带 `tabId` |

### 2.3 扩展没连上怎么办（用户手动做）

1. `chrome://extensions` → 右上角开「开发者模式」
2. 安装扩展：扩展包在 `~/.kimi-webbridge/`（或官方渠道拿）
3. 点扩展图标 → 显示已连接
4. 重跑 `status`，确认 `extension_connected: true`

> **daemon 在跑 ≠ 扩展在连。** daemon 是本地 HTTP 服务，扩展是浏览器端注入。
> 只看 `running: true` 就开跑，会在第一次 `evaluate` 时才炸。

### 2.4 两条驱动路径

**A. 本 agent 装了 kimi-webbridge skill**（`status.skills` 数组里能看到本 agent）：
直接用 skill 的 CLI 驱动。

**B. 本 agent 没装 skill**（实测 MCode：`~/.minimax/skills/kimi-webbridge` 不存在，
只有 `~/.claude` / `~/.codex` 有）：走 HTTP API，`marvis/scripts/wb.py` 已封装：

```python
import sys; sys.path.insert(0, r"<repo>\marvis")
from scripts.wb import call, evaluate, navigate

call("list_tabs", {})                      # 看有哪些标签页
print(evaluate("location.href"))          # 执行 JS
call("navigate", {"url": "https://www.zhipin.com/web/geek/chat"})
```

要点：

- 请求体是 JSON，**含中文时必须写临时文件再用 `curl.exe --data-binary "@file"` 发送**
  （`wb.py` 已封好。别自己手拼 curl —— PowerShell 会破坏内联 JSON 里的中文）
- 每个 `call()` 有 `session` 参数（默认 `"boss-main"`），**不同任务用不同 session**
- **同一个标签页不能并行跑两个任务**。要两个平台同时跑，就用两个 session 指向两个标签页
- 没有 `reload` 动作，用 `evaluate("location.reload()")`

### 2.5 查账号

```powershell
python <repo>\marvis\scripts\env_check.py
```

它一次查四件事：daemon 可达 → 标签页可交互 → 目标平台已登录 →
本地 `user_profile.json` 与登录账户的**用户名 / 城市**是否对得上。

> `env_check.py` 里 `evaluate("1+1")` 返回 `"2"`，本身就是「扩展已连接」的证明
> —— 要执行 JS 必须经过扩展。

**登录态被踢**（跳 `/web/user/` 或出现二维码）→ **立即停批**，让用户扫码重登。
症状会伪装成「消息页加载不出来」，很容易误判成脚本坏了。

---

## 三、要准备的文件

```
<你的工作目录>/
├── 招聘/
│   ├── <岗位名>/新建 文本文档.txt     ← 话术（主推版 / 精简版）
│   ├── <岗位名>/*.pdf                 ← 简历 PDF
│   ├── <岗位名>/shot_*.png            ← 简历截图（BOSS 投递时发图）
│   └── boss_manifest.json             ← 机器可读幂等清单
└── output/
    ├── 投递记录.md                     ← 总记录（追加式）
    └── boss_work/                     ← 脚本产物
```

| 文件 | 缺了会怎样 | 怎么补 |
|---|---|---|
| `招聘/<岗位>/新建 文本文档.txt` | `pick_by_company()` 取不到话术 → 回退成通用模板（用户最讨厌的「一套模板」） | 让 Agent 按 JD 生成 |
| 简历截图 `*.png` | 只能发纯文字，转化率明显下降 | 从 PDF 转图（`pdf2png.py`） |
| `boss_manifest.json` | **重复投递**已投过的岗位 | 补齐历史投递记录 |
| `output/投递记录.md` | 这轮没留痕 | 新建 |
| `marvis/user_profile.json` | 话术只能写空话，没有差异化 | 让 Agent 按你的真实经历生成 |

> 目录名**带批次前缀**（`跨城-` / `收藏-` / `广东2-` / `收藏AI-` …），
> 因为 `pick_by_company()` 按**公司名前缀**匹配文件夹，不带前缀会串批。

---

## 四、第一次跑：端到端

### Step 1 · 先问，再动手

**第一次用这个 skill，agent 要先问用户，不要自己拍板。**
投递是对外可见、不可撤回的操作，替用户默认「先投几个试试」是越权。

一次性问完（用问卷，别挤牙膏式一问一答）：

| # | 问题 | 问不到时怎么办 |
|---|---|---|
| 1 | **目标平台**？（BOSS 直聘 / 前程无忧 51job） | 只能问；用户点名别的平台 → 那是扩展开发，先说清楚再动手 |
| 2 | **投递范围**？城市 / 方向 / 岗位关键词 / 大致数量 | 只能问 |
| 3 | **允许我直接发出去吗？** | 只能问，默认「不发送，只准备材料」 |
| 4 | **用哪份简历**？（全量版 / AI Coding 版 / 其他） | 从 `招聘\` 目录读，读不到再问 |
| 5 | **岗位从哪来**？（站内搜索 / 收藏夹 / 给定链接 / 指定 jobId） | 从上下文推 |
| 6 | **投递形态**？（站内打招呼 / 直接投简历） | 本地已有适配器的平台可自己确定 |

**这四件事永远要问，不许自己决定**：投哪个平台、投多少、发不发。

能自己读掉的（不反问）：简历目录在哪、话术目录在哪、记录文件在哪、
目标平台登了没、本地有没有这个平台的适配器。

用户答「你看着办」「随便投」时：**范围**可以自己定（从已有池子里挑），
但**发送前一定要把清单摆给用户看、要一句明确的「发」**——
模糊授权不等于授权。

### Step 2 · 先翻本地适配器，再考虑 GitHub

**这个仓库本身就是那个轮子。** 先看本地已经有什么：

```powershell
Get-ChildItem YOUR_REPO\marvis\scripts\ -Filter 'wb_*.py' |
  Select-Object -ExpandProperty Name
```

| 已有 | 覆盖 | 能干什么 |
|---|---|---|
| `wb_cross.py` / `wb_deliver.py` / `wb_deliver_batch.py` | BOSS | 选岗 → 抓 JD → 筛 → 生成话术 → 投递 → 核对 |
| `wb_jd.py` / `wb_jd3.py` / `wb_resume.py` | BOSS | JD 全文抓取 |
| `wb_scan3.py` / `gen_ai_scan.py` / `gen_fav_ai2.py` / `gen_b3.py` | BOSS | 扫岗与选岗 |
| `wb_msg_time.py` / `wb_fav_check.py` / `wb_verify_batch.py` / `wb_audit_convs.py` | BOSS | 三态指纹核对 / 独立复核 / 逐条审计 |
| `wb_resend.py` | BOSS | 第二次触达（未读会话补发） |
| `wb_51job*.py` | 51job | 一键投简历 + 附件 + 在线简历 + HR 二维码 |

**要投 BOSS 或 51job，到这一步就结束了** —— 直接复用，按参数换目标清单和产物前缀，
不要重写适配器、别再造一遍轮子。

只有目标平台**本地没有**（猎聘 / 智联 / 58 / 牛客…）时，才去 GitHub 搜现成项目 ——
但这属于**扩展开发**，不在本 skill 支持范围内，先跟用户确认清楚再动手。
清单见 `platform-adapters.md`。

**但平台口碑不能直接当结论** —— 51job 在 2026 年的公开评价里被标为「已经烂掉了」，
2026-10-23 实测它却是唯一稳定产出 AI 实习岗的来源。
**接扩展平台前先探一次投递形态，用实测产出而不是公开评价决定优先级。**

### Step 3 · 分叉：走 BOSS 流程 还是 51job 流程

**这一步决定后面 4 步怎么做，别跳过。** 两个平台的投递形态完全不同：

| | BOSS 直聘 | 前程无忧 51job |
|---|---|---|
| 主脚本 | `wb_cross.py` → `wb_deliver_batch.py` → `wb_fav_check.py` | `wb_51job*.py`（独立仓 `job51-assistant`） |
| 有没有话术框 | **有**（消息页 `#chat-input`） | **没有**（7 个入口实测都没有 textarea / contenteditable / iframe） |
| 简历怎么给 | 文字话术 + 2 张简历图（p1/p2） | 「选择需要同步发送的附件简历」弹窗（**选错叶子节点 = 投递没提交**） |
| 投递动作 | 点「立即沟通」→ 消息页发送 | 点「投递」即提交，无二次确认 |
| 核对入口 | 消息页数话术条数 + 图片张数 | 「我的申请」记录页（`i.51job.com/userset/my_apply.php`）数记录 + 查附件回执 |
| 第二次触达 | 支持 | **不支持**（没有站内聊天，只有微信扫码） |
| 主要风控 | 打招呼有每日上限，高频踢登录态 | 详情页连访约 13–15 次触发**滑动验证**（要用户人工过） |

**四块共用**：话术引擎、JD 归一、核对口径、写回。
**各平台独立**：投递动作、简历交付方式、核对入口。

> **形态探测**（确认「网页端能不能填自定义话术」）是**扩展平台**才需要的步骤，
> 见 `platform-adapters.md` 第四节。BOSS 与 51job 的形态都已经实测确认过了。

### Step 4 · 抓 JD → 按正文筛

**岗位标题会骗人。** 必须按 JD 的**职责 + 要求**两段筛，
不要用公司介绍段（全是业务词，会把「做店铺运营的公司」误判成运营岗）。
劝退词表见 `safety-checklist.md`。

**先把 JD 归一成同一份结构再筛**：BOSS 用 `wb_jd.py` / `wb_jd3.py`，
51job 用 `wb_51job.py` 里的 `DUTY_MARKS_51` / `REQ_MARKS_51`
（51job 详情页开头要先剥掉「职位描述 / 竞争力分析 / 微信分享」那行标签栏）。

判不出来的条目**不要猜**：标「未切分」，让打分退化到只按标题命中，比错切可控。

### Step 5 · 生成差异化话术（**只有 BOSS 需要**）

按 JD 生成，不是套模板。核心是**证据原子 + 组合**。
生成完必须跑**差异度量化验收**（`diff_report.py`），给出实测值：

- 开头句去重 == 批大小
- 完全相同的两份 == 0
- 两两相似度均值明显低于旧基线

详见 `greeting-engine.md`。

> **51job 没有话术框，这一步整条跳过。** 51job 的差异化改落在两处：
> ① 在线简历的「个人优势」写成按岗位方向定制的那段；
> ② 附件简历按方向选对版本（ai_agent / java_backend / aicoding 三版）。
> 别在 51job 上死磕「怎么发话术」——平台层面就没有这个输入框。

### Step 6 · 投递（**授权后才做**）

- 「打招呼」「点立即沟通」「发附件」都是对外可见、不可撤回的
- **先把要投的清单摆给用户看，拿到一句明确的「发」再动手**
  ——用户说「你看着办」不算授权
- 全程带**登录态守卫**：URL 命中 `/web/user` / `login` / `passport` 立刻停
- **先投 3 个试跑**，核对没问题再扩量

**BOSS 直聘**：

- 发送间隔 ≥6 秒；批量大时每 15–20 条歇 25 秒
- 链路：详情页 → 校验 → 点「立即沟通」→ 消息页 → 填话术 → 发送 → 传简历图
- 填输入框要用**原生 fill**，之后轮询等 Vue 把 `disabled` 摘掉

**前程无忧 51job**：

- **点「投递」之前**先判校招网申（`src == "网申"`）——点完再判就已经投出去了，账对不上
- 附件弹窗要**选对叶子节点**，选完等 **≥2.5s** 再点「发送」
- 附件简历文件名**必须纯 ASCII**
- 详情页连访约 13–15 次会触发**滑动验证**，要用户人工过一次，**不要程序化绕过**
- 校招网申岗位要去 `campus.51job.com` 单独投

### Step 7 · 核对（**不信脚本自报**）

**BOSS 直聘** —— 回消息页读 DOM 逐个核对：

> **送达 = 会话内有含本人标识的话术 + ≥2 张简历图**，且头部岗位名与目标对位。

要区分「这一轮投的」还是「几天前就投过的」，用话术指纹比对（`wb_msg_time.py`）：

| 判定 | 依据 | 处理 |
|---|---|---|
| `this_batch` 本轮新投 | 会话内我方消息含本批话术指纹 | 写 manifest |
| `older_batch` 历史已投 | 会话里是旧话术，本批指纹不在 | 不重复写，只补 jobId |
| `no_my_msg` 没投出去 | 会话不存在或没有我方消息 | 不写 manifest，进遗留清单 |

**前程无忧 51job** —— 回**「我的申请」记录页**核对（`i.51job.com/userset/my_apply.php`）：

> **送达 = 记录页出现这一条**。没有「会话里有话术」这回事。

- 记录页是**权威口径**，各批次结果文件只用来补「附件简历同步状态」
- 附件绑定状态看 `modify-attach-resume` 回执 `{"status":"1"}`
- 同岗位重复调用会返回「发送附件简历失败」——那是重复添加被拒，**说明第一次已发成功**

### Step 8 · 写回

- `output/投递记录.md` **追加**一节：扫了什么、筛掉了什么（附 JD 原文关键词）、
  话术策略、投递明细表、核对结论、遗留待办
- `招聘/boss_manifest.json` 追加条目
- 三态分流：`sent` 新增 / `already_sent` 只补 jobId / `not_sent` **不写 manifest**

### Step 9 · 汇报

只报**实测数字**：送达几个、合格几个、劝退几个、相似度均值多少。
没核对过的不要说「已验证」。

---

## 五、第一次跑最常犯的错

| 症状 | 真因 | 处理 |
|---|---|---|
| 页面全是「加载不出来」 | 扩展没连 / daemon 没起 / 账号被踢 | 跑 2.1–2.5，先分清是哪一种 |
| `evaluate` 返回值全是 0 / 空 | JS 返回了对象不是 JSON | 改成 `JSON.stringify({...})` |
| 会话只有 40 条 | 虚拟滚动没触发懒加载 | 容器用 `.user-list-content` + 派发 `scroll` 事件 |
| 点会话没反应 | 查元素和 click 不在同一次 evaluate | 合并成一次；点完轮询等选中态 |
| 会话头为空 / 计数全是 0 | `MY_STATE` 返回对象没 stringify | 同上 |
| 话术全是同一个样 | 证据原子选得太像 | 改**原子的选取与组合**，别改模板数量 |
| 中文脚本报 UnicodeEncodeError | PowerShell 是 GBK | `$env:PYTHONIOENCODING='utf-8'`，或脚本内 `reconfigure` |
| `python -c "中文…"` ParseError | 内联代码被 GBK 破坏 | 中文逻辑一律写成 `.py` 文件再跑 |
| 目标平台投出去了但记录里没有 | manifest 里有同公司同岗位但缺 jobId | 用本批 jobId 补齐，否则会重复投 |
| 投递记录里的章节莫名消失 | 另一个会话整文件覆写了 | 见 SKILL.md「共享文件」一节 |
| 51job 投了但「我的申请」里没有 | 附件弹窗选错叶子节点（点到标题） | 选对叶子节点 + 等 ≥2.5s 再点「发送」 |
| 51job 访问详情页中途要滑块 | 账号级风控，连访 13–15 次触发 | **要用户人工过**，别程序化绕过 |
| 51job 点「立即投递」只弹跳转 | 那是校招网申岗位（`src == "网申"`） | 去 `campus.51job.com` 单独投；**判定必须在点之前做** |

---

## 六、命令速查

```powershell
# 环境自检
& "$env:USERPROFILE\.kimi-webbridge\bin\kimi-webbridge.exe" status
python <repo>\marvis\scripts\env_check.py

# 编码
$env:PYTHONIOENCODING='utf-8'

# 跑一批（BOSS 直聘）
python <repo>\marvis\scripts\wb_cross.py deliver

# 核对（BOSS：回消息页逐个点开会话重数）
python <repo>\marvis\scripts\wb_fav_check.py

# 话术差异度
python <repo>\marvis\scripts\diff_report.py <targets.json>

# 写回
$env:B3_PREFIX=xxx $env:B3_APPENDIX=附录X $env:B3_TITLE="..." python <repo>\marvis\scripts\writeback_b3.py

# 跑一批（前程无忧 51job，脚本在独立仓 job51-assistant）
python <repo51>\marvis\scripts\wb_51job_apply_batch.py
python <repo51>\marvis\scripts\wb_51job_verify_records.py   # 回「我的申请」核对
python <repo51>\marvis\scripts\wb_51job_writeback.py
```
