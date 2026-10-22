import json,io
p=r"D:\Idea_project\SpringAI-2.0\shmetro-live\data\raw\t.json"
d=json.load(open(p,encoding="utf-8"))
print("top keys:", list(d.keys()))
print("city:", d.get("s"), "lines:", len(d.get("l",[])))
for L in d["l"]:
    st=L.get("st",[])
    print(L.get("ln"), "| color", L.get("cl"), "| stations", len(st), "| loop", L.get("lo"), "| f-count", len(L.get("f",[])), "| c-pts", len(L.get("c",[])), "| li", L.get("li"))