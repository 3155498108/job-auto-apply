#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""recruit_greetings.py — 复用「招聘」目录下已精修的专属话术。

背景：
    YOUR_HOME\招聘\\<岗位名>\\新建 文本文档.txt 里存着每个岗位
    定制的话术（主推版 / 精简版），比通用模板精准得多。
    自动化投递时按公司名 / 岗位名匹配对应文件夹，取出主推版；
    找不到对应岗位时回退到 greetings.json 的通用变体。

导出：
    load_index()    -> {folder_name: {...}}  全量索引
    pick(job_info)  -> (text, source, meta)  取话术
"""

import json
import os
import re

# 「招聘」目录：可用环境变量 BOSS_RECRUIT_DIR 覆盖
DEFAULT_RECRUIT_DIR = r"YOUR_HOME\招聘"

# 话术文件候选名
_FILE_CANDIDATES = ["新建 文本文档.txt", "新建 文本文档-v12.txt", "话术.txt"]

# 【主推版 ...】/【精简版 ...】段落
_RE_MAIN = re.compile(r"【主推版[^\n]*】\s*\n(.*?)(?=\n【|\n={5,}|\n-{5,}|\Z)", re.S)
_RE_SHORT = re.compile(r"【精简版[^\n]*】\s*\n(.*?)(?=\n【|\n={5,}|\n-{5,}|\Z)", re.S)

# 去掉 markdown 粗体标记、引用符号、列表符号
_RE_CLEAN = re.compile(r"^\s*[-*>]\s*|^\s*\d+\.\s*|^#+\s*", re.M)


_RE_TERMINAL = re.compile(r"[。！？!?；;）)】》\"]\s*$")


def _clean(text):
    """把话术整理成**带换行**的多行文本。

    BOSS 聊天输入框是 contenteditable（提示语「按 Ctrl+Enter 键换行」），
    支持真正的换行，不需要压成一行。

    源文件里「主推版/精简版」每段本来就是一整行，但不同文件段落之间
    有的用空行分隔、有的用单换行分隔，规则统一为：
      · 每行独立成段（一段一行），行与行之间用 \\n；
      · 若上一行结尾不是句末标点，说明它被软换行截断了，与下一行合并。
    """
    if not text:
        return ""
    # 先去掉成对粗体标记，再清行首符号；
    # 顺序不能反：行首的 '**' 会被行首符号分支吃掉一个 '*'，留下残缺的 '*'
    t = text.replace("**", "").replace("`", "")
    t = _RE_CLEAN.sub("", t)
    lines = [ln.strip() for ln in t.splitlines()]
    lines = [ln for ln in lines if ln]
    paras = []
    for ln in lines:
        if paras and not _RE_TERMINAL.search(paras[-1]):
            paras[-1] = paras[-1] + " " + ln      # 软换行 → 并回上一段
        else:
            paras.append(ln)
    return "\n".join(paras).strip()


def _company_aliases(text):
    """从话术文件首行提取公司名候选。

    首行格式统一为「公司名（括注）· 岗位名」，括注里还可能有别名
    （如「示例大厂J（飞书）」「示例科技A（DBS 银行）」）。
    公司名是强标识，岗位通用词（"开发工程师"）容易误配，所以分开处理。
    """
    if not text:
        return []
    first = text.splitlines()[0] if text.splitlines() else ""
    m = re.match(r"^\s*([^（(·]+)", first)
    aliases = []
    base = m.group(1).strip() if m else ""
    if len(base) >= 2:
        aliases.append(base)
    head = first.split("·")[0] if "·" in first else first
    for mm in re.finditer(r"[（(]([^)）]+)[)）]", head):
        a = mm.group(1).strip()
        if len(a) >= 2:
            aliases.append(a)
    return aliases


def _extract(text):
    """从话术文件中抽出 (主推版, 精简版)。"""
    main = _RE_MAIN.search(text)
    short = _RE_SHORT.search(text)
    return (
        _clean(main.group(1)) if main else "",
        _clean(short.group(1)) if short else "",
    )


def _pdf_path(folder):
    try:
        for fn in os.listdir(folder):
            if fn.lower().endswith(".pdf"):
                return os.path.join(folder, fn)
    except OSError:
        pass
    return ""


def _role_parts(folder_name):
    """文件夹名里公司名之后的部分 = 岗位描述词，匹配权重低。"""
    parts = [p.strip() for p in re.split(r"[-—\s·|]+", folder_name) if p.strip()]
    return parts[1:] if len(parts) > 1 else []


def load_index(recruit_dir=None):
    """扫描「招聘」目录，建立 {文件夹名: {...}} 索引。"""
    root = recruit_dir or os.environ.get("BOSS_RECRUIT_DIR") or DEFAULT_RECRUIT_DIR
    index = {}
    if not os.path.isdir(root):
        return index

    for folder in sorted(os.listdir(root)):
        fdir = os.path.join(root, folder)
        if not os.path.isdir(fdir):
            continue
        content = ""
        for fn in _FILE_CANDIDATES:
            fp = os.path.join(fdir, fn)
            if os.path.isfile(fp):
                try:
                    with open(fp, "r", encoding="utf-8") as f:
                        content = f.read()
                    break
                except OSError:
                    pass
        if not content:
            continue
        main, short = _extract(content)
        if not main and not short:
            continue
        index[folder] = {
            "company": _company_aliases(content),     # 强标识
            "roles": _role_parts(folder),             # 弱标识
            "main": main,
            "short": short,
            "pdf": _pdf_path(fdir),
            "path": fdir,
        }
    return index


def _score(item, haystack):
    """公司名命中权重远高于岗位通用词，避免「开发工程师」这类词乱配。"""
    score = 0
    for alias in item.get("company", []):
        if alias in haystack:
            score += 10 * len(alias)
    for role in item.get("roles", []):
        if len(role) >= 4 and role in haystack:
            score += len(role)
    return score


def pick(job_info, index=None, limit=None):
    """按岗位信息挑一份最贴合的专属话术。

    返回 (text, source, meta)
        source: 'recruit'（来自招聘目录）/ 'generic'（通用变体）/ 'none'
        meta:   {'variant':..., 'folder':..., 'pdf':..., 'short':...}
    """
    job_info = job_info or {}
    index = index if index is not None else load_index()

    haystack = " ".join([
        str(job_info.get("company", "")),
        str(job_info.get("title", "")),
        str(job_info.get("jd_text", "") or job_info.get("description", "")),
    ])

    best = None
    best_score = 0
    for folder, item in index.items():
        score = _score(item, haystack)
        if score > best_score:
            best, best_score = (folder, item), score

    if best:
        folder, item = best
        text = item["main"] or item["short"]
        short = item["short"] or item["main"]
        if limit and len(text) > limit:
            text = short if len(short) <= limit else short[:limit]
        return text, "recruit", {
            "variant": "recruit",
            "folder": folder,
            "pdf": item["pdf"],
            "short": short,
        }

    # 回退到通用变体
    from scripts.deliver_engine import load_greeting, pick_greeting_text
    gtext, variant = load_greeting(job_info)
    gshort = pick_greeting_text(variant, limit=0)
    if limit and len(gtext) > limit:
        gtext = gshort if len(gshort) <= limit else gshort[:limit]
    return gtext, "generic", {"variant": variant, "folder": "", "pdf": "", "short": gshort}


def pick_by_company(company_kw, index=None):
    """只按公司名定位话术（补发/消息页场景，没有岗位标题可用）。

    匹配顺序：文件夹名前缀 > 公司别名（互相前缀匹配）。
    返回 (text, source, meta)；找不到返回 (None, 'none', {})。
    """
    if not company_kw:
        return None, "none", {}
    index = index if index is not None else load_index()

    # 1) 文件夹名前缀，如「示例科技A-后端JAVA开发实习生」命中「示例科技Y」
    for folder, item in index.items():
        if folder.startswith(company_kw):
            return _result(folder, item), "recruit", _meta(folder, item)

    # 2) 公司别名互相前缀匹配
    for folder, item in index.items():
        for alias in item.get("company", []):
            if alias.startswith(company_kw) or company_kw.startswith(alias):
                return _result(folder, item), "recruit", _meta(folder, item)

    return None, "none", {}


def _result(folder, item):
    return item["main"] or item["short"]


def _meta(folder, item):
    return {
        "variant": "recruit",
        "folder": folder,
        "pdf": item["pdf"],
        "short": item["short"] or item["main"],
    }


if __name__ == "__main__":
    idx = load_index()
    print(f"招聘目录索引: {len(idx)} 个岗位有可用话术\n")
    for name, item in idx.items():
        print(f"  {name}")
        print(f"      主推 {len(item['main']):>3} 字 | 精简 {len(item['short']):>3} 字 | PDF: "
              f"{os.path.basename(item['pdf']) if item['pdf'] else '(无)'}")
