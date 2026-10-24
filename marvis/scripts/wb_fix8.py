#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_fix8.py — 给「上午 8 个会话」补发「38 款 → 数十款」更正话术 + 重发新版简历截图。

会话列表是**虚拟滚动**（DOM 只渲染可视区附近约 40 条），
所以要先分段滚动把整个列表的条目文本收集起来，记下每条的 scrollTop，
再按「文本 + scrollTop」回到该位置点击。

子命令：
  scan  <关键词...>   只扫描：列出候选会话、岗位名、是否含「38 款」、图数
  send  <关键词...>   补发（幂等：会话里已含标记词就跳过）
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate
from scripts.wb import call, navigate
import scripts.wb_deliver as D

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")
RECRUIT = r"YOUR_HOME\招聘"
CHAT = "https://www.zhipin.com/web/geek/chat"
IMG_SEL = ".btn-sendimg input[type=file]"

# 更正文案：首行必须以「补充一下」开头（wb_fix.py 的安全闸要求）
TEXT = (
    "补充一下更正一个数字：我前面发的项目经历里写的是 38 款网页小游戏，"
    "后来又持续加了一批，实际到现在是 数十款了。\n"
    "简历也重新发您一份，以新图为准。"
)
MARK = "补充一下更正一个数字"

BAD = ["说明：", "说明:", "不要改", "不要再改", "归档", "内部", "本节", "这是发给", "注：", "（附"]

# 关键词 → 配置
#   shots: 要补发的简历截图（相对 招聘 目录）
#   must: 会话标题里必须包含的片段（用来区分同公司的不同 HR）
#   role: 头部岗位名里必须包含的片段（防发错岗位）
SHOTS = {
    "示例科技Y": dict(shots=[r"示例科技A-后端JAVA开发实习生\shot_示例20_p1.png"],
                 must="候选人F女士示例科技Y", role="JAVA开发工程师"),
    "示例文化B": dict(shots=[r"后端开发实习生\shot_示例17_p1.png"],
                     must="候选人G先生示例文化B", role="AI应用与Agent"),
    "示例企业74": dict(shots=[r"全栈开发实习生\shot_示例12_p1.png"],
                 must="候选人D女士示例科技C", role="见习全栈"),
    "示例科技D": dict(shots=[r"示例科技D-游戏开发实习生\shot_示例15_p1.png"],
                   must="候选人H女士示例科技D", role="游戏开发"),
    "示例企业68": dict(shots=[r"后端开发实习生\shot_示例17_p1.png"],
                   must="候选人D女士示例网络E", role="后端开发"),
    "示例数据科技": dict(shots=[r"研发实习生\shot_示例20_p1.png"],
                       must="候选人N先生示例数据科技", role="应届生/实习生"),
    "示例软件F": dict(shots=[r"软件实习生\shot_示例19_p1.png"],
                     must="候选人O广州示例软件F", role="软件开发"),
    "示例云服务G": dict(shots=[r"示例云服务G-AI全栈开发工程师\shot_示例11_p1.png"],
                   must="候选人E女士广州示例云服务G", role="AI"),
}

SNAP = r"""JSON.stringify((function(){
    var l=document.querySelector('.user-list-content');
    var items=[];
    document.querySelectorAll('.friend-content').forEach(function(e){
        var r=e.getBoundingClientRect();
        items.push({t:(e.textContent||'').replace(/\s+/g,' ').trim().slice(0,110),
                    top:Math.round(r.top)});
    });
    return {st:l?Math.round(l.scrollTop):-1, sh:l?l.scrollHeight:-1, ch:l?l.clientHeight:-1, items:items};
})())"""

STATS = r"""(function(){
    var b=document.querySelector('.chat-message');
    if(!b) return {err:'no_box'};
    var li=b.querySelectorAll('li.message-item');
    var imgs=0, myText=0, brs=0, others=[], c38=0, c50=0, marked=0;
    li.forEach(function(l){
        var isMe=l.className.indexOf('item-myself')>=0;
        var n=l.querySelectorAll('img.message-image').length;
        if(n){ imgs+=n; return; }
        var c=l.querySelector('.message-content');
        var h=c?(c.innerHTML||''):'';
        var t=(c?(c.innerText||c.textContent||''):(l.textContent||''))||'';
        if(isMe){
            myText++;
            brs+=(h.match(/<br\s*\/?>/gi)||[]).length;
            if(t.indexOf('38')>=0 && t.indexOf('款')>=0) c38++;
            if(t.indexOf('50')>=0 && t.indexOf('款')>=0) c50++;
            if(t.indexOf('补充一下更正一个数字')>=0) marked++;
        } else {
            var s=t.replace(/\s+/g,' ').trim();
            if(s && s.indexOf('竞争者')<0) others.push(s.slice(0,50));
        }
    });
    var pos=document.querySelector('.position-name');
    var sel=document.querySelector('.friend-content.selected');
    return {myText:myText, images:imgs, brs:brs, c38:c38, c50:c50, marked:marked,
            pos:pos?(pos.textContent||'').replace(/\s+/g,' ').trim():'',
            conv:sel?(sel.textContent||'').replace(/\s+/g,' ').trim().slice(0,70):'',
            others:others.slice(0,2)};
})()"""


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def set_scroll(top):
    evaluate(r"""(function(){
        var l=document.querySelector('.user-list-content');
        if(!l) return 'no';
        l.scrollTop=%d;
        l.dispatchEvent(new Event('scroll',{bubbles:true}));
        return l.scrollTop;
    })()""" % int(top))
    time.sleep(1.3)


