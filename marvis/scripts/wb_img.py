#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_img.py — 向 BOSS 聊天会话发送简历截图（图片）。

机制：聊天输入区工具栏「图片」按钮背后是一个隐藏的
      <input type=file accept="image/...">，用 WebBridge 的 upload 动作喂文件。

用法:
    python wb_img.py <会话关键词> <图片路径>
    python wb_img.py --all            # 按内置映射批量发 12 个
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate
from scripts.wb import call

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")
RECRUIT = r"YOUR_HOME\招聘"

IMG_INPUT = "input[type=file][accept*='image/png']"

# BOSS 12 个岗位 → 会话关键词 + 简历首页截图
SEND_MAP = [
    dict(conv="示例科技A", img=r"示例科技A-后端JAVA开发实习生\shot_示例20_p1.png"),
    dict(conv="示例文化B", img=r"AI应用与Agent工程实习生\shot_示例16_p1.png"),
    dict(conv="示例讯动U", img=r"Java后端开发实习生\shot_guangzhou-java_p1.png"),
    dict(conv="示例科技V", img=r"java实习生\shot_示例13_p1.png"),
    dict(conv="示例平台I", img=r"产品实习生\shot_示例14_p1.png"),
    dict(conv="示例科技C", img=r"全栈开发实习生\shot_示例12_p1.png"),
    dict(conv="示例科技D", img=r"示例科技D-游戏开发实习生\shot_示例15_p1.png"),
    dict(conv="示例网络E", img=r"后端开发实习生\shot_示例17_p1.png"),
    dict(conv="示例传媒T", img=r"示例传媒T-AI智能体研发实习生\shot_示例21_p1.png"),
    dict(conv="示例数据科技", img=r"研发实习生\shot_示例18_p1.png"),
    dict(conv="示例软件F", img=r"软件实习生\shot_示例19_p1.png"),
    dict(conv="示例企业69", img=r"示例云服务G-AI全栈开发工程师\shot_示例11_p1.png"),
]

LIST_JS = r"""JSON.stringify((function(){
    var out=[];
    document.querySelectorAll('.friend-content').forEach(function(e,i){
        var r=e.getBoundingClientRect();
        if(r.width<=0||r.height<=0) return;
        out.push({i:i, y:Math.round(r.top), t:(e.textContent||'').replace(/\s+/g,' ').trim().slice(0,70)});
    });
    return out;
})())"""

# 聊天区里的图片消息数（用于确认发送成功）
IMG_COUNT_JS = r"""(function(){
    var n=0, urls=[];
    document.querySelectorAll('.chat-record img, .message-item img, [class*="message"] img').forEach(function(e){
        var r=e.getBoundingClientRect();
        if(r.width>0&&r.height>0){ n++; if(urls.length<4) urls.push((e.src||'').slice(-50)); }
    });
    return n+'|'+(document.querySelectorAll('.chat-record').length)+'|'+urls.join(',');
})()"""


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def select_conv(kw):
    raw = evaluate(LIST_JS)
    try:
        convs = json.loads(raw) if raw else []
    except Exception:
        return "list_failed"
    hits = [c for c in convs if kw in c["t"]]
    if not hits:
        return "not_found"
    hits.sort(key=lambda c: c["y"])
    idx = hits[0]["i"]
    r = evaluate(r"""(function(){
        var list=document.querySelectorAll('.friend-content');
        var e=list[%d]; if(!e) return 'gone';
        e.scrollIntoView({block:'center'}); e.click(); return 'clicked';
    })()""" % idx)
    time.sleep(2.5)
    sel = evaluate(r"""(function(){
        var s=document.querySelector('.friend-content.selected');
        return s?((s.textContent||'').replace(/\s+/g,' ').trim().slice(0,50)):'none';
    })()""")
    return f"{r} | {sel}"


def send_img(path, tag="img"):
    """把图片文件喂给隐藏的 file input。"""
    if not os.path.isfile(path):
        return "file_missing", path
    before = evaluate(IMG_COUNT_JS)
    r = call("upload", {"selector": IMG_INPUT, "files": [path]})
    time.sleep(2.5)
    after = evaluate(IMG_COUNT_JS)
    ok = "ok" in json.dumps(r, ensure_ascii=False) and "success" in json.dumps(r, ensure_ascii=False)
    call("screenshot", {"path": os.path.join(WORK, f"img_{tag}.png"), "format": "png"})
    return f"upload_ok={ok} before={before} after={after}", json.dumps(r, ensure_ascii=False)[:200]


def main():
    if sys.argv[1] == "--all":
        jobs = SEND_MAP
    else:
        kw = sys.argv[1]
        path = os.path.abspath(sys.argv[2])
        jobs = [dict(conv=kw, img=path)]
        jobs[0]["abs"] = True

    for j in jobs:
        path = j.get("abs") and j["img"] or os.path.join(RECRUIT, j["img"])
        log(f"--- {j['conv']}  ← {os.path.basename(path)}")
        if not os.path.isfile(path):
            log(f"    !! 文件不存在: {path}")
            continue
        log(f"    选会话 {select_conv(j['conv'])}")
        res, raw = send_img(path, tag=j["conv"])
        log(f"    发送 {res}")
        time.sleep(2)


if __name__ == "__main__":
    raise SystemExit(main())
