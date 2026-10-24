const fs=require("fs"), path=require("path");
const geom=JSON.parse(fs.readFileSync(path.join(process.argv[2],"osm_suzhou_tram_geom.json"),"utf8"));
const ids=[];
const info={};
geom.elements.forEach(e=>{
  const refs=e.members.filter(m=>m.type==="node").map(m=>m.ref);
  info[e.id]={name:e.tags.name,color:e.tags.colour,refs};
  refs.forEach(r=>ids.push(r));
});
console.log("总节点 "+ids.length);
const q=`[out:json][timeout:60];node(id:${ids.join(",")});out body;`;
(async()=>{
  const r=await fetch("https://overpass-api.de/api/interpreter",{method:"POST",
    headers:{"User-Agent":"dsh-metro/1.0","Content-Type":"application/x-www-form-urlencoded"},
    body:"data="+encodeURIComponent(q)});
  const j=await r.json();
  const map={};
  (j.elements||[]).forEach(n=>{ map[n.id]={name:(n.tags||{}).name,lat:n.lat,lon:n.lon,tags:n.tags||{}}; });
  const out={lines:[]};
  for(const [rid,d] of Object.entries(info)){
    const stops=d.refs.map(id=>map[id]).filter(Boolean);
    out.lines.push({rel:rid,name:d.name,color:d.color,stops});
    console.log("\n=== "+d.name+"  color="+d.color+"  解析到站点 "+stops.length+"/"+d.refs.length);
    stops.forEach((s,i)=>console.log("  "+String(i+1).padStart(2)+". "+(s.name||"(无名)")+"  "+s.lat.toFixed(5)+","+s.lon.toFixed(5)));
  }
  fs.writeFileSync(path.join(process.argv[2],"suzhou_tram_stops.json"), JSON.stringify(out,null,1));
  console.log("\n已保存 suzhou_tram_stops.json");
})();