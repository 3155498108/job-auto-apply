# 新人第一次用这个 skill · 完整走查

> 面向第一次拿到这个 skill、机器上什么都还没有的人。
> 目标：**在不踩坑的前提下，先投出第一批 3 个岗位**，再谈扩量。

---

## 零、先搞清楚这是什么

一句话：**它不是一个「网页脚本」，它是一套「在你自己已登录的浏览器里，替人做投递动作」的流程。**

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

### Step 1 · 收集输入

要说清五件事，缺哪件先问：

1. 目标平台
2. 岗位来源（站内搜索 / 收藏夹 / 给定 URL 清单）
3. 投递形态（站内打招呼 vs 直接投简历）—— 决定要不要话术环节
4. 简历版本（哪份 PDF / 哪组截图）
5. **投递范围，以及是否允许自动发送**

能从上下文和已有产物推出来的（简历目录、话术目录、记录文件路径）直接读，别反问。

### Step 2 · 查现成轮子

接新平台前先在 GitHub 搜。清单见 `platform-adapters.md`。
**但平台口碑不能直接当结论** —— 51job 在 2026 年的公开评价里被标为「已经烂掉了」，
2026-10-23 实测它却是唯一稳定产出 AI 实习岗的来源。
**先探一次投递形态，用实测产出而不是公开评价决定优先级。**

### Step 3 · 形态探测

探错了整套适配器写法都要重做，所以放最前面。探测顺序见 `platform-adapters.md` 第四节。

### Step 4 · 抓 JD → 按正文筛

**岗位标题会骗人。** 必须按 JD 的**职责 + 要求**两段筛，
不要用公司介绍段（全是业务词，会把「做店铺运营的公司」误判成运营岗）。
劝退词表见 `safety-checklist.md`。

判不出来的条目**不要猜**：标「未切分」，让打分退化到只按标题命中，比错切可控。

### Step 5 · 生成差异化话术

按 JD 生成，不是套模板。核心是**证据原子 + 组合**。
生成完必须跑**差异度量化验收**（`diff_report.py`），给出实测值：

- 开头句去重 == 批大小
- 完全相同的两份 == 0
- 两两相似度均值明显低于旧基线

详见 `greeting-engine.md`。

### Step 6 · 投递（**授权后才做**）

- 「打招呼」「点立即沟通」「发附件」都是对外可见、不可撤回的
- 没有明确授权就停在这里，把话术和清单给用户看
- 发送间隔 ≥6 秒；批量大时每 15–20 条歇 25 秒
- 全程带**登录态守卫**：URL 命中 `/web/user` / `login` / `passport` 立刻停

**先投 3 个试跑**，核对没问题再扩量。

### Step 7 · 核对（**不信脚本自报**）

投递脚本返回「成功」不算成功。必须回消息页读 DOM 逐个核对：

> **送达 = 会话内有含本人标识的话术 + ≥2 张简历图**，且头部岗位名与目标对位。

要区分「这一轮投的」还是「几天前就投过的」，用话术指纹比对（`wb_msg_time.py`）：

| 判定 | 依据 | 处理 |
|---|---|---|
| `this_batch` 本轮新投 | 会话内我方消息含本批话术指纹 | 写 manifest |
| `older_batch` 历史已投 | 会话里是旧话术，本批指纹不在 | 不重复写，只补 jobId |
| `no_my_msg` 没投出去 | 会话不存在或没有我方消息 | 不写 manifest，进遗留清单 |

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

---

## 六、命令速查

```powershell
# 环境自检
& "$env:USERPROFILE\.kimi-webbridge\bin\kimi-webbridge.exe" status
python <repo>\marvis\scripts\env_check.py

# 编码
$env:PYTHONIOENCODING='utf-8'

# 跑一批（BOSS）
python <repo>\marvis\scripts\wb_cross.py deliver

# 核对
python <repo>\marvis\scripts\wb_fav_check.py

# 话术差异度
python <repo>\marvis\scripts\diff_report.py <targets.json>

# 写回
$env:B3_PREFIX=xxx $env:B3_APPENDIX=附录X $env:B3_TITLE="..." python <repo>\marvis\scripts\writeback_b3.py
```
