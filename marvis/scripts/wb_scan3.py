#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_scan3.py — 第三批候选池扫描：城市 × 关键词 × 分页。

与 scan_cities.py 的区别：
  1) 排除口径从硬编码 10 个 jobId 改为读 manifest + 全部 targets/final json（覆盖 112 条已投）
  2) 关键词池扩容
  3) 每 5 次导航做一次重置锚点，规避 Vue Router 缓存劫持（B21）

只读采集，不投递。
用法: python wb_scan3.py [--cities 广州,深圳] [--queries "Java实习生,软件开发实习生"] [--pages 2]
"""
import io
import json
import os
import re
import sys
import time

sys.path.insert(0, r"YOUR_REPO\marvis")
from scripts.webbridge_client import evaluate, extract_jobs
from scripts.wb import navigate, search_url

WORK = r"YOUR_HOME\output\boss_work"
RECRUIT = r"YOUR_HOME\招聘"

CITY_CODES = {
    "广州": "101280100", "深圳": "101280600", "珠海": "101280700", "佛山": "101280800",
    "惠州": "101280300", "东莞": "101281600", "中山": "101281700", "江门": "101281100",
    "某城市": "101281000", "肇庆": "101280900", "汕头": "101280500", "梅州": "101280400",
    "云浮": "101281400", "潮州": "101281500", "清远": "101281300", "河源": "101281200",
}

DEFAULT_QUERIES = [
    "Java实习生", "后端开发实习生", "软件开发实习生", "全栈开发实习生",
    "AI开发实习生", "Python开发实习生", "数据开发实习生", "测试开发实习生",
    "Go开发实习生", "大模型应用实习生", "SpringBoot实习生", "Web开发实习生",
]

INTERN = ["实习", "见习", "应届", "校招", "管培", "培训生", "助理工程师", "工程师助理", "trainee"]
TECH = ["java", "后端", "全栈", "前端", "开发", "算法", "测试", "ai", "软件",
        "大数据", "golang", "go开发", "python", "web", "程序", "大模型", "llm", "数据"]
BAD = ["硬件", "机械", "电路", "电气", "汽车", "汽修", "质检", "普工", "操作工",
       "销售", "客服", "文员", "行政", "人事", "财务", "教师", "置业", "中介",
       "储备干部", "生产", "包装", "模具", "数控", "叉车", "仓管", "采购",
       "会计", "律师", "医疗", "美容", "健身", "外贸", "跟单", "店铺", "导购",
       "安装", "维修", "施工", "厨师", "服务生", "导购员", "标注", "客服", "外呼"]
# 硬件/外包类公司名
BAD_COMP = ["电子", "光电", "半导体", "精密", "科技股份", "分公司", "档案服务",
            "人力资源", "外包", "劳务", "中介"]


def norm(s):
    return re.sub(r"\s+", "", (s or "")).lower()


def load_done():
    """所有已投 jobId：manifest + 各批 targets/final/result。"""
    done = set()
    try:
        m = json.load(io.open(os.path.join(RECRUIT, "boss_manifest.json"), encoding="utf-8"))
        for j in m.get("boss_jobs", []):
            if j.get("jobId"):
                done.add(j["jobId"])
    except (OSError, ValueError):
        pass
    for fn in os.listdir(WORK):
        if not fn.endswith(".json"):
            continue
        # 只认「真的投出去了」的记录：投递结果 / 会话核对。
        # 旧口径把 targets/final/kept 也算进来 → 选好但还没投的岗位被当成已投，
        # 同一批重复跑选岗会把它们全部误排除（实测 AI 批第二次跑池子从 44 掉到 22）。
        if not re.search(r"result|check", fn):
            continue
        try:
            data = json.load(io.open(os.path.join(WORK, fn), encoding="utf-8"))
        except (OSError, ValueError):
            continue
        items = data if isinstance(data, list) else list(data.values())
        for it in items:
            if isinstance(it, dict) and it.get("jobId"):
                done.add(it["jobId"])
    return done


def keep(j):
    t = norm(j.get("title"))
    c = norm(j.get("company"))
    if not any(k in t for k in INTERN):
        return False
    if not any(k in t for k in TECH):
        return False
    if any(b in t for b in BAD):
        return False
    if any(h in c for h in BAD_COMP):
        return False
    m = re.search(r"(\d+)-(\d+)K", j.get("salary", "") or "")
    if m and int(m.group(2)) > 9:
        return False
    return True


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def main():
    args = sys.argv[1:]
    cities = ["广州", "深圳", "东莞", "佛山", "珠海", "惠州", "中山"]
    queries = list(DEFAULT_QUERIES)
    pages = 2
    for i, a in enumerate(args):
        if a == "--cities" and i + 1 < len(args):
            cities = args[i + 1].split(",")
        elif a == "--queries" and i + 1 < len(args):
            queries = args[i + 1].split(",")
        elif a == "--pages" and i + 1 < len(args):
            pages = int(args[i + 1])

    done = load_done()
    log(f"已投 jobId {len(done)} 个")
    found = {}
    seen_pair = set()
    nav = 0

    for city in cities:
        code = CITY_CODES.get(city)
        if not code:
            log(f"!! 未知城市 {city}")
            continue
        for q in queries:
            for page in range(1, pages + 1):
                try:
                    navigate(search_url(q, code) + (f"&page={page}" if page > 1 else ""))
                    nav += 1
                except Exception as e:
                    log(f"  {city}/{q}/p{page} 导航失败 {e}")
                    continue
                time.sleep(2.4)
                try:
                    evaluate(r"""(function(){window.scrollTo(0,document.body.scrollHeight);return 1;})()""")
                except Exception:
                    pass
                time.sleep(1.0)
                try:
                    jobs = extract_jobs()
                except Exception as e:
                    log(f"  {city}/{q}/p{page} 提取失败 {e}")
                    continue
                add = 0
                for j in jobs:
                    jid = j.get("jobId")
                    if not jid or jid in done or jid in found:
                        continue
                    if not keep(j):
                        continue
                    pair = (norm(j.get("company")), norm(j.get("title")))
                    if pair in seen_pair:
                        continue
                    seen_pair.add(pair)
                    j["_city"] = city
                    j["_query"] = q
                    found[jid] = j
                    add += 1
                log(f"  {city}/{q}/p{page}: {len(jobs)} 条 → 新增 {add}｜累计 {len(found)}")
                if not jobs:
                    break
                if nav % 5 == 0:
                    time.sleep(2.0)   # B21：每 5 次导航让 SPA 缓存自然重置
            time.sleep(0.8)

    out = os.path.join(WORK, "batch3_candidates.json")
    with io.open(out, "w", encoding="utf-8") as f:
        json.dump(list(found.values()), f, ensure_ascii=False, indent=1)
    log(f"\n===== 命中 {len(found)} → {out}")
    for j in sorted(found.values(), key=lambda x: (x.get("_city", ""), x.get("company", ""))):
        log(f"  {j.get('_city',''):<5} {j.get('salary',''):<10} {j.get('title','')[:30]:<32} "
            f"{j.get('company','')[:20]:<22} {j.get('jobId')}")


if __name__ == "__main__":
    main()
