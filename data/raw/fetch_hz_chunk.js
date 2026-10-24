const fs=require("fs"), path=require("path");
const out=process.argv[2];
(async()=>{
  const r=await fetch("https://www.hzmetro.com/js/index-BvROaDrj.js",{headers:{"User-Agent":"Mozilla/5.0"}});
  const b=Buffer.from(await r.arrayBuffer());
  fs.writeFileSync(path.join(out,"hz_schedule_chunk.js"), b);
  console.log("chunk "+r.status+" "+b.length+"b");
})();