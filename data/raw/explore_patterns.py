# -*- coding: utf-8 -*-
import json, io, os
base=r"D:\Idea_project\SpringAI-2.0\shmetro-live\data\raw\official"
out=io.StringIO()
for n in [2,5,10,11]:
    ls=json.load(open(os.path.join(base,"lineStations_%d.txt"%n),encoding="utf-8-sig"))
    locs=ls["levels"][0]["locations"]
    out.write("\n===== L%d lineStations order (%d) =====\n"%(n,len(locs)))
    out.write(" > ".join("%s[%s]"%(l["title"],l["id"].replace("station","")) for l in locs)+"\n")
    d=json.load(open(os.path.join(base,"fltime_%d.txt"%n),encoding="utf-8-sig"))
    pats={}
    for r in d: pats.setdefault(r["description"],[]).append(r)
    for desc,recs in pats.items():
        recs=sorted(recs,key=lambda r:int(r["stat_id"]))
        out.write("  PATTERN %-24s n=%2d  " % (desc,len(recs)))
        out.write(" | ".join("%s:%s%s"%(r["name"],r["first_time"],"*" if r["firstarrival_time"] else "") for r in recs[:6]))
        out.write(" ... "+" | ".join("%s:%s%s"%(r["name"],r["first_time"],"*" if r["firstarrival_time"] else "") for r in recs[-3:]))
        out.write("\n")
open(r"D:\Idea_project\SpringAI-2.0\shmetro-live\data\raw\explore_patterns.txt","w",encoding="utf-8").write(out.getvalue())
print("ok")