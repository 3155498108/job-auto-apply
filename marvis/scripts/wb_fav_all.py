# -*- coding: utf-8 -*-
"""wb_fav_all.py — 拉取 tag=4（疑似收藏）全量，dump 字段与列表。"""
import json
import os
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb import navigate

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")

FETCH = r"""(function(){
    var out=[];
    for(var p=1;p<=8;p++){
        var u='/wapi/zprelation/interaction/geekGetJob?page='+p+'&tag=4&isActive=true';
        try{
            var xhr=new XMLHttpRequest();
            xhr.open('GET',u,false);
            xhr.setRequestHeader('Accept','application/json');
            xhr.send(null);
            var j=JSON.parse(xhr.responseText||'{}');
            var z=j.zpData||{};
            var cards=(z.cardList||[]);
            if(p===1) out.push({_total:z.totalCount, _keys:Object.keys(cards[0]||{})});
            out.push.apply(out, cards);
            if(!cards.length) break;
        }catch(e){ out.push({_err:String(e).slice(0,120)}); break; }
    }
    return JSON.stringify(out);
})()"""


def main():
    navigate("https://www.zhipin.com/web/geek/recommend")
    time.sleep(5)
    raw = evaluate(FETCH)
    try:
        v = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        print("fail", str(raw)[:300]); return
    total = None
    keys = []
    cards = []
    for x in v or []:
        if "_total" in x:
            total = x["_total"]
            keys = x.get("_keys") or []
            continue
        if "_err" in x:
            print("err", x)
            continue
        cards.append(x)
    print(f"totalCount={total}  拿到 {len(cards)} 张")
    print("字段:", ", ".join(keys))
    out = os.path.join(WORK, "favorites_tag4.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=1)
    print(f"→ {out}\n")
    for c in cards:
        print(f"  {str(c.get('cityName','')):<6} {str(c.get('jobSalary','')):<10} "
              f"{str(c.get('jobName',''))[:30]:<32} {str(c.get('brandName',''))[:20]:<22} "
              f"{str(c.get('bossName','')):<8} {c.get('encryptJobId')}")


if __name__ == "__main__":
    main()
