# -*- coding: utf-8 -*-
"""wb_imginfo.py — 查看当前选中会话里每张图片的完整 URL 与尺寸。"""
import json
import os
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb import call
from scripts.wb_fiximg import select_conv

JS = r"""JSON.stringify(Array.prototype.map.call(
    document.querySelectorAll('.chat-message li.message-item'), function(l,i){
        var im=l.querySelectorAll('img.message-image');
        if(!im.length) return null;
        return {i:i, list: Array.prototype.map.call(im, function(e,k){
            return {k:k, src:(e.src||''), w:e.naturalWidth, h:e.naturalHeight,
                    disp: Math.round(e.getBoundingClientRect().width)+'x'+Math.round(e.getBoundingClientRect().height)};
        })};
    }).filter(Boolean))"""


def main():
    kw = sys.argv[1]
    sel, i = select_conv(kw)
    time.sleep(1.2)
    raw = evaluate(JS)
    try:
        v = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        print("fail", str(raw)[:300]); return
    print("选中:", sel)
    for grp in v:
        for im in grp["list"]:
            s = im["src"]
            print(f"  msg[{grp['i']}] img{im['k']}  {im['w']}x{im['h']} 显示{im['disp']}")
            print(f"      {s}")
    # 滚到会话底部再截一张全图
    evaluate(r"""(function(){
        var b=document.querySelector('.chat-message'); if(b) b.scrollTop=b.scrollHeight; return 1;})()""")
    time.sleep(1.5)
    call("screenshot", {"path": r"YOUR_HOME\output\boss_work\conv_img_info.png", "format": "png"})


if __name__ == "__main__":
    main()
