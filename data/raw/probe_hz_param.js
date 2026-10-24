const fs=require("fs");
const H={"User-Agent":"Mozilla/5.0","Referer":"https://www.hzmetro.com/operation/networkMap",
         "Content-Type":"application/x-www-form-urlencoded"};
(async()=>{
  const bodies=["type=1","dayType=1","dateType=1","isWeekend=0","weekType=1","timeType=1","type=weekday","day=1"];
  for(const bd of bodies){
    try{
      const r=await fetch("https://www.hzmetro.com/api/operation/all",{method:"POST",headers:H,body:bd});
      const t=await r.text();
      let title="";
      try{ title=JSON.parse(t).data.title; }catch(e){}
      // 取1号线首站首末班作为指纹
      let fp="";
      try{ const j=JSON.parse(t); const s=j.data.subwaySiteDetail["1号线"][0].allStation[0]; fp=s.sitName+" "+s.startTime+"-"+s.endTime; }catch(e){}
      console.log(bd.padEnd(14)+r.status+" "+(title||"-").padEnd(10)+" "+fp+"   len="+t.length);
    }catch(e){ console.log(bd+" ERR "+e.message); }
  }
})();