const fs=require("fs"), path=require("path");
const out=process.argv[2];
const H={"User-Agent":"Mozilla/5.0","Referer":"https://www.hzmetro.com/operation/networkMap",
         "Content-Type":"application/x-www-form-urlencoded","Accept":"application/json, text/plain, */*"};
(async()=>{
  const bodies=["", "cityId=3301", "lineCode=", "{}"];
  for(const bd of bodies){
    try{
      const r=await fetch("https://www.hzmetro.com/api/operation/all",{method:"POST",headers:H,body:bd});
      const t=await r.text();
      console.log("body="+JSON.stringify(bd)+" -> "+r.status+" "+t.length+"b  "+t.slice(0,150).replace(/\s+/g," "));
      if(r.status===200 && t.length>500){
        fs.writeFileSync(path.join(out,"hz_all.json"), t);
        const j=JSON.parse(t);
        console.log("   keys="+Object.keys(j));
        if(j.data) console.log("   data.keys="+Object.keys(j.data)+"  lineList="+(j.data.lineList?j.data.lineList.length:"-"));
        break;
      }
    }catch(e){ console.log("body="+JSON.stringify(bd)+" ERR "+e.message); }
  }
})();