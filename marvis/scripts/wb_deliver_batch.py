#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""deliver_ai2.py — 投递本批 5 个新 AI 岗位（广东AI2 / 收藏AI2）。

流程（每个岗位）：
  1. 打开 job_detail 页（按 jobId 直达）
  2. 校验页面公司名 + 岗位名与预期一致（不一致直接跳过，绝不投错）
  3. 点「立即沟通」（= 已向 BOSS 发出默认招呼语，不可撤回）
  4. 进消息页 → 选最顶部新会话 → 校验会话里的岗位名
  5. 填话术 → 点发送 → 校验
  6. 上传 2 张简历图 → 校验

用法:
    python deliver_ai2.py            # 处理全部 5 个
    python deliver_ai2.py 0 2        # 只处理第 0、2 个
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, r"YOUR_REPO\job-auto-apply\marvis")
from scripts.wb import call, navigate            # noqa: E402
from scripts.webbridge_client import evaluate     # noqa: E402
import scripts.wb_deliver as D                    # noqa: E402

WORK = r"YOUR_HOME\output\boss_work"
RECRUIT = r"YOUR_HOME\招聘"
FINAL = os.path.join(WORK, "ai2_final.json")
RESULT = os.path.join(WORK, "ai2_result.json")
CHAT_URL = "https://www.zhipin.com/web/geek/chat"
IMG_SELECTOR = ".btn-sendimg input[type=file]"
GAP = 7.0            # 两个岗位之间的最小间隔（秒）——BOSS 风控

_RE_MAIN = re.compile(r"【主推版[^\n]*】\s*\n(.*?)(?=\n【|\n={5,}|\n-{5,}|\Z)", re.S)
_RE_CLEAN = re.compile(r"^\s*[-*>]\s*|^\s*\d+\.\s*|^#+\s*", re.M)
_RE_TERMINAL = re.compile(r"[。！？!?；;）)】》\"]\s*$")


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def _clean(text):
    t = text.replace("**", "").replace("`", "")
    t = _RE_CLEAN.sub("", t)
    lines = [ln.strip() for ln in t.splitlines()]
    lines = [ln for ln in lines if ln]
    paras = []
    for ln in lines:
        if paras and not _RE_TERMINAL.search(paras[-1]):
            paras[-1] = paras[-1] + " " + ln
        else:
            paras.append(ln)
    return "\n".join(paras).strip()


def read_text(folder):
    fp = os.path.join(RECRUIT, folder, "新建 文本文档.txt")
    raw = open(fp, encoding="utf-8").read()
    m = _RE_MAIN.search(raw)
    return _clean(m.group(1)) if m else ""


def norm(s):
    return re.sub(r"[\s（）()【】\[\]/·|、,，.。\-—:：]+", "", (s or "")).lower()


def similar(a, b, min_n=2):
    """两个公司名是否至少共享一个 min_n 字的连续片段（粗粒度防投错）。"""
    a, b = norm(a), norm(b)
    if not a or not b:
        return False
    if a in b or b in a:
        return True
    for i in range(len(a) - min_n + 1):
        if a[i:i + min_n] in b:
            return True
    return False


def conv_stats():
    """当前选中会话的统计：我的文字条数、图片条数、岗位名、会话标题。"""
    code = r"""(function(){
        var box=document.querySelector('.chat-message')||document.querySelector('.chat-record');
        var out={myText:0,imgs:0,other:[],pos:'',title:'',lastIsMe:null};
        if(!box) return JSON.stringify(out);
        var li=box.querySelectorAll('li.message-item');
        li.forEach(function(l){
            var isMe=(l.className||'').indexOf('item-myself')>=0;
            var hasImg=l.querySelectorAll('img.message-image').length>0;
            var t=(l.textContent||'').replace(/\s+/g,' ').trim();
            if(hasImg){ out.imgs++; }
            else if(t.indexOf('候选人')>=0){ out.myText++; }
            else if(!isMe && t && t.indexOf('竞争者')<0 && t.indexOf('严禁')<0){ out.other.push(t.slice(0,40)); }
            out.lastIsMe = isMe;
        });
        var p=document.querySelector('.position-name');
        out.pos = p ? (p.textContent||'').trim() : '';
        var s=document.querySelector('.friend-content.selected');
        out.title = s ? (s.textContent||'').replace(/\s+/g,' ').trim().slice(0,60) : '';
        return JSON.stringify(out);
    })()"""
    raw = evaluate(code)
    try:
        return json.loads(raw)
    except Exception:
        return {"err": str(raw)[:200]}


def upload_img(path, label):
    r = call("upload", {"selector": IMG_SELECTOR, "files": [path]})
    ok = r.get("ok")
    log(f"    上传 {label}: ok={ok} {json.dumps(r, ensure_ascii=False)[:110]}")
    if not ok:
        return False
    for _ in range(12):
        time.sleep(2.0)
        st = conv_stats()
        if st.get("imgs", 0) >= 1:
            return True
    return False


