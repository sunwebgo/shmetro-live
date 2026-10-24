const fs=require("fs"), path=require("path");
const out=process.argv[2];
const q=`[out:json][timeout:60];
relation["route"="tram"](31.15,120.25,31.55,120.75);
out tags;`;
(async()=>{
  const eps=["https://overpass-api.de/api/interpreter","https://overpass.kumi.systems/api/interpreter"];
  for(const ep of eps){
    try{
      const r=await fetch(ep,{method:"POST",headers:{"User-Agent":"dsh-metro/1.0","Content-Type":"application/x-www-form-urlencoded"},
        body:"data="+encodeURIComponent(q)});
      const t=await r.text();
      console.log(ep.split("/")[2]+" -> "+r.status+" "+t.length+"b");
      if(r.status===200 && t.length>50){
        fs.writeFileSync(path.join(out,"osm_suzhou_tram.json"), t);
        const j=JSON.parse(t);
        console.log("elements="+j.elements.length);
        j.elements.slice(0,12).forEach(e=>{
          const T=e.tags||{};
          console.log("  rel"+e.id+"  name="+(T.name||"-")+"  ref="+(T.ref||"-")+"  from="+(T.from||"-")+"  to="+(T.to||"-")+"  network="+(T.network||"-"));
        });
        return;
      }
    }catch(e){ console.log(ep.split("/")[2]+" ERR "+e.message); }
  }
})();