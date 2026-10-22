#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_fav_pull.py — 拉取收藏夹全部分组的岗位卡片（分页拉满）。

v1 的 bug：只拉 tag=4、且最多 8 页，漏掉了 tag=5（total 232）。
本脚本按 totalCount 自适应翻页，支持多 tag。

用法: python wb_fav_pull.py 4,5
输出: output/boss_work/favorites_tag<N>.json
"""
import io
import json
import os
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb import navigate

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")


def build_fetch(tags):
    tl = ",".join(str(t) for t in tags)
    return r"""(function(){
    var TAGS=[%s];
    var out=[];
    for(var ti=0;ti<TAGS.length;ti++){
        var t=TAGS[ti], page=1, total=null, cards=[];
        while(page<=40){
            var u='/wapi/zprelation/interaction/geekGetJob?page='+page+'&tag='+t+'&isActive=true';
            try{
                var xhr=new XMLHttpRequest();
                xhr.open('GET',u,false);
                xhr.setRequestHeader('Accept','application/json');
                xhr.send(null);
                var j=JSON.parse(xhr.responseText||'{}');
                var z=j.zpData||{};
                var c=(z.cardList||[]);
                if(page===1){ total=z.totalCount; out.push({_tag:t,_total:total,_keys:Object.keys(c[0]||{})}); }
                if(!c.length) break;
                c.forEach(function(x){ x._tag=t; });
                cards=cards.concat(c);
                if(total && cards.length>=total) break;
                page++;
            }catch(e){ out.push({_tag:t,_err:String(e).slice(0,120)}); break; }
        }
        out.push.apply(out, cards);
    }
    return JSON.stringify(out);
})()""" % tl


def main():
    tags = [int(x) for x in (sys.argv[1] if len(sys.argv) > 1 else "4,5").split(",")]
    navigate("https://www.zhipin.com/web/geek/recommend")
    time.sleep(6)
    raw = evaluate(build_fetch(tags))
    try:
        v = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        print("parse fail:", str(raw)[:300])
        return
    buckets = {t: [] for t in tags}
    totals = {}
    for x in v or []:
        if "_total" in x:
            totals[x["_tag"]] = x["_total"]
            continue
        if "_err" in x:
            print("err", x)
            continue
        t = x.get("_tag")
        if t in buckets:
            buckets[t].append(x)
    for t in tags:
        cards = buckets[t]
        # 去重（分页可能重复）
        seen, uniq = set(), []
        for c in cards:
            k = c.get("encryptJobId")
            if k and k not in seen:
                seen.add(k)
                uniq.append(c)
        out = os.path.join(WORK, f"favorites_tag{t}.json")
        json.dump(uniq, io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"tag={t} total={totals.get(t)} 拉取={len(cards)} 去重后={len(uniq)} → {out}")


if __name__ == "__main__":
    main()
