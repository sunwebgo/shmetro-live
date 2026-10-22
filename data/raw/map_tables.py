# -*- coding: utf-8 -*-
import re, io, json
from html.parser import HTMLParser
base = r"D:\Idea_project\SpringAI-2.0\shmetro-live\data\raw"

class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.events=[]; self.intable=0; self.instyle=0; self.incell=0
        self.cur_table=None; self.row=None; self.cell=None
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style"): self.instyle+=1
        if tag=="table":
            self.intable+=1
            if self.intable==1:
                self.cur_table=[]
                self.events.append(("TABLE_START",len(self.events)))
        elif tag=="tr" and self.cur_table is not None: self.row=[]
        elif tag in ("td","th") and self.row is not None: self.cell=[]
    def handle_endtag(self,tag):
        if tag in ("script","style"): self.instyle=max(0,self.instyle-1)
        if tag in ("td","th") and self.cell is not None:
            t=" ".join("".join(self.cell).split())
            self.row.append(t); self.cell=None
        elif tag=="tr" and self.row is not None:
            if any(self.row): self.cur_table.append(self.row)
            self.row=None
        elif tag=="table":
            if self.intable==1:
                self.events.append(("TABLE",self.cur_table)); self.cur_table=None
            self.intable=max(0,self.intable-1)
    def handle_data(self,data):
        if self.incell: pass
        if self.cell is not None: self.cell.append(data)
        elif self.intable==0 and not self.instyle:
            t=" ".join(data.split())
            if t: self.events.append(("TEXT",t))

raw=open(base+r"\hcskb_0.html",encoding="utf-8",errors="replace").read()
p=P(); p.feed(raw)
out=io.StringIO()
recent=[]
ti=0
for kind,val in p.events:
    if kind=="TEXT":
        recent.append(val); recent=recent[-14:]
    elif kind=="TABLE":
        ti+=1
        ctx=" / ".join(recent[-8:])
        first=val[0] if val else []
        out.write("\n### TABLE %d  ctx: %s\n"%(ti, ctx[-260:]))
        for r in val[:6]:
            out.write("    "+" | ".join(r)+"\n")
open(base+r"\table_map.txt","w",encoding="utf-8").write(out.getvalue())

# AMap line names
d=json.load(open(base+r"\t.json",encoding="utf-8"))
o2=io.StringIO()
for i,L in enumerate(d["l"]):
    o2.write("%2d  ln=%-10s color=%-8s st=%d loop=%s first=%s last=%s\n"%(
        i,L.get("ln"),L.get("cl"),len(L.get("st",[])),L.get("lo"),
        L["st"][0]["n"] if L.get("st") else "?", L["st"][-1]["n"] if L.get("st") else "?"))
open(base+r"\amap_lines.txt","w",encoding="utf-8").write(o2.getvalue())
print("ok")