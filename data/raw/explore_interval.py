import re,io,os
base=r"D:\Idea_project\SpringAI-2.0\shmetro-live\data\raw"
out=io.StringIO()
for f in os.listdir(base):
    if not f.endswith(".html"): continue
    t=open(os.path.join(base,f),encoding="utf-8",errors="replace").read()
    n=len(re.findall("间隔",t))
    if n: out.write("%s : 间隔 x%d\n"%(f,n))
ok=io.StringIO()
open(base+r"\explore_interval.txt","w",encoding="utf-8").write(out.getvalue())
print("interval scan done")