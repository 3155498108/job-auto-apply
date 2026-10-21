#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_batch.py — BOSS 直聘批量投递。

两个阶段：
  locate  — 只定位岗位（搜索 → 提取 → 匹配 → 存 plan.json），不点任何按钮
  deliver — 读 plan.json → job_detail 页 → 立即沟通 → 消息页 → 填话术 → 发送

用法:
    python wb_batch.py locate
    python wb_batch.py deliver
    python wb_batch.py one <folder>       # 单个岗位全流程（定位+投递）
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import extract_jobs, evaluate
from scripts.deliver_engine import pick_greeting_for_job
from scripts.recruit_greetings import pick_by_company
from scripts.wb import navigate, search_url, call
import scripts.wb_deliver as D

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")
PLAN = os.path.join(WORK, "plan.json")
LOG = os.path.join(WORK, "batch_log.txt")

# ── 12 个 BOSS 岗位 ─────────────────────────────────────────────
# folder  = 招聘目录里的文件夹名（话术索引键）
# query   = BOSS 搜索词；role = 岗位名关键词；comp = 公司名关键词（可空）
# conv_kw = 消息列表里该公司的会话关键词 —— 已存在会话的走「原会话补发」，
#           不再点「立即沟通」，避免重复打招呼
TARGETS = [
    dict(folder="AI应用与Agent工程实习生", company="示例文化B", conv_kw="示例文化B",
         query="AI应用与Agent工程实习生", role="AI应用", comp="示例企业30"),
    dict(folder="Java后端开发实习生", company="广州某公司", conv_kw="",
         query="Java后端开发实习生", role="Java后端", comp=""),
    dict(folder="java实习生", company="示例科技V", conv_kw="示例科技V",
         query="Java开发实习生", role="java", comp="示例企业94"),
    dict(folder="产品实习生", company="示例平台I", conv_kw="示例平台I",
         query="产品实习生", role="产品", comp="示例平台I"),
    dict(folder="全栈开发实习生", company="示例科技C", conv_kw="示例科技C",
         query="全栈开发实习生", role="全栈", comp="示例企业74"),
    dict(folder="示例科技D-游戏开发实习生", company="广州示例科技D信息技术", conv_kw="示例科技D",
         query="游戏开发实习生", role="游戏", comp="示例科技D"),
    dict(folder="后端开发实习生", company="示例网络E", conv_kw="示例网络E",
         query="后端开发实习生", role="后端", comp="示例企业13"),
    dict(folder="示例传媒T-AI智能体研发实习生", company="示例传媒T", conv_kw="示例传媒T",
         query="AI智能体研发实习生", role="智能体", comp="示例企业71"),
    dict(folder="示例科技A-后端JAVA开发实习生", company="示例科技A", conv_kw="示例科技Y",
         query="Java后端开发", role="后端JAVA", comp="示例科技Y", done=True),
    dict(folder="研发实习生", company="示例数据科技", conv_kw="示例数据科技",
         query="研发实习生", role="研发", comp="示例数据科技"),
    dict(folder="软件实习生", company="广州示例软件F", conv_kw="示例软件F",
         query="软件开发实习生", role="软件开发", comp="示例软件F"),
    dict(folder="示例云服务G-AI全栈开发工程师", company="广州示例云服务G网络科技", conv_kw="示例企业69",
         query="AI全栈开发工程师", role="AI全栈", comp="示例企业69"),
]

# 会话列表关键词 → 消息页里该公司会话（一次拉全部，用于判断是否已有会话）
CONV_LIST_JS = r"""JSON.stringify((function(){
    var out=[];
    document.querySelectorAll('.friend-content').forEach(function(e,i){
        var r=e.getBoundingClientRect();
        if(r.width<=0||r.height<=0) return;
        out.push({i:i, y:Math.round(r.top), t:(e.textContent||'').replace(/\s+/g,' ').trim().slice(0,70)});
    });
    return out;
})())"""


