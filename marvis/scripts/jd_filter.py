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
                  "成绩前20%", "成绩前 20%"]),
]
# 届别用正则抓：关键词列表覆盖不了「毕业时间：2026年」这种写法
GRADE_PATTERNS = [
    (r"毕业时间\s*[:：]?\s*2026", "毕业时间2026"),
    (r"毕业时间\s*[:：]?\s*2028", "毕业时间2028"),
    (r"(?:20)?26\s*届", "26届"),
    (r"(?:20)?28\s*届", "28届"),
    (r"(?:20)?26\s*年[^。；\n]{0,4}毕业", "26年毕业"),
    (r"(?:20)?28\s*年[^。；\n]{0,4}毕业", "28年毕业"),
]

# 标题级强非技术信号：标题是硬信号，正文再没提也要拦
TITLE_REJECT = ["数据采集员", "数据标注", "ai训练师", "主播", "剪辑", "客服", "人事",
                "招聘专员", "政企合作", "产业政策", "政策研究", "商务专员", "客户成功",
                "产品助理", "产品经理", "运营专员", "市场专员", "游戏运营", "数据运营"]

REJECT = [
    ("硬件/嵌入式", ["stm32", "gd32", "mcu", "寄存器", "datasheet", "mipi", "lvds", "相机模组",
                     "电机控制", "伺服驱动", "变频器", "原理图", "示波器", "逻辑分析仪",
                     "嵌入式", "硬件调试", "上位机", "pcb", "单片机", "电路设计"]),
    ("C系语言", ["c语言", "c#", "objective-c", "汇编语言", "rust", "汇编"]),
    ("Unity/引擎", ["unity", "u3d", "unreal", "cocos", "egret", "game jam"]),
    ("视觉/图形库", ["opencv", "qt", "mfc", "directx", "vulkan", "opengl", "shader"]),
    ("算法研究", ["视觉算法", "图像算法", "计算机视觉", "计算机图形学", "语音处理",
                  "多模态", "多模态学习", "深度学习", "cuda", "pytorch", "tensorflow",
                  "顶会", "研究方向", "论文发表", "模型微调", "预训练", "强化学习",
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
                    "文案", "配音", "摄影", "建模", "3dmax", "c4d", "blender", "剪辑软件"]),
    ("底薪/无责底薪", ["无责底薪", "高提成", "拉人头", "日结", "小时工"]),
]

# 职责段里的非开发信号：出现这些、且整段没有开发信号 → 判为运营/商务岗
NONDEV_DUTY = ["上架", "选品", "客服", "销售", "店铺", "业务员", "带货", "主播", "剪辑",
               "内容运营", "社群运营", "地推", "接单", "跑腿", "客服接听", "回访", "催收"]
# 职责段里的开发信号：出现任一即认为岗位有开发内容
DEV_SIGNAL = ["开发", "研发", "代码", "编程", "接口", "数据库", "测试", "部署", "上线",
              "重构", "架构", "实现", "程序", "系统", "服务", "算法", "数据处理", "调试"]

# 后端语言：出现这些说明这是后端/全栈方向，C++ 并列时不算劝退项
BACKEND_LANGS = ("java", "go", "golang", "python", "spring", "后端", "服务端", "php",
                  "node", "接口", "数据库", "redis", "mysql")

