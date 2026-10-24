const fs=require("fs"), path=require("path");
const out=process.argv[2];
const H={"User-Agent":"Mozilla/5.0","Referer":"https://www.hzmetro.com/operation/operatingSchedule","Accept":"application/json, text/plain, */*"};
const cands=["/api/operation/all","/api/operation/timetable","/api/operation/schedule","/api/operation/time",
             "/api/operation/operatingSchedule","/api/operation/line","/api/operation/station","/api/operation/fare"];
(async()=>{
  for(const p of cands){
    try{
      const r=await fetch("https://www.hzmetro.com"+p,{headers:H});
      const b=Buffer.from(await r.arrayBuffer());
      const head=b.toString("utf8",0,140).replace(/\s+/g," ");
      console.log(p.padEnd(34)+r.status+" "+String(b.length).padStart(8)+"b  "+head);
      if(r.status===200 && b.length>200) fs.writeFileSync(path.join(out,"hz"+p.replace(/\//g,"_")+".json"), b);
    }catch(e){ console.log(p.padEnd(34)+"ERR "+e.message); }
  }
})();