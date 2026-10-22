import json,io
base=r"D:\Idea_project\SpringAI-2.0\shmetro-live\data\raw"
d=json.load(open(base+r"\api_fltime_1.txt",encoding="utf-8-sig"))
out=io.StringIO()
out.write("type=%s len=%d\n"%(type(d).__name__, len(d)))
out.write(json.dumps(d[:4],ensure_ascii=False,indent=1)+"\n")
out.write("...\n")
out.write(json.dumps(d[-3:],ensure_ascii=False,indent=1)+"\n")
# distinct last_time_desc shapes
seen=set()
for r in d:
    for k in r.keys(): seen.add(k)
out.write("keys: %s\n"%sorted(seen))
out.write("lines present: %s\n"%sorted(set(r.get("line") for r in d)))
open(base+r"\explore_fltime.txt","w",encoding="utf-8").write(out.getvalue())
print("ok")