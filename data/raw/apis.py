import re,io
base=r"D:\Idea_project\SpringAI-2.0\shmetro-live\data\raw"
out=io.StringIO()
for f in ["hcskb_0.html","gxyxqk.html","czxx.html","zuiwantime.html","jhndcx.html","lcywgz.html","yxxlt.html"]:
    t=open(base+"\\"+f,encoding="utf-8",errors="replace").read()
    out.write("\n===== %s len=%d =====\n"%(f,len(t)))
    urls=set()
    for m in re.finditer(r'''url\s*:\s*["']([^"']+)["']''', t):
        urls.add(m.group(1))
    for m in re.finditer(r'''https?://[A-Za-z0-9_./?=&:%\-]+\.(?:aspx|ashx|json)[A-Za-z0-9_./?=&:%\-]*''', t):
        urls.add(m.group(0))
    for u in sorted(urls):
        out.write("  URL "+u+"\n")
open(base+r"\apis.txt","w",encoding="utf-8").write(out.getvalue())
print("ok")