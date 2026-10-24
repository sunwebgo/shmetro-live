# -*- coding: utf-8 -*-
import json, io, os
base=r"D:\shmetro-live\data\raw"
d=json.load(open(os.path.join(base,"sz_dto","1_周一至周四时刻表.json"),encoding="utf-8"))
out=io.StringIO()
out.write("keys=%s\n"%list(d.keys()))
out.write("guideDescZh=%s\n\n"%d.get("guideDescZh"))
for f in d["timetableFrequency"]:
    out.write("freq: name=%-6s dirType=%-5s keys=%s\n"%(f.get("frequencyNameZh"),f.get("frequencyDirectionType"),list(f.keys())))
    td=f.get("timetableDirection") or []
    out.write("   timetableDirection 组数=%d  keys=%s\n"%(len(td), list(td[0].keys()) if td else []))
    if td:
        item=td[0]
        out.write("   item keys=%s\n"%list(item.keys()))
        for k,v in item.items():
            if isinstance(v,list):
                out.write("     %s: list len=%d sample=%s\n"%(k,len(v),json.dumps(v[:2],ensure_ascii=False)))
            else:
                out.write("     %s=%s\n"%(k,v))
    out.write("\n")
open(os.path.join(base,"sz_freq.txt"),"w",encoding="utf-8").write(out.getvalue())
print("ok")