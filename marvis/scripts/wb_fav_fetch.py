# -*- coding: utf-8 -*-
"""wb_fav_fetch.py — 拉取 tag=2/4/5 的列表，打印卡片字段，判断哪个是「我的收藏」。"""
import json
import os
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb import navigate

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")

FETCH = r"""(function(){
    var urls=__URLS__;
    var out=[];
    urls.forEach(function(u){
        try{
            var xhr=new XMLHttpRequest();
            xhr.open('GET',u,false);
            xhr.setRequestHeader('Accept','application/json');
            xhr.send(null);
            var j=JSON.parse(xhr.responseText||'{}');
            var z=j.zpData||{};
            out.push({u:u, code:j.code, msg:j.message,
                      total:z.totalCount,
                      cards:(z.cardList||[]).map(function(c){
                          var o={};
                          Object.keys(c).forEach(function(k){
                              var v=c[k];
                              if(v===null||v===undefined) return;
                              if(typeof v==='object'){
                                  if(v.name||v.text||v.title) o[k]=(v.name||v.text||v.title);
                              } else o[k]=v;
                          });
                          return o;
                      })});
        }catch(e){ out.push({u:u, err:String(e).slice(0,120)}); }
    });
    return JSON.stringify(out);
})()"""

URLS = [
    "/wapi/zprelation/interaction/geekGetJob?page=1&tag=2",
    "/wapi/zprelation/interaction/geekGetJob?page=1&tag=4&isActive=true",
    "/wapi/zprelation/interaction/geekGetJob?page=1&tag=5&isActive=true",
]


def main():
    navigate("https://www.zhipin.com/web/geek/recommend")
    time.sleep(5)
    raw = evaluate(FETCH.replace("__URLS__", json.dumps(URLS)))
    try:
        v = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        print("fail", str(raw)[:300]); return
    with open(os.path.join(WORK, "fav_lists.json"), "w", encoding="utf-8") as f:
        json.dump(v, f, ensure_ascii=False, indent=1)
    for grp in v or []:
        print(f"\n===== {grp.get('u')}  total={grp.get('total')} 拿到 {len(grp.get('cards') or [])} 张")
        for c in (grp.get("cards") or [])[:6]:
            keep = {k: v2 for k, v2 in c.items()
                    if k in ("jobName", "brandName", "cityName", "salaryDesc", "jobId",
                             "encryptJobId", "jobTitle", "companyName", "city", "salary",
                             "collectionTime", "createTime", "positionName", "jobArea",
                             "activeTime", "updateTime", "name", "title", "text")}
            print("   ", json.dumps(keep, ensure_ascii=False)[:300])
        if grp.get("cards"):
            print("    全部字段:", json.dumps(grp["cards"][0], ensure_ascii=False)[:700])


if __name__ == "__main__":
    main()
