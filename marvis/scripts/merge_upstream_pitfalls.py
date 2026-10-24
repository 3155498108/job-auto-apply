#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""merge_upstream_pitfalls.py — 把上游 pitfalls.md 里最致命的几条并进我们的 skill。

上游 `marvis/references/pitfalls.md` 收了 34 条实战坑位，其中几条是我们 skill 里
没有的、且会直接导致「投错人」或「脚本失控」：

  B21/B28/B31  Vue Router 缓存劫持：连续 navigate 后渲染的是上一个 jobId 的内容
  B30          SPA 异步渲染残留：点到上一个岗位的按钮
  B33/B34      致命提示词必须用实际页面文本；且要先检测再关弹窗
  B28/B32      僵尸进程：杀 session 后 pipeline 还在跑，多进程抢同一批
  B22          排除词要分三档，宽泛词放正文会误杀（"五险一金"含"险"）
  B5           不要无脑批量投递，改逐条判断

本脚本只做两件事：插入新章节 + 把后续章节号顺延。
"""
import io
import os
import re

P = os.environ.get(
    "SAFETY_CHECKLIST",
    r"YOUR_HOME\.minimax\skills\job-auto-apply\references\safety-checklist.md")

NEW = """## 三、继承自上游踩坑记录的六条硬规则

上游 `marvis/references/pitfalls.md` 收了 34 条实战坑位（每次失败排查出来的）。
下面这几条**会直接导致投错人或脚本失控**，接新平台时必须继承，不要重新踩。

### 1. Vue Router 缓存劫持 —— 会投到上一个岗位（🔴 致命）

连续 `navigate` 到 job_detail A、B、C… 时，Vue Router 会缓存路由，
**URL 已经是 jobId C，页面渲染的还是 jobId B 的内容**。结果就是：
抓到的是 B 的 JD，投的是 C 的岗位，或者反过来。

两道防线：

- **每 5 次 navigate 就重置回搜索页**。搜索页每次 navigate 都会完整刷新 DOM，
  是天然的重置锚点。
- **提取 JD 后比对标题相似度**（详情页标题 vs 列表页标题），低于阈值就标记降级，
  投递时按「从严」处理——JD 与标题不符的直接跳过。

### 2. SPA 渲染残留 —— 会点到上一个岗位的按钮（🔴）

逐条 navigate 后立刻点「立即沟通」，偶尔投到错的岗位：脚本按 jobId 列表走，
但 SPA 异步渲染时上一个岗位的按钮状态还没刷新，click 事件错位。

- navigate 后等 **8–12 秒**（Vue 完整渲染的实测值）
- 点击前先验证按钮**存在且可点击**，再点
- 点完再回读一次头部岗位名，不对就丢弃这条

### 3. 致命提示词要用实际页面文本，且要先检测再关弹窗（🔴）

匹配规则**不能基于推测**。BOSS 实际的沟通上限弹窗是：

```
您已达到沟通上限
您今天已与150位BOSS沟通，休息一下，明天再来吧～
```

不是推测的「今日沟通次数已达上限」。先用 debug 脚本把真实弹窗文本抓出来再写规则。

还有一个顺序陷阱：`点「立即沟通」 → 先关弹窗 → 再检测页面文本` 会在关弹窗时
把上限提示一起关掉，检测不到 → 返回 unknown → 连续 unknown 触发误停。
**正确顺序：点按钮 → 等 2 秒 → 先读弹窗文本检测致命错误 → 再处理弹窗。**

### 4. 僵尸进程与 PID 锁（🟡）

杀 session / 关终端后，Windows 不会级联杀子进程，投递脚本变成孤儿继续跑，
**多个进程同时投同一批候选**。

- 投递脚本启动时获取 PID 锁，已存在实例就拒绝启动（exit 1）
- 每个岗位处理完立即落盘进度，中断最多丢当前一条
- **不要用 `background:true` 启动投递脚本**

### 5. 排除词分三档，不要混用（🟡）

| 档 | 作用位置 | 例 |
|---|---|---|
| T | 标题 | 硬件、测试、算法、数据标注 |
| C | 公司名 | 电子、光电、半导体、分公司、外包 |
| B | 正文标记 | 无责底薪、高提成、日结、引导玩家 |

**宽泛词不能放正文档**。实测误杀案例：
「保险」会把含「五险一金」的**所有**岗位全杀掉；
「保洁」会把「园区保洁服务」岗杀掉；「投资」会命中「投资建设/投资运营」。

正文档只用「无责底薪 / 高提成 / 日结 / 会基本打字」这类**语义唯一**的词。

### 6. 不要无脑批量投递（🔴）

上游血泪教训：2026-06-12 批量脚本无脑投了大量实习、日结、主播岗，被用户批评。
之后改成 **AI 逐条判断 + 用户决策**，不做无脑海投。
本项目现在的做法是「JD 正文逐条筛 + 淘汰理由写进记录」，本质就是这条规则的实现。

"""

s = io.open(P, encoding="utf-8").read()

if "继承自上游踩坑记录" in s:
    print("已存在，跳过")
    raise SystemExit(0)

# 后续章节号顺延：从「三、」往后全部 +1
CN = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def bump(m):
    num = m.group(1)
    if num not in CN:
        return m.group(0)
    return f"## {num}{CN[num] + 1}、" + m.group(2)

s = re.sub(r"## ([三四五六七八九十]+)、(.+)", bump, s)

# 章节号顺延后，锚点也顺延了 —— 按「JD 劝退关键词」这个特征找，不写死编号
anchor = None
for m in re.finditer(r"^## [^\n]*JD 劝退关键词[^\n]*$", s, re.M):
    anchor = m.group(0)
    break
if anchor is None:
    raise SystemExit("锚点没找到，章节结构变了")
s = s.replace(anchor, NEW + anchor)

io.open(P, "w", encoding="utf-8").write(s)
print("已插入新章节。章节结构：")
for m in re.finditer(r"^## .+$", s, re.M):
    print("   ", m.group(0))
