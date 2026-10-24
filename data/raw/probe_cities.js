const fs=require("fs"), path=require("path");
const targets=[
 ["amap_suzhou","https://map.amap.com/service/subway?_1469083453978&srhdata=3205_drw_suzhou.json"],
 ["amap_hangzhou","https://map.amap.com/service/subway?_1469083453978&srhdata=3301_drw_hangzhou.json"],
 ["szmtr_home","https://www.sz-mtr.com/"],
 ["hzmtr_home","https://www.hzmetro.com/"],
 ["hzmtr_index","https://www.hzmetro.com/index.html"]
];
(async()=>{
 for(const [n,u] of targets){
  const t0=Date.now();
  try{
   const r=await fetch(u,{headers:{"User-Agent":"Mozilla/5.0"}});
   const b=Buffer.from(await r.arrayBuffer());
   if(n.startsWith("amap")) fs.writeFileSync(path.join(process.argv[2],n+".json"), b);
   else fs.writeFileSync(path.join(process.argv[2],n+".html"), b);
   console.log(n.padEnd(14)+" "+r.status+" "+String(b.length).padStart(8)+"b "+(Date.now()-t0)+"ms");
  }catch(e){ console.log(n.padEnd(14)+" ERR "+e.message); }
 }
})();