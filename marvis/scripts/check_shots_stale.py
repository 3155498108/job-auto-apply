# -*- coding: utf-8 -*-
"""check_shots_stale.py — 检查 招聘\\ 下每张简历截图是否与当前 PDF 同步（像素比对）。

做法：把同名 PDF 的对应页按截图同样规格重新渲染，与磁盘上的 PNG 逐像素比对。
差异大 = 截图是旧版（PDF 改过但没重渲染）。
"""
import glob
import os

import fitz

try:
    from PIL import Image
    import numpy as np
    HAVE = True
except Exception as e:
    print("需要 Pillow + numpy：", e)
    HAVE = False

RECRUIT = r"YOUR_HOME\招聘"
ZOOM = 300 / 72.0


def main():
    if not HAVE:
        return
    rows = []
    for folder in sorted(os.listdir(RECRUIT)):
        d = os.path.join(RECRUIT, folder)
        if not os.path.isdir(d):
            continue
        pdfs = [f for f in os.listdir(d) if f.lower().endswith(".pdf")]
        shots = [f for f in os.listdir(d) if f.lower().endswith(".png") and f.startswith("shot_")]
        if not pdfs or not shots:
            continue
        pdf = os.path.join(d, pdfs[0])
        try:
            doc = fitz.open(pdf)
        except Exception:
            continue
        for sh in sorted(shots):
            # shot_xxx_p1.png → 页码 1
            tail = sh.rsplit("_p", 1)
            if len(tail) != 2 or not tail[1].split(".")[0].isdigit():
                continue
            pno = int(tail[1].split(".")[0])
            if pno > doc.page_count:
                continue
            page = doc.load_page(pno - 1)
            stored_path = os.path.join(d, sh)
            stored = Image.open(stored_path).convert("RGB")
            # 按截图自身宽度渲染，抹掉 1px 的缩放差异
            zoom = stored.size[0] / page.rect.width
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            fresh = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            if stored.size != fresh.size:
                rows.append((folder, sh, f"尺寸不同 {stored.size} vs {fresh.size}", "STALE"))
                continue
            a = np.asarray(stored, dtype=np.int16)
            b = np.asarray(fresh, dtype=np.int16)
            diff = float(np.mean(np.abs(a - b)))
            frac = float(np.mean(np.any(a != b, axis=2)))
            rows.append((folder, sh, f"平均像素差 {diff:.2f} / 变化像素 {frac*100:.2f}%",
                         "STALE" if frac > 0.002 else "same"))
        doc.close()

    print(f"{'文件夹':<32} {'截图':<34} {'比对':<38} 判定")
    for f, s, info, flag in rows:
        mark = "⚠️  过期" if flag == "STALE" else "✅  同步"
        print(f"{f:<32} {s:<34} {info:<38} {mark}")
    bad = [r for r in rows if r[3] == "STALE"]
    print(f"\n共 {len(rows)} 张截图，过期 {len(bad)} 张")


if __name__ == "__main__":
    main()
