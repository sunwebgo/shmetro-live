import re,io
base=r"D:\Idea_project\SpringAI-2.0\shmetro-live\data\raw"
t=open(base+r"\hcskb_0.html",encoding="utf-8",errors="replace").read()
out=io.StringIO()
out.write("len=%d\n"%len(t))
for kw in ["首班车","末班车","var ","json","JSON","firstTrain","lastTrain","station"]:
    n=len(re.findall(re.escape(kw),t))
    out.write("kw %s -> %d\n"%(kw,n))
# find script blocks
blocks=re.findall(r"<script[^>]*>(.*?)</script>", t, re.S|re.I)
out.write("script blocks: %d\n"%len(blocks))
for i,b in enumerate(blocks):
    out.write("--- block %d len=%d head=%s\n"%(i,len(b),b.strip()[:300].replace("\n"," ")))
    if len(b)>2000:
        out.write("   tail=%s\n"%b.strip()[-300:].replace("\n"," "))
open(base+r"\explore_hcskb.txt","w",encoding="utf-8").write(out.getvalue())
print("ok")