def find_conversation(conv_kw):
    """在消息页会话列表里找已有会话，返回 (index, 摘要) 或 None。"""
    if not conv_kw:
        return None
    raw = evaluate(CONV_LIST_JS)
    try:
        convs = json.loads(raw) if raw else []
    except Exception:
        return None
    hits = [c for c in convs if conv_kw in c["t"]]
    if not hits:
        return None
    hits.sort(key=lambda c: c["y"])
    return hits[0]


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def scan_pages(query, max_pages=4):
    """翻页扫描搜索结果，累积岗位。"""
    seen, order = {}, []
    for p in range(1, max_pages + 1):
        navigate(search_url(query, "101280100") + f"&page={p}")
        time.sleep(3.2)
        evaluate(r"""(function(){window.scrollTo(0,document.body.scrollHeight);return 1;})()""")
        time.sleep(1.2)
        jobs = extract_jobs()
        new = 0
        for j in jobs:
            jid = j.get("jobId")
            if jid and jid not in seen:
                seen[jid] = j
                order.append(j)
                new += 1
        if not jobs:
            break
        if new == 0 and p > 1:
            break
    return order


def _norm(s):
    """归一化：去空白 + 小写。

    BOSS 标题里常见「AI 全栈」「Java 后端」这种带空格的写法，
    直接用 'ai全栈' in title 匹配会漏掉。
    """
    return re.sub(r"\s+", "", (s or "")).lower()


def match(jobs, role, comp, city="广州", must_intern=True):
    """按 城市 + 实习岗 + 岗位词 + 公司词 过滤。

    12 个目标全是实习岗 → 标题必须含「实习/见习/应届/校招」，
    否则会把 15-25K 的社招岗当成实习岗投出去。
    """
    out = []
    for j in jobs:
        if city and j.get("city") != city:
            continue
        t = _norm(j.get("title", ""))
        if must_intern and not any(k in t for k in ("实习", "见习", "应届", "校招", "管培")):
            continue
        if role and _norm(role) not in t:
            continue
        if comp and _norm(comp) not in _norm(j.get("company", "")):
            continue
        out.append(j)
    return out


def locate_one(t):
    """定位单个目标，返回 plan 条目。"""
    log(f"--- 定位 {t['company']} / {t['folder']}  查询词={t['query']}")
    jobs = []
    cands = []
    for q in (t["query"], t["company"]):        # 先按岗位名搜，再按公司名搜
        try:
            jobs = scan_pages(q, max_pages=4)
        except Exception as e:
            log(f"    搜索异常({q}): {e}")
            continue
        cands = match(jobs, t["role"], t["comp"])
        if cands:
            log(f"    用查询词「{q}」命中 {len(cands)} 个候选")
            break
        log(f"    查询词「{q}」无精确匹配（搜到 {len(jobs)} 条）")
    if not cands:
        cands = match(jobs, t["role"], "")       # 只放宽公司词
        if cands:
            log(f"    ⚠ 无公司匹配，仅岗位词命中 {len(cands)} 个 —— 不自动投，需人工确认")
    if not cands:
        log(f"    !! 未匹配。搜索到 {len(jobs)} 条，标题示例：")
        for j in jobs[:8]:
            log(f"       {j['title'][:30]} | {j['salary']} | {j['company']} | {j['city']}")
        return dict(t, found=False, reason="no_match")
    best = cands[0]
    exact = _norm(t["comp"]) in _norm(best.get("company", "")) if t.get("comp") else False
    log(f"    命中 → {best['title']} | {best['salary']} | {best['company']} | {best['city']}"
        f"{'  [公司已校验]' if exact else '  [!! 公司未校验]'}")
    for c in cands[1:4]:
        log(f"       备选: {c['title'][:30]} | {c['salary']} | {c['company']}")
    return dict(t, found=exact, reason="ok" if exact else "company_unverified",
                jobId=best["jobId"], title=best["title"],
                salary=best["salary"], company=best["company"],
                city=best["city"], degree=best.get("degree", ""),
                alt=[dict(title=c["title"], salary=c["salary"], company=c["company"],
                          jobId=c["jobId"]) for c in cands[1:4]])


