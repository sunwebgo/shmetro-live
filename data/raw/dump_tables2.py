# -*- coding: utf-8 -*-
"""Extract 行车间隔 tables from shmetro 首末班车 page using stdlib HTMLParser."""
import re, io, json
from html.parser import HTMLParser

base = r"D:\Idea_project\SpringAI-2.0\shmetro-live\data\raw"

class TP(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables=[]; self.cur=None; self.row=None; self.cell=None; self.depth=0
    def handle_starttag(self, tag, attrs):
        if tag=="table":
            self.depth+=1
            if self.depth==1:
                self.cur=[]; self.tables.append(self.cur)
        elif tag=="tr" and self.cur is not None:
            self.row=[]
        elif tag in ("td","th") and self.row is not None:
            self.cell=[]
    def handle_endtag(self, tag):
        if tag in ("td","th") and self.cell is not None:
            txt=" ".join("".join(self.cell).split())
            self.row.append(txt); self.cell=None
        elif tag=="tr" and self.row is not None:
            if any(self.row): self.cur.append(self.row)
            self.row=None
        elif tag=="table":
            if self.depth==1: self.cur=None
            self.depth=max(0,self.depth-1)
    def handle_data(self, data):
        if self.cell is not None: self.cell.append(data)

raw=open(base+r"\hcskb_0.html",encoding="utf-8",errors="replace").read()
p=TP(); p.feed(raw)
tables=p.tables
out=io.StringIO()
out.write("tables=%d\n"%len(tables))
for i,t in enumerate(tables):
    if not t: continue
    ncols=max(len(r) for r in t)
    out.write("\n===== TABLE %d rows=%d cols=%d =====\n"%(i,len(t),ncols))
    for r in t:
        out.write("  "+" | ".join(r)+"\n")
open(base+r"\tables_dump.txt","w",encoding="utf-8").write(out.getvalue())
print("tables=%d written"%len(tables))