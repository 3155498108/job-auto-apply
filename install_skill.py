#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""install_skill.py — 一键安装 / 校验 GitHub 上的 job-auto-apply skill。

这个仓库里的 `skill/job-auto-apply/` 就是 skill 本体。它是 agent 的 skill，
装到 `<HOME>/.<agent>/skills/job-auto-apply/` 才会被加载。

用法:
    python install_skill.py                 # 从 GitHub 装到检测到的 agent
    python install_skill.py --list          # 只看检测到什么、装了什么
    python install_skill.py --check         # 只校验已装版本是否与 GitHub 一致
    python install_skill.py --target claude # 指定 agent（minimax / claude / codex）
    python install_skill.py --target all    # 装到所有检测到的 agent
    python install_skill.py --from <目录>   # 从本地 clone 装（离线/内网用）

只依赖标准库，不需要 pip install。
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import urllib.error
import urllib.request

REPO = "3155498108/job-auto-apply"
BRANCH = "main"
REMOTE_BASE = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/skill/job-auto-apply"
API_BASE = f"https://api.github.com/repos/{REPO}/contents/skill/job-auto-apply"

# skill 的文件清单（远端为准；本地 clone 模式会忽略这份）
FILES = [
    "SKILL.md",
    "references/greeting-engine.md",
    "references/onboarding.md",
    "references/platform-adapters.md",
    "references/safety-checklist.md",
    "references/second-touch.md",
    "references/upstream-pitfalls.md",
]

# agent → skills 目录名
AGENTS = {
    "minimax": ".minimax",
    "claude": ".claude",
    "codex": ".codex",
    "cursor": ".cursor",
    "opencode": ".opencode",
}


# ── 工具 ────────────────────────────────────────────────────────────────
def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(p):
    with open(p, "rb") as f:
        return sha_bytes(f.read())


def norm_text(s):
    """归一化换行符。

    Git 用 .gitattributes 的 `text=auto eol=lf` 存 LF，检出时（Windows 的
    core.autocrlf）转成 CRLF；而 raw.githubusercontent 返回的是 LF。
    直接比 sha 会永远报「不一致」，所以比对前统一成 LF。
    """
    return (s or "").replace("\r\n", "\n").replace("\r", "\n")


def text_sha(s):
    return sha_bytes(norm_text(s).encode("utf-8"))


def http_get(url, timeout=30):
    req = urllib.request.Request(url, headers={
        "User-Agent": "job-auto-apply-installer",
        "Accept": "application/vnd.github+json",
    })
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _walk_api(api_url, rel_prefix, got):
    """递归拉 Contents API。item['url'] 已经带了 ?ref，不要再拼。"""
    data = json.loads(http_get(api_url).decode("utf-8"))
    for item in data:
        if item.get("type") == "file":
            got[rel_prefix + item["name"]] = http_get(item["download_url"]).decode("utf-8")
        elif item.get("type") == "dir":
            _walk_api(item["url"], rel_prefix + item["name"] + "/", got)


def fetch_remote_files():
    """从 GitHub 拉 skill 的全部文件。优先用 Contents API 拿真实清单，失败则回退到内置清单。"""
    got = {}
    api_err = ""
    try:
        _walk_api(f"{API_BASE}?ref={BRANCH}", "", got)
        if got:
            return got, "Contents API"
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, json.JSONDecodeError) as e:
        api_err = repr(e)[:120]
    # 回退：逐个拉内置清单
    got = {}
    for rel in FILES:
        got[rel] = http_get(f"{REMOTE_BASE}/{rel}").decode("utf-8")
    return got, f"内置清单（API 不可用：{api_err}）"


def read_local(root):
    """从本地目录读 skill 文件。自动识别是仓库根目录还是 skill 目录本身。"""
    cand = os.path.join(root, "skill", "job-auto-apply")
    if os.path.isdir(cand):
        root = cand
    got = {}
    for rel in FILES:
        p = os.path.join(root, rel.replace("/", os.sep))
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                got[rel] = f.read()
    return got


def parse_frontmatter(text):
    """解析 SKILL.md 的 YAML frontmatter（只取顶层 key: value，够用即可）。"""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    fm = {}
    key = None
    for line in text[3:end].splitlines():
        if not line.strip():
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            key = m.group(1)
            fm[key] = m.group(2).strip()
        elif key and line.startswith((" ", "\t")):
            fm[key] = (fm[key] + " " + line.strip()).strip()
    return fm


def detect_agents():
    home = os.path.expanduser("~")
    found = []
    for name, folder in AGENTS.items():
        d = os.path.join(home, folder, "skills")
        if os.path.isdir(d):
            found.append((name, d))
    return found


def skill_dir(agent, base=None):
    home = os.path.expanduser("~")
    folder = AGENTS.get(agent, f".{agent}")
    root = base or os.path.join(home, folder, "skills")
    return os.path.join(root, "job-auto-apply")


