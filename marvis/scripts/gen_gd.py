#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_gd.py — 为广东全境扫出的新候选岗位生成定制话术归档 + 投递目标清单。

话术模板复用 gen_fav.py 的 7 套（方向 → 模板），
数字全部来自实测：某网页小游戏合集、两百余个 TS 文件 / 数万行、数十个 Vitest 测试文件、
18 个 Controller / 70 个 RESTful 接口 / 11 张业务表、5 个 AI 端点 / 1–3 秒 / < 50 毫秒。
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, r"YOUR_REPO\marvis")
from scripts.gen_fav import (TPL, SHORT, SHORT_TAIL, SHORT_END, IMGS_GENERIC,
                             IMGS_AICODE, build_txt)

RECRUIT = r"YOUR_HOME\招聘"
WORK = r"YOUR_HOME\output\boss_work"

# 岗位标题 → 方向模板（按优先级从上到下）
RULES = [
    ("T_AICODE", ["codex", "copilot", "ai coding", "aicoding", "vibe coding", "vibecoding",
                  "ai编程", "ai 编程", "ai工具编程"]),
    ("T_AI", ["智能体", "agent", "大模型", "llm", "aigc", "深度学习", "机器学习",
              "算法", "nlp", "多模态", "ai应用", "ai 应用", "ai开发", "ai 开发",
              "人工智能", "ai实习生", "ai 实习生"]),
    ("T_GAME", ["游戏", "unity", "ue5", "unreal", "cocos"]),
    ("T_PY", ["python", "爬虫", "django", "flask", "pandas", "数据挖掘"]),
    ("T_DATA", ["数据库", "sql", "数仓", "数据仓库", "数据分析", "数据开发", "数据工程",
                "大数据", "bi工程师", "etl", "大数据开发"]),
    ("T_FULL", ["全栈", "fullstack", "full stack", "前后端"]),
    ("T_JAVA", ["java", "后端", "服务端", "spring", "golang", "go开发", "go 开发",
                "php", "python后端", "node", "开发工程师", "软件工程", "研发工程师",
                "软件开发", "程序设计", "计算机"]),
]

# 非技术方向 / 与本人方向不符
BAD_TITLE = [
    # 泛运营与销售
    "数据标注", "ai训练师", "ai训练", "训练实习生", "客服", "运营", "营销", "出镜",
    "达人", "销售", "文案", "剪辑", "主播", "翻译", "精算", "商务", "渠道", "加盟",
    # 行政职能
    "人事", "财务", "教师", "老师", "会计", "行政", "文员", "产品助理", "产品实习",
    "售后", "置业", "中介", "储备干部",
    # 硬件与工业
    "硬件", "机械", "电路", "电气", "汽车", "汽修", "质检", "普工", "操作工", "生产",
    "包装", "模具", "数控", "叉车", "仓管", "采购", "汽配", "工业", "自动化测试",
    "计量", "校准", "检测", "可靠性", "芯片", "半导体", "材料", "mes", "plc",
    # 嵌入式 / 底层 / 移动端
    "嵌入式", "单片机", "鸿蒙", "安卓", "c++", "驱动", "ic设计", "射频", "结构",
    "硬件测试", "电机", "光学", "图像处理工程师",
    # 算法岗（需要模型训练背景，本人没做过）
    "视觉算法", "图像算法", "计算机视觉", "机器人规控", "运控算法", "运动控制",
    "标定", "语音算法", "nlp算法", "推荐算法", "算法研究", "算法工程师（",
    # 游戏非程序
    "游戏策划", "游戏原画", "游戏特效", "游戏ui", "游戏美术", "游戏投放",
    "游戏产品", "游戏玩家", "游戏体验",
    # 设计/内容
    "ui/ux", "ui设计", "ue", "动画", "美术", "短剧", "漫剧", "视频制作", "制作实习生",
    # 其他
    "外贸", "跟单", "导购", "安装", "维修", "施工", "厨师", "服务生", "导购员",
    "医疗", "美容", "健身", "法律", "律师", "安装工程",
    # 岗位太泛
    "软件工程师助理", "工程师助理", "助理工程师（", "程序员实习生",
]

# 需要模型/算法背景的关键词（出现在标题里就排除）
ALGO_HARD = ["算法", "机器学习", "深度学习", "计算机视觉", "视觉", "图像",
             "机器人", "无人机", "大模型算法", "推荐", "nlp", "cv"]
# 但这些是「应用落地」方向，可以投
ALGO_OK_CTX = ["ai应用", "ai 应用", "agent", "智能体", "llm", "aigc",
               "ai开发", "ai 开发", "ai研发", "ai 研发", "ai全栈", "ai 全栈",
               "ai工程", "ai 工程", "ai开发实习生", "大模型应用", "数据开发"]

# 明显是社招（要求 1 年以上经验）
SOCIAL = ["社招", "1-3年", "1-3 年", "3-5年", "3-5 年", "经验不限"]

