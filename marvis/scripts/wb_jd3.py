#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_jd3.py — 第三批 JD 抓取，带 Vue Router 缓存劫持防护。

相对 wb_jd.py 的加固（来自上游坑位 B21 / B1）：
  1) 每 5 次 job_detail 导航后重置回搜索页（搜索页每次 navigate 都完整刷新 DOM，
     是天然的重置锚点），避免 URL 已是 jobId C、页面还渲染 jobId B；
  2) 抓完立即比对详情页岗位名与目标岗位名，相似度低于阈值 → 重抓一次，
     仍不匹配则标记 mismatch（后续一律按「从严」处理，不投）；
  3) 登录态自检：被风控踢到 /web/user/ 立即停批。

用法: python wb_jd3.py <targets.json> [label ...]
输出: output/boss_work/jd_text.json（增量，已有 JD>200 字跳过）
"""
import difflib
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate
from scripts.wb import navigate

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")
HOME = "https://www.zhipin.com/web/geek/job"

JD_JS = r"""(function(){
    function vis(e){var r=e.getBoundingClientRect();return r.width>0&&r.height>0;}
    var out=[];
    var sels=['.job-sec-text','.job-detail-section .text','.job-description',
              '.job-detail .text','[class*="job-desc"]','[class*="jobDescription"]',
              '.job-sec-content','.text-cont','.job-detail-section'];
    for(var i=0;i<sels.length;i++){
        document.querySelectorAll(sels[i]).forEach(function(e){
            if(!vis(e)) return;
            var t=(e.innerText||e.textContent||'').replace(/\s+/g,' ').trim();
            if(t && t.length>40) out.push(t);
        });
    }
    var seen={}, all=[];
    out.forEach(function(t){ if(!seen[t]){ seen[t]=1; all.push(t); } });
    var body=(document.body.innerText||'').replace(/\s+/g,' ');
    function q(s){var e=document.querySelector(s);return e?(e.textContent||'').replace(/\s+/g,' ').trim():'';}
    return JSON.stringify({
        position: q('.job-banner .name, h1.name, .job-name, .job-title'),
        salary: q('.salary, .job-banner .salary'),
        comp: q('.company-info a, .company-card .name, .company-name, [class*="companyName"]'),
        closed: body.indexOf('职位已关闭')>=0 || body.indexOf('该职位已结束')>=0,
        jd: all.join('\n').slice(0,4000),
        body: body.slice(0,3000)
    });
})()"""

LOGIN_CHECK = r"""(function(){
    var u=location.href||'';
    return JSON.stringify({url:u, login:(u.indexOf('/web/user')>=0)||(u.indexOf('login')>=0)});
})()"""


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def norm(s):
    return re.sub(r"[\s·\-—_（）()【】\[\]]+", "", s or "").lower()


def sim(a, b):
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def grab(jid, wait=4.2):
    navigate(f"https://www.zhipin.com/job_detail/{jid}.html")
    time.sleep(wait)
    lk = evaluate(LOGIN_CHECK)
    try:
        lk = json.loads(lk) if isinstance(lk, str) else (lk or {})
    except Exception:
        lk = {}
    if lk.get("login"):
        return None, "login_lost"
    raw = evaluate(JD_JS)
    try:
        v = json.loads(raw) if isinstance(raw, str) else (raw or {})
    except Exception:
        v = {}
    jd = v.get("jd") or ""
    if not jd:
        b = v.get("body", "")
        i = b.find("职位描述")
        j = b.find("公司介绍", i)
        jd = b[i:j] if i >= 0 else b[:1500]
    return dict(jobId=jid, position=v.get("position", ""), comp=v.get("comp", ""),
                salary=v.get("salary", ""), closed=v.get("closed", False),
                jd=jd[:3000]), None


def main():
    tpath = sys.argv[1]
    only = set(sys.argv[2:])
    targets = json.load(open(tpath, encoding="utf-8"))
    out_path = os.path.join(WORK, "jd_text.json")
    data = {}
    if os.path.isfile(out_path):
        try:
            data = json.load(open(out_path, encoding="utf-8"))
        except Exception:
            data = {}
    nav = 0
    mismatch = []
    for t in targets:
        label = t["label"]
        if only and label not in only:
            continue
        if label in data and len(data[label].get("jd", "")) > 200:
            log(f"跳过（已有） {label}")
            continue
        want = t.get("position") or ""
        rec, err = grab(t["jobId"])
        nav += 1
        if err == "login_lost":
            log(f"  !! 登录态失效，停止本批")
            break
        if rec is None:
            log(f"  {label} 抓取失败")
            continue
        s = sim(rec.get("position"), want)
        if s < 0.5:
            # 疑似缓存劫持 → 重置回搜索页再抓一次
            log(f"  {label} 标题不符（{rec.get('position','')!r} vs {want!r}，sim={s:.2f}）→ 重置重抓")
            navigate(HOME)
            time.sleep(2.5)
            rec2, err2 = grab(t["jobId"])
            nav += 1
            if err2 == "login_lost":
                log("  !! 登录态失效，停止本批")
                break
            if rec2:
                s2 = sim(rec2.get("position"), want)
                if s2 >= s:
                    rec, s = rec2, s2
        rec["sim"] = round(s, 3)
        rec["title_match"] = s >= 0.5
        if s < 0.5:
            mismatch.append((label, rec.get("position", ""), want))
        data[label] = rec
        flag = "OK " if rec["title_match"] else "MISMATCH"
        log(f"  {flag} {label:<46} JD {len(rec.get('jd',''))} 字 sim={s:.2f} 详情标题={rec.get('position','')[:24]}")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        if nav % 5 == 0:
            navigate(HOME)
            time.sleep(2.0)
        time.sleep(1.0)
    log(f"[结果] {out_path} 共 {len(data)} 条")
    if mismatch:
        log(f"!! 标题不匹配 {len(mismatch)} 条（按从严处理，不投）：")
        for lab, got, want in mismatch:
            log(f"    {lab}  页面={got!r}  目标={want!r}")


if __name__ == "__main__":
    main()
