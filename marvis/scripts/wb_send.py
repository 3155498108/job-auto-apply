#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_send.py — 完整投递链路：定位岗位 → 点「立即沟通」→ 进聊天页 → 发定制话术。

实测要点：
  1. BOSS 的「立即沟通」是点击即发送默认招呼语，没有输入弹窗；
     要发定制话术必须点弹窗里的「继续沟通」进聊天页再发。
  2. 详情面板是异步渲染的，点卡片后必须等「立即沟通」出现才能继续。
  3. jobId 每次搜索都会变，必须每次重新提取。
  4. 按钮按「文本」匹配比按 class 匹配稳（class 随版本变化）。

用法：
    python wb_send.py <搜索词> <岗位关键词> <公司关键词> [stage|send]
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import extract_jobs, evaluate
from scripts.jd_reader import click_card_inplace
from scripts.deliver_engine import pick_greeting_for_job
from scripts.wb import navigate, search_url, call

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")


def _j(raw, default=None):
    try:
        return json.loads(raw) if raw else (default if default is not None else {})
    except Exception:
        return default if default is not None else {}


def wait_text(needles, timeout=25):
    """等待页面出现指定文本。"""
    t0 = time.time()
    while time.time() - t0 < timeout:
        txt = evaluate(r"""(document.body.innerText||'').replace(/\s+/g,' ')""") or ""
        if any(n in txt for n in needles):
            return True
        time.sleep(1.2)
    return False


def wait_inputs(timeout=25, min_n=1):
    t0 = time.time()
    while time.time() - t0 < timeout:
        n = evaluate(r"""document.querySelectorAll('textarea,[contenteditable="true"]').length""")
        try:
            if int(n or 0) >= min_n:
                return True
        except (TypeError, ValueError):
            pass
        time.sleep(1.2)
    return False


def click_by_text(texts, exact=True):
    """按可见文本点击元素（比 class 选择器稳）。"""
    code = r"""(function(){
        var WANT = __WANT__;
        var EXACT = __EXACT__;
        var all = document.querySelectorAll('a,button,div,span,i,em');
        var hits = [];
        for (var i=0;i<all.length;i++){
            var e = all[i];
            var t = (e.textContent||'').replace(/\s+/g,'').trim();
            if(!t || t.length>16) continue;
            var ok = EXACT ? (WANT.indexOf(t)>=0) : (t.indexOf(WANT)>=0);
            if(!ok) continue;
            var r = e.getBoundingClientRect();
            if(r.width<=0||r.height<=0) continue;
            if(e.children.length>3) continue;
            hits.push(e);
        }
        if(!hits.length) return 'not_found';
        // 取文本最短的（最内层）
        hits.sort(function(a,b){ return (a.textContent||'').length - (b.textContent||'').length; });
        var e = hits[0];
        e.scrollIntoView({block:'center'});
        e.click();
        return 'clicked:'+e.tagName+':'+(e.className||'').toString().slice(0,40)+':'+(e.textContent||'').replace(/\s+/g,'').trim().slice(0,20);
    })()""".replace("__WANT__", json.dumps(texts, ensure_ascii=False)).replace("__EXACT__", "true")
    return evaluate(code)


def find_job(query, role_kw, company_kw, city="广州"):
    navigate(search_url(query, "101280100"))
    time.sleep(3)
    jobs = extract_jobs()
    for j in jobs:
        if city and j.get("city") != city:
            continue
        if role_kw and role_kw not in j["title"]:
            continue
        if company_kw and company_kw not in j["company"]:
            continue
        return j, jobs
    return None, jobs


