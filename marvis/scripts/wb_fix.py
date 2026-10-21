# -*- coding: utf-8 -*-
"""wb_fix.py — 给已存在的会话补发一条更正话术 + 重发对口简历图。

幂等：消息里已含标记词（如「更正一个数字」）就跳过。
用法: python wb_fix.py <会话关键词> <标记词> <图片相对招聘目录路径> [更多图片...]
"""
import json
import os
import sys
import time

sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate
from scripts.wb import call
from scripts.wb_fiximg import select_conv
import scripts.wb_deliver as D

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")
RECRUIT = r"YOUR_HOME\招聘"
CHAT_URL = "https://www.zhipin.com/web/geek/chat"
IMG_SEL = ".btn-sendimg input[type=file]"

TEXT = r"""(function(){
    var b=document.querySelector('.chat-message');
    if(!b) return '';
    var out=[];
    b.querySelectorAll('li.message-item.item-myself .message-content').forEach(function(e){
        out.push(e.innerText||e.textContent||'');
    });
    return out.join('\n@@@\n');
})()"""

POSITION = r"""(function(){var e=document.querySelector('.position-name');return e?(e.textContent||'').trim():'';})()"""

IMG_N = r"""(function(){var b=document.querySelector('.chat-message');return b?b.querySelectorAll('img.message-image').length:-1;})()"""


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def main():
    kw = sys.argv[1]
    marker = sys.argv[2]
    args = sys.argv[3:]
    text_file = None
    if "--text" in args:
        i = args.index("--text")
        text_file = args[i + 1]
        args = args[:i] + args[i + 2:]
    imgs = args

    sel, idx = select_conv(kw)
    if sel == "not_found" or idx < 0:
        # 当前不在消息页（列表 DOM 不存在）→ 先跳转消息页再选
        log("!! 当前页无会话列表，跳转消息页")
        D.navigate(CHAT_URL)
        time.sleep(4)
        D.wait_chat_ready(timeout=45)
        time.sleep(2)
        sel, idx = select_conv(kw)
    time.sleep(1.0)
    log(f"会话[{idx}] {sel}")
    pos = evaluate(POSITION)
    log(f"岗位 {pos}")
    if not pos:
        log("!! 拿不到岗位名，放弃")
        return

    cur = evaluate(TEXT) or ""
    if marker in cur:
        log(f"!! 已含标记「{marker}」，跳过")
        return
    log(f"现有我方消息 {cur.count('@@@')+1 if cur else 0} 条")

    if text_file:
        text = open(text_file, encoding="utf-8").read().strip()
        log(f"（自定义文案）{text_file}")
    else:
        # 取话术：从招聘目录里按岗位文件夹取【更正补发版】
        from scripts.recruit_greetings import _clean
        fp = os.path.join(RECRUIT, "AI软件开发实习生", "新建 文本文档.txt")
        content = open(fp, encoding="utf-8").read()
        import re
        m = re.search(r"【更正补发版[^\n]*】\s*\n(.*?)(?=\n【|\Z)", content, re.S)
        if not m:
            log("!! 找不到更正补发版")
            return
        text = _clean(m.group(1))

        # 安全闸：正文里绝不能出现内部说明 / 归档备注 —— 这些是写给自己看的
        BAD = ["说明：", "说明:", "不要改", "不要再改", "归档", "内部", "本节",
               "这是发给", "投归档", "（附", "注："]
        bad = [w for w in BAD if w in text]
        if bad:
            log(f"!! 正文含内部词 {bad}，拒绝发送")
            return
        if not text.splitlines()[0].startswith(("补充一下", "您好", "抱歉")):
            log(f"!! 正文首行不是允许的开头：{text.splitlines()[0][:30]}，拒绝发送")
            return
    log(f"话术 {len(text)} 字 / {text.count(chr(10))+1} 行")
    for i, l in enumerate(text.split("\n"), 1):
        log(f"   {i}. {l}")

    f = D.fill_chat(text)
    log(f"填充 {f}")
    st = evaluate(r"""(function(){var b=document.querySelector('button.btn-send');return b?((b.className||'')): 'none';})()""")
    log(f"发送键 {st}")
    if "disabled" in str(st) or "none" in str(st):
        log("!! 发送键不可用，放弃")
        return
    s = D.click_send()
    log(f"发送 {s}")
    time.sleep(2.5)

    for rel in imgs:
        p = os.path.join(RECRUIT, rel)
        if not os.path.isfile(p):
            log(f"!! 缺文件 {p}")
            continue
        before = evaluate(IMG_N)
        try:
            before = int(before)
        except (TypeError, ValueError):
            before = -1
        up = call("upload", {"selector": IMG_SEL, "files": [p]})
        after = before
        for _ in range(10):
            time.sleep(2.0)
            try:
                after = int(evaluate(IMG_N))
            except (TypeError, ValueError):
                after = -1
            if after > before:
                break
        log(f"简历图 {os.path.basename(rel)} {before}→{after} upload={up.get('ok')}")
        time.sleep(1.5)

    call("screenshot", {"path": os.path.join(WORK, f"fix_{kw}.png"), "format": "png"})
    log("完成")


if __name__ == "__main__":
    raise SystemExit(main())
