#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_final.py — 最终核对：13 个会话的文字话术条数 + 图片条数。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate
from scripts.wb import call
from scripts.wb_fiximg import select_conv, log

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")

STATS = r"""(function(){
    var b=document.querySelector('.chat-message');
    if(!b) return {err:'no_box'};
    var li=b.querySelectorAll('li.message-item');
    var text=0, imgs=0, myText=0, other=[];
    li.forEach(function(l){
        var isMe = l.className.indexOf('item-myself')>=0;
        var hasImg = l.querySelectorAll('img.message-image').length>0;
        var t=(l.textContent||'').replace(/\s+/g,' ').trim();
        if(hasImg){ imgs++; return; }
        if(t.indexOf('候选人')>=0){ text++; if(isMe) myText++; return; }
        if(!isMe && t && t.indexOf('竞争者')>=0) return;
        if(!isMe && t) other.push(t.slice(0,40));
    });
    var srcs=[];
    b.querySelectorAll('img.message-image').forEach(function(i,k){
        srcs.push((i.src||'').split('ff9281')[1] ? 'S'+((i.src||'').split('ff9281')[1]||'').slice(0,10) : 'X');
    });
    return {total:li.length, myGreeting:text, images:imgs, imgIds:srcs, other:other.slice(0,3)};
})()"""

TARGETS = [
    ("示例科技A", "候选人D女士示例科技Y"), ("示例科技A2", "候选人A女士示例科技Y"), ("示例文化B", "候选人G先生示例文化B"),
    ("示例讯动U", "候选人I女士示例讯动U"), ("示例科技V", "候选人J先生示例科技V"), ("示例平台I", "候选人F女士示例平台I"),
    ("示例科技C", "候选人B女士示例科技C"), ("示例科技D", "候选人H女士示例科技D"), ("示例网络E", "候选人B女士示例网络E"),
    ("示例传媒T", "候选人E先生示例传媒T"), ("示例数据科技", "候选人N先生示例数据科技"),
    ("示例软件F", "候选人O广州示例软件F"), ("示例云服务G", "候选人C女士广州示例云服务G"),
]


def main():
    rows = []
    for label, kw in TARGETS:
        sel, i = select_conv(kw)
        time.sleep(1.0)
        v = evaluate(STATS)
        if isinstance(v, str):
            try:
                v = json.loads(v)
            except Exception:
                v = {"err": v}
        v["label"] = label
        v["sel"] = sel
        rows.append(v)
        log(f"{label:<12} {str(v.get('myGreeting')):>3} 条话术  {str(v.get('images')):>2} 张图  "
            f"总{v.get('total')}  {str(v.get('imgIds'))}")
    out = os.path.join(WORK, "final_check.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    log(f"[结果] {out}")


if __name__ == "__main__":
    raise SystemExit(main())
