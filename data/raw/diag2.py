# -*- coding: utf-8 -*-
import json, os, sys, io
sys.path.insert(0, r"D:\shmetro-live\tools")
import build_data as bd
out=io.StringIO()

def probe(label, stations, times):
    pts=[times.get(bd.norm_name(s["n"])) for s in stations]
    n=len(pts); known=[i for i,t in enumerate(pts) if t is not None]
    out.write("\n=== %s  n=%d known=%d\n"%(label,n,len(known)))
    out.write("  缺失站: %s\n"%[stations[i]["n"] for i,t in enumerate(pts) if t is None])
    if len(known)>=2:
        bad=[(stations[a]["n"],stations[b]["n"],pts[b]-pts[a]) for a,b in zip(known,known[1:]) if pts[b]<=pts[a]]
        out.write("  非单调对: %s\n"%bad[:5])
        span=(pts[known[-1]]-pts[known[0]])/max(1,known[-1]-known[0])
        out.write("  平均每站用时=%.1fs  全程=%.1fmin\n"%(span,(pts[known[-1]]-pts[known[0]])/60))
        segs=[pts[b]-pts[a] for a,b in zip(known,known[1:])]
        out.write("  段用时 min=%s max=%s\n"%(min(segs) if segs else None,max(segs) if segs else None))
    out.write("  data_offsets -> %s\n"%("OK" if bd.data_offsets(stations,times) else "None"))

# 苏州1
amap=[e for e in bd.load_amap("amap_suzhou.json") if e["ln"]=="1号线"][0]
st=bd.amap_stations(amap)
dto=bd.load_json(os.path.join(bd.SZ_DTO,"1_周一至周四时刻表.json"))
id2name={s["stationId"]:bd.norm_name(s["stationNameZh"]) for s in dto["stations"]}
first={}
for f in dto["timetableFrequency"]:
    for td in f["timetableDirection"]:
        if "钟南街" in td.get("directionNameZh","") and f["frequencyNameZh"]=="首班车":
            for it in td["timetableFirstLastTimes"]:
                nm=id2name.get(it["stationId"]); t=bd.sec_of(it["tfltTime"])
                if nm and t is not None: first[nm]=t
probe("苏州1号线 往钟南街", st, first)

# 杭州1
amap=[e for e in bd.load_amap("amap_hangzhou.json") if e["ln"]=="1号线"][0]
st2=bd.amap_stations(amap)
api=bd.load_json(os.path.join(bd.RAW,"hz_all.json"))["data"]["subwaySiteDetail"]["1号线"]
d=[x for x in api if "萧山国际机场" in x["title"]][0]
fw={}
for s in d["allStation"]:
    fw[bd.norm_name(s["sitName"])]=bd.sec_of(s["startTime"])
probe("杭州1号线 往萧山国际机场", st2, fw)
open(os.path.join(bd.RAW,"diag2.txt"),"w",encoding="utf-8").write(out.getvalue())
print("ok")