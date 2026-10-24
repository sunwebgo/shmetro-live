const fs=require("fs"), path=require("path");
const out=process.argv[2];
const H={"User-Agent":"Mozilla/5.0","Referer":"https://www.sz-mtr.com/service/guide/time/","Accept":"application/json"};
async function j(u){ const r=await fetch(u,{headers:H}); return JSON.parse(await r.text()); }
(async()=>{
  for(const lid of ["1","2","4","5","6","7","8","3_11"]){
    const d=await j("https://www.sz-mtr.com/admin/time_table/getTimetableTimeByLineId.do?lineId="+lid);
    const arr=d.data||[];
    console.log("\nlineId="+lid+"  时刻表数="+arr.length);
    arr.forEach(x=>console.log("   order="+x.order+"  "+x.timeNameZh+"  id="+x.timeId));
    if(arr.length) fs.writeFileSync(path.join(out,"sz_ids_"+lid+".json"), JSON.stringify(arr));
  }
  const first=await j("https://www.sz-mtr.com/admin/time_table/getTimetableDtoByTimeId.do?timeId="+JSON.parse(fs.readFileSync(path.join(out,"sz_ids_1.json")).toString())[0].timeId);
  fs.writeFileSync(path.join(out,"sz_dto_sample.json"), JSON.stringify(first,null,1));
  console.log("\nDTO keys="+Object.keys(first.data||first));
  console.log(JSON.stringify(first).slice(0,900));
})();