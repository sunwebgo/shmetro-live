const fs=require("fs"), path=require("path");
const out=process.argv[2];
const H={"User-Agent":"Mozilla/5.0"};
async function get(u){
  try{ const r=await fetch(u,{headers:H,redirect:"follow"}); const b=Buffer.from(await r.arrayBuffer());
    return {status:r.status, buf:b, ct:r.headers.get("content-type")||"", url:r.url}; }
  catch(e){ return {status:0, err:e.message}; }
}
(async()=>{
  const jobs=[
    ["sz_time","https://www.sz-mtr.com/service/guide/time/"],
    ["sz_metromap_api","https://szex.sz-mtr.com/sz-app-h5/ipis/metromap/index.html"],
    ["hz_bundle","https://www.hzmetro.com/js/index-Byg-IV4M.js"]
  ];
  for(const [n,u] of jobs){
    const r=await get(u);
    if(r.status===200){
      const isJs = n==="hz_bundle";
      fs.writeFileSync(path.join(out,n+(isJs?".js":".html")), r.buf);
      console.log(n.padEnd(18)+r.status+" "+String(r.buf.length).padStart(8)+"b  "+r.ct.slice(0,40));
    } else console.log(n.padEnd(18)+"ERR "+r.status+" "+(r.err||""));
  }
})();