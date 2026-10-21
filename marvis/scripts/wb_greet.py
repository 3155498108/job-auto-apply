#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_greet.py — 探查并设置 BOSS 的「默认打招呼语」。

BOSS 的「立即沟通」是点击即发送默认招呼语，没有输入弹窗；
要自定义文案必须先在【消息通知-设置打招呼语】里改全局默认值。

用法：
    python wb_greet.py probe          # 只看当前设置与表单结构
    python wb_greet.py set <文本>     # 填入并保存（文本从文件读，避免命令行中文与引号问题）
"""
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate
from scripts.wb import navigate, call

URL = "https://www.zhipin.com/web/geek/notify-set"


def probe():
    navigate(URL, wait=4)
    st = evaluate(r"""JSON.stringify({
        title: document.title,
        url: location.href,
        head: document.body.innerText.replace(/\s+/g,' ').slice(0,600),
        fields: (function(){
            var out=[];
            document.querySelectorAll('textarea, input[type=text], .textarea, [contenteditable=true]').forEach(function(e){
                var r=e.getBoundingClientRect();
                if(r.width<=0||r.height<=0) return;
                out.push({tag:e.tagName, cls:(e.className||'').toString().slice(0,36),
                          maxlength:e.getAttribute('maxlength')||'', value:(e.value||e.textContent||'').slice(0,120),
                          ph:e.getAttribute('placeholder')||''});
            });
            return out;
        })(),
        buttons: (function(){
            var out=[];
            document.querySelectorAll('button, .btn, a.btn').forEach(function(e){
                var r=e.getBoundingClientRect();
                if(r.width<=0||r.height<=0) return;
                var t=(e.textContent||'').trim();
                if(t && t.length<12) out.push({text:t, cls:(e.className||'').toString().slice(0,34)});
            });
            return out.slice(0,25);
        })()
    })""")
    print(json.dumps(json.loads(st) if st else {}, ensure_ascii=False, indent=2))
    return json.loads(st) if st else {}


def set_text(text):
    navigate(URL, wait=4)
    r = evaluate(r"""(function(){
        var G = __TEXT__;
        var cands = document.querySelectorAll('textarea, [contenteditable="true"]');
        for (var i=0;i<cands.length;i++){
            var el=cands[i];
            var rc=el.getBoundingClientRect();
            if(rc.width<=0||rc.height<=0) continue;
            if(el.isContentEditable){
                el.textContent=G;
                el.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:G}));
            } else {
                var proto = HTMLTextAreaElement.prototype;
                var setter=Object.getOwnPropertyDescriptor(proto,'value').set;
                setter.call(el,G);
                el.dispatchEvent(new Event('input',{bubbles:true}));
                el.dispatchEvent(new Event('change',{bubbles:true}));
            }
            return 'filled:'+el.tagName+':'+((el.value||el.textContent||'').length);
        }
        return 'no_textarea';
    })()""".replace("__TEXT__", json.dumps(text, ensure_ascii=False)))
    print(f"[填入] {r}")
    time.sleep(1)
    # 找保存按钮
    save = evaluate(r"""(function(){
        var bs=document.querySelectorAll('button,.btn,span.btn,a');
        for(var i=0;i<bs.length;i++){
            var t=(bs[i].textContent||'').trim();
            if(t==='保存'||t==='确定'||t==='确认'||t==='保存设置'||t==='提交'){
                return 'found:'+t;
            }
        }
        return 'not_found';
    })()""")
    print(f"[保存按钮] {save}")
    return r, save


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "probe"
    if mode == "probe":
        probe()
    elif mode == "set":
        path = sys.argv[2]
        text = io.open(path, encoding="utf-8").read().strip()
        print(f"待设置话术 {len(text)} 字:")
        print(text[:200])
        set_text(text)
    else:
        print("用法: python wb_greet.py probe|set <文件>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
