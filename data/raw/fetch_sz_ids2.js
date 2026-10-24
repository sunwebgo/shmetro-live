const fs=require("fs"), path=require("path");
const out=process.argv[2];
const H={"User-Agent":"Mozilla/5.0","Referer":"https://www.sz-mtr.com/service/guide/time/",
         "Accept":"application/json, text/plain, */*"};
async function j(u){ const r=await fetch(u,{headers:H}); const t=await r.text(); return JSON.parse(t); }
(async()=>{
  const summary={};
  for(const lid of ["1","2","4","5","6","7","8","3_11"]){
    const d=await j("https://www.sz-mtr.com/admin/time_table/getTimetableTimeByLineId.do?lineId="+lid);
    const arr=d.data||[];
    console.log("\nlineId="+lid+"  时刻表数="+arr.length);
    arr.forEach(x=>console.log("   order="+x.order+"  "+x.timeNameZh+"  id="+x.timeId));
    summary[lid]=arr;
  }
  fs.writeFileSync(path.join(out,"sz_ids.json"), JSON.stringify(summary,null,1));
  const tid=summary["1"][0].timeId;
  const dto=await j("https://www.sz-mtr.com/admin/time_table/getTimetableDtoByTimeId.do?timeId="+tid);
  fs.writeFileSync(path.join(out,"sz_dto_1.json"), JSON.stringify(dto,null,1));
  console.log("\nDTO 顶层 keys="+Object.keys(dto));
  console.log("data keys="+(dto.data?Object.keys(dto.data):"-"));
  console.log(JSON.stringify(dto).slice(0,1200));
})();