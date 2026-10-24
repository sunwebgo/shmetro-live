# -*- coding: utf-8 -*-
import json, os, math
base=r"D:\shmetro-live\data\raw"
subway=json.load(open(os.path.join(base,"amap_suzhou.json"),encoding="utf-8"))
def find(name):
    out=[]
    for L in subway["l"]:
        for s in L.get("st",[]):
            if s.get("n")==name:
                sl=s["sl"].split(",")
                out.append((L["ln"], float(sl[0]), float(sl[1])))
    return out
tram=json.load(open(os.path.join(base,"suzhou_tram_stops.json"),encoding="utf-8"))
print("地铁中的同名站:")
for nm in ["狮子山","苏州乐园","苏州新区火车站","龙康路"]:
    m=find(nm)
    t=[(L["name"],s["lon"],s["lat"]) for L in tram["lines"] for s in L["stops"] if s["name"]==nm]
    print("  %-8s 地铁=%s"%(nm, m if m else "无"))
    print("  %-8s 电车=%s"%("", t if t else "无"))
    for (ln,lng,lat) in m:
        for (tn,tlng,tlat) in t:
            d=math.hypot((lng-tlng)*111.32*math.cos(math.radians(lat)), (lat-tlat)*110.57)
            print("       距离 %s↔%s = %.0f m"%(ln,tn,d*1000))