def collect(max_rounds=40):
    """分段滚动收集全部会话条目（文本 → scrollTop 位置）。"""
    navigate(CHAT)
    time.sleep(6)
    seen = {}          # 文本 → scrollTop
    order = []         # [(scrollTop, text)]
    st = 0
    sh = 0
    for _ in range(max_rounds):
        raw = evaluate(SNAP)
        try:
            v = json.loads(raw) if raw else {}
        except Exception:
            break
        items = v.get("items", [])
        for it in items:
            t = it["t"]
            if t and t not in seen:
                seen[t] = v.get("st", 0)
                order.append((v.get("st", 0), t))
        sh = v.get("sh", 0)
        nxt = v.get("st", 0) + max(v.get("ch", 600) - 120, 200)
        if nxt >= sh - 100:
            break
        set_scroll(nxt)
    set_scroll(0)
    log(f"收集到 {len(order)} 条会话（列表总高 {sh}px）")
    return order, seen


def click_by_text(text, scroll_top):
    """滚到记录位置，按文本点击会话。

    虚拟列表的渲染窗口会随滚动重建，精确 scrollTop 可能对不齐，
    所以失败时以 ±60px 为步长在附近微调。
    """
    for delta in (0, -60, 60, -120, 120, -180, 180, -240, 240, -300, 300):
        set_scroll(max(0, scroll_top + delta))
        raw = evaluate(r"""JSON.stringify(Array.prototype.map.call(
            document.querySelectorAll('.friend-content'), function(e,i){
                return {i:i, t:(e.textContent||'').replace(/\s+/g,' ').trim().slice(0,110)};
            }))""")
        try:
            items = json.loads(raw) if raw else []
        except Exception:
            items = []
        target = next((x for x in items if x["t"] == text), None)
        if not target:
            target = next((x for x in items if text[:40] and text[:40] in x["t"]), None)
        if not target:
            continue
        evaluate(r"""(function(){
            var list=document.querySelectorAll('.friend-content');
            var e=list[%d]; if(!e) return 'gone';
            e.scrollIntoView({block:'center'}); e.click(); return 'clicked';
        })()""" % target["i"])
        time.sleep(2.2)
        # 确认选中
        sel = evaluate(r"""(function(){
            var s=document.querySelector('.friend-content.selected');
            return s?(s.textContent||'').replace(/\s+/g,' ').trim().slice(0,110):'none';
        })()""")
        if str(sel)[:40] and str(sel)[:40] in text:
            return True
    return False


def cmd_scan(kws):
    order, seen = collect()
    with open(os.path.join(WORK, "all_convs_scan.json"), "w", encoding="utf-8") as f:
        json.dump([{"st": s, "t": t} for s, t in order], f, ensure_ascii=False, indent=1)
    for kw in kws:
        hits = [(s, t) for s, t in order if kw in t]
        log(f"=== {kw}：命中 {len(hits)} 条")
        for s, t in hits:
            if not click_by_text(t, s):
                log(f"    !! 点击失败 {t[:50]}")
                continue
            v = evaluate(STATS)
            if isinstance(v, str):
                try:
                    v = json.loads(v)
                except Exception:
                    v = {"err": v}
            log(f"    岗位={str(v.get('pos'))[:28]:<30} 话术{v.get('myText')} br={v.get('brs')} "
                f"图{v.get('images')} 含38款={v.get('c38')} 含50款={v.get('c50')} "
                f"已更正={v.get('marked')} | {t[:44]}")


def find_and_click(needle):
    """分段滚动整个列表，找包含 needle 的会话并点击。

    虚拟列表在新增会话后会整体位移，记录的 scrollTop 会失效，
    所以这里不依赖记录位置，直接边滚边找。
    """
    navigate(CHAT)
    time.sleep(6)
    step = 420
    top = 0
    for _ in range(30):
        set_scroll(top)
        raw = evaluate(r"""JSON.stringify(Array.prototype.map.call(
            document.querySelectorAll('.friend-content'), function(e,i){
                return {i:i, t:(e.textContent||'').replace(/\s+/g,' ').trim().slice(0,120)};
            }))""")
        try:
            items = json.loads(raw) if raw else []
        except Exception:
            items = []
        hit = next((x for x in items if needle in x["t"]), None)
        if hit:
            evaluate(r"""(function(){
                var list=document.querySelectorAll('.friend-content');
                var e=list[%d]; if(!e) return 'gone';
                e.scrollIntoView({block:'center'}); e.click(); return 'clicked';
            })()""" % hit["i"])
            time.sleep(2.2)
            sel = evaluate(r"""(function(){
                var s=document.querySelector('.friend-content.selected');
                return s?(s.textContent||'').replace(/\s+/g,' ').trim().slice(0,120):'none';
            })()""")
            if needle in str(sel):
                return True, str(sel)
        sh = evaluate(r"""(function(){var l=document.querySelector('.user-list-content');
            return l?l.scrollHeight:0;})()""")
        try:
            sh = int(sh)
        except (TypeError, ValueError):
            sh = 0
        top += step
        if top > sh:
            break
    set_scroll(0)
    return False, ""


