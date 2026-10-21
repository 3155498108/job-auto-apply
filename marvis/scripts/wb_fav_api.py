# -*- coding: utf-8 -*-
"""wb_fav_api.py — 试出「我的收藏」列表接口（页内 fetch，带 cookie）。"""
import json
import os
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb import call, navigate

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")

CANDIDATES = [
    "/wapi/zpgeek/collection/list",
    "/wapi/zpgeek/collection/list.json",
    "/wapi/zpgeek/collection/job/list",
    "/wapi/zpgeek/collection/job/list.json",
    "/wapi/zpgeek/collection/query",
    "/wapi/zpgeek/collection/query.json",
    "/wapi/zpgeek/collection/geek/list",
    "/wapi/zpgeek/collection/get",
    "/wapi/zpgeek/collection/info",
    "/wapi/zpgeek/collection/all",
    "/wapi/zpgeek/job/collection/list",
    "/wapi/zpgeek/collect/list",
    "/wapi/zpgeek/favorite/list",
    "/wapi/zpgeek/brand/collection/list",
    "/wapi/zprelation/collection/geekGetJob?page=1",
    "/wapi/zprelation/interaction/geekGetJob?page=1&tag=3",
    "/wapi/zprelation/interaction/geekGetJob?page=1&tag=4",
    "/wapi/zprelation/interaction/geekGetJob?page=1&tag=6",
]

PROBE = r"""(function(){
    var urls = __URLS__;
    var out=[];
    urls.forEach(function(u){
        try{
            var xhr=new XMLHttpRequest();
            xhr.open('GET', u, false);
            xhr.setRequestHeader('Accept','application/json');
            xhr.send(null);
            var body=(xhr.responseText||'').slice(0,300);
            out.push({u:u, st:xhr.status, body:body});
        }catch(e){ out.push({u:u, st:'ERR', body:String(e).slice(0,120)}); }
    });
    return JSON.stringify(out);
})()"""


def main():
    navigate("https://www.zhipin.com/web/geek/recommend")
    time.sleep(5)
    js = PROBE.replace("__URLS__", json.dumps(CANDIDATES))
    raw = evaluate(js)
    try:
        v = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        print("fail:", str(raw)[:400]); return
    for x in v or []:
        flag = ""
        if x["st"] == 200 and ("code" in x["body"] or "list" in x["body"] or "job" in x["body"]):
            flag = "  <== 有戏"
        print(f"  [{x['st']}] {x['u']:<58}{x['body'][:110]}{flag}")
    with open(os.path.join(WORK, "fav_api_probe.json"), "w", encoding="utf-8") as f:
        json.dump(v, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
