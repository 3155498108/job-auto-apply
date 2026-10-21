# -*- coding: utf-8 -*-
"""reall_shots.py — 重新渲染 招聘\\ 下所有 shot_*.png，使其与当前 PDF 同步。

一个文件夹里可能有多份 PDF，shot 图片要自己对上号：
  对每张 shot，遍历文件夹内所有 PDF 的对应页，按像素差找出「它原本来自哪份 PDF」，
  再用这份 PDF 按 300dpi 重新渲染覆盖。
"""
import os
import glob

import fitz
from PIL import Image
import numpy as np

RECRUIT = r"YOUR_HOME\招聘"
ZOOM = 300 / 72.0


def render_page(pdf, pno, width=None):
    doc = fitz.open(pdf)
    if pno > doc.page_count:
        doc.close()
        return None
    page = doc.load_page(pno - 1)
    zoom = (width / page.rect.width) if width else ZOOM
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    doc.close()
    return img


def main():
    for folder in sorted(os.listdir(RECRUIT)):
        d = os.path.join(RECRUIT, folder)
        if not os.path.isdir(d):
            continue
        pdfs = sorted(glob.glob(os.path.join(d, "*.pdf")))
        shots = sorted(glob.glob(os.path.join(d, "shot_*.png")))
        if not pdfs or not shots:
            continue
        for sh in shots:
            base = os.path.basename(sh)
            tail = base.rsplit("_p", 1)
            if len(tail) != 2 or not tail[1].split(".")[0].isdigit():
                print(f"  ?? 跳过 {folder}/{base}（文件名没有页码）")
                continue
            pno = int(tail[1].split(".")[0])
            stored = Image.open(sh).convert("RGB")
            a = np.asarray(stored, dtype=np.int16)
            best = None
            for pdf in pdfs:
                img = render_page(pdf, pno, width=stored.size[0])
                if img is None:
                    continue
                # 新旧 PDF 页高可能差 1~3px，比对时按存量图裁齐
                if img.size[1] != stored.size[1] or img.size[0] != stored.size[0]:
                    img = img.crop((0, 0, min(img.size[0], stored.size[0]),
                                    min(img.size[1], stored.size[1])))
                b = np.asarray(img, dtype=np.int16)
                if b.shape != a.shape:
                    continue
                frac = float(np.mean(np.any(a != b, axis=2)))
                if best is None or frac < best[1]:
                    best = (pdf, frac, img)
            if best is None:
                print(f"  !! {folder}/{base} 找不到可用 PDF")
                continue
            pdf, frac, _ = best
            # 用匹配上的 PDF 重新渲染（300dpi 标准规格）
            fresh = render_page(pdf, pno)
            if fresh is None:
                print(f"  !! {folder}/{base} 重新渲染失败")
                continue
            fresh.save(sh)
            print(f"  {folder}/{base:<34} ← {os.path.basename(pdf):<44} "
                  f"旧图与该PDF差异 {frac*100:5.2f}%  新图 {fresh.size[0]}x{fresh.size[1]}")


if __name__ == "__main__":
    main()
