# -*- coding: utf-8 -*-
import re, io, os
base=r"D:\shmetro-live\data\raw"
t=open(os.path.join(base,"sz_stationInfo.js"),encoding="utf-8",errors="replace").read()
i=t.find("szmtr.stations")
out=io.StringIO()
out.write("stations @%d / len %d\n"%(i,len(t)))
out.write(t[i:i+2000]+"\n")
open(os.path.join(base,"sz_stations.txt"),"w",encoding="utf-8").write(out.getvalue())
print("ok")