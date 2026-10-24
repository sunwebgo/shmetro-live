# -*- coding: utf-8 -*-
import re, io, os
base=r"D:\shmetro-live\data\raw"
out=io.StringIO()
p=os.path.join(base,"hz_schedule_chunk.js")
if os.path.exists(p):
    c=open(p,encoding="utf-8",errors="replace").read()
    out.write("chunk len=%d\n"%len(c))
    for m in list(re.finditer(r'["\'`](/[a-zA-Z0-9_\-/]{4,80})["\'`]', c))[:40]:
        out.write("  path "+m.group(1)+"\n")
    out.write("--- api-ish ---\n")
    for m in list(re.finditer(r'(get|post)\(\s*["\'`]([^"\'`]{2,90})["\'`]', c))[:20]:
        out.write("  %s(%s)\n"%(m.group(1),m.group(2)))
    out.write("--- base 拼装 ---\n")
    for m in list(re.finditer(r'(?:baseURL|API_BASE|VITE_)[^\n]{0,120}', c))[:10]:
        out.write("  "+m.group(0)[:140]+"\n")
# 主包里 https://www.hzmetro.com/api 的上下文
h=open(os.path.join(base,"hz_bundle.js"),encoding="utf-8",errors="replace").read()
out.write("\n=== 主包 base 上下文 ===\n")
for m in list(re.finditer(r'https://www\.hzmetro\.com/api', h))[:4]:
    s=max(0,m.start()-350); e=min(len(h),m.end()+250)
    out.write("---\n"+h[s:e].replace("\n"," ")+"\n")
open(os.path.join(base,"hz_chunk.txt"),"w",encoding="utf-8").write(out.getvalue())
print("ok")