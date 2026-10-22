#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_msg_time.py — 逐会话取「最后一条我方消息」的文本 + 时间戳。

用途：区分「本轮新投」与「历史已投」。
本轮新投 = 会话里最后一条我方消息 == 本批生成的话术（文本指纹一致）。
历史已投 = 最后一条我方消息是更早批次发的（模板话术或旧定制话术）。

不改动任何已有 check/result 文件，输出 <prefix>_msgtime.json。
用法: python wb_msg_time.py <prefix> <targets_file>
"""
import io
import json
import os
import re
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb_fiximg import log

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")
RECRUIT = r"YOUR_HOME\招聘"

STATS = r"""(function(){
    var b=document.querySelector('.chat-message');
    if(!b) return {err:'no_box'};
    var li=b.querySelectorAll('li.message-item');
    var imgs=0, others=[], last='', lastTime='', myN=0, myAll=[];
    li.forEach(function(l){
        var isMe=l.className.indexOf('item-myself')>=0;
        var n=l.querySelectorAll('img.message-image').length;
        if(n){ imgs+=n; return; }
        var c=l.querySelector('.message-content');
        var h=c?(c.innerHTML||''):'';
        var t=(c?(c.innerText||c.textContent||''):(l.textContent||''))||'';
        if(t.indexOf('候选人')>=0){
            if(isMe){
                myN++;
                var s=t.replace(/\s+/g,' ').trim();
                myAll.push(s);
                last=s;   /* 会话内我方消息按时间升序，数组最后一条即最新 */
                var tm=l.querySelector('.message-status, .status, time, span[class*="time"], span[class*="status"]');
                if(tm){ var tt=(tm.getAttribute('title')||tm.textContent||'').replace(/\s+/g,' ').trim(); if(tt) lastTime=tt; }
            }
            return;
        }
        if(isMe) return;
        var s2=t.replace(/\s+/g,' ').trim();
        if(s2 && s2.indexOf('竞争者')<0) others.push(s2.slice(0,44));
    });
    var pos=document.querySelector('.position-name');
    var sel=document.querySelector('.friend-content.selected');
    return {myN:myN, images:imgs, last:last.slice(0,400), lastTime:lastTime,
            myAll:myAll.slice(-6),
            pos:pos?(pos.textContent||'').replace(/\s+/g,' ').trim():'',
            conv:sel?(sel.textContent||'').replace(/\s+/g,' ').trim().slice(0,70):'',
            others:others.slice(0,3)};
})()"""

LIST = r"""JSON.stringify(Array.prototype.map.call(
    document.querySelectorAll('.friend-content'), function(e,i){
        return {i:i, t:(e.textContent||'').replace(/\s+/g,' ').trim().slice(0,120)};
    }))"""

CHAT = "https://www.zhipin.com/web/geek/chat"

SCROLL_ALL = r"""(function(){
    var lists=document.querySelectorAll('.friend-list, .chat-friend-list, [class*="friend-list"], [class*="conversation"]');
    var n=0;
    lists.forEach(function(l){ if(l.scrollHeight>l.clientHeight+20){ l.scrollTop=l.scrollHeight; n++; } });
    window.scrollTo(0,document.body.scrollHeight);
    return 'scrolled:'+n;
})()"""


def norm(s):
    return re.sub(r"[\s（）()【】\[\]，,、/·\-—:：~～!！?？\"'“”‘’*_#`>|-]", "", (s or "")).lower()


def pos_ok(page_pos, want_pos):
    """岗位名对位：包含关系 或 相似度 >= 0.45。

    同一 HR 的多个岗位共用一个会话（BOSS 头部只显示一个岗位名），
    严格相等/包含都会判失败，用相似度兜底。
    """
    a, b = norm(page_pos), norm(want_pos)
    if not a or not b:
        return False
    if a == b or a in b or b in a:
        return True
    import difflib
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.45


def fp_of(folder):
    """本批为该岗位生成的话术指纹（归一化后取前 80 字）。

    话术文件开头是元信息（公司/地址/薪资/【主推版 · 按 JD 定制 · N 字】），
    真正发出去的是该标记之后的主体，所以要剥掉头部。
    """
    gf = os.path.join(RECRUIT, folder, "新建 文本文档.txt")
    if not os.path.isfile(gf):
        return ""
    txt = io.open(gf, encoding="utf-8").read()
    i = txt.find("】")
    if i >= 0:
        tail = txt[i + 1:]
        # 跳过标记后残留的换行
        tail = tail.lstrip("\r\n")
        # 主推版正文结束于下一个方括号标记（如【备用版】）
        j = tail.find("【")
        if j > 0:
            tail = tail[:j]
        if len(norm(tail)) > 60:
            txt = tail
    return norm(txt)


def open_chat():
    from scripts.wb import navigate
    navigate(CHAT)
    time.sleep(6)
    for _ in range(8):
        evaluate(SCROLL_ALL)
        time.sleep(1.0)
    for _ in range(4):
        evaluate(r"""(function(){
            var lists=document.querySelectorAll('.friend-list, .chat-friend-list, [class*="friend-list"], [class*="conversation"]');
            lists.forEach(function(l){ l.scrollTop=0; });
            var f=document.querySelector('.friend-content');
            if(f && f.scrollIntoView) f.scrollIntoView({block:'start'});
            return 1;
        })()""")
        time.sleep(0.8)


def jload(name):
    p = os.path.join(WORK, name)
    if not os.path.isfile(p):
        return None
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return None


def main():
    prefix = sys.argv[1]
    tfile = sys.argv[2]
    targets = json.load(io.open(os.path.join(WORK, tfile), encoding="utf-8"))

    boss = {}
    for fn in ("favorites_tag4.json", "favorites_fresh.json"):
        favs = jload(fn)
        if not favs:
            continue
        for f in favs:
            if isinstance(f, dict) and f.get("encryptJobId"):
                boss[f["encryptJobId"]] = f.get("bossName") or ""
        if boss:
            break

    open_chat()
    rows = []
    for t in targets:
        comp = t.get("company", "")
        bname = boss.get(t.get("jobId"), "") or t.get("boss", "")
        np_ = norm(t.get("position", ""))
        nc = norm(comp)
        raw = evaluate(LIST)
        try:
            convs = json.loads(raw) if raw else []
        except Exception:
            convs = []
        cands = [c for c in convs if nc and nc in norm(c["t"])]
        if bname:
            tight = [c for c in cands if norm(bname) in norm(c["t"])]
            if tight:
                cands = tight

        picked = None
        for c in cands[:6]:
            evaluate(r"""(function(){
                var list=document.querySelectorAll('.friend-content');
                var e=list[%d]; if(!e) return 'gone';
                e.scrollIntoView({block:'center'}); e.click(); return 'clicked';
            })()""" % c["i"])
            time.sleep(1.6)
            v = evaluate(STATS)
            if isinstance(v, str):
                try:
                    v = json.loads(v)
                except Exception:
                    v = {"err": v}
            if np_ and pos_ok(v.get("pos", ""), np_):
                picked = v
                break
        if picked is None:
            if cands:
                v = evaluate(STATS)
                if isinstance(v, str):
                    try:
                        v = json.loads(v)
                    except Exception:
                        v = {"err": v}
                picked = v
            else:
                picked = {"err": "no_conv_match"}

        picked["label"] = t["label"]
        picked["folder"] = t["folder"]
        picked["company"] = comp
        picked["target_pos"] = t.get("position", "")
        picked["fp"] = fp_of(t["folder"])
        picked["convKey"] = norm(picked.get("pos", "")) + "|" + norm(picked.get("conv", ""))[:24]
        rows.append(picked)

    # ── 第二阶段：按会话汇总，再判定每个岗位 ─────────────────────
    # 同一 HR 的多个岗位共用一个会话，该会话里可能同时躺着本批多条话术，
    # 因此不能只看「最后一条」，要把整个会话的我方消息都纳入指纹比对。
    conv_msgs = {}
    for r in rows:
        conv_msgs.setdefault(r["convKey"], []).extend(r.get("myAll", []) or [])
    for r in rows:
        msgs = norm(" ".join(conv_msgs.get(r["convKey"], [])))
        fp = r.pop("fp", "") or ""
        if not r.get("myN"):
            r["verdict"] = "no_my_msg"
        elif fp and fp[:60] in msgs:
            r["verdict"] = "this_batch"
        else:
            r["verdict"] = "older_batch"
        log(f"{r['verdict']:<12} {r['company'][:12]:<14} {str(r.get('lastTime'))[:16]:<16} "
            f"myN={r.get('myN')} img={r.get('images')} pos={str(r.get('pos'))[:24]}")
        if r.get("others"):
            log(f"    对方: {r['others']}")

    out = os.path.join(WORK, f"{prefix}_msgtime.json")
    json.dump(rows, io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    from collections import Counter
    log(f"[结果] {out}")
    log(f"分布: {dict(Counter(r['verdict'] for r in rows))}")


if __name__ == "__main__":
    main()
