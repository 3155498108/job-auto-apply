# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.recruit_greetings import pick_by_company, load_index

idx = load_index()
print('索引岗位数:', len(idx))
for f in ('AI软件开发实习生', '人工智能开发工程师'):
    print('=' * 50)
    print('目标:', f, '| 索引里有:', f in idx)
    text, src, meta = pick_by_company(f)
    if not text:
        print('  !! 没取到话术')
        continue
    print('  source =', src, '| folder =', meta.get('folder'), '| pdf =', os.path.basename(meta.get('pdf') or ''))
    print('  字数 =', len(text), '| 行数 =', text.count('\n') + 1)
    for i, l in enumerate(text.split('\n'), 1):
        print(f'   {i}. {l}')
    print('  末尾标记:', repr(text[-20:]))