# 届别：只投面向本人届别或不限届的岗位。
# 本人届别由环境变量 GRADE_OK 提供（例：GRADE_OK=2026）；不设置则不做届别筛除。
GRADE = os.environ.get("GRADE_OK", "").strip()
OTHER_GRADE = [g for g in ("25", "26", "28")
               if not GRADE or g != GRADE[2:]]
OTHER_GRADE = ([f"{g}届" for g in OTHER_GRADE] + [f"{g} 届" for g in OTHER_GRADE] +
               [f"{g}年" for g in OTHER_GRADE])

# 纯前端（本人主方向是后端 / AI）
FRONT_ONLY = ["前端", "web前端", "web 前端", "html", "react", "vue3", "vue工程师"]


def norm(s):
    return re.sub(r"[\s（）()【】\[\]，,、/·\-—:：~～!！?？+]", "", (s or "")).lower()


def pick_tpl(title, jd=""):
    t = (title or "").lower() + " " + (jd or "").lower()
    for key, kws in RULES:
        for k in kws:
            if k in t:
                return key
    return "T_JAVA"


def safe(s):
    """把公司/岗位名里的文件系统非法字符换掉。"""
    s = re.sub(r'[\\/:*?"<>|]', "-", s or "")
    s = s.replace(" ", "")
    return s[:40]


MAX_TOTAL = int(os.environ.get("GD_MAX", "32"))
# 每城名额：按岗位密度分配（深圳/广州最多），保证小城市也有覆盖
CITY_QUOTA = {
    "深圳": 7, "广州": 5,
    "佛山": 3, "东莞": 3, "珠海": 3, "惠州": 3,
    "中山": 2, "汕头": 2, "江门": 2, "肇庆": 2, "某城市": 2,
    "梅州": 1, "云浮": 1, "潮州": 1, "清远": 1, "河源": 1, "韶关": 1,
}
PER_CITY_OTHER = 1


def score(j, tpl):
    """给候选打分：实习岗 + 薪资高 + 方向对口 + 届别对口。"""
    s = 0
    title = (j.get("title") or "")
    low = title.lower()
    if GRADE and (f"{GRADE[2:]}届" in title or GRADE in title):
        s += 30
    if "实习" in title:
        s += 20
    if any(k in low for k in ("应届", "毕业")) or (GRADE and GRADE in low):
        s += 5
    # 技术方向权重
    s += {"T_JAVA": 20, "T_AI": 22, "T_AICODE": 22, "T_FULL": 18,
          "T_PY": 16, "T_GAME": 16, "T_DATA": 14}.get(tpl, 10)
    sal = j.get("salary") or ""
    import re as _re
    m = _re.search(r"(\d+)-(\d+)元/天", sal)
    if m:
        hi = int(m.group(2))
    else:
        m2 = _re.search(r"(\d+)-(\d+)元/时", sal)
        if m2:
            hi = int(m2.group(2)) * 8          # 元/时 → 折算元/天
        else:
            m3 = _re.search(r"(\d+)-(\d+)K", sal)
            if m3:
                hi = int(m3.group(2)) * 30      # K/月 → 折算日薪量级
            else:
                hi = 0
    if hi >= 400:
        s += 42
    elif hi >= 300:
        s += 36
    elif hi >= 200:
        s += 30
    elif hi >= 150:
        s += 22
    elif hi >= 100:
        s += 14
    else:
        s += 5
    return s


# 手动固定保留的高价值岗位（排序并列会被挤掉）
MANUAL = [
    ("c113d0a55411d55a0nd43N-4ElVZ", "T_JAVA"),   # 示例大厂K 后端开发实习生 450-650元/天 深圳
    ("JOBID007", "T_JAVA"),   # 示例企业07 日常实习 后端 400-450元/天 深圳
    ("df4f75fc56bb1b440nVz29-9GVZX", "T_AI"),     # 示例企业46 实习研发工程师 350-400元/天 广州
]


