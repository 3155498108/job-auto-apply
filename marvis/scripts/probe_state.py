# -*- coding: utf-8 -*-
import sys, os, json, time
sys.path.insert(0, r'YOUR_REPO\marvis')
from scripts.webbridge_client import evaluate

print('URL:', evaluate('location.href'))
print('TITLE:', evaluate('document.title'))
body = evaluate(r"""(document.body.innerText||'').replace(/\s+/g,' ').slice(0,300)""")
print('BODY:', body)
print('登录态:', evaluate(r"""(function(){
   var e=document.querySelector('.user-info, .avatar, .boss-info, [class*="user-name"], [class*="userInfo"]');
   return e ? (e.textContent||'').replace(/\s+/g,' ').trim().slice(0,40) : 'no-user-el';
})()"""))
print('有登录弹窗:', '登录' in (evaluate(r"""(document.body.innerText||'')""") or ''))
