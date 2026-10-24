const fs=require("fs"), path=require("path");
const q=`[out:json][timeout:90];
rel(5161881); out geom;
rel(13334262); out geom;`;
(async()=>{
  const r=await fetch("https://overpass-api.de/api/interpreter",{method:"POST",
    headers:{"User-Agent":"dsh-metro/1.0","Content-Type":"application/x-www-form-urlencoded"},
    body:"data="+encodeURIComponent(q)});
  const t=await r.text();
  console.log("status="+r.status+" len="+t.length);
  fs.writeFileSync(path.join(process.argv[2],"osm_suzhou_tram_geom.json"), t);
  const j=JSON.parse(t);
  for(const e of j.elements){
    const T=e.tags||{};
    const mem=e.members||[];
    const ways=mem.filter(m=>m.type==="way"&&m.geometry);
    const nodes=mem.filter(m=>m.type==="node");
    console.log("\n"+T.name+"  id="+e.id+"  members="+mem.length+" ways(geom)="+ways.length+" nodes="+nodes.length);
    console.log("  roles="+[...new Set(mem.map(m=>m.role))].join(","));
    console.log("  tags="+JSON.stringify(T).slice(0,200));
    if(ways[0]) console.log("  way0 pts="+ways[0].geometry.length+" first="+JSON.stringify(ways[0].geometry[0]));
    if(nodes[0]) console.log("  node0 "+JSON.stringify(nodes[0]).slice(0,180));
  }
})();