def install(files, target_dir, dry=False):
    """把 files 写入 target_dir，返回安装结果列表。"""
    rows = []
    for rel, content in sorted(files.items()):
        dst = os.path.join(target_dir, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        new = content.encode("utf-8")
        old = sha_file(dst) if os.path.isfile(dst) else None
        if old == sha_bytes(new):
            rows.append((rel, "已是最新", len(new)))
            continue
        if not dry:
            with open(dst, "wb") as f:
                f.write(new)
        rows.append((rel, "已写入" if not dry else "（dry-run）", len(new)))
    return rows


def check_installed(target_dir, files):
    """比对已装文件与远端。**换行符归一化后再比**，否则 CRLF/LF 会永远报「不一致」。"""
    rows, missing, diff = [], [], []
    for rel, content in sorted(files.items()):
        p = os.path.join(target_dir, rel.replace("/", os.sep))
        if not os.path.isfile(p):
            missing.append(rel)
            continue
        with open(p, encoding="utf-8") as f:
            same = text_sha(f.read()) == text_sha(content)
        rows.append((rel, "一致" if same else "不一致", os.path.getsize(p)))
        if not same:
            diff.append(rel)
    return rows, missing, diff


# ── 主流程 ──────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="安装/校验 job-auto-apply skill")
    ap.add_argument("--target", default="auto",
                    help="minimax / claude / codex / all / auto（默认 auto）")
    ap.add_argument("--from", dest="from_dir", default="",
                    help="从本地目录安装（离线用）")
    ap.add_argument("--check", action="store_true", help="只校验，不写入")
    ap.add_argument("--list", action="store_true", help="只列出检测结果")
    ap.add_argument("--dry-run", action="store_true", help="不实际写盘")
    args = ap.parse_args()

    detected = detect_agents()
    print("=" * 66)
    print("job-auto-apply skill 安装器")
    print("=" * 66)
    print(f"检测到的 agent skills 目录：")
    for name, d in detected:
        inst = os.path.join(d, "job-auto-apply")
        mark = "已装" if os.path.isdir(inst) else "未装"
        print(f"  · {name:<10} {d}   [{mark}]")
    if not detected:
        print("  （没检测到任何 agent 的 skills 目录）")
    print()

    if args.list:
        return 0

    # 取源文件
    if args.from_dir:
        files = read_local(args.from_dir)
        origin = f"本地目录 {args.from_dir}"
        if not files:
            print(f"!! 在 {args.from_dir} 下没找到 skill 文件"
                  f"（期望 {FILES[0]} 或 skill/job-auto-apply/{FILES[0]}）")
            return 2
    else:
        try:
            files, origin = fetch_remote_files()
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            print(f"!! 拉取失败：{e}")
            print("   可改用 --from <本地 clone 目录> 离线安装")
            return 2
    print(f"来源：{origin}（{len(files)} 个文件）")
    print()

    # 校验 frontmatter
    sk = files.get("SKILL.md", "")
    fm = parse_frontmatter(sk)
    if not fm.get("name") or not fm.get("description"):
        print("!! SKILL.md 的 frontmatter 缺 name 或 description，安装中止")
        return 2
    if fm["name"] != "job-auto-apply":
        print(f"!! frontmatter 的 name 是 {fm['name']!r}，与目录名不一致，安装中止")
        return 2
    print(f"✓ frontmatter 校验通过：name={fm['name']}")
    desc = fm.get("description", "")
    print(f"  description {len(desc)} 字符")
    print()

    # 决定目标
    if args.target == "auto":
        targets = [n for n, _ in detected] or ["minimax"]
    elif args.target == "all":
        targets = [n for n, _ in detected] or ["minimax"]
    else:
        targets = [args.target]
    if args.check and args.target == "auto":
        # 校验模式下只查「已经装了」的 agent，没装的不算失败
        installed = [n for n in targets if os.path.isdir(skill_dir(n))]
        skipped = [n for n in targets if n not in installed]
        if skipped:
            print(f"（跳过未安装的 agent：{', '.join(skipped)}）\n")
        targets = installed
        if not targets:
            print("没有检测到已安装 job-auto-apply skill 的 agent。")
            return 1
    print(f"目标 agent：{', '.join(targets)}")
    print()

    rc = 0
    for agent in targets:
        tdir = skill_dir(agent)
        print("-" * 66)
        print(f"[{agent}] → {tdir}")
        if args.check:
            rows, missing, diff = check_installed(tdir, files)
            for rel, st, size in rows:
                print(f"  {st:<8} {rel}  ({size} bytes)")
            if missing:
                print(f"  缺失 {len(missing)} 个：{', '.join(missing)}")
            if diff:
                print(f"  有差异 {len(diff)} 个：{', '.join(diff)}")
                rc = 1
            if not rows:
                print("  未安装")
                rc = 1
        else:
            for rel, st, size in install(files, tdir, dry=args.dry_run):
                print(f"  {st:<10} {rel}  ({size} bytes)")
        print()

    if not args.check:
        print("=" * 66)
        print("完成。重新打开 agent 会话让 skill 生效。")
        print("然后让 agent 跑一次环境自检：")
        print(f"  & \"$env:USERPROFILE\\.kimi-webbridge\\bin\\kimi-webbridge.exe\" status")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
