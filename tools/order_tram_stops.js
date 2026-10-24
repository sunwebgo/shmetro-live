/* =========================================================================
 * order_tram_stops.js —— 重建有轨电车线路折线并确定站序
 *
 * 做法:
 *   1. 把 route 关系里的每条 way 当作一条边, 其端点作为图节点
 *   2. 从度为 1 的端点出发遍历图, 逐段拼接成一条连续折线
 *   3. 把站点节点投影到折线上, 按里程排序得到真实站序
 *
 * 用法: node order_tram_stops.js
 * ========================================================================= */
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '..');
const RAW = path.join(ROOT, 'data', 'raw');

const R = 6371008.8;
function dist(a, b) {
  const p1 = a.lat * Math.PI / 180, p2 = b.lat * Math.PI / 180;
  const dp = p2 - p1, dl = (b.lon - a.lon) * Math.PI / 180;
  const h = Math.sin(dp / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}
const key = p => p.lat.toFixed(6) + ',' + p.lon.toFixed(6);

const geom = JSON.parse(fs.readFileSync(path.join(RAW, 'osm_suzhou_tram_geom.json'), 'utf8'));
const stopsFile = JSON.parse(fs.readFileSync(path.join(RAW, 'suzhou_tram_stops.json'), 'utf8'));

// 坐标 -> 站名
const nameByCoord = {};
stopsFile.lines.forEach(L => L.stops.forEach(s => {
  nameByCoord[s.lat.toFixed(5) + ',' + s.lon.toFixed(5)] = s.name;
}));

const out = { lines: [] };

geom.elements.forEach(rel => {
  const ways = rel.members
    .filter(m => m.type === 'way' && m.geometry && m.geometry.length > 1)
    .map(m => m.geometry.map(p => ({ lat: p.lat, lon: p.lon })));

  // ---- 1. 建图 ----
  const adj = {};                      // nodeKey -> [{way, end}]
  ways.forEach((g, wi) => {
    [0, 1].forEach(end => {
      const k = key(end === 0 ? g[0] : g[g.length - 1]);
      (adj[k] = adj[k] || []).push({ way: wi, end });
    });
  });

  // ---- 2. 找最大连通分量里的端点作为起点 ----
  const visitedWay = new Array(ways.length).fill(false);
  function component(startKey) {
    const seen = new Set([startKey]), stack = [startKey];
    while (stack.length) {
      const k = stack.pop();
      (adj[k] || []).forEach(e => {
        const g = ways[e.way];
        const other = key(e.end === 0 ? g[g.length - 1] : g[0]);
        if (!seen.has(other)) { seen.add(other); stack.push(other); }
      });
    }
    return seen;
  }
  const comp = component(key(ways[0][0]));
  const ends = Object.keys(adj).filter(k => adj[k].length === 1 && comp.has(k));

  // 选离某个站点最近的端点
  const stopPts = rel.members.filter(m => m.type === 'node').map(n => ({ lat: n.lat, lon: n.lon }));
  function nearestStopDist(k) {
    const p = { lat: +k.split(',')[0], lon: +k.split(',')[1] };
    let m = Infinity;
    stopPts.forEach(s => { m = Math.min(m, dist(p, s)); });
    return m;
  }
  let startKey = ends.length
    ? ends.sort((a, b) => nearestStopDist(a) - nearestStopDist(b))[0]
    : key(ways[0][0]);

  // ---- 3. 遍历拼接 ----
  let path_ = [], cur = startKey, guard = 0;
  while (guard++ < ways.length + 5) {
    const cands = (adj[cur] || []).filter(e => !visitedWay[e.way]);
    if (!cands.length) break;
    const e = cands[0];
    visitedWay[e.way] = true;
    let g = ways[e.way];
    // 使 g 从 cur 出发
    if (key(g[g.length - 1]) === cur && key(g[0]) !== cur) g = g.slice().reverse();
    if (!path_.length) path_ = g.slice();
    else path_ = path_.concat(g.slice(1));
    cur = key(g[g.length - 1]);
  }

  // 累计距离
  const cum = [0];
  for (let i = 1; i < path_.length; i++) cum[i] = cum[i - 1] + dist(path_[i - 1], path_[i]);
  const totalLen = cum[cum.length - 1];

  // ---- 4. 站点投影排序 ----
  const placed = rel.members.filter(m => m.type === 'node').map(n => {
    let best = { d: Infinity, s: 0 };
    for (let i = 0; i < path_.length; i++) {
      const d = dist({ lat: n.lat, lon: n.lon }, path_[i]);
      if (d < best.d) best = { d, s: cum[i] };
    }
    const nm = nameByCoord[n.lat.toFixed(5) + ',' + n.lon.toFixed(5)] || null;
    return { name: nm, lat: n.lat, lon: n.lon, s: best.s, off: best.d };
  }).filter(p => p.name);

  placed.sort((a, b) => a.s - b.s);
  const seen = new Set(), ordered = [];
  placed.forEach(p => { if (!seen.has(p.name)) { seen.add(p.name); ordered.push(p); } });

  // 若首个站点离起点较远, 反转(让折线从首站开始)
  if (ordered.length > 1 && ordered[0].s > totalLen / 2) ordered.reverse();

  let maxGap = 0;
  for (let i = 1; i < ordered.length; i++) maxGap = Math.max(maxGap, dist(ordered[i - 1], ordered[i]));
  const maxOff = Math.max(...placed.map(p => p.off));

  console.log(`\n${rel.tags.name}: ways=${ways.length} 路径点=${path_.length} 长度=${(totalLen / 1000).toFixed(1)}km`);
  console.log(`  站点=${ordered.length} 投影误差=${maxOff.toFixed(0)}m 相邻站最大间距=${(maxGap / 1000).toFixed(2)}km ${maxGap > 4000 ? '⚠' : '✓'}`);
  ordered.forEach((p, i) => console.log(`   ${String(i + 1).padStart(2)}. ${p.name.padEnd(10)} ${(p.s / 1000).toFixed(2)}km`));

  out.lines.push({
    rel: String(rel.id), name: rel.tags.name, color: rel.tags.colour,
    stops: ordered.map(p => ({ name: p.name, lat: p.lat, lon: p.lon }))
  });
});

fs.writeFileSync(path.join(RAW, 'suzhou_tram_stops.json'), JSON.stringify(out, null, 1));
console.log('\n已写回 suzhou_tram_stops.json');
