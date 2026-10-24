# -*- coding: utf-8 -*-
import re, io, os
base=r"D:\shmetro-live\data\raw"
h=open(os.path.join(base,"hz_bundle.js"),encoding="utf-8",errors="replace").read()
i=h.find('const ut={')
seg=h[i:i+40000]
end=seg.find('};')
seg=seg[:end if end>0 else 40000]
out=io.StringIO()
out.write("ut 长度 %d\n"%len(seg))
pairs=re.findall(r'([A-Za-z_][A-Za-z0-9_]*)\s*:\s*("(?:[^"]*)"|[^,{}]{0,120})', seg)
out.write("字段数 %d\n"%len(pairs))
for k,v in pairs:
    v=v.strip().strip('"')
    if any(s in v.lower() for s in ("time","schedul","station","line","timetable","first","operation")):
        out.write("  %-36s %s\n"%(k,v))
out.write("\n--- 全部字段名 ---\n")
out.write(", ".join(k for k,_ in pairs))
open(os.path.join(base,"hz_endpoints2.txt"),"w",encoding="utf-8").write(out.getvalue())
print("ok")