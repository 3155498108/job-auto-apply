#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb_cross.py — 跨城市批量投递（读取 crosscity_targets.json）。

链路与 wb_new.py 一致：job_detail → 校验 → 立即沟通 → 消息页（用自动选中的新会话）
      → 原生 fill 填话术（带换行）→ 点发送 → 上传简历截图 → 校验

安全阀：
  1. 详情页岗位名必须命中关键词，否则跳过；
  2. 消息页 .position-name 必须命中关键词，否则跳过（防止发错人）；
  3. 会话里已有含「候选人」的话术则跳过（幂等）；
  4. 正文含内部说明词则拒绝发送。

用法: python wb_cross.py [label ...]      不带参数 = 全部
"""
import json
import os
import sys
import time
import difflib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.webbridge_client import evaluate
from scripts.recruit_greetings import load_index
from scripts.wb import call, navigate
import scripts.wb_deliver as D

WORK = os.environ.get("BOSS_WORK_DIR", r"YOUR_HOME\output\boss_work")
RECRUIT = r"YOUR_HOME\招聘"
IMG_SEL = ".btn-sendimg input[type=file]"
# 目标清单与产物前缀：跨城 = crosscity_targets.json / cross，收藏 = fav_targets.json / fav
TARGETS_FILE = os.environ.get("BOSS_TARGETS_FILE", "crosscity_targets.json")
PREFIX = os.environ.get("BOSS_PREFIX", "cross")

DETAIL = r"""JSON.stringify((function(){
    var t=(document.body.innerText||'').replace(/\s+/g,' ');
    function q(sel){var e=document.querySelector(sel);return e?(e.textContent||'').replace(/\s+/g,' ').trim():'';}
    var name=q('.job-banner .name, h1.name, .job-name, .job-detail-banner .name, .job-title');
    var sal=q('.salary, .job-banner .salary');
    var area=q('.location, .job-location, .company-location, .job-banner .company-location');
    var comp='';
    var sels=['.company-info a','.company-card .name','.company-name','[class*="companyName"]',
              '[class*="company-name"]','.company-info .name','.job-detail-company .name'];
    for(var i=0;i<sels.length;i++){
        var e=document.querySelector(sels[i]);
        if(!e) continue;
        var s=(e.textContent||'').replace(/\s+/g,' ').trim();
        if(s && s.length<40){ comp=s; break; }
    }
    return {name:name, salary:sal, area:area, comp:comp, head:t.slice(0,200)};
})())"""

SEL_TEXT = r"""(function(){
    var s=document.querySelector('.friend-content.selected');
    if(!s) return 'none';
    var j=document.querySelector('.position-name');
    return ((s.textContent||'').replace(/\s+/g,' ').trim().slice(0,44))+' @ '+(j?(j.textContent||'').trim():'?');
})()"""

POSITION = r"""(function(){var e=document.querySelector('.position-name');return e?(e.textContent||'').trim():'';})()"""

# 登录态自检：被风控踢到登录页时立刻停下来，别继续乱点
LOGIN_CHECK = r"""(function(){
    var u=location.href||'';
    var body=(document.body.innerText||'');
    var isLogin=(u.indexOf('/web/user')>=0) || (u.indexOf('login')>=0);
    var hasUser=body.indexOf('候选人')>=0;
    return JSON.stringify({url:u, login:isLogin, user:hasUser});
})()"""

GREET_HIT = r"""(function(){
    var b=document.querySelector('.chat-message');
    if(!b) return -1;
    var n=0;
    b.querySelectorAll('li.message-item.item-myself .message-content').forEach(function(e){
        if((e.textContent||'').indexOf('候选人')>=0) n++;
    });
    return n;
})()"""

IMGS_IN_CHAT = r"""(function(){
    var b=document.querySelector('.chat-message');
    if(!b) return -1;
    return b.querySelectorAll('img.message-image').length;
})()"""

BAD = ["说明：", "说明:", "不要改", "不要再改", "归档", "内部", "本节", "这是发给", "注："]


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def norm(s):
    return "".join((s or "").split())


def applied_job_ids():
    """已投 jobId 集合：manifest + 各批 result.json。

    只靠 DOM 判断幂等会误判：**同一个 HR 的多个岗位共用一个会话**，
    对该 HR 的第 2 个岗位发话术时，会话里已经有第 1 个岗位的「候选人」话术，
    于是被当成「已发」跳过——整批会静默漏投。
    第三个实测：示例文旅W三个 AI 全栈岗都是同一个人（候选人A女士），
    三个里有几个就是这样被跳过的。

    所以 DOM 命中只作为「这个岗位确实投过」的旁证，
    真正的判定依据是 jobId 是否在已投清单里。
    """
    ids = set()
    try:
        with open(r"YOUR_HOME\招聘\boss_manifest.json", encoding="utf-8") as f:
            m = json.load(f)
        for j in m.get("boss_jobs", []):
            if j.get("jobId"):
                ids.add(j["jobId"])
    except Exception as e:
        print(f"  (manifest 读取失败：{e})")
    try:
        for fn in os.listdir(WORK):
            if not fn.endswith("_result.json"):
                continue
            try:
                with open(os.path.join(WORK, fn), encoding="utf-8") as f:
                    rows = json.load(f)
            except Exception:
                continue
            for r in rows if isinstance(rows, list) else []:
                if isinstance(r, dict) and r.get("jobId"):
                    ids.add(r["jobId"])
    except Exception as e:
        print(f"  (result.json 扫描失败：{e})")
    return ids


def name_sim(a, b):
    """岗位名相似度：详情页名 vs 列表页名。

    不能直接判「包含」——列表页标题常带薪资尾巴（「java实习生200元/天」），
    详情页又没有（「java实习生」）。用相似度比包含更稳。
    """
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return 0.0
    if na in nb or nb in na:
        return 1.0
    return difflib.SequenceMatcher(None, na.lower(), nb.lower()).ratio()


def wait_send_enabled(timeout=12):
    """等发送按钮从 disabled 变成可用。

    fill 之后 Vue 需要一拍才把 class 里的 disabled 摘掉；立刻判断会误判成不可用。
    返回可用的 class 字符串；超时返回 None。
    """
    t0 = time.time()
    last = ""
    while time.time() - t0 < timeout:
        st = evaluate(r"""(function(){var b=document.querySelector('button.btn-send');
            return b?((b.className||'')+'|'+(b.textContent||'').trim()):'none';})()""")
        last = str(st)
        if "none" not in last and "disabled" not in last:
            return last
        time.sleep(0.8)
    log(f"    (发送键等待超时，最后状态 {last[:50]})")
    return None


def main():
    only = set(sys.argv[1:])
    targets = json.load(open(os.path.join(WORK, TARGETS_FILE), encoding="utf-8"))
    index = load_index()
    results = []
    navigated = 0
    applied = applied_job_ids()
    out = os.path.join(WORK, f"{PREFIX}_result.json")
    log(f"已投 jobId {len(applied)} 个（用于精确幂等）")
    for t in targets:
        if only and t["label"] not in only:
            continue
        log(f"===== {t['label']}  {t['city']} · {t['company']}")
        folder = t["folder"]
        item = index.get(folder)
        if not item or not item["main"]:
            log(f"    !! 没有话术：{folder}")
            results.append(dict(label=t["label"], status="no_greeting"))
            continue
        text = item["main"]
        bad = [w for w in BAD if w in text]
        if bad:
            log(f"    !! 正文含内部词 {bad}，拒绝发送")
            results.append(dict(label=t["label"], status="internal_text"))
            continue

        # 1) 详情页
        navigate(f"https://www.zhipin.com/job_detail/{t['jobId']}.html")
        time.sleep(5.0)
        # 登录态自检：被踢到登录页就停下，避免连续触发风控
        lk = evaluate(LOGIN_CHECK)
        try:
            lk = json.loads(lk) if isinstance(lk, str) else (lk or {})
        except Exception:
            lk = {}
        if lk.get("login") or not lk.get("user"):
            log(f"    !! 登录态失效（{lk.get('url','')}），本轮暂停")
            results.append(dict(label=t["label"], status="login_lost"))
            break
        d = evaluate(DETAIL)
        try:
            d = json.loads(d) if isinstance(d, str) else d
        except Exception:
            d = {}
        log(f"    岗位 {d.get('name')} | {d.get('salary')} | {d.get('area')} | 公司 {d.get('comp')}")
        # 安全阀 2：详情页岗位名必须与目标岗位对得上。
        # Vue Router 缓存劫持时，URL 是 C 的 jobId、页面还渲染 B 的内容，
        # 这时点「立即沟通」就等于给 B 投了话术。
        sim = name_sim(d.get("name", ""), t.get("position", ""))
        if sim < 0.4:
            log(f"    !! 详情页岗位名不匹配（页面={d.get('name','')!r} 目标={t.get('position','')!r} "
                f"sim={sim:.2f}），重置搜索页后重试一次")
            navigate("https://www.zhipin.com/web/geek/job")
            time.sleep(3.0)
            navigate(f"https://www.zhipin.com/job_detail/{t['jobId']}.html")
            time.sleep(6.0)
            d2 = evaluate(DETAIL)
            try:
                d2 = json.loads(d2) if isinstance(d2, str) else d2
            except Exception:
                d2 = {}
            sim2 = name_sim(d2.get("name", ""), t.get("position", ""))
            if sim2 < 0.4:
                log(f"    !! 重试后仍不匹配（sim={sim2:.2f}），跳过")
                results.append(dict(label=t["label"], status="detail_mismatch",
                                    page_name=d2.get("name", ""), sim=round(sim2, 3)))
                continue
            d = d2
            log(f"    重试成功 岗位 {d.get('name')} sim={sim2:.2f}")
        if not D.wait_text(["立即沟通", "继续沟通"], timeout=20):
            # 详情页偶发白屏/卡住 → reload 一次再等
            log("    (详情页未就绪，reload 重试)")
            evaluate("location.reload()")
            time.sleep(5)
            if not D.wait_text(["立即沟通", "继续沟通"], timeout=20):
                log("    !! 详情页未就绪")
                results.append(dict(label=t["label"], status="detail_timeout"))
                continue

        # 2) 立即沟通
        r = D.click_text(["立即沟通"])
        if r == "not_found":
            r = D.click_text(["继续沟通"])
            log(f"    已沟通过（{r}）")
        else:
            log(f"    点立即沟通 {r}")
        time.sleep(3.5)

        # 3) 消息页
        D.enter_chat()
        # 消息页也可能被踢 → 再查一次
        lk2 = evaluate(LOGIN_CHECK)
        try:
            lk2 = json.loads(lk2) if isinstance(lk2, str) else (lk2 or {})
        except Exception:
            lk2 = {}
        if lk2.get("login"):
            log(f"    !! 消息页跳到登录页（{lk2.get('url','')}），本轮暂停")
            results.append(dict(label=t["label"], status="login_lost"))
            break
        sel = evaluate(SEL_TEXT)
        pos = evaluate(POSITION)
        log(f"    当前会话 {sel}")
        log(f"    头部岗位 {pos}")
        if "none" in str(sel):
            log("    !! 没选中会话，跳过")
            results.append(dict(label=t["label"], status="no_conversation"))
            continue
        # 安全阀：头部岗位名必须命中公司或岗位关键词
        hay = norm(pos) + norm(sel)
        kw = [t["company"], t["position"]]
        if not any(norm(k) and norm(k) in hay for k in kw):
            log(f"    !! 岗位名不匹配（期望含 {kw}），跳过")
            results.append(dict(label=t["label"], status="position_mismatch", pos=pos))
            continue

        # 4) 幂等
        hit = evaluate(GREET_HIT)
        try:
            hit = int(hit)
        except (TypeError, ValueError):
            hit = -1
        log(f"    已发话术计数 {hit}")
        if hit > 0:
            # 会话里已有候选人的话术 —— 要分清是「这个岗位投过」还是「同一 HR 的别的岗位投过」
            if t["jobId"] in applied:
                log(f"    !! 该岗位已投过（jobId 命中已投清单），跳过")
                results.append(dict(label=t["label"], status="already_sent", jobId=t["jobId"]))
                continue
            log("    (会话里有本 HR 其它岗位的话术，本岗位未投过 → 继续)")

        # 5) 填 + 发
        f = D.fill_chat(text)
        log(f"    填充 {f} | 话术 {len(text)} 字 {text.count(chr(10))+1} 行")
        st = wait_send_enabled(timeout=12)
        if st is None:
            log(f"    !! 发送键一直不可用，跳过")
            results.append(dict(label=t["label"], status="send_disabled"))
            continue
        log(f"    发送键 {st}")
        s = D.click_send()
        log(f"    发送 {s}")
        sent_ok = "input_len=0" in str(s)

        # 6) 简历图
        for rel in t["imgs"]:
            p = os.path.join(RECRUIT, rel)
            if not os.path.isfile(p):
                log(f"    !! 截图不存在 {p}")
                continue
            before = evaluate(IMGS_IN_CHAT)
            try:
                before = int(before)
            except (TypeError, ValueError):
                before = -1
            up = call("upload", {"selector": IMG_SEL, "files": [p]})
            after = before
            for _ in range(10):
                time.sleep(2.0)
                try:
                    after = int(evaluate(IMGS_IN_CHAT))
                except (TypeError, ValueError):
                    after = -1
                if after > before:
                    break
            log(f"    简历图 {os.path.basename(rel)} {before}→{after} upload={up.get('ok')}")
            time.sleep(1.5)

        call("screenshot", {"path": os.path.join(WORK, f"{PREFIX}_{t['label']}.png"), "format": "png"})
        results.append(dict(label=t["label"], city=t["city"], company=t["company"],
                            status="sent" if sent_ok else "send_unverified",
                            greeting_len=len(text), lines=text.count("\n") + 1,
                            jobId=t["jobId"]))
        applied.add(t["jobId"])
        log(f"    → {'成功' if sent_ok else '待核实'}")
        # 实时落盘：中断最多丢当前一条
        with open(out, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=1)
        time.sleep(6)

    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    log("=== 完成 ===")
    for r in results:
        log(f"    {r['status']:<18} {r.get('city','')} {r['label']}")


if __name__ == "__main__":
    raise SystemExit(main())
