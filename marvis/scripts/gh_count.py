#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gh_count.py — 核对 GitHub 仓库数与 commit 总数（话术里要写真实数字）。"""
import json
import urllib.request

API = "https://api.github.com/users/3155498108/repos?per_page=100"
HDR = {"User-Agent": "resume-check", "Accept": "application/vnd.github+json"}


def get(url):
    req = urllib.request.Request(url, headers=HDR)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    repos = get(API)
    own = [r for r in repos if not r.get("fork")]
    forks = [r for r in repos if r.get("fork")]
    print(f"公开仓库 {len(repos)} 个：自有 {len(own)}，fork {len(forks)}")
    for r in sorted(repos, key=lambda x: x["pushed_at"], reverse=True):
        print(f"  {'fork' if r.get('fork') else '    '} {r['name']:<30} "
              f"{r.get('language') or '-':<12} commits? pushed {r['pushed_at'][:10]}")
    total = 0
    print("\n逐仓库 commit 数：")
    for r in own:
        c = get(f"https://api.github.com/repos/3155498108/{r['name']}/commits?per_page=100")
        n = len(c) if isinstance(c, list) else 0
        total += n
        print(f"  {r['name']:<30} {n:>3}")
    print(f"\n自有仓库 commit 合计（每仓取前 100）：{total}")
    print(f"→ 可安全写「GitHub {len(own)} 个公开仓库」")


if __name__ == "__main__":
    main()
