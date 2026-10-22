import re,io
base=r"D:\Idea_project\SpringAI-2.0\shmetro-live\data\raw"
t=open(base+r"\hcskb_0.html",encoding="utf-8",errors="replace").read()
out=io.StringIO()
for m in list(re.finditer("间隔",t))[:60]:
    s=max(0,m.start()-350); e=min(len(t),m.end()+350)
    out.write("### @%d\n"%m.start())
    out.write(re.sub(r"\s+"," ",t[s:e])+"\n")
open(base+r"\explore_interval_ctx.txt","w",encoding="utf-8").write(out.getvalue())
print("ok")