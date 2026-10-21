# -*- coding: utf-8 -*-
"""wb_fav_filter.py — 从 68 个收藏里剔除「已投 / 已沟通过」的，输出候选。

已投判定：同一 jobId，或 同公司 + 同岗位名（jobId 每次搜索都会变，不能只靠 id）。
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb import call, navigate
from scripts.wb_fiximg import select_conv

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")
CHAT = "https://www.zhipin.com/web/geek/chat"

CONV = r"""(function(){
    var out=[];
    document.querySelectorAll('.friend-content').forEach(function(e,i){
        out.push({i:i, t:(e.textContent||'').replace(/\s+/g,' ').trim().slice(0,120)});
    });
    return JSON.stringify(out);
})()"""

POS = r"""(function(){
    var e=document.querySelector('.position-name');
    return e?(e.textContent||'').replace(/\s+/g,' ').trim():'';
})()"""

# 不投的方向
BAD_KW = ["数据标注", "AI训练师", "客服", "运营", "营销", "出镜", "达人", "销售",
          "HRBP", "人事", "财务", "会计", "教师", "教师岗", "电工", "普工", "仓管",
          "导购", "服务生", "置业", "实习运营", "产品实习生", "产品助理", "课程顾问",
          "文案", "剪辑", "主播", "翻译", "精算", "汽修", "硬件", "PCB", "结构",
          "物流", "采购", "外贸", "跟单", "美工", "平面", "室内", "置业顾问",
          "某桌面数据工具工程师", "商务", "渠道", "加盟", "校招-AI Agent 工程师"]


def norm(s):
    return re.sub(r"[\s（）()【】\[\]，,、/·\-—:：]", "", (s or "")).lower()


def main():
    # 1) 已沟通的会话 → 岗位名
    navigate(CHAT)
    time.sleep(5)
    raw = evaluate(CONV)
    convs = json.loads(raw) if isinstance(raw, str) else (raw or [])
    talked_pos, talked_comp = set(), {}
    for c in convs:
        sel, idx = select_conv(c["t"][:14])
        time.sleep(0.8)
        p = evaluate(POS)
        if p:
            talked_pos.add(norm(p))
            # 会话文本里第 2 段通常是「时间+招聘方+公司」
            m = re.search(r"[\u4e00-\u9fa5A-Za-z0-9]{2,8}(?=[A-Za-z]?[\u4e00-\u9fa5]{2,10}(HR|招聘|人事|经理|主管|专员|CEO|创始人|总经理|负责人|总监|主管|专员|猎头|老师|博士))", c["t"])
            if m:
                talked_comp.setdefault(norm(m.group(1)), set()).add(norm(p))
            else:
                for comp in (c["t"][:30],):
                    talked_comp.setdefault(norm(comp[:6]), set()).add(norm(p))
    print(f"已沟通会话 {len(convs)} 个，涉及岗位 {len(talked_pos)} 个")

    # 2) 收藏列表
    faves = json.load(open(os.path.join(WORK, "favorites_tag4.json"), encoding="utf-8"))
    # 已知本轮/上午已投的 jobId
    DONE_IDS = {
        "JOBID013", "5307e75f07a37e1e0nRz2N-4FlVW",
        "JOBID102", "JOBID103",
        "JOBID024", "JOBID032",
        "JOBID104", "JOBID004",
        "JOBID018", "JOBID105",
        "JOBID035", "JOBID038",
        "JOBID037", "JOBID010",
        "JOBID025", "6ae5137d0ee0ce0e0nN_2t21F1VZ",
        "JOBID019", "JOBID027",
        "JOBID046", "JOBID014",
        "JOBID016", "JOBID044",
        "JOBID020",
    }
    # 明确已投过的（公司+岗位）组合
    DONE_PAIRS = {
        ("示例广告AB", "AI软件开发实习生"), ("示例企业02", "人工智能开发工程师"),
        ("示例科技H", "实习生-Java开发实习生-佛山"), ("示例科技N集团有限公司", "AI Agent实习生"),
        ("示例科技K", "JAVA开发实习生（某城市）"), ("示例企业33", "在校Java开发实习生-东莞"),
        ("示例大厂J", "AI全栈开发实习生"), ("示例科技F", "Java 后端开发实习生"),
        ("示例科技G", "AI应用开发实习生（深圳）"), ("示例企业55", "TypeScript 全栈工程师（实习生）"),
        ("示例科技I", "实习生（Java开发）"), ("示例科技J", "软件全栈开发实习生-珠海"),
        ("示例企业62", "全栈开发实习生"), ("示例企业67", "企业智能体开发实习生"),
        ("示例科技L", "ai软件实习生"), ("示例科技M", "java软件开发实习生"),
        ("示例企业16", "软件开发实习生"), ("示例文化B", "AI应用与Agent工程实习生"),
        ("示例平台I", "产品实习生"), ("示例数据科技", "应届生/实习生(研发岗)"),
        ("示例科技C", "见习全栈开发工程师（有转正机会）"), ("示例网络E", "后端开发实习生"),
        ("广州示例软件F", "软件开发实习生"), ("示例讯动U", "java后端实习生"),
        ("示例科技V", "java开发实习生"), ("示例科技A", "后端JAVA开发工程师"),
        ("示例科技D", "游戏开发实习生（在校）"), ("示例云服务G", "AI 全栈开发工程师（实习岗）"),
    }

    fresh, skipped = [], []
    for f in faves:
        jid = f.get("encryptJobId")
        title = f.get("jobName") or ""
        comp = f.get("brandName") or ""
        if jid in DONE_IDS or (comp, title) in DONE_PAIRS:
            skipped.append((comp, title, "已投"))
            continue
        if norm(title) in talked_pos:
            skipped.append((comp, title, "同岗位已沟通"))
            continue
        if any(k in title for k in BAD_KW):
            skipped.append((comp, title, "方向不匹配"))
            continue
        fresh.append(f)

    out = os.path.join(WORK, "favorites_fresh.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(fresh, f, ensure_ascii=False, indent=1)
    print(f"\n收藏 {len(faves)} → 可投候选 {len(fresh)}，剔除 {len(skipped)}")
    print(f"→ {out}\n")
    for f in fresh:
        print(f"  {f.get('cityName',''):<6} {f.get('jobSalary',''):<10} {f.get('jobName','')[:30]:<32} "
              f"{f.get('brandName','')[:20]:<22} {f.get('bossName',''):<8} {f.get('encryptJobId')}")
    print("\n剔除明细：")
    for c, t, why in skipped:
        print(f"  {c[:20]:<22}{t[:30]:<32}{why}")


if __name__ == "__main__":
    main()
