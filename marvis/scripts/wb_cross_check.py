# -*- coding: utf-8 -*-
"""wb_cross_check.py — 核对跨城 14 个会话：话术条数 / 换行 br 数 / 图片数 / 岗位名。"""
import json
import os
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb import call
from scripts.wb_fiximg import select_conv, log

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")

STATS = r"""(function(){
    var b=document.querySelector('.chat-message');
    if(!b) return {err:'no_box'};
    var li=b.querySelectorAll('li.message-item');
    var text=0, imgs=0, brs=0, other=[], myText=0, lastText='';
    li.forEach(function(l){
        var isMe=l.className.indexOf('item-myself')>=0;
        var n=l.querySelectorAll('img.message-image').length;
        if(n){ imgs+=n; return; }
        var c=l.querySelector('.message-content');
        var h=c?(c.innerHTML||''):'';
        var t=(c?(c.innerText||c.textContent||''):(l.textContent||''));
        if(t.indexOf('候选人')>=0){ text++; if(isMe){ myText++; brs += (h.match(/<br\s*\/?>/gi)||[]).length; lastText=t.replace(/\s+/g,' ').trim(); } return; }
        if(!isMe && t && t.indexOf('竞争者')<0) other.push(t.replace(/\s+/g,' ').trim().slice(0,40));
    });
    var pos=document.querySelector('.position-name');
    var sel=document.querySelector('.friend-content.selected');
    return {total:li.length, myText:myText, text:text, images:imgs, brs:brs,
            pos:pos?(pos.textContent||'').trim():'',
            conv:sel?(sel.textContent||'').replace(/\s+/g,' ').trim().slice(0,60):'',
            other:other.slice(0,3), last:lastText.slice(0,90)};
})()"""


def main():
    targets = json.load(open(os.path.join(WORK, "crosscity_targets.json"), encoding="utf-8"))
    rows = []
    for t in targets:
        kw = t["company"]
        sel, idx = select_conv(kw)
        time.sleep(1.0)
        v = evaluate(STATS)
        if isinstance(v, str):
            try:
                v = json.loads(v)
            except Exception:
                v = {"err": v}
        v["label"] = t["label"]
        v["city"] = t["city"]
        v["company"] = t["company"]
        rows.append(v)
        log(f"{t['city']:<4} {t['company']:<14} 话术{v.get('myText')} br={v.get('brs')} 图{v.get('images')} "
            f"总{v.get('total')}  岗位={str(v.get('pos'))[:24]}  {str(v.get('last'))[:50]}")
    out = os.path.join(WORK, "cross_check.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    log(f"[结果] {out}")
    bad = [r for r in rows if r.get("myText", 0) < 1 or r.get("images", 0) < 2 or r.get("brs", 0) < 1]
    log(f"合格 {len(rows)-len(bad)}/{len(rows)}" + (f"　不合格：{[b['label'] for b in bad]}" if bad else ""))


if __name__ == "__main__":
    main()
