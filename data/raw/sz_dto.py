# -*- coding: utf-8 -*-
import json, io, os
base=r"D:\shmetro-live\data\raw"
d=json.load(open(os.path.join(base,"sz_dto_1.json"),encoding="utf-8"))
data=d["data"]
out=io.StringIO()
out.write("data keys: %s\n"%list(data.keys()))
out.write("timeNameZh=%s  timeStart=%s timeEnd=%s\n"%(data.get("timeNameZh"),data.get("timeStart"),data.get("timeEnd")))
out.write("guideDescZh=%s\n"%str(data.get("guideDescZh"))[:200])
out.write("\nstations 数=%d  第一项: %s\n"%(len(data["stations"]), json.dumps(data["stations"][0],ensure_ascii=False)))
out.write("station 字段: %s\n"%list(data["stations"][0].keys()))
tf=data.get("timetableFrequency")
out.write("\ntimetableFrequency 类型=%s\n"%type(tf).__name__)
out.write(json.dumps(tf,ensure_ascii=False)[:1500]+"\n")
open(os.path.join(base,"sz_dto_struct.txt"),"w",encoding="utf-8").write(out.getvalue())
print("ok")