#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 BOSS 直聘渠道的岗位清单（可执行 manifest）。

只收录走 BOSS 直聘的岗位；51job 与邮件投递的另行处理。
"""
import io
import json
import os
import re
import sys

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SKILL_DIR)
os.environ.setdefault("BOSS_WORK_DIR", SKILL_DIR)

from scripts.recruit_greetings import load_index

ROOT = r"YOUR_HOME\招聘"
OUT = os.path.join(ROOT, "boss_manifest.json")

# 从话术文件头部解析：公司 · 岗位 / 地址 / 薪资
def head_meta(text):
    lines = [l.strip() for l in text.splitlines()[:12] if l.strip()]
    first = lines[0] if lines else ""
    company = ""
    m = re.match(r"^\s*([^（(·]+)", first)
    if m:
        company = m.group(1).strip()
    title = ""
    if "·" in first:
        title = first.split("·", 1)[1].strip()
    salary = ""
    city = ""
    for l in lines[1:]:
        if not salary and ("薪资" in l or "元/天" in l or "K/月" in l):
            salary = l
        if not city and ("地址" in l or "地点" in l):
            city = l
    return company, title, salary, city

def channel_of(text):
    if "51job" in text or "前程无忧" in text:
        return "51job"
    if "邮件投递" in text:
        return "email"
    return "boss"

items = []
for folder in sorted(os.listdir(ROOT)):
    fdir = os.path.join(ROOT, folder)
    if not os.path.isdir(fdir):
        continue
    txt = ""
    for fn in os.listdir(fdir):
        if fn.lower().endswith(".txt"):
            txt = io.open(os.path.join(fdir, fn), encoding="utf-8").read()
            break
    if not txt:
        continue
    ch = channel_of(txt)
    company, title, salary, city = head_meta(txt)
    pdf = ""
    for fn in os.listdir(fdir):
        if fn.lower().endswith(".pdf"):
            pdf = os.path.join(fdir, fn)
            break
    items.append({
        "folder": folder,
        "channel": ch,
        "company": company,
        "title": title or folder,
        "salary": salary,
        "city": city,
        "greeting_file": os.path.join(fdir, "新建 文本文档.txt"),
        "pdf": pdf,
    })

boss = [i for i in items if i["channel"] == "boss"]
other = [i for i in items if i["channel"] != "boss"]

manifest = {
    "generated": "auto",
    "target_city": "广州",
    "city_code": "101280100",
    "boss_jobs": boss,
    "other_channels": other,
}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)

print(f"BOSS 直聘岗位 {len(boss)} 个 → {OUT}\n")
print(f"{'公司':<22} {'岗位':<26} {'话术':>4} {'PDF':>4}")
print("-" * 66)
for i in boss:
    g = i["greeting_file"]
    glen = len(io.open(g, encoding="utf-8").read()) if os.path.isfile(g) else 0
    print(f"{i['company'][:20]:<22} {i['title'][:24]:<26} {glen:>4} {'有' if i['pdf'] else '无':>4}")

print(f"\n其他渠道 {len(other)} 个：")
for i in other:
    print(f"  [{i['channel']:<6}] {i['company'][:18]:<20} {i['title'][:28]}")
