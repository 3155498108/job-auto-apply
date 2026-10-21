# -*- coding: utf-8 -*-
import re, sys, os, glob

JOBS = [
    r'YOUR_HOME\招聘\AI软件开发实习生\新建 文本文档.txt',
    r'YOUR_HOME\招聘\人工智能开发工程师\新建 文本文档.txt',
]

def clean(text):
    """模拟 recruit_greetings._clean 的核心：去掉 markdown 标记、压缩空白"""
    t = text
    t = re.sub(r'\*\*(.*?)\*\*', r'\1', t, flags=re.S)
    t = re.sub(r'^\s*[-*+]\s+', '', t, flags=re.M)
    t = re.sub(r'^\s*#+\s*', '', t, flags=re.M)
    return t

def count_len(t):
    return len(re.sub(r'\s+', '', t))

for p in JOBS:
    if not os.path.exists(p):
        print('MISSING', p); continue
    raw = open(p, encoding='utf-8').read()
    print('=' * 60)
    print(os.path.basename(os.path.dirname(p)))
    blocks = re.split(r'^【(.+?)】\s*$', raw, flags=re.M)
    # blocks: [pre, name1, body1, name2, body2, ...]
    for i in range(1, len(blocks), 2):
        name = blocks[i]
        body = blocks[i + 1]
        # 只取正文到下一个标签前
        body = body.split('\n\n【')[0]
        if '主推' in name or '精简' in name:
            c = clean(body)
            n = count_len(c)
            lines = [l for l in c.strip().split('\n') if l.strip()]
            print(f'  [{name}] 字数={n}  行数={len(lines)}')
            for l in lines:
                print('     |', l)
        else:
            print(f'  [{name}] (文档说明, 跳过)')
