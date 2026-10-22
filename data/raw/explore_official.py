# -*- coding: utf-8 -*-
import json, io, os
base=r"D:\Idea_project\SpringAI-2.0\shmetro-live\data\raw\official"
out=io.StringIO()
for n in [2,11,16,41,51]:
    d=json.load(open(os.path.join(base,"fltime_%d.txt"%n),encoding="utf-8-sig"))
    out.write("\n===== fltime line %d  records=%d\n"%(n,len(d)))
    dirs={}
    for r in d:
        dirs.setdefault((r.get("direction"),r.get("description")),[]).append(r)
    for k,v in dirs.items():
        out.write("  dir=%s desc=%s n=%d  first=%s  last=%s\n"%(k[0],k[1],len(v),v[0]["first_time"],v[0]["last_time"]))
    out.write("  stations(ordered as given): %s\n"%(" > ".join(r["name"] for r in d[:8])))
# lineStations
for n in [1,2,11]:
    p=os.path.join(base,"lineStations_%d.txt"%n)
    d=json.load(open(p,encoding="utf-8-sig"))
    out.write("\n===== lineStations %d keys=%s\n"%(n,list(d.keys())[:12]))
    s=json.dumps(d,ensure_ascii=False)
    out.write(s[:1200]+"\n")
open(r"D:\Idea_project\SpringAI-2.0\shmetro-live\data\raw\explore_official.txt","w",encoding="utf-8").write(out.getvalue())
print("ok")