#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_imgbatch.py — 批量把各岗位的简历截图发到对应 BOSS 会话。

要点:
  1. 图片按钮是 .btn-sendimg，其内部 <input type=file accept="image/..."> 用
     WebBridge 的 upload 动作喂文件（需扩展已开「允许访问文件网址」）。
  2. 上传后 BOSS 走 POST /wapi/zpupload/quicklyUpload，再从 imgaz.bosszhipin.com
     取图，渲染有延迟 —— 必须轮询等大图数量增加，不能立刻截图判断。
  3. 幂等：发送前统计会话内大图(.message-image)数量，已发过就跳过。

用法: python wb_imgbatch.py [会话关键词 ...]
不带参数 = 全部 12 个。
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
IMG_SELECTOR = ".btn-sendimg input[type=file]"

# 会话关键词 → 简历首页截图（相对 招聘\ 目录）
SEND_MAP = [
    ("示例科技A", r"示例科技A-后端JAVA开发实习生\shot_示例20_p1.png"),
    ("示例文化B", r"AI应用与Agent工程实习生\shot_示例16_p1.png"),
    ("示例讯动U", r"Java后端开发实习生\shot_guangzhou-java_p1.png"),
    ("示例科技V", r"java实习生\shot_示例13_p1.png"),
    ("示例平台I", r"产品实习生\shot_示例14_p1.png"),
    ("示例科技C", r"全栈开发实习生\shot_示例12_p1.png"),
    ("示例科技D", r"示例科技D-游戏开发实习生\shot_示例15_p1.png"),
    ("示例网络E", r"后端开发实习生\shot_示例17_p1.png"),
    ("示例传媒T", r"示例传媒T-AI智能体研发实习生\shot_示例21_p1.png"),
    ("示例数据科技", r"研发实习生\shot_示例18_p1.png"),
    ("示例软件F", r"软件实习生\shot_示例19_p1.png"),
    ("示例企业69", r"示例云服务G-AI全栈开发工程师\shot_示例11_p1.png"),
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

IMG_N_JS = r"""(function(){
    var b=document.querySelector('.chat-record');
    if(!b) return -1;
    return b.querySelectorAll('.message-image').length;
})()"""

IMG_LIST_JS = r"""JSON.stringify(Array.prototype.slice.call(
    document.querySelectorAll('.chat-record .message-image')).map(function(e,i){
        var r=e.getBoundingClientRect();
        return {i:i, w:Math.round(r.width), h:Math.round(r.height), src:(e.querySelector('img')?e.querySelector('img').src:'').slice(-40)};
    }))"""


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
    evaluate(r"""(function(){
        var list=document.querySelectorAll('.friend-content');
        var e=list[%d]; if(!e) return 'gone';
        e.scrollIntoView({block:'center'}); e.click(); return 'clicked';
    })()""" % idx)
    time.sleep(2.5)
    sel = evaluate(r"""(function(){
        var s=document.querySelector('.friend-content.selected');
        return s?((s.textContent||'').replace(/\s+/g,' ').trim().slice(0,50)):'none';
    })()""")
    return f"{sel}"


def img_count():
    try:
        return int(evaluate(IMG_N_JS) or -1)
    except (TypeError, ValueError):
        return -1


def send_one(kw, img_rel):
    path = os.path.join(RECRUIT, img_rel)
    log(f"--- {kw}  ← {os.path.basename(img_rel)}")
    if not os.path.isfile(path):
        log(f"    !! 文件不存在: {path}")
        return dict(conv=kw, status="file_missing")
    sel = select_conv(kw)
    log(f"    会话 {sel}")
    if sel == "not_found" or sel == "list_failed":
        return dict(conv=kw, status="conv_not_found")

    before = img_count()
    log(f"    现有大图 {before}")
    if before >= 1:
        log("    !! 该会话已有简历图，跳过")
        return dict(conv=kw, status="already_has_image", before=before)

    r = call("upload", {"selector": IMG_SELECTOR, "files": [path]})
    if not r.get("ok"):
        log(f"    !! 上传失败 {json.dumps(r, ensure_ascii=False)[:200]}")
        return dict(conv=kw, status="upload_failed")

    # 轮询等大图出现
    after = before
    for i in range(10):
        time.sleep(2.0)
        after = img_count()
        if after > before:
            break
    log(f"    大图 {before} → {after}")
    time.sleep(1.5)
    call("screenshot", {"path": os.path.join(WORK, f"img_{kw}.png"), "format": "png"})
    return dict(conv=kw, status="sent" if after > before else "no_image_after_upload",
                before=before, after=after, imgs=evaluate(IMG_LIST_JS))


def main():
    only = set(sys.argv[1:])
    results = []
    for kw, rel in SEND_MAP:
        if only and kw not in only:
            continue
        try:
            results.append(send_one(kw, rel))
        except Exception as e:
            log(f"    !! 异常 {e}")
            results.append(dict(conv=kw, status="error", detail=str(e)))
        time.sleep(1.5)

    log("=== 批量发图完成 ===")
    for r in results:
        log(f"    {r['status']:<20} {r['conv']}")
    out = os.path.join(WORK, "img_result.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    log(f"[结果] {out}")


if __name__ == "__main__":
    raise SystemExit(main())
