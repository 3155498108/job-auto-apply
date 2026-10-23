# -*- coding: utf-8 -*-
"""audit_70.py — 逐条打开 70 个会话，审计真实状态。

产出每个会话的：
  myStates   我方每条消息的状态序列
  anyRead    是否有任意一条我方消息已读
  others     对方说过的话
  lastIsMe   最后一条是不是我发的
  last       最后一条内容
据此给出「按用户口径（线上已读即不再发）本该跳过的会话」清单。
"""
import io
import json
import os
import sys
import time

sys.path.insert(0, r"YOUR_REPO\job-auto-apply\marvis")
from scripts.wb import evaluate, navigate   # noqa: E402

WORK = r"YOUR_HOME\output\boss_work"
CHAT = "https://www.zhipin.com/web/geek/chat"

LIST_ALL = r"""JSON.stringify(Array.prototype.map.call(
    document.querySelectorAll('.friend-content'), function(e,i){
        var r=e.getBoundingClientRect();
        if(r.width<=0||r.height<=0) return null;
        return {i:i, t:(e.textContent||'').replace(/\s+/g,' ').trim()};
    }).filter(Boolean))"""

SCROLL_DOWN = r"""(function(){
    var el=document.querySelector('.user-list-content');
    if(!el) return 'no_el';
    el.scrollTop = el.scrollTop + Math.round(el.clientHeight*0.9);
    el.dispatchEvent(new Event('scroll',{bubbles:true}));
    return JSON.stringify({sh:el.scrollHeight, st:Math.round(el.scrollTop)});
})()"""

RESET_TOP = r"""(function(){
    var el=document.querySelector('.user-list-content');
    if(el){ el.scrollTop=0; el.dispatchEvent(new Event('scroll',{bubbles:true})); }
    window.scrollTo(0,0); return 'top';
})()"""

OPEN_JS = r"""(function(){
    var TARGET=__T__;
    function hof(s){
        s=(s||'').replace(/\s+/g,' ').trim();
        s=s.replace(/^(今天|昨天|前天|\d{1,2}月\d{1,2}日|\d{1,2}:\d{2})\s*/,'');
        var m=s.indexOf('['); if(m>=0) s=s.slice(0,m).trim();
        return s;
    }
    var list=document.querySelectorAll('.friend-content');
    for(var i=0;i<list.length;i++){
        var e=list[i]; var r=e.getBoundingClientRect();
        if(r.width<=0||r.height<=0) continue;
        var h=hof(e.textContent);
        if(h===TARGET || h.indexOf(TARGET)===0){ e.scrollIntoView({block:'center'}); e.click(); return 'clicked'; }
    }
    return 'not_found';
})()"""

AUDIT = r"""(function(){
    var b=document.querySelector('.chat-message')||document.querySelector('.chat-record');
    if(!b) return JSON.stringify({err:'no_box'});
    var li=b.querySelectorAll('li.message-item');
    var myStates=[], anyRead=false, others=[], myTexts=[], lastIsMe=null, last='', n=0;
    li.forEach(function(l){
        var isMe=(l.className||'').indexOf('item-myself')>=0;
        var c=l.querySelector('.message-content');
        var t=((c?(c.innerText||c.textContent||''):(l.textContent||''))||'').replace(/\s+/g,' ').trim();
        if(isMe){
            n++;
            var st=l.querySelector('.message-status, .status, [class*="status"]');
            var sv=st?((st.getAttribute('title')||st.textContent||'')+''):'';
            sv=sv.replace(/\s+/g,' ').trim();
            myStates.push(sv);
            if(sv.indexOf('已读')>=0) anyRead=true;
            if(t) myTexts.push(t.slice(0,90));
            lastIsMe=true; last=(t||'[图片]').slice(0,90);
        } else {
            var s2=t.replace(/\s+/g,' ').trim();
            if(s2 && s2.indexOf('竞争者')<0 && s2.indexOf('严禁')<0){
                others.push(s2.slice(0,70));
                lastIsMe=false; last=s2.slice(0,90);
            }
        }
    });
    var sel=document.querySelector('.friend-content.selected');
    return JSON.stringify({myN:n, myStates:myStates, anyRead:anyRead, others:others,
        myTexts:myTexts, lastIsMe:lastIsMe, last:last,
        conv: sel?((sel.textContent||'').replace(/\s+/g,' ').trim().slice(0,120)):''});
})()"""


