# -*- coding: utf-8 -*-
import json, io, os, re, sys
sys.path.insert(0, r"D:\shmetro-live\tools")
import build_data as bd

out=io.StringIO()
# 苏州 1号线
amap=[e for e in bd.load_amap("amap_suzhou.json") if e["ln"]=="1号线"][0]
st=bd.amap_stations(amap)
dto=bd.load_json(os.path.join(bd.SZ_DTO,"1_周一至周四时刻表.json"))
id2name={s["stationId"]:bd.norm_name(s["stationNameZh"]) for s in dto["stations"]}
out.write("苏州1号线 AMap 站名: "+", ".join(s["n"] for s in st[:8])+" ...\n")
out.write("苏州1号线 API  站名: "+", ".join(id2name[k] for k in list(id2name)[:8])+" ...\n")
first={}
for f in dto["timetableFrequency"]:
    for td in f["timetableDirection"]:
        dn=td.get("directionNameZh","")
        if "钟南街" in dn and f["frequencyNameZh"]=="首班车":
            for it in td["timetableFirstLastTimes"]:
                nm=id2name.get(it["stationId"])
                t=bd.sec_of(it["tfltTime"])
                if nm and t is not None: first[nm]=t
out.write("方向=往钟南街 首班车条目数=%d\n"%len(first))
miss=[s["n"] for s in st if bd.norm_name(s["n"]) not in first]
out.write("AMap 有但 API 无: %s\n"%miss)
out.write("API 时刻样例: %s\n"%str(list(first.items())[:6]))

# 杭州 1号线
amap=[e for e in bd.load_amap("amap_hangzhou.json") if e["ln"]=="1号线"][0]
st=bd.amap_stations(amap)
api=bd.load_json(os.path.join(bd.RAW,"hz_all.json"))["data"]["subwaySiteDetail"]
d=api["1号线"]
out.write("\n杭州1号线 方向: %s\n"%[x["title"] for x in d])
dd=d[0]
nm=[x["sitName"] for x in dd["allStation"]]
out.write("API 站名(前8): %s\n"%nm[:8])
out.write("AMap 站名(前8): %s\n"%[s["n"] for s in st[:8]])
out.write("样例时间: %s\n"%[(x["sitName"],x["startTime"],x["endTime"]) for x in dd["allStation"][:4]])
setA=set(bd.norm_name(s["n"]) for s in st); setB=set(bd.norm_name(x) for x in nm)
out.write("AMap-API 差集: %s\n"%(setA-setB))
out.write("API-AMap 差集: %s\n"%(setB-setA))
open(os.path.join(bd.RAW,"diag_names.txt"),"w",encoding="utf-8").write(out.getvalue())
print("ok")