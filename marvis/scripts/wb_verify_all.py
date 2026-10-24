# -*- coding: utf-8 -*-
"""wb_verify_all.py — 全量核对 BOSS 会话：话术里的游戏数量 vs 简历图对应的 PDF 数量。

输出每个会话：话术里出现「38 款」还是「数十款」、行数写法、简历图数量。
"""
import json
import os
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb_fiximg import select_conv, log

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")

# 12 个上午的 + 2 个收藏夹 + 14 个跨城
CONVS = [
    ("示例科技Y候选人F女士", "候选人F女士示例科技Y"), ("示例科技Y候选人A女士", "候选人A女士示例科技Y"),
    ("示例文化B", "候选人G先生示例文化B"), ("示例讯动U", "候选人I女士示例讯动U"),
    ("示例科技V", "候选人J先生示例科技V"), ("示例平台I", "候选人K女士示例平台I"),
    ("示例科技C", "候选人D女士示例科技C"), ("示例科技D", "候选人H女士示例科技D"),
    ("示例网络E", "候选人D女士示例网络E"), ("示例传媒T", "候选人J先生示例传媒T"),
    ("示例数据科技", "候选人N先生示例数据科技"), ("示例软件F", "候选人O广州示例软件F"),
    ("示例云服务G", "候选人E女士广州示例云服务G"),
    ("候选人K女士AI开发", "候选人K女士示例广告AB"), ("候选人H先生人工智能", "候选人H先生示例企业24"),
    ("示例大厂JAI全栈", "联系人E北京示例大厂J"), ("示例科技F", "候选人K女士示例科技F"),
    ("示例科技G", "候选人I女士示例科技G"), ("示例企业55", "候选人H先生示例企业55"),
    ("示例科技H", "候选人B先生示例科技H"), ("示例科技N", "联系人C示例科技N"),
    ("示例科技I", "候选人A女士示例科技I"), ("示例科技J", "候选人L先生示例科技J"),
    ("示例科技K", "候选人G先生示例科技K"), ("示例企业62", "联系人M示例企业62"),
    ("示例企业67", "候选人C女士示例企业67"), ("示例科技L", "联系人A示例科技L"),
    ("示例科技M", "联系人B示例科技M"), ("示例企业93", "联系人F示例企业16"),
]

SCAN = r"""(function(){
    var b=document.querySelector('.chat-message');
    if(!b) return {err:'no_box'};
    var li=b.querySelectorAll('li.message-item');
    var imgs=0, mine=[], others=[];
    li.forEach(function(l){
        var isMe=l.className.indexOf('item-myself')>=0;
        var n=l.querySelectorAll('img.message-image').length;
        if(n){ imgs+=n; return; }
        var c=l.querySelector('.message-content');
        var t=(c?(c.innerText||c.textContent||''):(l.textContent||'')).replace(/\s+/g,' ');
        if(!t.trim()) return;
        if(isMe) mine.push(t.trim()); else others.push(t.trim());
    });
    var all=mine.join(' ');
    var cnt38=(all.match(/38\s*款/g)||[]).length;
    var cnt50=(all.match(/50\s*款/g)||[]).length;
    var lines=(all.match(/(\d{5})\s*行/g)||[]);
    var pos=document.querySelector('.position-name');
    return {imgs:imgs, mine:mine.length, others:others.length,
            c38:cnt38, c50:cnt50, lines:lines.slice(0,3),
            pos:pos?(pos.textContent||'').trim():'',
            other:others.map(function(x){return x.slice(0,46);})};
})()"""


def main():
    rows = []
    for label, kw in CONVS:
        sel, idx = select_conv(kw)
        time.sleep(0.9)
        v = evaluate(SCAN)
        if isinstance(v, str):
            try:
                v = json.loads(v)
            except Exception:
                v = {"err": v}
        v["label"] = label
        rows.append(v)
        if v.get("err"):
            log(f"{label:<16} !! {v.get('err')}  (sel={sel})")
            continue
        num = "50款" if v.get("c50") else ("38款" if v.get("c38") else "无数字")
        log(f"{label:<16} 话术{v.get('mine')} 图{v.get('imgs')} 数字={num} 行数写法={v.get('lines')} "
            f"| 对方消息{v.get('other')}")
    out = os.path.join(WORK, "verify_all.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    log(f"[结果] {out}")
    n38 = [r["label"] for r in rows if r.get("c38")]
    log(f"话术里含「38 款」的会话：{len(n38)} 个 → {n38}")


if __name__ == "__main__":
    main()
