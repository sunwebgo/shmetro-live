# -*- coding: utf-8 -*-
import json, io, os, datetime
base=r"D:\Idea_project\SpringAI-2.0\shmetro-live\data\raw\official"
out=io.StringIO()
out.write("2026-10-18 weekday=%d (0=Sun)\n"%datetime.date(2026,10,18).weekday())
for n,stn,desc in [(7,"花木路","美兰湖"),(9,"曹路","上海松江站"),(10,"基隆路","航中路"),(13,"金运路","张江路"),(1,"莘庄","富锦路")]:
    d=json.load(open(os.path.join(base,"fltime_%d.txt"%n),encoding="utf-8-sig"))
    for r in d:
        if r["name"]==stn and desc in (r.get("description") or ""):
            out.write("L%d %s %-22s first=%-6s last=%-6s arr=%s desc=%s\n"%(n,stn,r["description"],r["first_time"],r["last_time"],r["firstarrival_time"],r["last_time_desc"][:110]))
open(r"D:\Idea_project\SpringAI-2.0\shmetro-live\data\raw\check_adj.txt","w",encoding="utf-8").write(out.getvalue())
print("ok")