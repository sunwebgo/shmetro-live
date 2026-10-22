# -*- coding: utf-8 -*-
import json, io, os
base=r"D:\Idea_project\SpringAI-2.0\shmetro-live\data\raw"
out=io.StringIO()
d=json.load(open(base+r"\official\fltime_4.txt",encoding="utf-8-sig"))
pats={}
for r in d: pats.setdefault(r["description"],[]).append(r)
for k,v in pats.items():
    v=sorted(v,key=lambda r:int(r["stat_id"]))
    out.write("L4 pat %-10s n=%d first=%s last=%s :: %s\n"%(k,len(v),v[0]["first_time"],v[0]["last_time"]," > ".join(x["name"] for x in v[:5])))
a=json.load(open(base+r"\t.json",encoding="utf-8"))
for L in a["l"]:
    if L["ln"]=="4号线":
        out.write("AMAP 4: "+" > ".join(s["n"] for s in L["st"][:6])+" ... "+" > ".join(s["n"] for s in L["st"][-4:])+"\n")
# 11号线 迪士尼 往花桥 record
d11=json.load(open(base+r"\official\fltime_11.txt",encoding="utf-8-sig"))
for r in d11:
    if r["name"]=="迪士尼":
        out.write("L11 迪士尼 %-16s first=%s last=%s arr=%s\n"%(r["description"],r["first_time"],r["last_time"],r["firstarrival_time"]))
open(base+r"\check4.txt","w",encoding="utf-8").write(out.getvalue())
print("ok")