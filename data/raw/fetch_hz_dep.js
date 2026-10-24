const fs=require("fs"), path=require("path");
(async()=>{
  for(const n of ["subway-DmnKy35h.js","index-N8aFRZSi.js","index-BUSnveWw.js"]){
    try{
      const r=await fetch("https://www.hzmetro.com/js/"+n,{headers:{"User-Agent":"Mozilla/5.0"}});
      const b=Buffer.from(await r.arrayBuffer());
      fs.writeFileSync(path.join(process.argv[2], "hz_"+n), b);
      console.log(n.padEnd(26)+r.status+" "+String(b.length).padStart(8)+"b  "+b.toString("utf8",0,90).replace(/\s+/g," "));
    }catch(e){ console.log(n+" ERR "+e.message); }
  }
})();