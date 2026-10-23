# -*- coding: utf-8 -*-
"""verify_resend.py — 独立复核 70 条第二次触达是否真的落在会话里。

两步：
  A) 全量：重收会话列表，逐个比对「现在的预览」与「发送前的预览」——
     变了 = 消息确实进去了。
  B) 抽查：随机打开 10 个会话，确认最后一条是我方消息、且内容是第二次触达话术。

用法: python verify_resend.py [抽查条数]
"""
import io
import json
import os
import random
import re
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
        if(h===TARGET || h.indexOf(TARGET)===0){ e.scrollIntoView({block:'center'}); e.click(); return 'clicked:'+h; }
    }
    return 'not_found';
})()"""

MY_STATE = r"""(function(){
    var b=document.querySelector('.chat-message')||document.querySelector('.chat-record');
    if(!b) return JSON.stringify({err:'no_box'});
    var li=b.querySelectorAll('li.message-item');
    var myN=0, myLast='', others=[], lastIsMe=null;
    li.forEach(function(l){
        var isMe=(l.className||'').indexOf('item-myself')>=0;
        var c=l.querySelector('.message-content');
        var t=((c?(c.innerText||c.textContent||''):(l.textContent||''))||'').replace(/\s+/g,' ').trim();
        if(isMe){ myN++; myLast=t.slice(0,160); lastIsMe=true; }
        else if(t && t.indexOf('竞争者')<0 && t.indexOf('严禁')<0){ others.push(t.slice(0,50)); lastIsMe=false; }
    });
    var sel=document.querySelector('.friend-content.selected');
    return JSON.stringify({myN:myN, myLast:myLast, others:others.slice(-2),
        lastIsMe:lastIsMe,
        conv: sel?((sel.textContent||'').replace(/\s+/g,' ').trim().slice(0,120)):''});
})()"""


def norm(s):
    return re.sub(r"[\s（）()【】\[\]，,、/·\-—:：~～!！?？\"'“”‘’*_#`>|-]", "", (s or "")).lower()


def header_of(t):
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
    evaluate(RESET_TOP)
    return seen


def open_conv(header, max_steps=50):
    for attempt in range(2):
        if attempt == 1:
            evaluate(RESET_TOP)
            time.sleep(1.0)
        for _ in range(max_steps):
            r = evaluate(OPEN_JS.replace("__T__", json.dumps(header, ensure_ascii=False)))
            if r and str(r).startswith("clicked:"):
                t0 = time.time()
                while time.time() - t0 < 15:
                    raw = evaluate(MY_STATE)
                    try:
                        d = json.loads(raw) if raw else {}
                    except Exception:
                        d = {}
                    if d.get("myN", 0) > 0 and header_of(d.get("conv", "")) == header:
                        return d
                    time.sleep(0.7)
                return None
            evaluate(SCROLL_DOWN)
            time.sleep(0.55)
    return None


def main():
    n_spot = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    tgt = json.load(io.open(os.path.join(WORK, "resend_targets.json"), encoding="utf-8"))
    sent = json.load(io.open(os.path.join(WORK, "resend2_send_result.json"), encoding="utf-8"))
    fin = json.load(io.open(os.path.join(WORK, "resend_final.json"), encoding="utf-8"))
    sent_labels = {s.get("label") for s in sent if s.get("status") == "sent"}

    print(f"收集会话列表……")
    convs = collect()
    now_by_header = {}
    for c in convs:
        now_by_header.setdefault(header_of(c), c)
    print(f"会话列表 {len(convs)} 条")

    # ── A) 全量比对 ────────────────────────────────────────────
    changed, unchanged, missing = 0, [], []
    for t in tgt:
        h = header_of(t["conv"])
        now = now_by_header.get(h)
        if not now:
            missing.append(t["company"])
            continue
        if norm(now) != norm(t["conv"]):
            changed += 1
        else:
            unchanged.append((t["company"], now[:60]))
    print(f"\n[A] 全量比对：预览已变（=消息进去了）{changed} 条 / "
          f"未变 {len(unchanged)} 条 / 会话没找到 {len(missing)} 条")
    for u in unchanged[:10]:
        print("    未变:", u)
    for m in missing[:10]:
        print("    找不到:", m)

    # ── B) 抽查会话内部 ────────────────────────────────────────
    rows = [t for t in tgt if t.get("label") in sent_labels]
    random.seed(7)
    spot = random.sample(rows, min(n_spot, len(rows)))
    print(f"\n[B] 抽查 {len(spot)} 个会话内部……")
    ok, bad = 0, []
    for t in spot:
        h = header_of(t["conv"])
        d = open_conv(h)
        if not d:
            bad.append((t["company"], "打不开"))
            print(f"    {t['company'][:12]:<14} 打不开")
            continue
        last = d.get("myLast", "")
        is_resend = ("能对上的地方" in last) or ("上次" in last) or ("补" in last) or ("打扰" in last)
        good = d.get("lastIsMe") is True and d.get("myN", 0) >= 5
        print(f"    {t['company'][:12]:<14} myN={d.get('myN')} 末条是我={d.get('lastIsMe')} "
              f"像重发话术={is_resend} | {last[:52]}")
        if good and is_resend:
            ok += 1
        else:
            bad.append((t["company"], last[:50]))
    print(f"\n抽查通过 {ok}/{len(spot)}")
    json.dump({"changed": changed, "unchanged": unchanged, "missing": missing,
               "spot_ok": ok, "spot_bad": bad},
              io.open(os.path.join(WORK, "verify_resend.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


main()
