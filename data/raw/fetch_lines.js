const fs=require("fs");
const HOSTS=["https://marketing.cyberspaceit.cn/interface/metromap/metromap.aspx?func=lines",
             "https://m.shmetro.com/interface/metromap/metromap.aspx?func=lines"];
(async()=>{
  for(const u of HOSTS){
    try{
      const r=await fetch(u,{headers:{"User-Agent":"Mozilla/5.0","Referer":"https://service.shmetro.com/"}});
      const b=Buffer.from(await r.arrayBuffer());
      if(r.status===200 && b.length>50){
        const d=JSON.parse(b.toString("utf8"));
        fs.writeFileSync(process.argv[2], JSON.stringify(d));
        console.log("ok "+d.length+" lines from "+u.split("/")[2]);
        return;
      }
    }catch(e){ console.log("fail "+u.split("/")[2]+": "+e.message); }
  }
  console.log("ALLFAIL"); process.exit(1);
})();