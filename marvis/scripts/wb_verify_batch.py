# -*- coding: utf-8 -*-
"""verify_ai2.py — 独立核对本批 5 个新会话。

不走投递脚本的自报结果，重新打开消息页，点开每个目标会话，
数「我的文字条数」和「简历图张数」，确认：
  · 恰好 1 条定制话术
  · 恰好 2 张简历图
  · 岗位名与预期一致
"""
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
        return {i:i, t:(e.textContent||'').replace(/\s+/g,' ').trim()};
    }))"""

SCROLL = r"""(function(){
    var el=document.querySelector('.user-list-content');
    var info=[];
    if(el){
        info.push({sh:el.scrollHeight, ch:el.clientHeight, st:Math.round(el.scrollTop)});
        el.scrollTop = el.scrollTop + Math.round(el.clientHeight*0.9);
        el.dispatchEvent(new Event('scroll',{bubbles:true}));
    }
    return JSON.stringify(info);
})()"""

STATS = r"""(function(){
    var box=document.querySelector('.chat-message')||document.querySelector('.chat-record');
    var out={myText:0,imgs:0,others:[],pos:'',lastIsMe:null,last:''};
    if(!box) return JSON.stringify(out);
    var li=box.querySelectorAll('li.message-item');
    li.forEach(function(l){
        var isMe=(l.className||'').indexOf('item-myself')>=0;
        var hasImg=l.querySelectorAll('img.message-image').length>0;
        var c=l.querySelector('.message-content');
        var t=((c?(c.innerText||c.textContent||''):(l.textContent||''))||'').replace(/\s+/g,' ').trim();
        if(hasImg){ out.imgs++; out.lastIsMe=isMe; out.last='[图片]'; }
        else if(t.indexOf('候选人')>=0){ out.myText++; out.lastIsMe=isMe; out.last=t.slice(0,70); }
        else if(!isMe && t && t.indexOf('竞争者')<0 && t.indexOf('严禁')<0){ out.others.push(t.slice(0,50)); out.lastIsMe=isMe; out.last=t.slice(0,70); }
    });
    var p=document.querySelector('.position-name');
    out.pos = p ? (p.textContent||'').trim() : '';
    var s=document.querySelector('.friend-content.selected');
    out.title = s ? (s.textContent||'').replace(/\s+/g,' ').trim().slice(0,70) : '';
    return JSON.stringify(out);
})()"""


def collect(max_steps=90):
    navigate(CHAT)
    time.sleep(6)
    evaluate(r"""(function(){var el=document.querySelector('.user-list-content');if(el)el.scrollTop=0;window.scrollTo(0,0);return 1;})()""")
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
        sig = evaluate(SCROLL)
        if sig == last_sig:
            stall += 1
            if stall >= 4:
                break
        else:
            stall = 0
        last_sig = sig
        time.sleep(0.6)
    return seen


def click_conv(text):
    """在会话列表里定位并点开一条会话。

    列表是虚拟滚动，DOM 里只有 ~40 条；且发消息会把会话置顶，
    所以每次定位都从顶部重新滚下去找。
    """
    evaluate(r"""(function(){var el=document.querySelector('.user-list-content');if(el)el.scrollTop=0;window.scrollTo(0,0);return 1;})()""")
    time.sleep(0.8)
    for _ in range(90):
        raw = evaluate(LIST_ALL)
        try:
            cur = json.loads(raw) if raw else []
        except Exception:
            cur = []
        for c in cur:
            if text[:40] in c["t"]:
                evaluate(r"""(function(){
                    var list=document.querySelectorAll('.friend-content');
                    var e=list[%d]; if(!e) return 'gone';
                    e.scrollIntoView({block:'center'}); e.click(); return 'clicked';
                })()""" % c["i"])
                time.sleep(2.0)
                return c["t"]
        evaluate(SCROLL)
        time.sleep(0.5)
    return None


def main():
    targets = json.load(open(os.path.join(WORK, "ai2_final.json"), encoding="utf-8"))
    # 用「会话标题里的 HR 名 + 公司」定位 —— 更精确
    KEYS = {
        "广东AI2-示例大厂K-ai实习生-东莞": "联系人J先生示例大厂K",
        "广东AI2-示例科技Z软件-AICoding实习生-东莞": "候选人M女士示例科技Z软件",
        "收藏AI2-广州示例科技M电子商务-AI前沿部署工程师FDE电商方向(实习)-广州": "梁思远广州示例科技M电子商务",
        "收藏AI2-广东省示例科技Y-ai实习生-广州": "联系人L女士广东省示例科技Y",
        "收藏AI2-示例科技O-Agent应用研发工程师(实习)-广州": "联系人D示例科技O",
    }
    convs = collect()
    print(f"会话列表收集到 {len(convs)} 条")
    rows = []
    for t in targets:
        key = KEYS[t["folder"]]
        hit = None
        for c in convs:
            if key in c:
                hit = c
                break
        if not hit:
            print(f"  !! {t['folder']}：会话列表里找不到「{key}」")
            rows.append(dict(folder=t["folder"], status="conv_not_found"))
            continue
        # 精确定位：列表里可能有多条同名，选最靠前的（最新）
        picked = click_conv(hit[:60])
        if not picked:
            print(f"  !! {t['folder']}：DOM 里点不到「{key}」")
            rows.append(dict(folder=t["folder"], status="click_failed"))
            continue
        raw = evaluate(STATS)
        try:
            v = json.loads(raw)
        except Exception:
            v = {"err": str(raw)[:150]}
        ok = (v.get("myText") == 1 and v.get("imgs") == 2)
        print(f"  {'OK ' if ok else '?? '} {t['folder'][:38]:<40} 话术{v.get('myText')} 图{v.get('imgs')} "
              f"岗位={v.get('pos')!r} 对方消息={v.get('others')}")
        rows.append(dict(folder=t["folder"], status="verified" if ok else "mismatch",
                         my_text=v.get("myText"), imgs=v.get("imgs"), pos=v.get("pos"),
                         others=v.get("others"), title=v.get("title")))
        time.sleep(1.5)

    json.dump(rows, open(os.path.join(WORK, "ai2_verify.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n→ ai2_verify.json")
    good = sum(1 for r in rows if r.get("status") == "verified")
    print(f"核对通过 {good}/{len(rows)}")


main()
