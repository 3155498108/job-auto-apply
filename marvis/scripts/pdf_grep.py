# -*- coding: utf-8 -*-
"""pdf_grep.py — 在 PDF 里搜关键词（核对已渲染简历的数字）。"""
import re
import sys

import fitz

PAT = re.compile(r"\d+\s*款")


def main():
    for p in sys.argv[1:]:
        try:
            doc = fitz.open(p)
        except Exception as e:
            print(f"{p}\n  !! 打不开 {e}")
            continue
        print(f"{p}  ({doc.page_count} 页)")
        for i, page in enumerate(doc, 1):
            t = page.get_text()
            for m in PAT.finditer(t):
                s = max(0, m.start() - 45)
                print(f"   p{i}: ...{t[s:m.end()+25].replace(chr(10),' ')}...")
        doc.close()


if __name__ == "__main__":
    main()
