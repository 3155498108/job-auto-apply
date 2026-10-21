#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""jd_filter.py — 只看 JD 的「职责 + 要求」两段，做硬性劝退。

关键：只在职责/要求段里匹配关键词，**不扫公司介绍**——否则会出现
「示例企业44」因为公司业务是「店铺运营」被误判成运营岗这种假阳性。

用法: python jd_filter.py <targets.json> <out.json>
"""
import io
import json
import os
import re
import sys

WORK = r"YOUR_HOME\output\boss_work"

# (规则名, 关键词列表) —— 命中任意一条即劝退
REJECT = [
    ("学历门槛-硕士", ["硕士及以上", "硕士学历", "研究生及以上", "博士", "985高校", "985 高校",
                       "成绩前20%", "成绩前 20%"]),
    ("硬件/嵌入式", ["stm32", "gd32", "mcu", "寄存器", "datasheet", "mipi", "lvds", "相机模组",
                     "电机控制", "伺服驱动", "变频器", "原理图", "示波器", "逻辑分析仪",
                     "嵌入式", "硬件调试", "上位机", "pcb"]),
    ("C系语言", ["c语言", "c++", "c#", "objective-c", "汇编语言"]),
    ("Unity/引擎", ["unity", "u3d", "unreal", "cocos", "egret", "game jam"]),
    ("视觉/图形库", ["opencv", "qt", "mfc", "directx", "vulkan", "openGL", "shader"]),
    ("算法研究", ["视觉算法", "图像算法", "计算机视觉", "cuda", "pytorch", "tensorflow", "顶会",
                 "研究方向", "论文发表", "模型微调", "预训练", "强化学习", "扩散模型"]),
    ("社招经验", ["1-3年", "1-3 年", "3-5年", "3-5 年", "3年以上", "3 年以上", "两年以上",
                 "2年以上", "有工作经验", "已毕业", "正式员工"]),
    ("非技术岗", ["引导玩家", "会基本打字", "接受小白", "熟悉办公软件", "无学历", "不限学历",
                 "数据标注", "数据采集员", "审核采集", "接听电话", "陌拜", "地推", "客服专员",
                 "招聘专员", "人事助理", "主播", "剪辑"]),
    ("底薪/无责底薪", ["无责底薪", "高提成", "拉人头", "日结", "小时工"]),
]

# 明显偏纯前端的（只在前端是主职责时才劝退）
FRONT_ONLY_REQ = ["react", "vue", "angular", "小程序开发", "flutter", "android", "ios", "web前端"]


def split_jd(jd):
    """只取「职责 + 要求」两段，丢掉公司介绍。"""
    i = jd.find("岗位职责")
    if i < 0:
        i = jd.find("工作职责")
    if i < 0:
        i = jd.find("工作内容")
    if i < 0:
        i = jd.find("职位描述")
    k = jd.find("任职要求")
    if k < 0:
        k = jd.find("岗位要求")
    if k < 0:
        k = jd.find("职位要求")
    if i < 0 and k < 0:
        return jd[:900]
    duty = jd[i:k] if i >= 0 and k > i else (jd[i:i + 900] if i >= 0 else "")
    req = jd[k:k + 900] if k >= 0 else ""
    return (duty + "\n" + req).strip()


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "gd2_targets.json"
    dst = sys.argv[2] if len(sys.argv) > 2 else "gd2_kept.json"
    targets = json.load(io.open(os.path.join(WORK, src), encoding="utf-8"))
    jds = json.load(io.open(os.path.join(WORK, "jd_text.json"), encoding="utf-8"))
    kept, dropped = [], []
    for t in targets:
        jd = (jds.get(t["label"]) or {}).get("jd", "")
        if len(jd) < 120:
            dropped.append((t["label"], "JD 未抓全"))
            continue
        core = split_jd(jd)
        low = core.lower()
        bad = []
        for name, kws in REJECT:
            hit = [k for k in kws if k.lower() in low]
            if hit:
                bad.append(f"{name}[{'/'.join(hit[:3])}]")
        # 纯前端：前端词出现次数 >= 3 且没有后端词，说明主职责是前端
        fhits = [k for k in FRONT_ONLY_REQ if k.lower() in low]
        bhits = [k for k in ("java", "python", "后端", "spring", "接口", "api", "数据库", "sql",
                             "flask", "django", "全栈", "ai") if k in low]
        if len(fhits) >= 2 and len(bhits) == 0:
            bad.append(f"纯前端[{'/'.join(fhits[:3])}]")
        if bad:
            dropped.append((t["label"], "；".join(bad)))
            continue
        t["jd_core_len"] = len(core)
        kept.append(t)
    json.dump(kept, io.open(os.path.join(WORK, dst), "w", encoding="utf-8"),
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
