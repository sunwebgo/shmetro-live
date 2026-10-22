# -*- coding: utf-8 -*-
import re, io
base = r"D:\Idea_project\SpringAI-2.0\shmetro-live\data\raw"
raw=open(base+r"\hcskb_0.html",encoding="utf-8",errors="replace").read()
out=io.StringIO()
for key in ["航头～御桥","沈杜公路～汇臻路","虹桥2号航站楼～浦东1号2号航站楼","磁浮","18号线","机场联络线"]:
    for m in list(re.finditer(re.escape(key), raw))[:2]:
        s=max(0,m.start()-2500); e=min(len(raw),m.end()+1200)
        seg=raw[s:e]
        txt=re.sub(r"<[^>]+>"," ",seg)
        txt=" ".join(txt.split())
        imgs=re.findall(r'(?:src|url\()["\']?([^"\')]+\.(?:jpg|png|svg))', seg)
        out.write("\n##### %s @%d\nTEXT: %s\nIMGS: %s\n"%(key,m.start(),txt[-1400:],imgs[-8:]))
open(base+r"\near.txt","w",encoding="utf-8").write(out.getvalue())
print("ok")