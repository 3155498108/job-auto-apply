#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""jd_filter.py — 只看 JD 的「职责 + 要求」两段，做硬性劝退。

## 为什么要重写（2026-10-22 第三批实战暴露）

原来的规则是「关键词出现在职责+要求段就劝退」，实测误杀率太高：

  · 示例企业07 后端：要求写「至少熟悉 Golang、C/C++、Java、Python 等**一种**语言」
    → C++ 只是并列选项之一，被误杀
  · 字节飞书后端：要求写「熟悉 Golang、Python、Java、C/C++ 等至少一门语言」
    → 同上误杀
  · 示例集团A：要求写「…参与过 AI 大模型应用研究**发表过顶会论文**…者优先」
    → 加分项被当成硬门槛
  · 示例集团B：要求写「接触过 PyTorch、Transformer、LLM、RAG、Agent 等相关技术**者优先**」
    → 同上

同时漏掉了一个更严重的问题：字节飞书那个岗位标题只写「后端开发实习生」，
**要求段里写的是「2028 届本科及以上学位在读」** —— 候选人是 在校，标题完全看不出来。

## 现在的做法

1. **段落切分要收口**：req 段遇到「公司介绍 / 职位描述 / 扫码分享」等结束标记就停，
   否则会把公司介绍里的「团队负责人为清华大学博士」误判成学历门槛。
2. **条目级强度判定**：要求段按编号切成条目，逐条判断是「硬要求」还是「加分项」：
   - 先剥掉句尾的「…者优先」子句
   - 剥完后若整条不含强动词（精通/扎实/熟练/深入/必须/至少/具备…经验/实践…），
     视为加分项，丢弃
   - 只留「了解/接触/基础」这类弱描述的条目也丢弃
3. **C++ 降级为条件规则**：C++ 与其它后端语言并列时不算劝退项；
   只有岗位主体方向就是 C/C++ 时才劝退。
4. **新增届别规则**：正文写 26/28 届直接劝退（本人 在校）——
   标题看不出来的硬伤，必须靠正文筛。

