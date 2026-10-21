#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scan_gd.py — 广东省全境扫描技术实习岗候选（第三轮扩投用）。

与 scan_cities.py 的差别：
  1. 覆盖广东全部 21 个地级市（城市码用 probe_cities.py 实测值，不能凭记忆）；
  2. 搜索词扩到 12 个（补上 AI Agent / Python / TypeScript / 游戏 / 数据 / 测试等方向）；
  3. 已投 jobId 从 boss_manifest.json + 收藏夹/跨城目标清单动态读取，不再手写常量。

用法: python scan_gd.py [城市名 ...]     不带参数 = 全部广东城市
"""
import io
import json
import os
import re
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate, extract_jobs
from scripts.wb import navigate, search_url

WORK = r'YOUR_HOME\output\boss_work'
RECRUIT = r'YOUR_HOME\招聘'

# probe_cities.py 实测核验过的城市码
CITY_CODES = {
    "广州": "101280100", "深圳": "101280600", "珠海": "101280700",
    "佛山": "101280800", "惠州": "101280300", "东莞": "101281600",
    "中山": "101281700", "江门": "101281100", "某城市": "101281000",
    "肇庆": "101280900", "汕头": "101280500", "梅州": "101280400",
    "云浮": "101281400", "潮州": "101281500", "清远": "101281300",
    "河源": "101281200", "韶关": "101280200", "揭阳": "101281900",
    "汕尾": "101282100", "云浮2": "101281400",
}
# 揭阳 / 汕尾 / 韶关 的码需要实测，先用占位跳过
NEED_PROBE = {"揭阳", "汕尾", "韶关"}

QUERIES = ["Java实习生", "软件开发实习生", "全栈开发实习生", "后端开发实习生",
           "AI开发实习生", "Python开发实习生", "前端开发实习生",
           "算法实习生", "测试开发实习生", "数据开发实习生",
           "游戏开发实习生", "计算机实习生"]

# 每城翻几页（欠发达城市岗位少，翻 2 页够）
PAGES = int(os.environ.get("GD_PAGES", "3"))

INTERN = ["实习", "见习", "应届", "校招", "管培", "培训生", "助理工程师", "工程师助理"]
TECH = ["java", "后端", "全栈", "前端", "开发", "算法", "测试", "ai", "软件",
        "大数据", "golang", "go开发", "嵌入式", "python", "web", "程序",
        "agent", "智能体", "typescript", "数据", "游戏", "计算机"]
BAD = ["硬件", "机械", "电路", "电气", "汽车", "汽修", "质检", "普工", "操作工",
       "销售", "客服", "文员", "行政", "人事", "财务", "教师", "置业", "中介",
       "储备干部", "生产", "包装", "模具", "数控", "叉车", "仓管", "采购",
       "会计", "律师", "医疗", "美容", "健身", "外贸", "跟单", "店铺", "导购",
       "安装", "维修", "施工", "厨师", "服务生", "导购员",
       # 非技术方向
       "数据标注", "AI训练师", "运营", "营销", "出镜", "达人", "主播",
       "文案", "剪辑", "翻译", "精算", "汽修", "PCB", "物流", "美工",
       "室内", "置业顾问", "商务", "渠道", "加盟", "产品实习生", "产品助理"]


def norm(s):
    return re.sub(r"\s+", "", (s or "")).lower()


def load_done_ids():
    """已投 jobId：从 boss_manifest + 收藏夹/跨城目标清单里收集。"""
    done = set()
    try:
        d = json.load(io.open(os.path.join(RECRUIT, "boss_manifest.json"), encoding="utf-8"))
        for j in d.get("boss_jobs", []):
            if j.get("jobId"):
                done.add(j["jobId"])
    except (OSError, ValueError):
        pass
    for fn in ("fav_targets.json", "crosscity_targets.json", "favorites_fresh.json",
               "favorites_tag4.json"):
        try:
            data = json.load(io.open(os.path.join(WORK, fn), encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for it in data:
            if isinstance(it, dict):
                jid = it.get("encryptJobId") or it.get("jobId")
                if jid:
                    done.add(jid)
    return done


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
    targets = sys.argv[1:] or [c for c in CITY_CODES if c not in NEED_PROBE]
    done = load_done_ids()
    log(f"已投 jobId {len(done)} 个将被排除")
    out = os.path.join(WORK, "gd_candidates.json")
    found = {}
    # 支持续跑：已有结果先载入（增量落盘，中断后不丢前面的进度）
    if os.path.isfile(out):
        try:
            for j in json.load(io.open(out, encoding="utf-8")):
                if j.get("jobId"):
                    found[j["jobId"]] = j
            log(f"载入已有候选 {len(found)} 个（续跑）")
        except (OSError, ValueError):
            pass
    for city in targets:
        code = CITY_CODES.get(city)
        if not code:
            log(f"!! 未知城市 {city}")
            continue
        for q in QUERIES:
            for page in range(1, PAGES + 1):
                try:
                    navigate(search_url(q, code) + (f"&page={page}" if page > 1 else ""))
                except Exception as e:
                    log(f"  {city}/{q}/p{page} 导航失败 {e}")
                    continue
                time.sleep(2.6)
                evaluate(r"""(function(){window.scrollTo(0,document.body.scrollHeight);return 1;})()""")
                time.sleep(1.2)
                try:
                    jobs = extract_jobs()
                except Exception:
                    jobs = []
                for j in jobs:
                    jid = j.get("jobId")
                    if not jid or jid in done or jid in found:
                        continue
                    if not keep(j, city):
                        continue
                    found[jid] = j
                if not jobs:
                    break
            time.sleep(0.5)
        # 每城扫完增量落盘，中断也不丢进度
        with io.open(out, "w", encoding="utf-8") as f:
            json.dump(list(found.values()), f, ensure_ascii=False, indent=1)
        log(f"  {city}: 累计命中 {len(found)}  → 已落盘")

    log(f"\n===== 命中 {len(found)} 个岗位 → {out}")
    for j in sorted(found.values(), key=lambda x: (x.get("city", ""), x.get("company", ""))):
        log(f"  {j.get('city',''):<8} {j.get('salary',''):<10} {j.get('title','')[:32]:<34} "
            f"{j.get('company','')[:22]:<24} {j.get('jobId')}")


if __name__ == "__main__":
    main()
