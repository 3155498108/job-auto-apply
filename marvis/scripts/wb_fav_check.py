# -*- coding: utf-8 -*-
"""wb_fav_check.py — 核对收藏夹 41 个会话：话术条数 / 换行 br 数 / 图片数 / 岗位名是否对位。

会话选择用「公司名 + boss 名」关键词，命中多个时逐个试，直到头部岗位名与目标一致。
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb import call
from scripts.wb_fiximg import select_conv, log

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")
TARGETS_FILE = os.environ.get("BOSS_TARGETS_FILE", "fav_targets.json")
PREFIX = os.environ.get("BOSS_PREFIX", "fav")

STATS = r"""(function(){
    var b=document.querySelector('.chat-message');
    if(!b) return {err:'no_box'};
    var li=b.querySelectorAll('li.message-item');
    var imgs=0, myText=0, brs=0, others=[], last='', c38=0, c50=0;
    li.forEach(function(l){
        var isMe=l.className.indexOf('item-myself')>=0;
        var n=l.querySelectorAll('img.message-image').length;
        if(n){ imgs+=n; return; }
        var c=l.querySelector('.message-content');
        var h=c?(c.innerHTML||''):'';
        var t=(c?(c.innerText||c.textContent||''):(l.textContent||''))||'';
        if(t.indexOf('候选人')>=0){
            if(isMe){ myText++; brs+=(h.match(/<br\s*\/?>/gi)||[]).length; last=t.replace(/\s+/g,' ').trim(); }
            return;
        }
        if(isMe) return;
        var s=t.replace(/\s+/g,' ').trim();
        if(s && s.indexOf('竞争者')<0) others.push(s.slice(0,44));
    });
    var pos=document.querySelector('.position-name');
    var sel=document.querySelector('.friend-content.selected');
    return {myText:myText, images:imgs, brs:brs,
            pos:pos?(pos.textContent||'').replace(/\s+/g,' ').trim():'',
            conv:sel?(sel.textContent||'').replace(/\s+/g,' ').trim().slice(0,70):'',
            others:others.slice(0,3), last:last.slice(0,110)};
})()"""

LIST = r"""JSON.stringify(Array.prototype.map.call(
    document.querySelectorAll('.friend-content'), function(e,i){
        return {i:i, t:(e.textContent||'').replace(/\s+/g,' ').trim().slice(0,120)};
    }))"""

CHAT = "https://www.zhipin.com/web/geek/chat"

# 展开会话列表：BOSS 列表是懒加载的，先滚到底再回顶，确保 DOM 里包含全部会话
SCROLL_ALL = r"""(function(){
    var lists=document.querySelectorAll('.friend-list, .chat-friend-list, [class*="friend-list"], [class*="conversation"]');
    var n=0;
    lists.forEach(function(l){
        if(l.scrollHeight>l.clientHeight+20){ l.scrollTop=l.scrollHeight; n++; }
    });
    window.scrollTo(0,document.body.scrollHeight);
    return 'scrolled:'+n;
})()"""


def open_chat():
    """跳到消息页并把会话列表全部加载出来。"""
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


def norm(s):
    return re.sub(r"[\s（）()【】\[\]，,、/·\-—:：~～]", "", (s or "")).lower()


def pos_match(page_pos, want_pos):
    """岗位名对位：允许前后缀差异。

    页面写「兼职·软件开发实习生」、扫描时是「软件开发实习生」——同一个岗位，
    只作备注不算失败。严格相等会误判成不合格。
    """
    a, b = norm(page_pos), norm(want_pos)
    if not a or not b:
        return False
    return a == b or a in b or b in a


def main():
    targets = json.load(open(os.path.join(WORK, TARGETS_FILE), encoding="utf-8"))
    open_chat()
    # boss 名（用于更准地选会话）
    boss = {}
    for fn in ("favorites_tag4.json", "favorites_fresh.json"):
        try:
            favs = json.load(open(os.path.join(WORK, fn), encoding="utf-8"))
        except OSError:
            continue
        for f in favs:
            if isinstance(f, dict) and f.get("encryptJobId"):
                boss[f["encryptJobId"]] = f.get("bossName") or ""
        if boss:
            break

    rows = []
    for t in targets:
        comp = t.get("company", "")
        bname = boss.get(t.get("jobId"), "")
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
            if np_ and pos_match(v.get("pos", ""), np_):
                picked = (c, v)
                break
        if not picked:
            if cands:
                v = evaluate(STATS)
                if isinstance(v, str):
                    try:
                        v = json.loads(v)
                    except Exception:
                        v = {"err": v}
                picked = (cands[0], v)
            else:
                v = {"err": "no_conv_match"}
                picked = (None, v)

        v = picked[1]
        v["label"] = t["label"]
        v["city"] = t.get("city", "")
        v["company"] = comp
        v["target_pos"] = t.get("position", "")
        v["boss"] = bname
        rows.append(v)
        ok = (v.get("myText", 0) >= 1 and v.get("images", 0) >= 2
              and v.get("brs", 0) >= 1 and pos_match(v.get("pos", ""), np_))
        v["ok"] = ok
        log(f"{'✓' if ok else '✗'} {t.get('city',''):<4} {comp[:12]:<13} 话术{v.get('myText')} "
            f"br={v.get('brs')} 图{v.get('images')} 岗位={str(v.get('pos'))[:22]} "
            f"| {str(v.get('last'))[:46]}")
        if v.get("others"):
            log(f"    对方: {v['others']}")

    out = os.path.join(WORK, f"{PREFIX}_check.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    log(f"[结果] {out}")
    bad = [r for r in rows if not r.get("ok")]
    log(f"合格 {len(rows)-len(bad)}/{len(rows)}"
        + (f"　不合格：{[b['label'] for b in bad]}" if bad else ""))


if __name__ == "__main__":
    main()
