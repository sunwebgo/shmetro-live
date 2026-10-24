# -*- coding: utf-8 -*-
import json, io, os
base=r"D:\shmetro-live\data\raw"
j=json.load(open(os.path.join(base,"hz_all.json"),encoding="utf-8"))
d=j["data"]
out=io.StringIO()
out.write("title=%s\n"%d.get("title"))
out.write("lineList=%d  subwaySiteDetail=%s  subwaySiteInfo=%s  stationlist=%d\n"%(
    len(d["lineList"]), type(d["subwaySiteDetail"]).__name__, type(d["subwaySiteInfo"]).__name__, len(d["stationlist"])))
out.write("\n--- lineList[0] ---\n"+json.dumps(d["lineList"][0],ensure_ascii=False)[:600])
out.write("\n\n--- lineList 全部 ---\n")
for L in d["lineList"]:
    out.write("  %-8s code=%-4s other=%-10s stations=%s\n"%(L.get("lineName"),L.get("lineCode"),L.get("otherName"),len(L.get("stations",[]) or [])))
out.write("\n--- stationlist[0] ---\n"+json.dumps(d["stationlist"][0],ensure_ascii=False)[:900])
out.write("\n\n--- subwaySiteInfo 类型/样例 ---\n")
si=d["subwaySiteInfo"]
if isinstance(si,list) and si: out.write(json.dumps(si[0],ensure_ascii=False)[:600])
elif isinstance(si,dict): out.write("dict keys="+str(list(si.keys())[:20]))
out.write("\n\n--- subwaySiteDetail 样例 ---\n")
sd=d["subwaySiteDetail"]
if isinstance(sd,list) and sd: out.write(json.dumps(sd[0],ensure_ascii=False)[:800])
elif isinstance(sd,dict):
    k=list(sd.keys())[:3]; out.write("dict keys="+str(k))
    out.write("\n"+json.dumps(sd[k[0]],ensure_ascii=False)[:600])
open(os.path.join(base,"hz_struct.txt"),"w",encoding="utf-8").write(out.getvalue())
print("ok")