def main():
    src = os.path.join(WORK, "gd_candidates.json")
    cands = json.load(io.open(src, encoding="utf-8"))

    # 已投过的 jobId
    done = set()
    try:
        d = json.load(io.open(os.path.join(RECRUIT, "boss_manifest.json"), encoding="utf-8"))
        for j in d.get("boss_jobs", []):
            if j.get("jobId"):
                done.add(j["jobId"])
    except (OSError, ValueError):
        pass
    for fn in ("fav_targets.json", "crosscity_targets.json"):
        try:
            for t in json.load(io.open(os.path.join(WORK, fn), encoding="utf-8")):
                if t.get("jobId"):
                    done.add(t["jobId"])
        except (OSError, ValueError):
            pass

    seen_pairs = set()
    pool = []
    skipped = []
    for j in cands:
        jid = j.get("jobId")
        title = j.get("title") or ""
        comp = j.get("company") or ""
        city = j.get("city") or ""
        if jid in done:
            skipped.append((comp, title, "已投过"))
            continue
        low = title.lower()
        if any(b.lower() in low for b in BAD_TITLE):
            skipped.append((comp, title, "方向不匹配"))
            continue
        if any(s in title for s in SOCIAL):
            skipped.append((comp, title, "社招非实习"))
            continue
        if any(g in title for g in OTHER_GRADE):
            skipped.append((comp, title, "届别不符"))
            continue
        # 纯前端岗位排除；含「全栈」等组合词的不算纯前端
        if any(f in low for f in FRONT_ONLY) and "全栈" not in title and "前后端" not in title:
            skipped.append((comp, title, "纯前端"))
            continue
        # 测试岗排除（除非是「测试开发」，那是开发岗）
        if "测试" in title and "测试开发" not in title:
            skipped.append((comp, title, "测试岗非开发"))
            continue
        # 硬件/嵌入式类公司名（含「电子/光电/半导体/精密」）的岗位排除
        if any(h in comp for h in ("电子", "光电", "半导体", "精密", "科技股份")):
            skipped.append((comp, title, "硬件/半导体公司"))
            continue
        # 外包/分公司/档案服务/培训类，排除
        if any(h in comp for h in ("分公司", "档案服务", "人力资源", "外包", "劳务")):
            skipped.append((comp, title, "外包/分公司类"))
            continue
        if "培训生" in title or "培训" in title:
            skipped.append((comp, title, "培训类岗位"))
            continue
        # 算法岗：除非是 AI 应用 / Agent / 数据开发落地方向
        if any(a in low for a in ALGO_HARD) and not any(o in low for o in ALGO_OK_CTX):
            skipped.append((comp, title, "算法岗（需模型背景）"))
            continue
        pair = (norm(comp), norm(title))
        if pair in seen_pairs:
            skipped.append((comp, title, "重复"))
            continue
        seen_pairs.add(pair)
        tpl = pick_tpl(title)
        pool.append((score(j, tpl), j, tpl))
        skipped.append((comp, title, "候选"))

    # 按分数排序后取前 N，且每城最多 PER_CITY 个
    pool.sort(key=lambda x: -x[0])
    picked = []
    per = {}
    manual_jids = {m[0] for m in MANUAL}
    # 手动固定的先占位
    byid = {j.get("jobId"): j for j in cands}
    for jid, tpl in MANUAL:
        j = byid.get(jid)
        if not j:
            continue
        c = j.get("city") or ""
        picked.append((score(j, tpl) + 1000, j, tpl))
        per[c] = per.get(c, 0) + 1
    for sc, j, tpl in pool:
        if j.get("jobId") in manual_jids:
            continue
        c = j.get("city") or ""
        cap = CITY_QUOTA.get(c, PER_CITY_OTHER)
        if per.get(c, 0) >= cap:
            continue
        per[c] = per.get(c, 0) + 1
        picked.append((sc, j, tpl))
        if len(picked) >= MAX_TOTAL:
            break

    targets = []
    for sc, j, tpl in picked:
        jid = j.get("jobId")
        title = j.get("title") or ""
        comp = j.get("company") or ""
        city = j.get("city") or ""
        folder = f"广东-{safe(comp)}-{safe(title)}-{safe(city)}"
        d = os.path.join(RECRUIT, folder)
        os.makedirs(d, exist_ok=True)
        txt = build_txt(comp, title, city, j.get("salary", ""), tpl)
        imgs = IMGS_AICODE if tpl == "T_AICODE" else IMGS_GENERIC
        src_pdf = (r"AI Coding全栈工程师\你的名字-AICoding全栈工程师.pdf（AI Coding 方向 2 页）"
                   if imgs is IMGS_AICODE else r"研发实习生\候选人-实习.pdf（全量版 3 页 11 项目）")
        with io.open(os.path.join(d, "新建 文本文档.txt"), "w", encoding="utf-8") as fp:
            fp.write(txt)
            fp.write(f"简历：{src_pdf}\n")
        targets.append(dict(label=folder, folder=folder, jobId=jid, city=city,
                            company=comp, position=title, salary=j.get("salary", ""),
                            tpl=tpl, imgs=imgs, score=sc))
        print(f"  [{sc:>3}] {folder:<52} {city:<6} {j.get('salary',''):<11} {tpl}")

    out = os.path.join(WORK, "gd_targets.json")
    with io.open(out, "w", encoding="utf-8") as f:
        json.dump(targets, f, ensure_ascii=False, indent=1)
    print(f"\n候选 {len(cands)} → 可投 {len(pool)} → 选中 {len(targets)}"
          f"（上限 {MAX_TOTAL}，每城按岗位密度分配名额）")
    print(f"城市分布：{per}")
    print(f"→ {out}")


if __name__ == "__main__":
    main()
