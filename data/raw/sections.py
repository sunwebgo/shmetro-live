# -*- coding: utf-8 -*-
import re, io
base = r"D:\Idea_project\SpringAI-2.0\shmetro-live\data\raw"
raw=open(base+r"\hcskb_0.html",encoding="utf-8",errors="replace").read()
hits=[(m.start(), m.group(1)) for m in re.finditer(r"images/([0-9A-Za-z_]+)bg\.jpg", raw)]
tabs=[m.start() for m in re.finditer(r"<table", raw)]
out=io.StringIO()
out.write("bg hits=%d\n"%len(hits))
merged=sorted([(p,"LINE:"+n) for p,n in hits]+[(p,"TABLE@%d"%(i+1)) for i,p in enumerate(tabs)])
for p,label in merged:
    if label.startswith("LINE:") or True:
        out.write("%8d  %s\n"%(p,label))
open(base+r"\sections.txt","w",encoding="utf-8").write(out.getvalue())
print("ok")