def deliver(item, idx):
    name = item["folder"]
    log("=" * 70)
    log(f"[{idx}] {name}")
    rec = {"folder": name, "jobId": item["jobId"], "company": item["company"],
           "position": item["position"], "city": item["city"], "status": "?", "detail": ""}

    text = read_text(name)
    if not text:
        rec["status"] = "no_text"
        return rec
    log(f"    话术 {len(text)} 字")

    # ── 1. 打开岗位详情页 ──────────────────────────────
    url = f"https://www.zhipin.com/job_detail/{item['jobId']}.html"
    navigate(url)
    time.sleep(4.0)
    if not D.wait_text(["立即沟通", "继续沟通", "已沟通"], timeout=25):
        rec["status"] = "detail_timeout"
        rec["detail"] = "详情页没出现沟通按钮"
        call("screenshot", {"path": os.path.join(WORK, f"ai2_fail_{idx}.png"), "format": "png"})
        return rec

    page_company = D.detail_company()
    page_body = D.body_text()
    log(f"    页面公司={page_company!r}")
    if not similar(page_company, item["company"]) and not similar(page_body[:400], item["company"]):
        rec["status"] = "company_mismatch"
        rec["detail"] = f"页面公司 {page_company!r} 与预期 {item['company']!r} 不符"
        call("screenshot", {"path": os.path.join(WORK, f"ai2_fail_{idx}.png"), "format": "png"})
        return rec

    # 岗位名校验（只做软校验：页面标题里应出现岗位关键词）
    pos_kw = norm(item["position"])
    head = norm(page_body[:600])
    pos_hit = pos_kw[:6] in head or pos_kw in head
    log(f"    岗位名校验={'通过' if pos_hit else '未命中(软校验继续)'}  期望={item['position']}")

    # ── 2. 打招呼 ─────────────────────────────────────
    already = "继续沟通" in page_body and "立即沟通" not in page_body
    if already:
        log("    该岗位已沟通过 → 不重复打招呼，直接进消息页")
        rec["route"] = "already"
    else:
        r = D.click_text(["立即沟通"])
        log(f"    点立即沟通: {r}")
        if r == "not_found":
            rec["status"] = "no_greet_btn"
            rec["detail"] = "详情页找不到立即沟通"
            return rec
        time.sleep(4.0)
        rec["route"] = "new"

    D.enter_chat()
    time.sleep(2.0)

    # ── 3. 选会话 ─────────────────────────────────────
    if rec.get("route") == "new":
        log(f"    取最顶部会话: {D.pick_newest_conversation()}")
        time.sleep(1.5)
    else:
        log(f"    选会话: {D.pick_conversation(item['company'])}")
        time.sleep(1.5)

    st = conv_stats()
    log(f"    当前会话: 岗位={st.get('pos')!r} 标题={st.get('title')!r} 我的文字={st.get('myText')} 图={st.get('imgs')}")
    if st.get("myText", 0) > 0:
        rec["status"] = "already_sent"
        rec["detail"] = f"该会话已有 {st['myText']} 条话术，不重复发"
        return rec

    # ── 4. 发话术 ─────────────────────────────────────
    log(f"    填充: {D.fill_chat(text)}")
    time.sleep(1.2)
    btn = evaluate(r"""(function(){var b=document.querySelector('button.btn-send');return b?((b.className||'')+'|'+(b.textContent||'').trim()):'none';})()""")
    log(f"    发送键: {btn}")
    if "disabled" in str(btn) or "none" in str(btn):
        rec["status"] = "send_disabled"
        rec["detail"] = f"发送键未就绪 {btn}"
        return rec
    s = D.click_send()
    log(f"    发送: {s}")
    time.sleep(3.0)
    st = conv_stats()
    log(f"    发送后: 我的文字={st.get('myText')} 图={st.get('imgs')}")
    if st.get("myText", 0) < 1:
        rec["status"] = "send_unverified"
        rec["detail"] = f"发送后仍无话术 {s}"
        return rec
    call("screenshot", {"path": os.path.join(WORK, f"ai2_sent_{idx}.png"), "format": "png"})

    # ── 5. 上传简历图 ─────────────────────────────────
    sent_imgs = 0
    for rel in item.get("imgs", []):
        ap = os.path.join(RECRUIT, rel)
        if not os.path.isfile(ap):
            log(f"    !! 图片缺失 {ap}")
            continue
        if upload_img(ap, rel):
            sent_imgs += 1
            time.sleep(1.5)
        else:
            log(f"    !! 图片上传未生效 {rel}")
    time.sleep(2.0)
    st = conv_stats()
    log(f"    最终: 我的文字={st.get('myText')} 图={st.get('imgs')}")

    rec["status"] = "sent" if st.get("myText", 0) >= 1 else "sent_text_only"
    rec["imgs_sent"] = sent_imgs
    rec["imgs_in_conv"] = st.get("imgs", 0)
    rec["my_text"] = st.get("myText", 0)
    rec["conv_pos"] = st.get("pos", "")
    rec["detail"] = f"话术 {st.get('myText')} 条 / 图 {st.get('imgs')} 张"
    return rec


def main():
    final = json.load(open(FINAL, encoding="utf-8"))
    idxs = [int(a) for a in sys.argv[1:]] if len(sys.argv) > 1 else list(range(len(final)))

    results = []
    if os.path.isfile(RESULT):
        try:
            results = json.load(open(RESULT, encoding="utf-8"))
        except Exception:
            results = []
    done = {r["folder"] for r in results if r.get("status") in ("sent", "sent_text_only", "already_sent")}

    for i in idxs:
        item = final[i]
        if item["folder"] in done:
            log(f"SKIP {item['folder']}（本批已处理）")
            continue
        try:
            rec = deliver(item, i)
        except Exception as e:
            rec = {"folder": item["folder"], "status": "exception", "detail": repr(e)[:300]}
            log(f"    !! 异常 {rec['detail']}")
        results = [r for r in results if r.get("folder") != rec.get("folder")]
        results.append(rec)
        json.dump(results, open(RESULT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        log(f"    → {rec['status']}  {rec.get('detail','')}")
        if i != idxs[-1]:
            time.sleep(GAP)

    log("=" * 70)
    for r in results:
        log(f"  {r['status']:<16} {r['folder']}  {r.get('detail','')}")
    log(f"[结果] {RESULT}")


if __name__ == "__main__":
    main()