def cmd_verify(kws):
    for kw in kws:
        cfg = SHOTS.get(kw) or {}
        needle = cfg.get("must") or kw
        ok, sel = find_and_click(needle)
        if not ok:
            log(f"{kw}: !! 没找到会话")
            continue
        v = evaluate(STATS)
        if isinstance(v, str):
            try:
                v = json.loads(v)
            except Exception:
                v = {"err": v}
        log(f"{kw:<10} 岗位={str(v.get('pos'))[:26]:<28} 话术{v.get('myText')} br={v.get('brs')} "
            f"图{v.get('images')} 含38款={v.get('c38')} 含50款={v.get('c50')} "
            f"已更正={v.get('marked')} | {sel[:50]}")


def cmd_send(kws):
    order, seen = collect()
    for kw in kws:
        cfg = SHOTS.get(kw)
        if not cfg:
            log(f"!! {kw} 没有配置要补发的截图")
            continue
        shots = cfg["shots"]
        must = cfg.get("must", "")
        role = cfg.get("role", "")
        hits = [(s, t) for s, t in order if kw in t and (not must or must in t)]
        log(f"=== {kw}：命中 {len(hits)} 条（must={must!r}）")
        for s, t in hits:
            if not click_by_text(t, s):
                log(f"    !! 点击失败 {t[:50]}")
                continue
            v = evaluate(STATS)
            if isinstance(v, str):
                try:
                    v = json.loads(v)
                except Exception:
                    v = {"err": v}
            log(f"    岗位={str(v.get('pos'))[:26]:<28} 图{v.get('images')} 含38款={v.get('c38')} "
                f"已更正={v.get('marked')} | {t[:40]}")
            # 安全阀：头部岗位名必须匹配
            if role and role not in str(v.get("pos", "")):
                log(f"    !! 岗位名不含「{role}」，不是目标岗位，跳过")
                continue
            if (v.get("marked") or 0) > 0:
                log("    ⏭ 已有更正消息，跳过")
                continue
            if (v.get("c38") or 0) == 0:
                log("    ⏭ 话术里没有「38 款」，不需要更正")
                continue
            bad = [w for w in BAD if w in TEXT]
            if bad:
                log(f"    !! 文案含内部词 {bad}，拒绝发送")
                continue
            if not TEXT.splitlines()[0].startswith(("补充一下", "您好", "抱歉")):
                log("    !! 首行不合规，拒绝发送")
                continue
            f = D.fill_chat(TEXT)
            log(f"    填充 {f}")
            st = evaluate(r"""(function(){var b=document.querySelector('button.btn-send');
                return b?((b.className||'')+'|'+(b.textContent||'').trim()):'none';})()""")
            log(f"    发送键 {st}")
            if "disabled" in str(st) or "none" in str(st):
                log("    !! 发送键不可用，放弃")
                continue
            s2 = D.click_send()
            log(f"    发送 {s2}")
            time.sleep(2.5)
            for rel in shots:
                p = os.path.join(RECRUIT, rel)
                if not os.path.isfile(p):
                    log(f"    !! 缺文件 {p}")
                    continue
                before = evaluate(r"""(function(){var b=document.querySelector('.chat-message');
                    return b?b.querySelectorAll('img.message-image').length:-1;})()""")
                try:
                    before = int(before)
                except (TypeError, ValueError):
                    before = -1
                up = call("upload", {"selector": IMG_SEL, "files": [p]})
                after = before
                for _ in range(10):
                    time.sleep(2.0)
                    try:
                        after = int(evaluate(r"""(function(){var b=document.querySelector('.chat-message');
                            return b?b.querySelectorAll('img.message-image').length:-1;})()"""))
                    except (TypeError, ValueError):
                        after = -1
                    if after > before:
                        break
                log(f"    简历图 {os.path.basename(rel)} {before}→{after} upload={up.get('ok')}")
                time.sleep(1.5)
            call("screenshot", {"path": os.path.join(WORK, f"fix8_{kw}.png"), "format": "png"})


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    kws = sys.argv[2:]
    if cmd == "scan":
        cmd_scan(kws)
    elif cmd == "send":
        cmd_send(kws)
    elif cmd == "verify":
        cmd_verify(kws)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