def main():
    query, role_kw, company_kw = sys.argv[1], sys.argv[2], sys.argv[3]
    mode = sys.argv[4] if len(sys.argv) > 4 else "stage"

    job, jobs = find_job(query, role_kw, company_kw)
    if not job:
        print("!! 未找到岗位")
        for j in jobs:
            print(f"   {j['title'][:30]:<32} {j['salary'][:12]:<14} {j['company'][:16]}")
        return 2

    print(f"[命中] {job['title']} | {job['salary']} | {job['company']} | {job['city']} | {job['degree']}")

    text, meta = pick_greeting_for_job(job)
    print(f"[话术] {meta.get('source')} / {meta.get('folder') or '(通用)'} / {len(text)} 字")
    print(f"       {text[:110]}...")

    cr = click_card_inplace(job["jobId"], verify=True, max_wait=8)
    print(f"[点卡片] ok={cr.get('ok')}")

    # 等详情面板渲染出「立即沟通」
    got = wait_text(["立即沟通", "继续沟通"], timeout=20)
    print(f"[详情面板就绪] {got}")

    r = click_by_text(["立即沟通", "继续沟通"])
    print(f"[点沟通] {r}")
    time.sleep(3.5)

    # 弹窗：点「继续沟通」进聊天页
    has_popup = wait_text(["已向BOSS发送消息", "继续沟通", "留在此页"], timeout=8)
    print(f"[发送弹窗] {has_popup}")
    if has_popup:
        r2 = click_by_text(["继续沟通"])
        print(f"[进聊天页] {r2}")
        time.sleep(3)

    ok = wait_inputs(timeout=25)
    print(f"[聊天输入框就绪] {ok}")

    probe = evaluate(r"""JSON.stringify((function(){
        function vis(e){var r=e.getBoundingClientRect();return r.width>0&&r.height>0;}
        var ins=[];
        document.querySelectorAll('textarea,[contenteditable="true"]').forEach(function(e){
            if(!vis(e)) return;
            if((e.className||'').toString().indexOf('search')>=0) return;
            ins.push({tag:e.tagName, cls:(e.className||'').toString().slice(0,46),
                      ml:e.getAttribute('maxlength')||'', ph:e.getAttribute('placeholder')||''});
        });
        var btns=[];
        document.querySelectorAll('button,.btn,span,div,i,a').forEach(function(e){
            if(!vis(e)) return;
            var t=(e.textContent||'').replace(/\s+/g,'').trim();
            var c=(e.className||'').toString();
            if(t==='发送'||c.indexOf('send')>=0) btns.push({t:t, cls:c.slice(0,46)});
        });
        return {ins:ins, btns:btns.slice(0,10),
                head:(document.body.innerText||'').replace(/\s+/g,' ').slice(0,240)};
    })())""")
    print(f"[输入框] {probe}")

    fill = evaluate(r"""(function(){
        var G = __TEXT__;
        var cands = document.querySelectorAll('textarea,[contenteditable="true"]');
        for(var i=0;i<cands.length;i++){
            var el=cands[i];
            var r=el.getBoundingClientRect();
            if(r.width<=0||r.height<=0) continue;
            if((el.className||'').toString().indexOf('search')>=0) continue;
            if(el.isContentEditable){
                el.textContent=G;
                el.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:G}));
            } else {
                var setter=Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set;
                setter.call(el,G);
                el.dispatchEvent(new Event('input',{bubbles:true}));
                el.dispatchEvent(new Event('change',{bubbles:true}));
            }
            return 'filled:'+el.tagName+':'+((el.value||el.textContent||'').length);
        }
        return 'no_input';
    })()""".replace("__TEXT__", json.dumps(text, ensure_ascii=False)))
    print(f"[填充] {fill}")
    time.sleep(1)

    call("screenshot", {"path": os.path.join(WORK, "send_shot.png"), "format": "png"})
    print(f"[截图] {os.path.join(WORK,'send_shot.png')}")

    if mode == "send":
        s = click_by_text(["发送"])
        print(f"[发送] {s}")
        time.sleep(2)
        call("screenshot", {"path": os.path.join(WORK, "sent_shot.png"), "format": "png"})
    else:
        print("\n>>> 已停在发送前。确认后回复「发送」。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
