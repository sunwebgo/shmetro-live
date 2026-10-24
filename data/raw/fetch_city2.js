const fs=require("fs"), path=require("path");
const out=process.argv[2];
const H={"User-Agent":"Mozilla/5.0","Referer":"https://www.hzmetro.com/"};
async function get(u,opt){
  try{ const r=await fetch(u,Object.assign({headers:H,redirect:"follow"},opt||{}));
    const b=Buffer.from(await r.arrayBuffer()); return {status:r.status,buf:b,ct:r.headers.get("content-type")||""}; }
  catch(e){ return {status:0,err:e.message}; }
}
(async()=>{
  const jobs=[
    ["sz_szmtrTime","https://www.sz-mtr.com/service/guide/map/javascript/szmtrTime.js"],
    ["sz_szmtr","https://www.sz-mtr.com/service/guide/map/javascript/szmtr.js"],
    ["sz_stationInfo","https://www.sz-mtr.com/service/guide/map/javascript/stationInfo_zh.js"],
    ["hz_schedule","https://www.hzmetro.com/api/operation/operatingSchedule"],
    ["hz_online","https://www.hzmetro.com/api/operation/online"],
    ["hz_builtLine","https://www.hzmetro.com/api/construction/builtLine"]
  ];
  for(const [n,u] of jobs){
    const r=await get(u);
    if(r.status===200&&r.buf.length>10){
      const ext = u.endsWith(".js")?".js":".txt";
      fs.writeFileSync(path.join(out,n+ext), r.buf);
      console.log(n.padEnd(16)+r.status+" "+String(r.buf.length).padStart(8)+"b  "+r.ct.slice(0,30)+"  | "+r.buf.toString("utf8",0,110).replace(/\s+/g," "));
    } else console.log(n.padEnd(16)+"ERR "+r.status+" "+(r.err||"")+" len="+(r.buf?r.buf.length:0));
  }
})();