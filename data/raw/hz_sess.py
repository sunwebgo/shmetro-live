# -*- coding: utf-8 -*-
import re, io, os
base=r"D:\shmetro-live\data\raw"
h=open(os.path.join(base,"hz_bundle.js"),encoding="utf-8",errors="replace").read()
out=io.StringIO()
for m in list(re.finditer("subwayLineStation", h))[:6]:
    s=max(0,m.start()-700); e=min(len(h),m.end()+300)
    out.write("--- @%d\n%s\n\n"%(m.start(), h[s:e].replace("\n"," ")))
open(os.path.join(base,"hz_sess.txt"),"w",encoding="utf-8").write(out.getvalue())
print("ok")