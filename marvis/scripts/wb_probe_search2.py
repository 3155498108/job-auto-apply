# -*- coding: utf-8 -*-
"""wb_probe_search2.py — 诊断聊天页搜索：填值后点击搜索图标，看会话列表是否变化。"""
import json
import os
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb import call, navigate

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")
CHAT = "https://www.zhipin.com/web/geek/chat"

COUNT = r"""(function(){return document.querySelectorAll('.friend-content').length;})()"""

TITLES = r"""JSON.stringify(Array.prototype.slice.call(
    document.querySelectorAll('.friend-content'),0,8).map(function(e){
        return (e.textContent||'').replace(/\s+/g,' ').trim().slice(0,60);}))"""

FILL = r"""(function(){
    var e=document.querySelector('.boss-search-input');
    if(!e) return 'no_input';
    e.focus(); e.value='示例科技Y';
    e.dispatchEvent(new Event('input',{bubbles:true}));
    return 'filled:'+(e.value||'');
})()"""

CLICK_ICON = r"""(function(){
    var sels=['.icon-search','.boss-search-container','.boss-search-top'];
    for(var i=0;i<sels.length;i++){
        var e=document.querySelector(sels[i]);
        if(!e) continue;
        var r=e.getBoundingClientRect();
        if(r.width<=0||r.height<=0) continue;
        e.click();
        return 'clicked:'+sels[i];
    }
    return 'no_icon';
})()"""

SCROLL_PROBE = r"""JSON.stringify((function(){
    var out=[];
    document.querySelectorAll('div,ul,section').forEach(function(e){
        if(e.scrollHeight>e.clientHeight+30 && e.clientHeight>80){
            out.push({cls:(e.className||'').toString().slice(0,50),
                      sh:e.scrollHeight, ch:e.clientHeight});
        }
    });
    return out.slice(0,15);
})())"""


def main():
    navigate(CHAT)
    time.sleep(6)
    print("初始会话数", evaluate(COUNT))
    print("可滚动容器:", evaluate(SCROLL_PROBE))
    print("fill →", evaluate(FILL))
    time.sleep(1.5)
    print("fill 后会话数", evaluate(COUNT))
    print("click 图标 →", evaluate(CLICK_ICON))
    time.sleep(2.5)
    print("点击后会话数", evaluate(COUNT))
    print("前 8 条:", evaluate(TITLES))
    call("screenshot", {"path": os.path.join(WORK, "probe_search2.png"), "format": "png"})


if __name__ == "__main__":
    main()
