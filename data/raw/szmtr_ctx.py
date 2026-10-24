# -*- coding: utf-8 -*-
import re, io, os
base=r"D:\shmetro-live\data\raw"
t=open(os.path.join(base,"szmtr_home.html"),encoding="utf-8",errors="replace").read()
out=io.StringIO()
out.write("=== 苏州: 首末班车/时刻表 上下文 ===\n")
for kw in ["首末班车","时刻表","timetable"]:
    for m in re.finditer(kw,t):
        s=max(0,m.start()-400); e=min(len(t),m.end()+200)
        out.write("--- @%d\n%s\n"%(m.start(), re.sub(r"\s+"," ",t[s:e])))
open(os.path.join(base,"szmtr_ctx.txt"),"w",encoding="utf-8").write(out.getvalue())
print("ok")