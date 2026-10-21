# -*- coding: utf-8 -*-
"""check_fix_shots.py — 校验「上午 8 个会话」要补发的截图是否已是新版（数十款 / 数万行）。

对每张截图：
  1) 在同文件夹里找出它对应的那份 PDF（像素差最小者，和 reall_shots.py 同一套逻辑）；
  2) 扫这份 PDF 该页文本里的「N 款」「N 行」；
  3) 再做一次像素比对，确认磁盘上的 PNG 与 PDF 同步（即截图内容 = PDF 内容）。
"""
import glob
import os
import re
import sys

import fitz
from PIL import Image
import numpy as np

RECRUIT = r"YOUR_HOME\招聘"
ZOOM = 300 / 72.0

# (会话关键词, 截图相对招聘目录的路径, 说明)
TARGETS = [
    ("候选人D女士示例科技Y", r"示例科技A-后端JAVA开发实习生\shot_示例20_p1.png", "示例科技A Java后端"),
    ("候选人G先生示例文化B", r"后端开发实习生\shot_示例17_p1.png", "示例文化B（后端开发实习生）"),
    ("候选人B女士示例科技C", r"全栈开发实习生\shot_示例12_p1.png", "示例科技C（全栈）"),
    ("候选人H女士示例科技D", r"示例科技D-游戏开发实习生\shot_示例15_p1.png", "示例科技D 游戏开发"),
    ("候选人B女士示例网络E", r"后端开发实习生\shot_示例17_p1.png", "示例网络E（后端）"),
    ("候选人N先生示例数据科技", r"研发实习生\shot_示例20_p1.png", "示例数据科技（5项目版）"),
    ("候选人O广州示例软件F", r"软件实习生\shot_示例19_p1.png", "示例软件F（软件实习生）"),
    ("候选人C女士广州示例云服务G", r"示例云服务G-AI全栈开发工程师\shot_示例11_p1.png", "示例云服务G AI全栈"),
]


def render_page(pdf, pno, width=None):
    doc = fitz.open(pdf)
    if pno > doc.page_count:
        doc.close()
        return None, None
    page = doc.load_page(pno - 1)
    zoom = (width / page.rect.width) if width else ZOOM
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    txt = page.get_text()
    doc.close()
    return img, txt


def main():
    print(f"{'会话':<22} {'截图':<40} {'PDF 里的数字':<26} 判定")
    bad = []
    for kw, rel, desc in TARGETS:
        p = os.path.join(RECRUIT, rel)
        if not os.path.isfile(p):
            print(f"{desc:<22} !! 截图不存在 {rel}")
            bad.append(desc)
            continue
        folder = os.path.dirname(p)
        pdfs = sorted(glob.glob(os.path.join(folder, "*.pdf")))
        base = os.path.basename(p)
        tail = base.rsplit("_p", 1)
        pno = int(tail[1].split(".")[0]) if len(tail) == 2 else 1

        stored = Image.open(p).convert("RGB")
        a = np.asarray(stored, dtype=np.int16)
        best = None
        for pdf in pdfs:
            img, txt = render_page(pdf, pno, width=stored.size[0])
            if img is None:
                continue
            if img.size[1] != stored.size[1] or img.size[0] != stored.size[0]:
                img = img.crop((0, 0, min(img.size[0], stored.size[0]),
                                min(img.size[1], stored.size[1])))
            b = np.asarray(img, dtype=np.int16)
            if b.shape != a.shape:
                continue
            frac = float(np.mean(np.any(a != b, axis=2)))
            if best is None or frac < best[0]:
                best = (frac, pdf, txt)
        if best is None:
            print(f"{desc:<22} !! 找不到匹配 PDF")
            bad.append(desc)
            continue
        frac, pdf, txt = best
        games = sorted(set(re.findall(r"(\d+)\s*款", txt)))
        lines = sorted(set(re.findall(r"(\d{4,6})\s*行", txt)))
        nums = f"款{games} 行{lines}" if (games or lines) else "(无数字)"
        ok_num = ("50" in games) and (not lines or "EXPECT_LINES" in lines)
        ok_sync = frac <= 0.002
        verdict = "✅ 可补发" if (ok_num and ok_sync) else "❌ 需重渲染"
        if not (ok_num and ok_sync):
            bad.append(f"{desc}（数字={nums} 同步差={frac*100:.2f}%）")
        print(f"{desc:<22} {base:<40} {nums:<26} {verdict}  同步差 {frac*100:.2f}%  ← {os.path.basename(pdf)}")

    print(f"\n可补发 {len(TARGETS)-len(bad)}/{len(TARGETS)}")
    for b in bad:
        print("  !!", b)


if __name__ == "__main__":
    main()
