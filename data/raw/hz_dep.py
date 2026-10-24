# -*- coding: utf-8 -*-
import re, io, os
base=r"D:\shmetro-live\data\raw"
out=io.StringIO()
for f in ["hz_subway-DmnKy35h.js","hz_index-N8aFRZSi.js","hz_index-BUSnveWw.js"]:
    p=os.path.join(base,f)
    if not os.path.exists(p): continue
    c=open(p,encoding="utf-8",errors="replace").read()
    out.write("\n===== %s  (%d) =====\n"%(f,len(c)))
    for m in list(re.finditer(r'["\'`](/[a-zA-Z0-9_\-/]{3,80}(?:time|Time|line|Line|station|Station|timetable|schedule)[a-zA-Z0-9_\-/]*)["\'`]', c))[:20]:
        out.write("  path "+m.group(1)+"\n")
    for m in list(re.finditer(r'(?:HOST_[A-Z_]+|co\s*\+\s*"[^"]+")', c))[:20]:
        out.write("  ep "+m.group(0)[:100]+"\n")
    for m in list(re.finditer(r'https?://[^"\'`]{6,90}', c))[:15]:
        out.write("  url "+m.group(0)+"\n")
open(os.path.join(base,"hz_dep.txt"),"w",encoding="utf-8").write(out.getvalue())
print("ok")