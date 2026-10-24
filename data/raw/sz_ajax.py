# -*- coding: utf-8 -*-
import re, io, os
base=r"D:\shmetro-live\data\raw"
t=open(os.path.join(base,"sz_time.html"),encoding="utf-8",errors="replace").read()
out=io.StringIO()
for m in re.finditer(r'\$\.ajax|\.ajax\(|getJSON|\.load\(|fetch\(', t):
    s=max(0,m.start()-200); e=min(len(t),m.end()+700)
    out.write("--- @%d\n%s\n\n"%(m.start(), re.sub(r"\s+"," ",t[s:e])))
open(os.path.join(base,"sz_ajax.txt"),"w",encoding="utf-8").write(out.getvalue())
print("ok")