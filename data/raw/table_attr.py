# -*- coding: utf-8 -*-
import re, io
from html.parser import HTMLParser
base = r"D:\Idea_project\SpringAI-2.0\shmetro-live\data\raw"
raw=open(base+r"\hcskb_0.html",encoding="utf-8",errors="replace").read()
# build line offsets
off=0; offsets=[0]
for line in raw.split("\n"):
    off+=len(line)+1; offsets.append(off)
def abspos(line, col):
    if 1<=line<len(offsets): return offsets[line-1]+col
    return 0

class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables=[]; self.depth=0; self.cur=None; self.row=None; self.cell=None
    def handle_starttag(self,tag,attrs):
        if tag=="table":
            self.depth+=1
            if self.depth==1:
                self.cur=[]; self.tables.append((abspos(*self.getpos()), self.cur))
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
namepat=re.compile(r"(\d{1,2}号线|浦江线|磁浮线|市域机场线|金山铁路|机场联络线)")
out=io.StringIO()
for i,(pos,tb) in enumerate(p.tables,1):
    if not tb: continue
    window=raw[max(0,pos-6000):pos]
    txt=re.sub(r"<[^>]+>"," ",window)
    txt=" ".join(txt.split())
    hits=[m.group(1) for m in namepat.finditer(txt)]
    head=tb[0][:4]
    out.write("TABLE %2d pos=%d lastnames=%s\n   row0: %s\n"%(i,pos,hits[-4:]," | ".join(head)))
open(base+r"\table_attr.txt","w",encoding="utf-8").write(out.getvalue())
print("ok")