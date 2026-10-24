# -*- coding: utf-8 -*-
import re, io, os
base=r"D:\shmetro-live\data\raw"
out=io.StringIO()
for f in ["sz_szmtr.js","sz_stationInfo.js"]:
    p=os.path.join(base,f)
    if not os.path.exists(p):
        out.write("missing "+f+"\n"); continue
    t=open(p,encoding="utf-8",errors="replace").read()
    out.write("\n===== %s (%d) =====\n"%(f,len(t)))
    out.write(t[:1500]+"\n")
    out.write("--- 结构概览 ---\n")
    for pat in [r"szmtr\.[A-Za-z]+", r"\.station\s*=", r"\.name\s*=", r"\.pointList", r"\.lineID", r"\.stationID"]:
        n=len(re.findall(pat,t)); out.write("  %s x%d\n"%(pat,n))
open(os.path.join(base,"sz_struct2.txt"),"w",encoding="utf-8").write(out.getvalue())
print("ok")