def do_locate(only_folders=None):
    plan = []
    for t in TARGETS:
        if t.get("done"):
            log(f"SKIP {t['company']}（已投递）")
            continue
        if only_folders and t["folder"] not in only_folders:
            plan.append(t)          # 保留旧条目
            continue
        plan.append(locate_one(t))
    with open(PLAN, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=1)
    ok = sum(1 for p in plan if p.get("found"))
    log(f"=== 定位完成 → {PLAN}  ({ok}/{len(plan)} 公司已校验命中)")
    return 0


def do_relocate():
    """只重跑上次没命中的目标，并合并回 plan.json。"""
    with open(PLAN, "r", encoding="utf-8") as f:
        old = json.load(f)
    failed = [p["folder"] for p in old
              if not p.get("done") and not (p.get("found") and p.get("reason") == "ok")]
    log(f"重跑 {len(failed)} 个未命中目标: {failed}")
    merged = []
    for t in TARGETS:
        if t.get("done") or t["folder"] not in failed:
            for p in old:
                if p.get("folder") == t["folder"]:
                    merged.append(p)
            continue
        merged.append(locate_one(t))
    with open(PLAN, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=1)
    ok = sum(1 for p in merged if p.get("found") and p.get("reason") == "ok")
    log(f"=== 重定位完成 ({ok}/{len(merged)} 公司已校验命中)")
    return 0


CONV_TEXT_JS = r"""JSON.stringify((function(){
    var out=[];
    // 会话列表里每条的「最后一条消息」预览 —— 最可靠的已发判定来源
    document.querySelectorAll('.friend-content').forEach(function(e){
        var s=document.querySelector('.friend-content.selected');
        var t=(e.textContent||'').replace(/\s+/g,' ').trim();
        if(t) out.push(t.slice(0,300));
    });
    return out;
})())"""

SEL_PREVIEW_JS = r"""(function(){
    var s=document.querySelector('.friend-content.selected');
    if(!s) return '';
    var m=s.querySelector('.last-msg-text');
    return ((m?s.textContent:s.textContent)||'').replace(/\s+/g,' ').trim().slice(0,300);
})()"""


def already_sent(marker="候选人"):
    """当前选中会话的最后一条消息里是否已有我们的定制话术。

    判定只认「当前选中会话的列表预览」——
    各岗位话术开头不同（『我是某高校…』/『我是计算机专业…』），
    用固定长句做标记会漏判；用『候选人』才通用。
    """
    prev = evaluate(SEL_PREVIEW_JS) or ""
    return marker in prev, prev[:90]


def send_in_chat(conv_kw, text, tag, marker="候选人", use_current=False):
    """在指定会话里填话术并发送。

    use_current=True：不按关键词找会话，直接用当前已选中的会话
    （新投递后 BOSS 会自动把刚建的会话选中并置顶，
     此时会话标题里是招聘方姓名+公司简称，用公司名反而匹配不到）。
    """
    if use_current:
        sel = evaluate(r"""(function(){
            var s=document.querySelector('.friend-content.selected');
            if(!s) return 'no_selected';
            var j=document.querySelector('.position-name');
            return ((s.textContent||'').replace(/\s+/g,' ').trim().slice(0,40))+' @ '+(j?(j.textContent||'').trim():'?');
        })()""")
        log(f"    用已选中会话 {sel}")
        if "no_selected" in str(sel):
            return "no_conversation", sel
    else:
        sel = D.pick_conversation(conv_kw)
        log(f"    选会话 {sel}")
        if "conv_not_found" in str(sel):
            return "no_conversation", sel
    dup, prev = already_sent(marker)
    if dup:
        log(f"    !! 该会话已发过定制话术（预览含「{marker}」: {prev}），跳过")
        return "already_sent", prev
    f = D.fill_chat(text)
    log(f"    填充 {f}")
    st = evaluate(r"""(function(){var b=document.querySelector('button.btn-send');return b?(b.className||''):'none';})()""")
    log(f"    发送键 {st}")
    if "disabled" in str(st) or "none" in str(st):
        return "send_disabled", st
    s = D.click_send()
    log(f"    发送 {s}")
    call("screenshot", {"path": os.path.join(WORK, f"sent_{tag}.png"), "format": "png"})
    return ("sent" if "input_len=0" in str(s) else "send_unverified"), s


