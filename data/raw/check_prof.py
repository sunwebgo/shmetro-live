# -*- coding: utf-8 -*-
import json, io, os
base=r"D:\Idea_project\SpringAI-2.0\shmetro-live\data\raw\official"
def sec(t):
    if not t or t in ("--",""): return None
    p=t.split(":")
    try: return int(p[0])*3600+int(p[1])*60+(int(p[2]) if len(p)>2 else 0)
    except: return None
out=io.StringIO()
for n,desc in [(1,"往富锦路"),(1,"往莘庄"),(9,"往曹路"),(9,"往上海松江站")]:
    d=json.load(open(os.path.join(base,"fltime_%d.txt"%n),encoding="utf-8-sig"))
    recs=[r for r in d if r["description"]==desc]
    recs=sorted(recs,key=lambda r:int(r["stat_id"]))
    out.write("\n== L%d %s (n=%d)\n"%(n,desc,len(recs)))
    prev=None
    for r in recs:
        s=sec(r["first_time"])
        inc = None if (s is None or prev is None) else s-prev
        out.write("  %-16s first=%-6s inc=%-5s stat=%s arr=%s\n"%(r["name"],r["first_time"],inc,r["stat_id"],r["firstarrival_time"]))
        if s is not None: prev=s
open(r"D:\Idea_project\SpringAI-2.0\shmetro-live\data\raw\check_prof.txt","w",encoding="utf-8").write(out.getvalue())
print("ok")