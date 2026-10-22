# -*- coding: utf-8 -*-
"""探测 BOSS 收藏夹所有分组（tag=0..10）的数量，找出是否漏了分组。"""
import io, json, os, sys, time
sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb import navigate

WORK = r"YOUR_HOME\output\boss_work"

FETCH = r"""(function(){
    var out=[];
    for(var t=0;t<=10;t++){
        var cnt=0, total=null, err=null, sample=null;
        for(var p=1;p<=6;p++){
            var u='/wapi/zprelation/interaction/geekGetJob?page='+p+'&tag='+t+'&isActive=true';
            try{
                var xhr=new XMLHttpRequest();
                xhr.open('GET',u,false);
                xhr.setRequestHeader('Accept','application/json');
                xhr.send(null);
                var j=JSON.parse(xhr.responseText||'{}');
                var z=j.zpData||{};
                var cards=(z.cardList||[]);
                if(p===1){ total=z.totalCount; }
                cnt+=cards.length;
                if(p===1 && cards.length) sample={name:cards[0].jobName, brand:cards[0].brandName};
                if(!cards.length) break;
            }catch(e){ err=String(e).slice(0,80); break; }
        }
        out.push({tag:t, total:total, got:cnt, err:err, sample:sample});
    }
    return JSON.stringify(out);
})()"""

def main():
    navigate("https://www.zhipin.com/web/geek/recommend")
    time.sleep(5)
    raw = evaluate(FETCH)
    try:
        rows = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        print("parse fail:", str(raw)[:300]); return
    io.open(os.path.join(WORK, "fav_tags_probe.json"), "w", encoding="utf-8").write(
        json.dumps(rows, ensure_ascii=False, indent=1))
    for r in rows:
        s = r.get("sample") or {}
        print(f"tag={r['tag']:<3} total={str(r.get('total')):<6} got={r.get('got'):<4} "
              f"err={r.get('err')} sample={s.get('name')} / {s.get('brand')}")

if __name__ == "__main__":
    main()
