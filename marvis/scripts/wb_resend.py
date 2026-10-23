#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""resend_v2.py — 给「已投但对方仍未读」的会话补发一次第二次触达。

修正了 v1 的三个问题：
  1) sys.path 指向了旧的 marvis 副本 → 改到 job-auto-apply/marvis
  2) 滚动容器漏了 .user-list-content + 缺 scroll 事件派发 → 只能看到前 40 条
  3) 定位靠公司名 → 同公司多会话会撞车；改用「会话头（HR名+公司+角色）」精确匹配，
     且按列表顺序增量滚动（发消息会把会话置顶，位置只往后漂 1 档）

发送前四道闸：
  a. 会话头必须精确匹配目标（防止发错人）
  b. 最后一条必须是我发的（对方回过话 = 我的消息已被读，跳过）
  c. 状态不能是「已读」
  d. 会话里不能已经有过同一段第二次触达话术

用法:
    python resend_v2.py <resend_final.json> <resend_targets.json> dry
    python resend_v2.py <resend_final.json> <resend_targets.json> send
"""
import io
import json
import os
import re
import sys
import time

sys.path.insert(0, r"YOUR_REPO\job-auto-apply\marvis")
from scripts.wb import evaluate, navigate   # noqa: E402
import scripts.wb_deliver as D               # noqa: E402

WORK = r"YOUR_HOME\output\boss_work"
RECRUIT = r"YOUR_HOME\招聘"
CHAT = "https://www.zhipin.com/web/geek/chat"

RE_TIME = re.compile(r"^(?:今天|昨天|前天|\d{1,2}月\d{1,2}日|\d{1,2}:\d{2})\s*")
RE_MAIN = re.compile(r"【主推版[^\n]*】\s*\n(.*?)(?=\n【|\n={5,}|\n-{5,}|\Z)", re.S)

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
    window.scrollTo(0,0);
    return 'top';
})()"""

MY_STATE = r"""(function(){
    var b=document.querySelector('.chat-message')||document.querySelector('.chat-record');
    if(!b) return JSON.stringify({err:'no_box'});
    var li=b.querySelectorAll('li.message-item');
    var lastState='', myN=0, others=[], myTexts=[], lastIsMe=null, last='';
    var myStates=[], anyRead=false;
    li.forEach(function(l){
        var isMe=(l.className||'').indexOf('item-myself')>=0;
        var nImg=l.querySelectorAll('img.message-image').length;
        var c=l.querySelector('.message-content');
        var t=((c?(c.innerText||c.textContent||''):(l.textContent||''))||'').replace(/\s+/g,' ').trim();
        if(isMe){
            myN++;
            var st=l.querySelector('.message-status, .status, [class*="status"]');
            var sv = st?((st.getAttribute('title')||st.textContent||'')+''):'';
            sv=sv.replace(/\s+/g,' ').trim();
            if(sv){ myStates.push(sv); if(sv.indexOf('已读')>=0) anyRead=true; }
            lastState=sv;
            if(t) myTexts.push(t.slice(0,120));
            lastIsMe=true; last=(t||'[图片]').slice(0,80);
        } else {
            var s2=t.replace(/\s+/g,' ').trim();
            if(s2 && s2.indexOf('竞争者')<0 && s2.indexOf('严禁')<0){
                others.push(s2.slice(0,60));
                lastIsMe=false; last=s2.slice(0,80);
            }
        }
    });
    var sel=document.querySelector('.friend-content.selected');
    var pos=document.querySelector('.position-name');
    return JSON.stringify({myN:myN, state:lastState, myStates:myStates, anyRead:anyRead,
            last:last, others:others.slice(-3),
            myTexts:myTexts.slice(-3),
            lastIsMe:lastIsMe,
            conv: sel?((sel.textContent||'').replace(/\s+/g,' ').trim().slice(0,90)):'',
            pos: pos?(pos.textContent||'').replace(/\s+/g,' ').trim():''});
})()"""


