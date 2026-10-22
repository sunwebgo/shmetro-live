# -*- coding: utf-8 -*-
import re, io, sys
from lxml import html as LH
base=r"D:\Idea_project\SpringAI-2.0\shmetro-live\data\raw"
doc=LH.parse(base+r"\hcskb_0.html")
root=doc.getroot()
def norm(s):
    s=re.sub(r"[\u00a0\u3000]"," ",s)
    s=re.sub(r"\s+"," ",s)
    return s.strip()
# walk all elements in document order, track headings
body=root.body if root.body is not None else root
tables=[]
for el in body.iter():
    if el.tag=="table":
        rows=[]
        for tr in el.iter("tr"):
            cells=[norm(" ".join(td.itertext())) for td in tr.iter("td","th")]
            if any(cells): rows.append(cells)
        tables.append(rows)
out=io.StringIO()
out.write("tables=%d\n"%len(tables))
for i,t in enumerate(tables):
    ncols=max(len(r) for r in t) if t else 0
    out.write("\n===== TABLE %d  rows=%d maxcols=%d =====\n"%(i,len(t),ncols))
    for r in t[:24]:
        out.write("  "+" | ".join(r)+"\n")
open(base+r"\tables_dump.txt","w",encoding="utf-8").write(out.getvalue())
print("tables=%d"%len(tables))