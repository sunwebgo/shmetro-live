# -*- coding: utf-8 -*-
import re, io, os
base=r"D:\shmetro-live\data\raw"
h=open(os.path.join(base,"hz_bundle.js"),encoding="utf-8",errors="replace").read()
out=io.StringIO()
for name in ["Gye"]:
    for m in list(re.finditer(r'(?:const|let|var|function)\s+'+name+r'\b', h))[:3]:
        s=m.start(); e=min(len(h), s+700)
        out.write("--- def %s @%d\n%s\n\n"%(name,s,h[s:e].replace("\n"," ")))
open(os.path.join(base,"hz_gye.txt"),"w",encoding="utf-8").write(out.getvalue())
print("ok")