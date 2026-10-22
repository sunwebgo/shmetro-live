# -*- coding: utf-8 -*-
import re, io
from html.parser import HTMLParser
base = r"D:\Idea_project\SpringAI-2.0\shmetro-live\data\raw"
raw=open(base+r"\hcskb_0.html",encoding="utf-8",errors="replace").read()
class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables=[]; self.depth=0; self.cur=None; self.row=None; self.cell=None; self.curpos=0
    def handle_starttag(self,tag,attrs):
        if tag=="table":
            self.depth+=1
            if self.depth==1:
                self.cur=[]; self.tables.append((self.getpos(),self.cur))
        elif tag=="tr" and self.cur is not None: self.row=[]
        elif tag in ("td","th") and self.row is not None: self.cell=[]
    def handle_endtag(self,tag):
        if tag in ("td","th") and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split())); self.cell=None
        elif tag=="tr" and self.row is not None:
            if any(self.row): self.cur.append(self.row)
            self.row=None
        elif tag=="table":
            if self.depth==1: self.cur=None
            self.depth=max(0,self.depth-1)
    def handle_data(self,d):
        if self.cell is not None: self.cell.append(d)
p=P(); p.feed(raw)
out=io.StringIO()
for i,(pos,tb) in enumerate(p.tables,1):
    if i<39: continue
    if not tb: continue
    out.write("\n### TABLE %d  (line %d of source)\n"%(i,pos[0]))
    for r in tb[:8]:
        out.write("    "+" | ".join(r)+"\n")
open(base+r"\tables_tail.txt","w",encoding="utf-8").write(out.getvalue())
print("ok")