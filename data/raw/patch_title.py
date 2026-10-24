import re, io, os
p=r"D:\shmetro-live\tools\render_png.py"
t=open(p,encoding="utf-8").read()
old='title = "上海地铁 2D 动态线路图 · %s %s" % (m["dateLabel"], m["dayLabel"])'
new='title = "%s 2D 动态线路图 · %s %s" % (m.get("cityName") or "城市轨道", m["dateLabel"], m["dayLabel"])'
assert old in t, "pattern not found"
t=t.replace(old,new)
open(p,"w",encoding="utf-8").write(t)
print("patched")