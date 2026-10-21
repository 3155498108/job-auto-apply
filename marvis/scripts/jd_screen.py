#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""jd_screen.py — 按 JD 正文做「能不能做」二次筛选。

标题会骗人：「软件开发实习生」可能是相机模组驱动（要硕士 + C + STM32）。
本脚本把每条 JD 的「岗位职责 / 任职要求」抠出来，打上风险标签，供人工/规则筛。
"""
import io
import json
import os
import re
import sys

WORK = r"YOUR_HOME\output\boss_work"

# 硬性劝退信号：命中就基本不是本人能做的岗
HARD = {
    "要硕士": ["硕士及以上", "硕士学历", "研究生及以上", "博士"],
    "硬件嵌入式": ["stm32", "gd32", "mcu", "soc", "嵌入式", "寄存器", "datasheet", "mipi", "lvds",
                   "isp参数", "硬件调试", "pcb", "电路", "示波器", "逻辑分析仪", "rtos", "驱动开发"],
    "C/C++/C#": ["c语言", "c/c++", "c++", "c#", "objective-c", "汇编"],
    "纯前端栈": ["react", "vue", "angular", "小程序开发", "flutter", "android开发", "ios开发",
                 "webgl", "three.js", "unity3d", "unreal", "cocos"],
    "算法研究": ["顶会", "论文", "研究方向", "硕博", "模型训练", "微调", "预训练", "强化学习",
                 "pytorch", "tensorflow", "opencv", "cuda", "sgd", "扩散模型", "推荐算法", "nlp算法",
                 "计算机视觉", "视觉算法", "图像算法", "大模型算法"],
    "社招经验": ["3年以上", "5年以上", "两年以上", "有正式实习", "已毕业", "1-3年"],
    "非技术": ["销售", "客服", "运营", "人事", "财务", "行政", "教师", "主播", "剪辑", "文案",
               "法务", "法务专员", "审核专员", "标注"],
}

# 软性加分：命中说明岗位方向跟本人技术栈对得上
GOOD = {
    "Java后端": ["java", "spring", "springboot", "spring boot", "mybatis", "mysql", "redis", "后端"],
    "Python": ["python", "flask", "django", "fastapi", "pandas", "脚本"],
    "AI应用": ["ai agent", "agent", "大模型", "llm", "aigc", "提示词", "spring ai", "deepseek", "智能体"],
    "全栈": ["全栈", "前后端", "联调", "独立交付", "完整项目"],
    "数据": ["sql", "数据开发", "数仓", "etl", "数据分析", "bi"],
    "测试开发": ["测试开发", "单元测试", "自动化测试", "pytest", "vitest", "接口测试", "质量"],
    "工程协作": ["git", "文档", "团队协作", "沟通", "自驱", "学习能力", "复用", "交接"],
    "AI Coding": ["ai编程", "ai coding", "claude", "codex", "copilot", "cursor", "vibe coding"],
    "游戏": ["游戏", "unity", "小游戏", "玩法", "关卡"],
}


def split_jd(jd):
    """把 JD 拆成 职责段 / 要求段。"""
    i = jd.find("岗位职责")
    if i < 0:
        i = jd.find("工作职责")
    if i < 0:
        i = jd.find("工作内容")
    k = jd.find("任职要求")
    if k < 0:
        k = jd.find("岗位要求")
    if k < 0:
        k = jd.find("职位要求")
    duty = jd[i:k] if i >= 0 and k > i else jd[:600]
    req = jd[k:k + 900] if k >= 0 else ""
    return duty.strip(), req.strip()


def main():
    tfile = sys.argv[1] if len(sys.argv) > 1 else "gd2_targets.json"
    targets = json.load(io.open(os.path.join(WORK, tfile), encoding="utf-8"))
    jds = json.load(io.open(os.path.join(WORK, "jd_text.json"), encoding="utf-8"))
    for t in targets:
        jd = (jds.get(t["label"]) or {}).get("jd", "")
        duty, req = split_jd(jd)
        hard = []
        for name, kws in HARD.items():
            hit = [k for k in kws if k.lower() in jd.lower()]
            if hit:
                hard.append(f"{name}({'/'.join(hit[:3])})")
        good = []
        for name, kws in GOOD.items():
            hit = [k for k in kws if k.lower() in jd.lower()]
            if hit:
                good.append(f"{name}({'/'.join(hit[:3])})")
        print("=" * 100)
        print(f"{t['label']}  |  {t['salary']}")
        print(f"  风险：{'、'.join(hard) if hard else '无'}")
        print(f"  对口：{'、'.join(good) if good else '无'}")
        print(f"  要求摘要：{req[:320] if req else duty[:320]}")
    print("\n" + "=" * 100)


if __name__ == "__main__":
    main()
