const fs=require("fs"), path=require("path");
const out=process.argv[2];
const H={"User-Agent":"Mozilla/5.0","Referer":"https://www.sz-mtr.com/service/guide/time/",
         "Accept":"application/json, text/plain, */*"};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function j(u,n=4){
  for(let i=0;i<n;i++){
    try{ const r=await fetch(u,{headers:H}); const t=await r.text(); return JSON.parse(t); }
    catch(e){ await sleep(600*(i+1)); }
  }
  return null;
}
(async()=>{
  const ids=JSON.parse(fs.readFileSync(path.join(out,"sz_ids.json"),"utf8"));
  const dir=path.join(out,"sz_dto"); fs.mkdirSync(dir,{recursive:true});
  let ok=0,bad=[];
  for(const [lid,arr] of Object.entries(ids)){
    for(const it of arr){
      const tag=lid+"_"+it.timeNameZh.replace(/[^\u4e00-\u9fa5]/g,"");
      const d=await j("https://www.sz-mtr.com/admin/time_table/getTimetableDtoByTimeId.do?timeId="+it.timeId);
      if(d&&d.data&&d.data.stations){
        fs.writeFileSync(path.join(dir,tag+".json"), JSON.stringify(d.data));
        ok++;
        console.log("✅ "+tag.padEnd(16)+" 站点"+String(d.data.stations.length).padStart(3)+
          "  方向组"+(d.data.timetableFrequency||[]).length);
      } else { bad.push(tag); console.log("❌ "+tag); }
      await sleep(250);
    }
  }
  console.log("\n完成 ok="+ok+" fail="+bad.length+" "+JSON.stringify(bad));
})();