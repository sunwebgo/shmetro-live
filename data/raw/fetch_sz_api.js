const fs=require("fs"), path=require("path");
const out=process.argv[2];
const H={"User-Agent":"Mozilla/5.0","Referer":"https://www.sz-mtr.com/service/guide/time/","Accept":"application/json, text/plain, */*"};
async function get(u){ const r=await fetch(u,{headers:H}); return {s:r.status,t:await r.text()}; }
(async()=>{
  let r=await get("https://www.sz-mtr.com/admin/time_table/getAllVirtualLines.do");
  console.log("getAllVirtualLines: "+r.s+" "+r.t.length+"b  "+r.t.slice(0,300));
  if(r.s===200&&r.t.trim().startsWith("{")) fs.writeFileSync(path.join(out,"sz_lines.json"), r.t);
  for(const id of [1,2,3,4,5,6,7,8,9,10,11,12]){
    r=await get("https://www.sz-mtr.com/admin/time_table/getTimetableTimeByLineId.do?lineId="+id);
    const head=r.t.slice(0,160).replace(/\s+/g," ");
    console.log("lineId="+String(id).padStart(2)+" -> "+r.s+" "+String(r.t.length).padStart(7)+"b  "+head);
    if(r.s===200&&r.t.length>500) fs.writeFileSync(path.join(out,"sz_tt_"+id+".json"), r.t);
  }
})();