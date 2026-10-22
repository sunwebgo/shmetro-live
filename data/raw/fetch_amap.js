const fs=require("fs");
const url="https://map.amap.com/service/subway?_1469083453978&srhdata=3100_drw_shanghai.json";
(async()=>{
  const r=await fetch(url,{headers:{"User-Agent":"Mozilla/5.0"}});
  const b=Buffer.from(await r.arrayBuffer());
  const d=JSON.parse(b.toString("utf8"));
  const dst=process.argv[2];
  fs.writeFileSync(dst, JSON.stringify(d));
  console.log("ok status="+r.status+" lines="+d.l.length+" bytes="+b.length+" -> "+dst);
})();