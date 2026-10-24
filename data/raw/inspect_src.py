# -*- coding: utf-8 -*-
import re, io, os
base=r"D:\shmetro-live\data\raw"
out=io.StringIO()

t=open(os.path.join(base,"sz_time.html"),encoding="utf-8",errors="replace").read()
out.write("=== 苏州 sz_time.html (%d) ===\n"%len(t))
# 表格/脚本
tabs=re.findall(r"<table.*?</table>", t, re.S|re.I)
out.write("tables=%d\n"%len(tabs))
for i,tb in enumerate(tabs[:2]):
    txt=re.sub(r"<[^>]+>"," ",tb); txt=" ".join(txt.split())
    out.write("  T%d: %s\n"%(i,txt[:600]))
for m in re.finditer(r'(?:url|src|href)\s*[=:]\s*["\']([^"\']+\.(?:json|aspx|ashx|js)[^"\']*)', t):
    out.write("  URL "+m.group(1)+"\n")
out.write("\n--- 关键词 ---\n")
for kw in ["首班","末班","间隔","ajax","fetch(","getJSON"]:
    out.write("  %s x%d\n"%(kw,len(re.findall(kw,t))))

h=open(os.path.join(base,"hz_bundle.js"),encoding="utf-8",errors="replace").read()
out.write("\n=== 杭州 bundle (%d) ===\n"%len(h))
urls=set()
for m in re.finditer(r'["\'](https?://[^"\']{6,120})["\']', h): urls.add(m.group(1))
for m in re.finditer(r'["\'](/[a-zA-Z0-9_\-/]{3,60}(?:api|Api|API)[a-zA-Z0-9_\-/]*)["\']', h): urls.add(m.group(1))
for u in sorted(urls)[:40]: out.write("  "+u+"\n")
out.write("--- baseURL / api 关键词 ---\n")
for m in list(re.finditer(r'baseURL\s*[:=]\s*["\']([^"\']+)["\']', h))[:10]:
    out.write("  baseURL="+m.group(1)+"\n")
for m in list(re.finditer(r'["\'](/[a-z0-9_\-/]*(?:timetable|schedule|first|last|time|station|line)[a-z0-9_\-/]*)["\']', h, re.I))[:25]:
    out.write("  path "+m.group(1)+"\n")
open(os.path.join(base,"city_src.txt"),"w",encoding="utf-8").write(out.getvalue())
print("ok")