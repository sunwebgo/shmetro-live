# -*- coding: utf-8 -*-
import re, io, os
base=r"D:\shmetro-live\data\raw"
c=open(os.path.join(base,"hz_schedule_chunk.js"),encoding="utf-8",errors="replace").read()
out=io.StringIO()
out.write("len=%d\n"%len(c))
strs=set(re.findall(r'"([^"\\]{3,80})"', c)) | set(re.findall(r"'([^'\\]{3,80})'", c))
out.write("--- 字符串字面量 ---\n")
for s in sorted(strs):
    if any(k in s.lower() for k in ("/","api","http","time","line","station","schedule","json")) or re.match(r"^[A-Z_]+$", s):
        out.write("  "+s+"\n")
out.write("\n--- import 依赖 ---\n")
for m in re.findall(r'import\("\./([^"]+)"\)', c): out.write("  "+m+"\n")
out.write("\n--- 片段(前 900 字符) ---\n")
out.write(c[:900].replace("\n"," ")+"\n")
open(os.path.join(base,"hz_chunk2.txt"),"w",encoding="utf-8").write(out.getvalue())
print("ok")