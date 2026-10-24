# -*- coding: utf-8 -*-
import re, io, os
base=r"D:\shmetro-live\data\raw"
h=open(os.path.join(base,"hz_bundle.js"),encoding="utf-8",errors="replace").read()
i=h.find('const ut={')
out=io.StringIO()
out.write("ut @%d\n"%i)
seg=h[i:i+6000]
# 提取 KEY:co+"..." 形式
for m in re.finditer(r'([A-Z_0-9]+)\s*:\s*(co|PF)\s*\+\s*"([^"]+)"', seg):
    out.write("  %-34s %s%s\n"%(m.group(1), "API" if m.group(2)=="co" else "FILE", m.group(3)))
open(os.path.join(base,"hz_endpoints.txt"),"w",encoding="utf-8").write(out.getvalue())
print("ok")