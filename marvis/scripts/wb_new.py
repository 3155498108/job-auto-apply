#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_new.py — 投递新目标（收藏夹 / 非广州）。

链路：job_detail → 校验 → 立即沟通 → 消息页（用自动选中的新会话）
      → 原生 fill 填话术（带换行）→ 点发送 → 上传简历截图 → 校验

用法: python wb_new.py [标签 ...]      不带参数 = 全部
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate
from scripts.recruit_greetings import pick_by_company
from scripts.wb import call, navigate
import scripts.wb_deliver as D

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")
RECRUIT = r"YOUR_HOME\招聘"
IMG_SEL = ".btn-sendimg input[type=file]"

# label → (jobId, 话术来源文件夹, [简历截图相对路径], 期望岗位标题关键词, 期望公司关键词)
TARGETS = [
    dict(label="AI软件开发实习生",
         jobId="JOBID013",
         folder="AI软件开发实习生",
         imgs=[r"AI Coding全栈工程师\shot_aicoding_p1.png",
               r"AI Coding全栈工程师\shot_aicoding_p2.png"],
         title_kw="AI软件开发实习生", company_kw=""),
    dict(label="人工智能开发工程师",
         jobId="5307e75f07a37e1e0nRz2N-4FlVW",
         folder="人工智能开发工程师",
         imgs=[r"研发实习生\shot_全量版_p1.png",
               r"研发实习生\shot_全量版_p2.png"],
         title_kw="人工智能开发工程师", company_kw=""),
]

DETAIL = r"""JSON.stringify((function(){
    var t=(document.body.innerText||'').replace(/\s+/g,' ');
    function q(sel){var e=document.querySelector(sel);return e?(e.textContent||'').replace(/\s+/g,' ').trim():'';}
    var name=q('.job-banner .name, h1.name, .job-name, .job-detail-banner .name');
    var sal=q('.salary, .job-banner .salary');
    var area=q('.location, .job-location, .company-location, .job-banner .company-location');
    var comp=q('.company-info a, .company-card .name, .company-name');
    return {name:name, salary:sal, area:area, comp:comp, head:t.slice(0,260)};
})())"""

IMGS_IN_CHAT = r"""(function(){
    var b=document.querySelector('.chat-message');
    if(!b) return -1;
    return b.querySelectorAll('img.message-image').length;
})()"""

SEL_TEXT = r"""(function(){
    var s=document.querySelector('.friend-content.selected');
    if(!s) return 'none';
    var j=document.querySelector('.position-name');
    return ((s.textContent||'').replace(/\s+/g,' ').trim().slice(0,44))+' @ '+(j?(j.textContent||'').trim():'?');
})()"""

# 当前选中会话里，我方是否已发过带「候选人」的定制话术（幂等判定）。
# BOSS 的「立即沟通」会自带一句默认招呼语（不含姓名），不计入。
GREET_HIT = r"""(function(){
    var b=document.querySelector('.chat-message');
    if(!b) return -1;
    var n=0;
    b.querySelectorAll('li.message-item.item-myself .message-content').forEach(function(e){
        if((e.textContent||'').indexOf('候选人')>=0) n++;
    });
    return n;
})()"""


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def chat_img_count():
    try:
        return int(evaluate(IMGS_IN_CHAT) or -1)
    except (TypeError, ValueError):
        return -1


def main():
    only = set(sys.argv[1:])
    results = []
    for t in TARGETS:
        if only and t["label"] not in only:
            continue
        log(f"===== {t['label']}")

        # 1) 详情页 + 校验
        navigate(f"https://www.zhipin.com/job_detail/{t['jobId']}.html")
        time.sleep(4.5)
        d = evaluate(DETAIL)
        try:
            d = json.loads(d) if isinstance(d, str) else d
        except Exception:
            d = {}
        log(f"    岗位 {d.get('name')} | {d.get('salary')} | {d.get('area')} | 公司 {d.get('comp')}")
        if t["title_kw"] and t["title_kw"] not in (d.get("name") or ""):
            log(f"    !! 岗位名不符，跳过")
            results.append(dict(label=t["label"], status="title_mismatch"))
            continue
        if not D.wait_text(["立即沟通", "继续沟通"], timeout=20):
            log("    !! 详情页未就绪")
            results.append(dict(label=t["label"], status="detail_timeout"))
            continue

        # 2) 话术
        text, src, meta = pick_by_company(t["folder"])
        if not text:
            log(f"    !! 找不到话术：{t['folder']}")
            results.append(dict(label=t["label"], status="no_greeting"))
            continue
        log(f"    话术 {meta.get('folder')} {len(text)} 字 / {text.count(chr(10))+1} 行")
        log(f"      {text.splitlines()[0][:60]}")

        # 3) 立即沟通
        r = D.click_text(["立即沟通"])
        if r == "not_found":
            r = D.click_text(["继续沟通"])
            log(f"    已沟通过（{r}）")
        else:
            log(f"    点立即沟通 {r}")
        time.sleep(3.5)

        # 4) 进消息页，用自动选中的新会话
        D.enter_chat()
        sel = evaluate(SEL_TEXT)
        log(f"    当前会话 {sel}")
        if "none" in str(sel):
            log("    !! 没选中会话，跳过")
            results.append(dict(label=t["label"], status="no_conversation"))
            continue

        # 4.5) 幂等保护：若该会话已发过带「候选人」的定制话术，不重复发
        hit = evaluate(GREET_HIT)
        try:
            hit = int(hit)
        except (TypeError, ValueError):
            hit = -1
        log(f"    已发话术计数 {hit}")
        if hit > 0:
            log("    !! 该会话已有定制话术，跳过（防重复）")
            results.append(dict(label=t["label"], status="already_sent"))
            continue

        # 5) 填话术并发送
        f = D.fill_chat(text)
        log(f"    填充 {f}")
        st = evaluate(r"""(function(){var b=document.querySelector('button.btn-send');return b?(b.className||''):'none';})()""")
        log(f"    发送键 {st}")
        if "disabled" in str(st) or "none" in str(st):
            log("    !! 发送键不可用，跳过")
            results.append(dict(label=t["label"], status="send_disabled"))
            continue
        s = D.click_send()
        log(f"    发送 {s}")
        sent_ok = "input_len=0" in str(s)

        # 6) 发简历截图
        for rel in t["imgs"]:
            p = os.path.join(RECRUIT, rel)
            if not os.path.isfile(p):
                log(f"    !! 截图不存在 {p}")
                continue
            before = chat_img_count()
            up = call("upload", {"selector": IMG_SEL, "files": [p]})
            after = before
            for _ in range(10):
                time.sleep(2.0)
                after = chat_img_count()
                if after > before:
                    break
            log(f"    简历图 {os.path.basename(rel)} 大图 {before}→{after} upload={up.get('ok')}")
            time.sleep(1.5)

        call("screenshot", {"path": os.path.join(WORK, f"new_{t['label']}.png"), "format": "png"})
        results.append(dict(label=t["label"], status="sent" if sent_ok else "send_unverified",
                            greeting_len=len(text), lines=text.count("\n") + 1))
        log(f"    → {'成功' if sent_ok else '待核实'}")
        time.sleep(3)

    with open(os.path.join(WORK, "new_result.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    log("=== 完成 ===")
    for r in results:
        log(f"    {r['status']:<16} {r['label']}")


if __name__ == "__main__":
    raise SystemExit(main())