SEL_STATE = r"""JSON.stringify((function(){
    var s=document.querySelector('.friend-content.selected');
    var box=document.querySelector('.chat-message')||document.querySelector('.chat-record');
    return {sel: s?((s.textContent||'').replace(/\s+/g,' ').trim().slice(0,90)):'',
            box: !!box, lis: box?box.querySelectorAll('li.message-item').length:-1,
            pos: (document.querySelector('.position-name')||{}).textContent||''};
})())"""

# 原子地「找到 + 点开」—— 查询和点击必须在同一次 evaluate 里完成，
# 否则虚拟列表在两次调用之间重渲染，拿到的是已失效的节点。
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
        if(h===TARGET || h.indexOf(TARGET)===0){
            e.scrollIntoView({block:'center'});
            e.click();
            return 'clicked:'+h;
        }
    }
    return 'not_found';
})()"""


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def norm(s):
    return re.sub(r"[\s（）()【】\[\]，,、/·\-—:：~～!！?？\"'“”‘’*_#`>|-]", "", (s or "")).lower()


def header_of(text):
    """从会话预览里抽出会话头：去掉时间前缀和状态标记后的那段。"""
    t = re.sub(r"\s+", " ", (text or "")).strip()
    t = RE_TIME.sub("", t)
    for mark in ("[送达]", "[已读]", "[投递中]", "[发送中]", "[未读]", "[图片]"):
        if mark in t:
            t = t.split(mark)[0].strip()
            break
    return t


def read_text(folder):
    fp = os.path.join(RECRUIT, folder, "新建 文本文档.txt")
    raw = io.open(fp, encoding="utf-8").read()
    m = RE_MAIN.search(raw)
    if not m:
        return ""
    body = m.group(1).replace("**", "").replace("`", "")
    paras = []
    for ln in body.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        if paras and not re.search(r"[。！？!?；;）)】》\"]$", paras[-1]):
            paras[-1] = paras[-1] + " " + ln
        else:
            paras.append(ln)
    return "\n".join(paras).strip()


def collect(max_steps=90, pause=0.55):
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
        time.sleep(pause)
    evaluate(RESET_TOP)
    return seen


def open_conv(header, max_steps=45):
    """定位并点开会话。

    点击是「找到 + click」同一次 evaluate（避免虚拟列表重渲染导致节点失效）；
    点开后要**轮询等选中态生效** —— BOSS 是异步拉会话，
    固定 sleep 2s 会读到旧状态（表现为会话头为空）。
    """
    for attempt in range(2):
        if attempt == 1:
            evaluate(RESET_TOP)
            time.sleep(1.0)
        for _ in range(max_steps):
            r = evaluate(OPEN_JS.replace("__T__", json.dumps(header, ensure_ascii=False)))
            if r and str(r).startswith("clicked:"):
                # 等选中态生效
                t0 = time.time()
                while time.time() - t0 < 15:
                    raw = evaluate(SEL_STATE)
                    try:
                        d = json.loads(raw) if raw else {}
                    except Exception:
                        d = {}
                    sel = d.get("sel") or ""
                    if (header_of(sel) == header or header in sel) and d.get("lis", 0) > 0:
                        return sel
                    time.sleep(0.7)
                # 没等到选中 —— 也可能已经选中了，只是头文本略有出入
                raw = evaluate(SEL_STATE)
                try:
                    d = json.loads(raw) if raw else {}
                except Exception:
                    d = {}
                if (d.get("sel") or "") and d.get("lis", 0) > 0:
                    return d["sel"]
                return None
            evaluate(SCROLL_DOWN)
            time.sleep(0.55)
    return None


URL_GUARD = "JSON.stringify({u:location.href,t:document.title})"


def still_logged_in():
    """登录态守卫：被风控踢到 /web/user/ 或登录页就立刻停。"""
    raw = evaluate(URL_GUARD)
    try:
        d = json.loads(raw) if raw else {}
    except Exception:
        return True, ""
    u = (d.get("u") or "")
    bad = ("/web/user" in u or "login" in u.lower() or "passport" in u.lower())
    return (not bad), u


def send_text(body):
    f = D.fill_chat(body)
    time.sleep(1.2)
    btn = evaluate(r"""(function(){var b=document.querySelector('button.btn-send');return b?((b.className||'')+'|'+(b.textContent||'').trim()):'none';})()""")
    if "disabled" in str(btn) or "none" in str(btn):
        return False, f"send_btn:{btn}"
    r = D.click_send()
    return ("input_len=0" in str(r)), str(r)


def main():
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass
    mode = sys.argv[3] if len(sys.argv) > 3 else "dry"
    finals = json.load(io.open(os.path.join(WORK, sys.argv[1]), encoding="utf-8"))
    targets = json.load(io.open(os.path.join(WORK, sys.argv[2]), encoding="utf-8"))
    assert len(finals) == len(targets), "final/targets 数量不一致"

    rows = []
    for t, f in zip(targets, finals):
        rows.append({
            "label": f["label"], "folder": f["folder"], "company": t["company"],
            "position": t["position"], "jobId": t.get("jobId", ""),
            "header": header_of(t["conv"]), "conv": t["conv"],
            "days_since": t.get("days_since", 0),
        })

    # 按会话在列表里的顺序处理（发消息会让会话置顶，位置只往后漂）
    convs = collect()
    print(f"会话列表 {len(convs)} 条；目标 {len(rows)} 个")
    order = {}
    for i, c in enumerate(convs):
        order.setdefault(header_of(c), i)
    for r in rows:
        r["list_idx"] = order.get(r["header"], -1)
    rows.sort(key=lambda x: (x["list_idx"] < 0, x["list_idx"]))

    # 只跑前 N 个（调试用）：RESEND_LIMIT=3
    lim = int(os.environ.get("RESEND_LIMIT", "0"))
    if lim:
        rows = rows[:lim]
        print(f"[调试模式] 只处理前 {lim} 个")

    out_path = os.path.join(WORK, f"resend2_{mode}_result.json")
    results = []
    sent_n = 0
    # 断点续跑：已发过的（status=sent）不再重发
    if os.path.isfile(out_path):
        try:
            prev = json.load(io.open(out_path, encoding="utf-8"))
            results = [p for p in prev if p.get("status") == "sent"]
            done_labels = {p.get("label") for p in results}
            print(f"[续跑] 已有 {len(results)} 条发过，跳过这些")
        except Exception:
            results = []
    done_labels = {p.get("label") for p in results}
    for n, r in enumerate(rows):
        if r["label"] in done_labels:
            continue
        alive, u = still_logged_in()
        if not alive:
            log(f"!! 登录态异常（{u}），立即停止")
            results.append(dict(r, status="aborted_login"))
            with io.open(out_path, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=1)
            break
        body = read_text(r["folder"])
        if not body:
            results.append(dict(r, status="no_text"))
            continue
        found = open_conv(r["header"])
        if not found:
            results.append(dict(r, status="conv_not_found"))
            print(f"  ({n+1}/{len(rows)}) {r['company'][:12]:<14} 列表里找不到 [{r['header'][:18]}]")
            continue
        raw = evaluate(MY_STATE)
        try:
            v = json.loads(raw)
        except Exception:
            v = {"err": str(raw)[:120]}

        rec = dict(r)
        rec["pos"] = v.get("pos", "")
        rec["myN"] = v.get("myN", 0)
        rec["state"] = v.get("state", "")
        rec["lastIsMe"] = v.get("lastIsMe")
        rec["last"] = (v.get("last") or "")[:70]
        rec["others"] = v.get("others", [])
        rec["chars"] = len(body)
        rec["conv_head"] = header_of(v.get("conv", ""))

        # ── 五道闸 ─────────────────────────────
        # 闸 1：会话头必须精确匹配目标（防止发错人）
        if not rec["conv_head"] or not (rec["conv_head"] == r["header"]
                                       or rec["conv_head"].startswith(r["header"][:12])):
            rec["status"] = "head_mismatch"
            results.append(rec)
            print(f"  ({n+1}/{len(rows)}) {r['company'][:12]:<14} 会话头不符，实际=[{rec['conv_head'][:22]}]")
            continue
        # 闸 2：对方只要回过一句（任何一条非我方消息），我的消息就必然已被读 → 跳过。
        # 不能只看「最后一条是不是我发的」：对方回过之后我又回了一句（如回复对方的
        # 婉拒），lastIsMe 仍是 true，会漏判成「未读」而误发。
        if v.get("others"):
            rec["status"] = "hr_replied"
            rec["hr_text"] = (v.get("others") or [""])[-1][:80]
            results.append(rec)
            print(f"  ({n+1}/{len(rows)}) {r['company'][:12]:<14} 对方已回「{rec['hr_text'][:26]}」→ 跳过")
            continue
        if v.get("lastIsMe") is False:
            rec["status"] = "hr_replied"
            results.append(rec)
            print(f"  ({n+1}/{len(rows)}) {r['company'][:12]:<14} 对方已回「{rec['last'][:26]}」→ 跳过")
            continue
        # 闸 3：会话里**任意一条**我方消息已读 → 这个会话线上已被读过 → 跳过。
        # 只看最后一条的状态是不够的：对方回话后我又回过一句，最后一条是「送达」，
        # 但更早的消息早已「已读」，用户口径「线上已读的不再新投」仍然适用。
        if v.get("anyRead") or "已读" in (v.get("state") or ""):
            rec["status"] = "already_read"
            rec["my_states"] = v.get("myStates", [])
            results.append(rec)
            print(f"  ({n+1}/{len(rows)}) {r['company'][:12]:<14} 已读 → 跳过")
            continue
        if "[已读]" in (v.get("conv") or ""):
            rec["status"] = "already_read"
            results.append(rec)
            print(f"  ({n+1}/{len(rows)}) {r['company'][:12]:<14} 已读 → 跳过")
            continue
        # 闸 4：会话里没有我的消息 → 不是「已投过的岗位」→ 跳过
        if not v.get("myN"):
            rec["status"] = "no_my_msg"
            results.append(rec)
            print(f"  ({n+1}/{len(rows)}) {r['company'][:12]:<14} 会话里没有我的消息 → 跳过")
            continue
        # 闸 5：会话里已经有同一段话术 → 不重复发
        mine = norm(" ".join(v.get("myTexts") or []))
        if norm(body)[:40] and norm(body)[:40] in mine:
            rec["status"] = "dup"
            results.append(rec)
            print(f"  ({n+1}/{len(rows)}) {r['company'][:12]:<14} 已发过同样内容 → 跳过")
            continue

        if mode == "dry":
            rec["status"] = "dry_ok"
            results.append(rec)
            print(f"  ({n+1}/{len(rows)}) {r['company'][:12]:<14} 可发（{len(body)}字）"
                  f" 岗位={rec['pos'][:16]!r} 末条是我={v.get('lastIsMe')}")
            time.sleep(0.4)
            continue

        ok, detail = send_text(body)
        time.sleep(2.0)
        v2 = evaluate(MY_STATE)
        try:
            v2 = json.loads(v2)
        except Exception:
            v2 = {}
        grew = (v2.get("myN") or 0) > (v.get("myN") or 0)
        rec["status"] = "sent" if (ok and grew) else "send_unverified"
        rec["send_detail"] = detail
        results.append(rec)
        print(f"  ({n+1}/{len(rows)}) {r['company'][:12]:<14} {rec['status']}（{len(body)}字）"
              f" myN {v.get('myN')}→{v2.get('myN')}")
        with io.open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=1)
        time.sleep(6)
        sent_n += 1
        if sent_n % 15 == 0:
            log(f"—— 已发 {sent_n} 条，歇 25 秒避开风控 ——")
            time.sleep(25)
            alive, u = still_logged_in()
            log(f"   登录态: {'正常' if alive else '异常!'} {u}")

    with io.open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    from collections import Counter
    print("\n结果:", dict(Counter(r.get("status") for r in results)))
    print("→", out_path)


main()
