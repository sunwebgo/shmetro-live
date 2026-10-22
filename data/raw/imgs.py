# -*- coding: utf-8 -*-
import re, io
base = r"D:\Idea_project\SpringAI-2.0\shmetro-live\data\raw"
raw=open(base+r"\hcskb_0.html",encoding="utf-8",errors="replace").read()
# collect image srcs with position
imgs=[]
for m in re.finditer(r'<img[^>]+src="([^"]+)"', raw):
    imgs.append((m.start(), m.group(1)))
# collect table positions roughly
tabs=[m.start() for m in re.finditer(r'<table', raw)]
out=io.StringIO()
out.write("images=%d tables=%d\n"%(len(imgs),len(tabs)))
for pos,src in imgs:
    if re.search(r"(line|metro|shmetro)", src, re.I) or "svg" in src:
        out.write("IMG @%d  %s\n"%(pos,src))
out.write("\n--- table positions ---\n")
for i,t in enumerate(tabs): out.write("TABLE %d @%d\n"%(i+1,t))
open(base+r"\imgs.txt","w",encoding="utf-8").write(out.getvalue())
print("ok")