# -*- coding: utf-8 -*-
"""scan_cities.py — 在非广州城市扫技术实习岗。

城市码来源：output/boss_work/city_map.json（probe_cities.py 实测核验，不能凭记忆）。
用法: python scan_cities.py [城市名 ...]
不带参数 = 全部目标城市。
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate, extract_jobs
from scripts.wb import navigate, search_url

WORK = r'YOUR_HOME\output\boss_work'
CMAP = os.path.join(WORK, 'city_map.json')

# probe_cities.py 实测核验过的城市码
CITY_CODES = {
    "广州": "101280100",
    "深圳": "101280600",
    "珠海": "101280700",
    "佛山": "101280800",
    "惠州": "101280300",
    "东莞": "101281600",
    "中山": "101281700",
    "江门": "101281100",
    "某城市": "101281000",
    "肇庆": "101280900",
    "汕头": "101280500",
    "梅州": "101280400",
    "云浮": "101281400",
    "潮州": "101281500",
    "清远": "101281300",
    "河源": "101281200",
}

QUERIES = ["Java实习生", "软件开发实习生", "全栈开发实习生", "前端开发实习生",
           "后端开发实习生", "AI开发实习生"]

INTERN = ["实习", "见习", "应届", "校招", "管培", "培训生", "助理工程师", "工程师助理"]
TECH = ["java", "后端", "全栈", "前端", "开发", "算法", "测试", "ai", "软件",
        "大数据", "golang", "go开发", "嵌入式", "python", "web", "程序"]
BAD = ["硬件", "机械", "电路", "电气", "汽车", "汽修", "质检", "普工", "操作工",
       "销售", "客服", "文员", "行政", "人事", "财务", "教师", "置业", "中介",
       "储备干部", "生产", "包装", "模具", "数控", "叉车", "仓管", "采购",
       "会计", "律师", "医疗", "美容", "健身", "外贸", "跟单", "店铺", "导购",
       "安装", "维修", "施工", "厨师", "服务生", "导购员"]

# 已投递过的 jobId（含 10-20 那批 + 收藏夹 2 个 + 早前手动投的）
DONE_JOBS = {
    "JOBID019",   # 示例讯动U
    "JOBID027",   # 示例科技Y
    "JOBID046",   # 示例企业74
    "JOBID014",   # 示例云服务G
    "JOBID016",   # 示例传媒T
    "JOBID044",   # 示例科技D
    "JOBID013",   # AI软件开发实习生
    "5307e75f07a37e1e0nRz2N-4FlVW",   # 人工智能开发工程师
    "JOBID020",   # 示例企业74 全栈
    "JOBID041",   # 示例企业47
}


def norm(s):
    return re.sub(r"\s+", "", (s or "")).lower()


def keep(j, city):
    t = norm(j.get("title"))
    c = norm(j.get("city"))
    if city not in c:
        return False
    if not any(k in t for k in INTERN):
        return False
    if not any(k in t for k in TECH):
        return False
    if any(b in t for b in BAD):
        return False
    m = re.search(r"(\d+)-(\d+)K", j.get("salary", "") or "")
    if m and int(m.group(2)) > 9:
        return False
    return True


def log(m):
    print(m, flush=True)


def main():
    targets = sys.argv[1:] or ["深圳", "东莞", "佛山", "珠海", "惠州",
                               "中山", "江门", "某城市", "汕头", "肇庆"]
    found = {}
    for city in targets:
        code = CITY_CODES.get(city)
        if not code:
            log(f"!! 未知城市 {city}")
            continue
        for q in QUERIES:
            for page in (1, 2):
                try:
                    navigate(search_url(q, code) + (f"&page={page}" if page > 1 else ""))
                except Exception as e:
                    log(f"  {city}/{q}/p{page} 导航失败 {e}")
                    continue
                time.sleep(2.6)
                evaluate(r"""(function(){window.scrollTo(0,document.body.scrollHeight);return 1;})()""")
                time.sleep(1.2)
                jobs = extract_jobs()
                new = 0
                for j in jobs:
                    jid = j.get("jobId")
                    if not jid or jid in DONE_JOBS or jid in found:
                        continue
                    if not keep(j, city):
                        continue
                    found[jid] = j
                    new += 1
                if page == 1:
                    log(f"  {city} / {q}: 第1页 {len(jobs)} 条 → 命中累计 {len(found)}")
                if not jobs:
                    break
            time.sleep(0.8)

    out = os.path.join(WORK, "city_candidates.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(list(found.values()), f, ensure_ascii=False, indent=1)

    log(f"\n===== 命中 {len(found)} 个岗位 → {out}")
    for j in sorted(found.values(), key=lambda x: (x.get("city", ""), -int(
            re.search(r"(\d+)-(\d+)K", x.get("salary", "") or "").group(2)) if
            re.search(r"(\d+)-(\d+)K", x.get("salary", "") or "") else 0)):
        log(f"  {j.get('city',''):<6} {j.get('salary',''):<9} {j.get('title','')[:30]:<32} "
            f"{j.get('company','')[:20]:<22} {j.get('jobId')}")


if __name__ == "__main__":
    main()
