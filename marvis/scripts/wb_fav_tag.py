# -*- coding: utf-8 -*-
"""wb_fav_tag.py — 扫 zprelation/interaction/geekGetJob 的所有 tag，找出收藏列表。"""
import json
import os
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb import navigate

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")

PROBE = r"""(function(){
    var out=[];
    for(var tag=0; tag<=20; tag++){
        var urls=[
          '/wapi/zprelation/interaction/geekGetJob?page=1&tag='+tag,
          '/wapi/zprelation/interaction/geekGetJob?page=1&tag='+tag+'&isActive=true'
        ];
        urls.forEach(function(u){
            try{
                var xhr=new XMLHttpRequest();
                xhr.open('GET',u,false);
                xhr.setRequestHeader('Accept','application/json');
                xhr.send(null);
                var body=(xhr.responseText||'');
                var n=null, first=null;
                try{ var j=JSON.parse(body);
                     var z=j.zpData||{};
                     n = z.totalCount!==undefined ? z.totalCount : (z.cardList?z.cardList.length:null);
                     if(z.cardList&&z.cardList.length) first=JSON.stringify(z.cardList[0]).slice(0,220);
                }catch(e){}
                out.push({tag:tag, u:u, st:xhr.status, n:n, first:first,
                          body:(n===null? body.slice(0,140):'')});
            }catch(e){ out.push({tag:tag,u:u,st:'ERR',body:String(e).slice(0,100)}); }
        });
    }
    return JSON.stringify(out);
})()"""


def main():
    navigate("https://www.zhipin.com/web/geek/recommend")
    time.sleep(5)
    raw = evaluate(PROBE)
    try:
        v = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        print("fail", str(raw)[:300]); return
    for x in v or []:
        if x.get("n"):
            print(f"  tag={x['tag']:<3} n={x['n']:<5} {x['u'][-30:]:<32} {str(x.get('first'))[:190]}")
    with open(os.path.join(WORK, "fav_tag_probe.json"), "w", encoding="utf-8") as f:
        json.dump(v, f, ensure_ascii=False, indent=1)
    print("\n所有返回：")
    for x in v or []:
        b = " ".join(str(x.get("body") or "").split())[:90]
        print(f"  tag={x['tag']:<3} [{x['st']}] n={x.get('n')} {b}")


if __name__ == "__main__":
    main()
