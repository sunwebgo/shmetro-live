const fs=require("fs"), path=require("path");
const out=process.argv[2];
const HOST="https://marketing.cyberspaceit.cn/interface/metromap/metromap.aspx?func=";
const H={"User-Agent":"Mozilla/5.0","Referer":"https://service.shmetro.com/"};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function get(url,tries=6){
  for(let i=0;i<tries;i++){
    try{
      const r=await fetch(url,{method:"GET",headers:H});
      const buf=Buffer.from(await r.arrayBuffer());
      if(r.status===200 && buf.length>2) return buf;
    }catch(e){}
    await sleep(600*(i+1));
  }
  return null;
}
(async()=>{
 const dir=path.join(out,"official"); fs.mkdirSync(dir,{recursive:true});
 let ok=0; const fail=[];
 const lines=[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,41,51];
 for(const n of lines){
  for(const [tag,url] of [
    ["fltime",HOST+"fltime&line="+n],
    ["exfltime",HOST+"exfltime&line1="+n],
    ["lineStations",HOST+"lineStations&line="+n],
    ["stationInfo",HOST+"lines"]]){
    if(tag==="stationInfo") continue;
    const buf=await get(url);
    if(buf){ fs.writeFileSync(path.join(dir,tag+"_"+n+".txt"),buf); ok++; }
    else fail.push(tag+"_"+n);
    await sleep(200);
  }
  process.stdout.write("line "+n+" ok="+ok+"\n");
 }
 console.log("ALLDONE ok="+ok+" fail="+JSON.stringify(fail));
})();