用法: python jd_filter.py <targets.json> <out.json>
"""
import io
import json
import os
import re
import sys

WORK = r"YOUR_HOME\output\boss_work"

# ── 段落切分 ──────────────────────────────────────────────────────────
DUTY_MARKS = ("岗位职责", "工作职责", "工作内容", "职位描述", "岗位介绍", "岗位描述")
REQ_MARKS = ("任职要求", "岗位要求", "职位要求", "任职资格", "岗位资格", "职位资格",
             "招聘条件", "任职条件", "岗位条件", "应聘条件", "基本要求", "我们希望你",
             "我们期待", "岗位需求", "任职需求", "福利待遇")
# req 段到这些标记就停，防止把公司介绍 / 加分项吸进来
END_MARKS = ("加分项", "加分条件", "优先考虑", "公司介绍", "工商信息", "公司信息",
             "职位描述", "扫码分享", "举报", "招聘人数", "职位更新时间", "发布时间",
             "工作地点", "公司地址", "其他信息", "面试流程", "公司简介", "我们提供")

# ── 强度判定 ──────────────────────────────────────────────────────────
STRONG = re.compile(
    r"(精通|扎实|熟练|深入|必须|至少|良好|丰富|独立|负责|核心|能够|掌握|"
    r"具备.{0,10}经验|有.{0,10}经验|实践经验|实践|研发|开发|设计|搭建|落地)")
WEAK = re.compile(r"(了解|接触|知道|基础|基本认识|基本流程|基本功|有一定|具备一定|"
                   r"一般|可选|辅助|有助于|加分|优先|者优|听说|入门)")

# ── 劝退规则 ──────────────────────────────────────────────────────────
# 硬门槛类：不管条目强弱，出现在职责/要求整段里就劝退。
# （届别、学历这种是「一票否决」，即使写成「熟悉xxx优先」也一样不能投）
REJECT_HARD_GATE = [
    ("学历门槛", ["硕士及以上", "硕士学历", "研究生及以上", "博士", "985高校", "985 高校",
                  "985院校", "985 院校", "211本科", "211 本科", "211院校", "211 院校",
                  "双一流", "成绩前20%", "成绩前 20%"]),
]
# 届别：JD 里出现明确的非本人届别 → 劝退。
# 不用关键词列表（覆盖不了「毕业时间：2025年」这种写法），改成泛化正则。
# 本人届别由环境变量 GRADE_OK 提供（例：GRADE_OK=2026）；不设置则整段届别筛除关闭。
GRADE_OK = os.environ.get("GRADE_OK", "").strip()


PRIORITY_WORDS = ("优先", "可投", "加分", "者优", "欢迎")


def _priority_positions(text):
    """返回「属于优先语境」的届别位置集合。

    判定：同一句内，届别与优先词的距离 ≤ 20 字。
      「因此2025届应届生，2026届在校生会被优先考虑」→ 两个届别都算优先（距离 13 / 5）
      「1、2028届本科及以上学位在读，计算机、人工智能等相关专业优先」
        → 「优先」修饰的是「专业」，离届别 31 字 → 硬要求
    句界用 。；！？和换行，逗号不算（并列届别常被逗号隔开）。
    """
    prio = set()
    for sm in re.finditer(r"[^。；！？\n]*", text):
        chunk = sm.group(0)
        if not chunk:
            continue
        best = None
        for kw in PRIORITY_WORDS:
            i = chunk.find(kw)
            if i >= 0 and (best is None or i < best):
                best = i
        if best is None:
            continue
        ppos = sm.start() + best
        for gm in re.finditer(r"(?:20)?(\d{2})\s*届", chunk):
            gpos = sm.start() + gm.start()
            if abs(ppos - gpos) <= 20:
                prio.add(gpos)
        for gm in re.finditer(r"毕业时间\s*[:：]?\s*(20\d{2})\s*年", chunk):
            gpos = sm.start() + gm.start()
            if abs(ppos - gpos) <= 20:
                prio.add(gpos)
    return prio


def grade_mismatch(text):
    """返回届别不符的原因列表；没有则返回 []。

    支持的写法：
      毕业时间：2026年 / 2028年 / 2025年
      26届 / 28届 / 29届
      2026年毕业 / 26年毕业
      毕业时间：2025年-2026年   ← 区间，含本人届别就不劝退
      27/28 届可投             ← 含本人届别短码的区间也不劝退
      ……会被优先考虑           ← 优先语境里的届别不劝退
    """
    if not GRADE_OK:
        return []          # 未提供本人届别 → 不做届别筛除
    reasons = []
    covered = []
    for m in re.finditer(r"毕业时间\s*[:：]?\s*(20\d{2})\s*年\s*[-~－—至到]\s*(20\d{2})\s*年", text):
        if GRADE_OK in (m.group(1), m.group(2)):
            covered.append((m.start(), m.end()))
    # 「27/28 届」这种并列写法：含本人届别短码就整段放过
    for m in re.finditer(r"(?:20)?" + re.escape(GRADE_OK[2:]) +
                         r"\s*[/、~～\-]\s*(?:20)?\d{2}\s*届", text):
        covered.append((m.start(), m.end()))

    prio = _priority_positions(text)

    def _skip(pos):
        return any(a <= pos < b for a, b in covered) or pos in prio

    for m in re.finditer(r"毕业时间\s*[:：]?\s*(20\d{2})\s*年", text):
        if m.group(1) != GRADE_OK and not _skip(m.start()):
            reasons.append(f"毕业时间{m.group(1)}")
    for m in re.finditer(r"(?:20)?(\d{2})\s*届", text):
        if m.group(1) != GRADE_OK[2:] and not _skip(m.start()):
            reasons.append(f"{m.group(1)}届")
    for m in re.finditer(r"(?:20)?(\d{2})\s*年[^。；\n]{0,4}毕业", text):
        if m.group(1) != GRADE_OK[2:] and not _skip(m.start()):
            reasons.append(f"{m.group(1)}年毕业")
    out = []
    for r in reasons:
        if r not in out:
            out.append(r)
    return out

# 标题级强非技术信号：标题是硬信号，正文再没提也要拦
TITLE_REJECT = ["数据采集员", "数据标注", "ai训练师", "主播", "剪辑", "客服", "人事",
                "招聘专员", "政企合作", "产业政策", "政策研究", "商务专员", "客户成功",
                "产品助理", "产品经理", "运营专员", "市场专员", "游戏运营", "数据运营"]

# 标题里明说不招实习生的：投过去只会被自动拒，白费一个招呼额度。
# 实测：示例企业37「vibe coding+后端开发：不考虑实习生」——
# 标题是硬信号，但正文写得像正经开发岗，之前的规则拦不住。
TITLE_NO_INTERN = ["不考虑实习生", "不考虑应届", "不接受实习生", "非实习", "拒绝实习",
                   "不招实习", "实习生勿扰", "坐班"]

# 标题里点了没做过的框架/平台：投过去只能承认不会，不如不投。
# 实测：佛山大白熊「AI智能体coze工作流开发工程师」——主体工作是工作流搭建。
TITLE_BOUNDARY = ["coze", "dify", "n8n", "langchain", "langgraph", "扣子"]

REJECT = [
    ("硬件/嵌入式", ["stm32", "gd32", "mcu", "寄存器", "datasheet", "mipi", "lvds", "相机模组",
                     "电机控制", "伺服驱动", "变频器", "原理图", "示波器", "逻辑分析仪",
                     "嵌入式", "硬件调试", "上位机", "pcb", "单片机", "电路设计"]),
    ("C系语言", ["c语言", "c#", "objective-c", "汇编语言", "rust", "汇编",
                 "php", "laravel", "thinkphp"]),
    ("Unity/引擎", ["unity", "u3d", "unreal", "cocos", "egret", "game jam"]),
    ("视觉/图形库", ["opencv", "qt", "mfc", "directx", "vulkan", "opengl", "shader"]),
    ("算法研究", ["视觉算法", "图像算法", "计算机视觉", "计算机图形学", "语音处理",
                  "多模态", "多模态学习", "深度学习", "cuda", "pytorch", "tensorflow",
                  "顶会", "算法研究方向", "大模型研究方向", "论文发表", "模型微调", "预训练", "强化学习",
                  "扩散模型", "大模型训练", "分布式训练",
                  "训练框架", "推理引擎", "推理优化", "千卡", "gpu 集群"]),
    ("向量检索/多模态引擎", ["faiss", "milvus", "向量检索", "ann 建库", "多维索引",
                             "跨模态检索", "pgvector", "倒排索引", "bm25", "向量数据库"]),
    ("云原生深度", ["kubernetes", "k8s", "operator", "crd", "webhook", "vllm", "sglang",
                    "tensorrt", "ray on", "spark on", "调度器", "装箱策略", "弹性伸缩"]),
    ("社招经验", ["1-3年", "1-3 年", "3-5年", "3-5 年", "3年以上", "3 年以上", "两年以上",
                  "2年以上", "有工作经验", "已毕业", "正式员工"]),
    ("非技术岗", ["引导玩家", "会基本打字", "接受小白", "熟悉办公软件",
                  "数据采集员", "数据采集", "审核采集", "接听电话", "陌拜", "地推",
                  "客服专员", "招聘专员", "人事助理", "主播", "ai漫剧剪辑", "短视频剪辑",
                  "影视剪辑", "政企合作", "产业政策",
                  "政策研究", "商务合作", "客户成功", "游戏运营", "产品助理"]),
    ("前端框架(硬要求)", ["vue", "react", "angular", "svelte", "小程序开发", "微信小程序",
                          "flutter", "android", "ios", "uniapp", "鸿蒙", "taro", "electron"]),
    ("非开发技能", ["会ps", "photoshop", "剪映", "premiere", "设计稿", "ui设计", "平面设计",
                    "文案", "配音", "摄影", "3dmax", "c4d", "blender", "剪辑软件",
                    "3d建模", "三维建模", "建模软件", "zbrush", "maya"]),
    ("底薪/无责底薪", ["无责底薪", "高提成", "拉人头", "日结", "小时工"]),
]

# 职责段里的非开发信号：出现这些、且整段没有开发信号 → 判为运营/商务岗
NONDEV_DUTY = ["上架", "选品", "客服", "销售", "店铺", "业务员", "带货", "主播", "剪辑",
               "内容运营", "社群运营", "地推", "接单", "跑腿", "客服接听", "回访", "催收",
               # 数据标注类：标题写成「ai实习生」看不出来，职责段才暴露
               "数据清洗", "数据标注", "人工标注", "数据预处理", "数据采集", "数据整理",
               "标注数据", "语料标注", "众包标注",
               # 视觉/内容创作类：AI 生图、漫剧、短剧分镜
               # 只收「岗位动作/岗位性质」词，不收业务对象词——
               # 「短剧」「素材」「画风」是业务领域词，字节的短剧服务端开发岗通篇是这些，
               # 用它们判非开发会把正经服务端岗误杀。
               "设计团队", "视觉生成", "创意构思", "概念方案", "设计深化", "构图",
               "生图", "图生图", "人物形象", "服装造型", "场景图", "道具图",
               "分镜", "分镜头", "画风漂移", "视觉叙事", "视觉传达", "美术",
               "数字媒体", "美学", "风格还原", "生图经验", "服装设计", "角色设计",
               # 运营/支持/销售类：产品支持、新媒体、电商运营、装机运维
               "客户沟通", "跟进客户订单", "营销推广", "电商运营", "业务问题诊断",
               "faq", "用户反馈", "应用模板", "操作手册", "部署指南", "装机",
               "网络维护", "话术", "品类运营", "客户需求", "运维",
               # AIGC 内容评测类：标题只写「AIGC内容评测实习生」，看起来像技术岗，
               # 职责却是评估配音音色/短剧配乐/音效/小说改编——纯主观评测，不写代码。
               # 实测：示例科技R那个岗，职责段几乎一个开发信号都没有。
               "音色", "发音", "停顿节奏", "短剧配乐", "音效", "音频后期",
               "内容评测", "评测标准", "视频化", "小说", "配音效果",
               "评估短剧", "素材评估", "内容筛选", "优化建议", "问题案例"]
# 职责段里的开发信号：出现任一即认为岗位有开发内容
DEV_SIGNAL = ["开发", "研发", "代码", "编程", "接口", "数据库", "测试", "部署", "上线",
              "重构", "架构", "实现", "程序", "系统", "服务", "算法", "数据处理", "调试"]
# 强开发信号：只有这些才算「真的在写代码」，用于职责段非开发判定
# （泛词「测试/系统/服务/数据处理」会让运营岗蒙混过关）
STRONG_DEV = ["开发", "研发", "编码", "代码", "编程", "接口", "数据库", "部署", "上线",
              "架构", "后端", "前端", "全栈", "服务端", "单元测试", "算法", "程序", "api"]
# 要求段里出现任一即认为岗位要求写代码（用来兜底「要求段完全没提编程」的运营岗）
PROG_REQ = ["编程", "开发", "代码", "语言", "python", "java", "javascript", "typescript",
            "golang", "c++", "c#", "前端", "后端", "全栈", "接口", "测试", "程序",
            "sql", "数据库", "算法"]

# 后端语言：出现这些说明这是后端/全栈方向，C++ 并列时不算劝退项
BACKEND_LANGS = ("java", "go", "golang", "python", "spring", "后端", "服务端", "php",
                  "node", "接口", "数据库", "redis", "mysql")

FRONT_ONLY_REQ = ["react", "vue", "angular", "小程序开发", "flutter", "android", "ios", "web前端"]

# JD 里写死的主语言：单一语言被硬要求时，话术必须把该语言的证据顶上来
# （示例传媒T要求「熟悉 Python 语言」，通用打分会输给「排错/异常」原子）
LANG_REQ = [
    ("python", ["python", "flask", "fastapi", "django", "pandas"]),
    ("java", ["java", "spring", "springboot", "spring boot", "mybatis"]),
    ("typescript", ["typescript", "javascript", "node.js", "nodejs"]),
]


def req_langs(duty, req):
    """返回 JD 明确要求的语言列表。

    只在**单一语言**被点名时才算（返回长度 1）；多语言并列说明「都行」，
    不该强行往话术里塞某一个语言的证据。
    匹配用 duty+req 原文（hard_items 会把「熟悉 Python 者优先」这类条目剥掉）。
    """
    text = (duty + "\n" + req).lower()
    hit = []
    for name, kws in LANG_REQ:
        if any(k in text for k in kws):
            hit.append(name)
    return hit


def _first(text, marks, start=0):
    """返回 marks 里最先出现的那个的索引，没有返回 -1。"""
    best = -1
    for m in marks:
        i = text.find(m, start)
        if i >= 0 and (best < 0 or i < best):
            best = i
    return best


def _strip_biz_tags(text):
    """删掉「A ; B ; C ; D」/「A | B | C | D」这种企业业务范围罗列。

    招聘页常在 JD 末尾附一串经营范围（…;集成电路设计;新兴能源技术研发;…），
    那不是岗位要求，但会命中「电路设计」「软件开发」这类词。
    顿号不做处理——正常句子里也用顿号。
    """
    text = re.sub(r"(\s*[|｜][^|｜]{2,24}){3,}", " ", text)
    text = re.sub(r"(\s*[;；][^;；]{2,30}){3,}", " ", text)
    return text


def split_jd(jd):
    """切出 duty / req 两段，req 段遇到结束标记就收口。"""
    i = _first(jd, DUTY_MARKS)
    k = _first(jd, REQ_MARKS, i + 1 if i >= 0 else 0)
    if i < 0 and k < 0:
        return jd[:900], ""
    if i < 0:
        duty = ""
    elif k > i:
        duty = jd[i:k]
    else:
        duty = jd[i:i + 900]
    # duty 段也要收口，否则会吸进公司介绍里的「系统/服务」等词
    for m in END_MARKS:
        p = duty.find(m)
        if p > 0:
            duty = duty[:p]
    if k < 0:
        return _strip_biz_tags(duty)[:900], ""
    seg = jd[k:k + 900]
    for m in END_MARKS:
        p = seg.find(m)
        if p > 0:
            seg = seg[:p]
    return _strip_biz_tags(duty), _strip_biz_tags(seg)


def hard_items(req):
    """要求段 → 只保留「硬要求」条目。

    1. 按编号/分号/换行切条目
    2. 剥掉句尾「…者优先」子句
    3. 剥完后整条不含强动词 → 判为加分项丢弃
    4. 只剩弱描述（「了解/基础」）→ 也丢弃
    """
    parts = re.split(r"(?=\d+\s*[、.．）)])|[；;\n]", req)
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        p2 = re.sub(r"[^，,。；;：:]{0,40}者优先[，,。；;]?", "", p)
        p2 = re.sub(r"[^，,。；;：:]{0,40}优先[，,。；;]?", "", p2)
        p2 = re.sub(r"[^，,。；;：:]{0,30}加分[，,。；;]?", "", p2)
        p2 = p2.strip(" ，,。；;：:")
        if len(p2) < 6:
            continue
        if len(p2) > 150:
            continue          # 超长条目基本是公司介绍被吸进来了
        if p2.count("|") >= 3:
            continue          # 「人工智能应用软件开发 | 网络安全 | 集成电路设计 | …」
                              # 这类是企业业务范围罗列，不是岗位要求
        if not STRONG.search(p2):
            continue
        if WEAK.search(p2) and not re.search(r"(精通|扎实|熟练|深入|必须|至少|具备|掌握)", p2):
            continue
        out.append(p2)
    if not out:
        # 兜底：格式不常规时，用整段（但仍剥掉优先子句）
        p2 = re.sub(r"[^，,。；;：:]{0,40}者优先[，,。；;]?", "", req)
        return p2 if len(p2) > 40 else req
    return "\n".join(out)


def cut_jd(jd, extra_marks=()):
    """截掉 BOSS 页面底部的推荐位噪声。

    详情页正文之后会跟一段「职位描述 + 标签 + 毕业时间 + 截止日期」，
    再往后是「竞争力分析 / BOSS 安全提示 / 公司介绍 / 更多职位 / 精选职位」——
    「更多职位」「精选职位」里是**别的岗位**（含它们的届别和学历要求）。
    不截断的话，某公司 那个岗会因为推荐位里的「博士后/特别研究助理」
    和「【2025/2026届】ESD设计工程师」被误判成博士门槛 + 错误届别。

    保留到「竞争力分析」之前：届别元信息（毕业时间：不限 / 2025年-2026年）
    在「职位描述」段里，位于「竞争力分析」之前，不会被截掉。
    """
    for m in tuple(("竞争力分析", "更多职位", "精选职位", "城市招聘")) + tuple(extra_marks):
        i = jd.find(m)
        if i > 0:
            jd = jd[:i]
    return jd


def screen_one(t, jd, closed=False, title_match=None, split=None, cut_marks=()):
    """对单个岗位做「基于 JD 正文」的硬性劝退判定。

    这是 BOSS 与 51job 共用的判定入口。BOSS 走默认 split_jd / cut_jd；
    51job 的分段标签不一样（「1、你要做的事 / 2、岗位要求」），
    通过 split= 与 cut_marks= 注入自己的一套。

    参数:
        t          目标 dict，至少含 "label" 与 "position"
        jd         详情页抓到的 JD 全文
        closed     职位是否已关闭
        title_match 详情页岗位名是否与目标一致（False → 从严劝退）
        split      (jd_text) -> (duty, req)，默认 split_jd
        cut_marks  额外截断标记

    返回:
        (ok: bool, reason: str, info: dict)
    """
    jd = cut_jd(jd, cut_marks)
    if title_match is False:
        return False, (f"详情页岗位名不匹配（页面={t.get('page_position','')!r} "
                       f"目标={t.get('position','')!r}）"), {}
    if closed:
        return False, "职位已关闭", {}
    if len(jd) < 120:
        return False, "JD 未抓全", {}
    sp = split or split_jd
    duty, req = sp(jd)
    hard = hard_items(req)
    core = (duty + "\n" + hard).lower()
    low = core.lower()
    duty_low_all = duty.lower()
    bad = []
    # 标题级：强非技术信号直接拦
    tlow = (t.get("position") or "").lower()
    thit = [k for k in TITLE_REJECT if k.lower() in tlow]
    if thit:
        bad.append(f"标题非技术岗[{'/'.join(thit[:3])}]")
    tno = [k for k in TITLE_NO_INTERN if k.lower() in tlow]
    if tno:
        bad.append(f"标题排除实习[{'/'.join(tno[:2])}]")
    tbd = [k for k in TITLE_BOUNDARY if k.lower() in tlow]
    if tbd:
        bad.append(f"标题点没做过的框架[{'/'.join(tbd[:2])}]")
    # 硬门槛（届别/学历）：在整份 JD 上判定，不受 duty/req 切片影响。
    whole = jd.lower()
    for name, kws in REJECT_HARD_GATE:
        hit = [k for k in kws if k.lower() in whole]
        if hit:
            bad.append(f"{name}[{'/'.join(hit[:3])}]")
    gm = grade_mismatch(whole)
    if gm:
        bad.append(f"届别不符[{'/'.join(gm[:3])}]")
    for name, kws in REJECT:
        if name == "非开发技能":
            # 只在「要求段的硬条目」里判：职责段描述工作内容不算技能门槛。
            hardlow = hard.lower()
            hit = [k for k in kws if k.lower() in hardlow]
        elif name == "底薪/无责底薪":
            hit = [k for k in kws if k.lower() in low]
            if hit and any(s in duty_low_all for s in DEV_SIGNAL):
                continue
        else:
            hit = [k for k in kws if k.lower() in low]
        if not hit:
            continue
        if name == "社招经验" and ("已毕业" in hit or "正式员工" in hit):
            # 「在校生能全职实习、已毕业的需要懂YOLO…」这类是**分情况描述**，
            # 不是要求已毕业。命中「在校生」时不能因为出现「已毕业」就误杀
            # （实测：广东长川「实习软件工程师（AI模型训练）」就是这么被误杀的）。
            # 判据：两者在 60 字内同段出现 → 分情况；否则仍按硬门槛劝退。
            paired = False
            for kw in ("已毕业", "正式员工"):
                p1 = whole.find("在校生")
                p2 = whole.find("应届")
                q = whole.find(kw)
                if q < 0:
                    continue
                for p in (p1, p2):
                    if p >= 0 and abs(p - q) < 60:
                        paired = True
            if paired:
                hit = [h for h in hit if h not in ("已毕业", "正式员工")]
                if not hit:
                    continue
        if name == "C系语言" and "c++" in hit:
            pos = low.find("c++")
            ctx = low[max(0, pos - 60):pos + 60]
            if any(b in ctx for b in BACKEND_LANGS):
                hit = [h for h in hit if h != "c++"]
                if not hit:
                    continue
        if name == "前端框架(硬要求)":
            # 只在这份 JD 完全没有后端/全栈硬要求时才劝退
            if any(b in low for b in ("java", "python", "后端", "spring", "node", "go",
                                     "golang", "全栈", "接口", "数据库", "sql")):
                continue
        bad.append(f"{name}[{'/'.join(hit[:3])}]")
    if ("不限学历" in low or "无学历" in low) and any(
            w in low for w in ("无责底薪", "日结", "高提成", "拉人头", "地推", "陌拜",
                               "引流", "会基本打字", "无需经验")):
        bad.append("非技术岗[不限学历+其它信号]")
    # 纯前端：前端词出现次数 >= 2 且没有后端词
    fhits = [k for k in FRONT_ONLY_REQ if k.lower() in low]
    bhits = [k for k in ("java", "python", "后端", "spring", "接口", "api", "数据库", "sql",
                         "flask", "django", "全栈", "ai", "go", "golang") if k in low]
    if len(fhits) >= 2 and len(bhits) == 0:
        bad.append(f"纯前端[{'/'.join(fhits[:3])}]")
    # 职责段是运营/商务/视觉岗：非开发信号出现次数多于强开发信号才劝退
    duty_low = duty.lower()
    ndh = [k for k in NONDEV_DUTY if k in duty_low]
    nd_count = sum(duty_low.count(k) for k in ndh)
    dev_count = sum(duty_low.count(s) for s in STRONG_DEV)
    if ndh and nd_count > dev_count:
        bad.append(f"职责非开发岗[{'/'.join(ndh[:3])}]")
    info = {"duty": duty, "req": req, "hard": hard, "core_len": len(core)}
    if bad:
        return False, "；".join(bad), info
    t["jd_core_len"] = len(core)
    t["jd_hard_items"] = len(hard.split("\n")) if hard else 0
    langs = req_langs(duty, req)
    if len(langs) == 1:
        t["req_lang"] = langs[0]
    return True, "", info


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "gd2_targets.json"
    dst = sys.argv[2] if len(sys.argv) > 2 else "gd2_kept.json"
    targets = json.load(io.open(os.path.join(WORK, src), encoding="utf-8"))
    jds = json.load(io.open(os.path.join(WORK, "jd_text.json"), encoding="utf-8"))
    kept, dropped = [], []
    for t in targets:
        rec = jds.get(t["label"]) or {}
        t["page_position"] = rec.get("position", "")
        ok, why, _info = screen_one(
            t, rec.get("jd", ""),
            closed=rec.get("closed", False),
            title_match=rec.get("title_match", True))
        if ok:
            kept.append(t)
        else:
            dropped.append((t["label"], why))
    json.dump(kept, io.open(os.path.join(WORK, dst), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    # 劝退清单落盘，供记录写回与人工复核
    drop_name = os.environ.get("JD_DROPPED", os.path.splitext(dst)[0] + "_dropped.json")
    json.dump([{"label": a, "reason": b} for a, b in dropped],
              io.open(os.path.join(WORK, drop_name), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"输入 {len(targets)} → 保留 {len(kept)}，劝退 {len(dropped)}\n")
    for lab, why in dropped:
        print(f"  ✗ {lab}\n      {why}")
    print(f"\n保留清单：")
    for t in kept:
        print(f"  ✓ {t['label']:<46} {t['city']:<5} {t['salary']}")
    print(f"\n→ {os.path.join(WORK, dst)}")


if __name__ == "__main__":
    main()
