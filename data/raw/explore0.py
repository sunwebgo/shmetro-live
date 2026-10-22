import re,io,sys
out=io.StringIO()
p=r"D:\Idea_project\SpringAI-2.0\shmetro-live\data\raw\shmetro_0.txt"
raw=open(p,"rb").read()
for enc in ("utf-8","gbk","gb18030"):
    try:
        t=raw.decode(enc); out.write("decoded with %s\n"%enc); break
    except Exception as e: out.write("fail %s %s\n"%(enc,e))
out.write("HEAD:\n"+t[:1500]+"\n")
out.write("\n--- script/link srcs ---\n")
for m in re.findall(r'(?:src|href)="([^"]+)"', t):
    out.write(m+"\n")
out.write("\n--- keywords ---\n")
for kw in ["首末班车","时刻表","间隔","api","ajax","getStation","line","json"]:
    idxs=[m.start() for m in re.finditer(re.escape(kw), t, re.I)][:6]
    out.write("%s: %d hits %s\n"%(kw, len(re.findall(re.escape(kw),t,re.I)), idxs))
open(r"D:\Idea_project\SpringAI-2.0\shmetro-live\data\raw\explore0.txt","w",encoding="utf-8").write(out.getvalue())
print("done")