FRONT_ONLY_REQ = ["react", "vue", "angular", "小程序开发", "flutter", "android", "ios", "web前端"]


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


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "gd2_targets.json"
    dst = sys.argv[2] if len(sys.argv) > 2 else "gd2_kept.json"
    targets = json.load(io.open(os.path.join(WORK, src), encoding="utf-8"))
    jds = json.load(io.open(os.path.join(WORK, "jd_text.json"), encoding="utf-8"))
    kept, dropped = [], []
    for t in targets:
        rec = jds.get(t["label"]) or {}
        jd = rec.get("jd", "")
        # 详情页岗位名与目标不一致 → 抓到的 JD 不可信（Vue Router 缓存劫持残留），从严劝退
        if rec.get("title_match") is False:
            dropped.append((t["label"], f"详情页岗位名不匹配（页面={rec.get('position','')!r} "
                                        f"目标={t.get('position','')!r}）"))
            continue
        if rec.get("closed"):
            dropped.append((t["label"], "职位已关闭"))
            continue
        if len(jd) < 120:
            dropped.append((t["label"], "JD 未抓全"))
            continue
        duty, req = split_jd(jd)
        hard = hard_items(req)
        core = (duty + "\n" + hard).lower()
        low = core.lower()
        bad = []
        # 标题级：强非技术信号直接拦
        tlow = (t.get("position") or "").lower()
        thit = [k for k in TITLE_REJECT if k.lower() in tlow]
        if thit:
            bad.append(f"标题非技术岗[{'/'.join(thit[:3])}]")
        # 硬门槛（届别/学历）：在整段职责+要求上判定，不受条目强弱影响
        whole = (duty + "\n" + req).lower()
        for name, kws in REJECT_HARD_GATE:
            hit = [k for k in kws if k.lower() in whole]
            if hit:
                bad.append(f"{name}[{'/'.join(hit[:3])}]")
        for pat, tag in GRADE_PATTERNS:
            if re.search(pat, whole):
                bad.append(f"届别不符[{tag}]")
                break
        for name, kws in REJECT:
            hit = [k for k in kws if k.lower() in low]
            if not hit:
                continue
            if name == "C系语言" and "c++" in hit:
                # C++ 与其它后端语言并列时不算劝退项
                pos = low.find("c++")
                ctx = low[max(0, pos - 60):pos + 60]
                if any(b in ctx for b in BACKEND_LANGS):
                    hit = [h for h in hit if h != "c++"]
                    if not hit:
                        continue
            if name == "前端框架(硬要求)":
                # 只在这份 JD 完全没有后端/全栈硬要求时才劝退：
                # 「前端：熟悉Vue／后端：熟悉Python」这种二选一岗位不杀
                if any(b in low for b in ("java", "python", "后端", "spring", "node", "go",
                                         "golang", "全栈", "接口", "数据库", "sql")):
                    continue
            bad.append(f"{name}[{'/'.join(hit[:3])}]")
        # 「不限学历」只有在同时出现明确非技术信号时才劝退——
        # 学历宽松的岗位照样可能是正经开发岗（AI 陪伴产品开发、AI 全栈开发都写过不限学历）
        if ("不限学历" in low or "无学历" in low) and any(
                w in low for w in ("无责底薪", "日结", "高提成", "拉人头", "地推", "陌拜",
                                   "引流", "会基本打字", "无需经验")):
            bad.append("非技术岗[不限学历+其它信号]")
        # 纯前端：前端词出现次数 >= 2 且没有后端词，说明主职责是前端
        fhits = [k for k in FRONT_ONLY_REQ if k.lower() in low]
        bhits = [k for k in ("java", "python", "后端", "spring", "接口", "api", "数据库", "sql",
                             "flask", "django", "全栈", "ai", "go", "golang") if k in low]
        if len(fhits) >= 2 and len(bhits) == 0:
            bad.append(f"纯前端[{'/'.join(fhits[:3])}]")
        # 职责段是运营/商务岗：出现非开发信号且整段无开发信号
        duty_low = duty[:400].lower()
        ndh = [k for k in NONDEV_DUTY if k in duty_low]
        if ndh and not any(s in duty_low for s in DEV_SIGNAL):
            bad.append(f"职责非开发岗[{'/'.join(ndh[:3])}]")
        if bad:
            dropped.append((t["label"], "；".join(bad)))
            continue
        t["jd_core_len"] = len(core)
        t["jd_hard_items"] = len(hard.split("\n")) if hard else 0
        kept.append(t)
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