def do_deliver(only=None):
    with open(PLAN, "r", encoding="utf-8") as f:
        plan = json.load(f)
    results = []

    for p in plan:
        folder = p["folder"]
        if p.get("done"):
            log(f"SKIP {p['company']}（已投递）")
            continue
        if only and folder not in only:
            continue

        text, src, meta = pick_by_company(folder)
        if not text:
            text, meta = pick_greeting_for_job(dict(p, title=p.get("title", "")))
            meta = dict(meta or {})
            meta["source"] = "generic"
        log(f"===== {p['company']} / {folder}  话术 {meta.get('source')}/{meta.get('folder') or '(通用)'} {len(text)} 字")

        # 会话匹配关键词：conv_kw 优先；没有就用公司名。
        # 绝不能留空 —— 空串会匹配到列表第一条（示例科技Y），导致误发。
        ck = p.get("conv_kw") or p.get("comp") or p.get("company") or ""
        if not ck:
            log("    !! 无会话关键词，跳过")
            results.append(dict(folder=folder, company=p["company"], route="none", status="no_keyword"))
            continue

        # ── A. 已有会话 → 直接在原会话补发（不重复立即沟通）──
        navigate("https://www.zhipin.com/web/geek/chat")
        time.sleep(3.0)
        D.wait_chat_ready(timeout=45)
        conv = find_conversation(ck)
        if conv:
            log(f"    已有会话 [{conv['i']}] {conv['t'][:50]} → 走补发")
            st, detail = send_in_chat(ck, text, folder)
            results.append(dict(folder=folder, company=p["company"], route="reply", status=st))
            log(f"    → {st}")
            time.sleep(3)
            continue

        # ── B. 没有会话 → 搜索定位 → job_detail → 立即沟通 → 聊天页发送 ──
        if not p.get("found"):
            log(f"    无已有会话且未定位到岗位 → 跳过")
            results.append(dict(folder=folder, company=p["company"], route="none", status="not_found"))
            continue
        log(f"    无已有会话 → 走新投递：{p['title']} | {p['salary']} | {p['company']}")
        url = f"https://www.zhipin.com/job_detail/{p['jobId']}.html"
        navigate(url)
        time.sleep(4)
        if not D.wait_text(["立即沟通", "继续沟通"], timeout=20):
            log("    !! 详情页未就绪，跳过")
            call("screenshot", {"path": os.path.join(WORK, f"fail_{folder}.png"), "format": "png"})
            results.append(dict(folder=folder, company=p["company"], route="new", status="detail_timeout"))
            continue
        head = D.body_text()[:300]
        if p.get("comp") and _norm(p["comp"]) not in _norm(head):
            log(f"    !! 页面公司不匹配，跳过: {head[:130]}")
            results.append(dict(folder=folder, company=p["company"], route="new", status="company_mismatch"))
            continue
        posting = D.detail_company()
        log(f"    详情页公司名: {posting!r}")
        r = D.click_text(["立即沟通"])
        if r == "not_found":
            r = D.click_text(["继续沟通"])
            log(f"    岗位已沟通过（{r}）")
        else:
            log(f"    点立即沟通 {r}")
        time.sleep(3.5)
        D.enter_chat()
        # 新建的会话在列表最顶，直接取最顶部那条（公司名可能对不上）
        log(f"    取最新会话 {D.pick_newest_conversation()}")
        st, detail = send_in_chat(ck, text, folder, use_current=True)
        results.append(dict(folder=folder, company=p["company"], route="new", status=st))
        log(f"    → {st}")
        time.sleep(3)

    with open(os.path.join(WORK, "batch_result.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    log("=== 投递完成")
    for r in results:
        log(f"    {r['status']:<18} {r['company']}  ({r['route']})")
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "locate"
    if cmd == "locate":
        return do_locate()
    if cmd == "relocate":
        return do_relocate()
    if cmd == "deliver":
        return do_deliver(set(sys.argv[2:]) if len(sys.argv) > 2 else None)
    print("用法: locate | relocate | deliver [目录名...]")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
