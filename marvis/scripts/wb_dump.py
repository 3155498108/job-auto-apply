# -*- coding: utf-8 -*-
"""wb_dump.py — 导出指定会话的完整消息明细（发/收、文字/图片、是否带换行）。

用法: python wb_dump.py <会话关键词> [更多关键词...]
"""
import json
import os
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb import call
from scripts.wb_fiximg import select_conv, log

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")

DUMP = r"""JSON.stringify((function(){
    var b=document.querySelector('.chat-message');
    if(!b) return {err:'no_box'};
    var out=[];
    b.querySelectorAll('li.message-item').forEach(function(l,i){
        var isMe = l.className.indexOf('item-myself')>=0;
        var img = l.querySelectorAll('img.message-image').length;
        var c  = l.querySelector('.message-content');
        var raw = c ? (c.innerText||c.textContent||'') : (l.textContent||'');
        var html = c ? (c.innerHTML||'') : '';
        // 行数：<p>/<div>/<br> 数量
        var brs = (html.match(/<br\s*\/?>/gi)||[]).length;
        var ps  = (html.match(/<p[\s>]/gi)||[]).length;
        var divs= (html.match(/<div[\s>]/gi)||[]).length;
        out.push({i:i, me:isMe, img:img,
                  text:raw.replace(/\u00a0/g,' '),
                  lines: raw.split('\n').filter(function(x){return x.trim();}).length,
                  brs:brs, ps:ps, divs:divs,
                  html:html.replace(/\s+/g,' ').slice(0,260)});
    });
    var pos=document.querySelector('.position-name');
    var sel=document.querySelector('.friend-content.selected');
    return {pos: pos?(pos.textContent||'').trim():'',
            conv: sel?(sel.textContent||'').replace(/\s+/g,' ').trim():'',
            msgs:out};
})())"""


def main():
    kws = sys.argv[1:]
    if not kws:
        print("用法: wb_dump.py <会话关键词>")
        return 2
    for kw in kws:
        sel, i = select_conv(kw)
        time.sleep(1.0)
        raw = evaluate(DUMP)
        try:
            v = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            v = {"err": str(raw)[:400]}
        log(f"===== 关键词[{kw}] 选中[{i}] {str(sel)[:50]}")
        if not isinstance(v, dict) or "msgs" not in v:
            log(f"    !! {v}")
            continue
        log(f"    岗位={v.get('pos')}  会话={str(v.get('conv'))[:60]}")
        for m in v["msgs"]:
            tag = "我" if m["me"] else "TA"
            if m["img"]:
                log(f"    [{m['i']}] {tag} <图片 x{m['img']}>")
            else:
                log(f"    [{m['i']}] {tag} 行数={m['lines']} br={m['brs']} p={m['ps']} div={m['divs']}")
                for ln in m["text"].split("\n"):
                    if ln.strip():
                        log(f"          | {ln}")
        call("screenshot", {"path": os.path.join(WORK, f"dump_{kw}.png"), "format": "png"})
        with open(os.path.join(WORK, f"dump_{kw}.json"), "w", encoding="utf-8") as f:
            json.dump(v, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
