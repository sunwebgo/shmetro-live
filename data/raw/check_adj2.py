# -*- coding: utf-8 -*-
import json, io, os
base=r"D:\Idea_project\SpringAI-2.0\shmetro-live\data\raw\official"
out=io.StringIO()
for n in [7,8,9,10,13,1,2]:
    d=json.load(open(os.path.join(base,"fltime_%d.txt"%n),encoding="utf-8-sig"))
    hits=[r for r in d if (r.get("last_time_desc") or "").strip() not in ("","{}")]
    out.write("\n=== L%d 有延时的记录 %d / %d\n"%(n,len(hits),len(d)))
    seen=set()
    for r in hits:
        key=(r["name"],r.get("description"))
        if key in seen: continue
        seen.add(key)
        try: wd=json.loads(r["last_time_desc"]).get("weekday")
        except Exception: wd=None
        out.write("   %-14s %-22s last=%s wd=%s\n"%(r["name"],r.get("description"),r["last_time"],wd))
        if len(seen)>14: out.write("   ...\n"); break
open(r"D:\Idea_project\SpringAI-2.0\shmetro-live\data\raw\check_adj2.txt","w",encoding="utf-8").write(out.getvalue())
print("ok")