# -*- coding: utf-8 -*-
import re, io, os
base=r"D:\shmetro-live\data\raw"
h=open(os.path.join(base,"hz_bundle.js"),encoding="utf-8",errors="replace").read()
out=io.StringIO()
out.write("=== operatingSchedule 上下文 ===\n")
for m in list(re.finditer("operatingSchedule", h))[:6]:
    s=max(0,m.start()-500); e=min(len(h),m.end()+300)
    out.write("--- @%d\n%s\n"%(m.start(), h[s:e].replace("\n"," ")))
out.write("\n=== /api 出现处 ===\n")
for m in list(re.finditer(r'["\'](/api[a-zA-Z0-9_\-/]*)["\']', h))[:10]:
    s=max(0,m.start()-250); e=min(len(h),m.end()+120)
    out.write("--- %s\n%s\n"%(m.group(1), h[s:e].replace("\n"," ")))
out.write("\n=== axios/create 配置 ===\n")
for m in list(re.finditer(r'create\(\{[^}]{0,300}\)', h))[:6]:
    out.write("  "+m.group(0).replace("\n"," ")[:300]+"\n")
out.write("\n=== VITE/env 变量 ===\n")
for m in list(re.finditer(r'(VITE_[A-Z_]+)', h))[:20]:
    out.write("  "+m.group(1)+"\n")
open(os.path.join(base,"hz_api_ctx.txt"),"w",encoding="utf-8").write(out.getvalue())
print("ok")