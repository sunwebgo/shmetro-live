# -*- coding: utf-8 -*-
import re, io, os
base=r"D:\shmetro-live\data\raw"
t=open(os.path.join(base,"sz_szmtrTime.js"),encoding="utf-8",errors="replace").read()
out=io.StringIO()
out.write("len=%d\n"%len(t))
out.write("--- 前 1200 字符 ---\n"+t[:1200]+"\n")
keys=re.findall(r"metroTimeArray\['([^']+)'\]", t)
out.write("\n不同 key 数: %d\n前 20: %s\n"%(len(keys), keys[:20]))
out.write("\n--- 字段名 ---\n")
fields=set(re.findall(r'"([a-z_]+)"\s*:', t))
out.write(", ".join(sorted(fields))+"\n")
open(os.path.join(base,"sz_time_struct.txt"),"w",encoding="utf-8").write(out.getvalue())
print("ok")