def header_of(t):
    import re
    t = re.sub(r"\s+", " ", (t or "")).strip()
    t = re.sub(r"^(今天|昨天|前天|\d{1,2}月\d{1,2}日|\d{1,2}:\d{2})\s*", "", t)
    for m in ("[送达]", "[已读]", "[投递中]", "[发送中]", "[未读]", "[图片]"):
        if m in t:
            t = t.split(m)[0].strip()
            break
    return t


def collect(max_steps=100):
    navigate(CHAT)
    time.sleep(6)
    evaluate(RESET_TOP)
    time.sleep(1.0)
    seen, seen_set = [], set()
    stall, last_sig = 0, None
    for _ in range(max_steps):
        raw = evaluate(LIST_ALL)
        try:
            cur = json.loads(raw) if raw else []
        except Exception:
            cur = []
        for c in cur:
            t = (c.get("t") or "").strip()
            if not t:
                continue
            k = t[:110]
            if k not in seen_set:
                seen_set.add(k)
                seen.append(t)
        sig = evaluate(SCROLL_DOWN)
        if sig == last_sig:
            stall += 1
            if stall >= 4:
                break
        else:
            stall = 0
        last_sig = sig
        time.sleep(0.55)
    return seen


def open_and_audit(header, max_steps=50):
    for attempt in range(2):
        if attempt:
            evaluate(RESET_TOP)
            time.sleep(1.0)
        for _ in range(max_steps):
            r = evaluate(OPEN_JS.replace("__T__", json.dumps(header, ensure_ascii=False)))
            if r == "clicked":
                t0 = time.time()
                while time.time() - t0 < 12:
                    raw = evaluate(AUDIT)
                    try:
                        d = json.loads(raw) if raw else {}
                    except Exception:
                        d = {}
                    if d.get("myN", 0) > 0:
                        return d
                    time.sleep(0.6)
                return None
            evaluate(SCROLL_DOWN)
            time.sleep(0.5)
    return None


def main():
    tgt = json.load(io.open(os.path.join(WORK, "resend_targets.json"), encoding="utf-8"))
    sent = json.load(io.open(os.path.join(WORK, "resend2_send_result.json"), encoding="utf-8"))
    sent_keys = {(s.get("company", ""), s.get("jobId", "")) for s in sent if s.get("status") == "sent"}

    convs = collect()
    order = {}
    for i, c in enumerate(convs):
        order.setdefault(header_of(c), i)
    rows = []
    for t in sorted(tgt, key=lambda x: order.get(header_of(x["conv"]), 9999)):
        h = header_of(t["conv"])
        d = open_and_audit(h)
        r = dict(t)
        r["header"] = h
        r["audit"] = d
        r["was_sent"] = (t.get("company", ""), t.get("jobId", "")) in sent_keys
        rows.append(r)
        if d:
            print(f"  {t['company'][:12]:<14} anyRead={str(d.get('anyRead')):<5} "
                  f"others={len(d.get('others') or [])} myStates={d.get('myStates')} "
                  f"lastIsMe={d.get('lastIsMe')}")
        else:
            print(f"  {t['company'][:12]:<14} !! 打不开")
        sys.stdout.flush()

    io.open(os.path.join(WORK, "audit_70.json"), "w", encoding="utf-8").write(
        json.dumps(rows, ensure_ascii=False, indent=1))

    over = [r for r in rows if r["was_sent"] and r.get("audit")
            and (r["audit"].get("anyRead") or (r["audit"].get("others") or []))]
    print(f"\n审计 {len(rows)} 个会话")
    print(f"按用户口径本不该发却发了的：{len(over)} 个")
    for r in over:
        a = r["audit"]
        print(f"  - {r['company']:<14} anyRead={a.get('anyRead')} 对方回过={len(a.get('others') or [])} 条 "
              f"| {(a.get('others') or [''])[-1][:40]}")
    clean = [r for r in rows if r["was_sent"] and r.get("audit")
             and not a_read(r)]
    print(f"确认干净（无已读、对方没回话）：{len(clean)} 个")


def a_read(r):
    a = r["audit"]
    return a.get("anyRead") or (a.get("others") or [])


main()
