# -*- coding: utf-8 -*-
import re, io, os
base=r"D:\shmetro-live\data\raw"
out=io.StringIO()
for f in ["szmtr_home.html","hzmtr_home.html"]:
    p=os.path.join(base,f)
    raw=open(p,"rb").read()
    for enc in ("utf-8","gbk","gb18030"):
        try: t=raw.decode(enc); used=enc; break
        except: t=raw.decode("utf-8","replace"); used="replace"
    out.write("\n========== %s  (%d bytes, %s) ==========\n"%(f,len(raw),used))
    out.write(t[:1200].replace("\n"," ")[:1200]+"\n--- links ---\n")
    links=set(re.findall(r'(?:href|src)="([^"]+)"',t))
    for l in sorted(links)[:40]: out.write("  "+l+"\n")
    out.write("--- 关键词 ---\n")
    for kw in ["首末班车","时刻表","运营时间","间隔","timetable","ajax","api","aspx","json"]:
        n=len(re.findall(kw,t,re.I))
        if n: out.write("  %s x%d\n"%(kw,n))
open(os.path.join(base,"city_html.txt"),"w",encoding="utf-8").write(out.getvalue())
print("ok")