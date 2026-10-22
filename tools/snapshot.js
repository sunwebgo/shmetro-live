/* =========================================================================
 * snapshot.js —— 复用 js/sim.js 的真实仿真逻辑, 导出指定时刻的
 * 像素级绘制数据(线路折线/车站/列车), 供 render_png.py 出图。
 * 用法: node snapshot.js <dayKey> <星期几0-6> <HH:MM> <输出json> [W] [H]
 * ========================================================================= */
global.window = global;
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '..');
require(path.join(ROOT, 'data/metro-data.js'));
require(path.join(ROOT, 'js/sim.js'));

const SIM = global.SIM;
const DATA = global.SHMETRO_DATA;

const dayKey = process.argv[2] || 'mon_thu';
const dow = +(process.argv[3] || 1);
const hhmm = process.argv[4] || '08:00';
const outFile = process.argv[5] || path.join(ROOT, 'data/snapshot.json');
const W = +(process.argv[6] || 1600);
const H = +(process.argv[7] || 1000);
const SAMPLES = 8;

const [hh, mm] = hhmm.split(':').map(Number);
const time = hh * 3600 + mm * 60;
// 2026-10-18 是周日
const date = new Date(2026, 9, 18 + dow);

/* ------------------------------------------------------------- 投影(同 app.js) */
const b = { x0: 1e9, x1: -1e9, y0: 1e9, y1: -1e9 };
DATA.lines.forEach(L => L.services.forEach(s => s.st.forEach(p => {
  b.x0 = Math.min(b.x0, p[1]); b.x1 = Math.max(b.x1, p[1]);
  b.y0 = Math.min(b.y0, p[2]); b.y1 = Math.max(b.y1, p[2]);
})));
const lat0 = (b.y0 + b.y1) / 2, lng0 = (b.x0 + b.x1) / 2;
const cosL = Math.cos(lat0 * Math.PI / 180);
const k = Math.min(W / ((b.x1 - b.x0) * cosL), H / (b.y1 - b.y0)) * 0.9;
const PADX = 0, PADY = 0;
function project(lng, lat) {
  return [
    Math.round(W / 2 + (lng - lng0) * cosL * k + PADX),
    Math.round(H / 2 - (lat - lat0) * k + PADY)
  ];
}
function crPoint(p0, p1, p2, p3, t) {
  const t2 = t * t, t3 = t2 * t;
  return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 +
    (-p0 + 3 * p1 - 3 * p2 + p3) * t3);
}

/* ------------------------------------------------------------------ 几何 */
const paths = [];
DATA.lines.forEach(L => L.services.forEach(s => {
  const pts = s.st, m = pts.length, loop = !!s.loop;
  const at = j => loop ? pts[(((j % (m - 1)) + (m - 1)) % (m - 1))] : pts[Math.max(0, Math.min(m - 1, j))];
  const line = [];
  for (let i = 0; i < m - 1; i++) {
    const p0 = at(i - 1), p1 = at(i), p2 = at(i + 1), p3 = at(i + 2);
    for (let j = 0; j < SAMPLES; j++) {
      const u = j / SAMPLES;
      line.push(project(
        crPoint(p0[1], p1[1], p2[1], p3[1], u),
        crPoint(p0[2], p1[2], p2[2], p3[2], u)));
    }
  }
  line.push(project(pts[m - 1][1], pts[m - 1][2]));
  paths.push({ line: L.name, color: L.color, pts: line, total: s.total, off: s.off, loop: loop, svcId: s.id });
}));

/* ------------------------------------------------------------------ 车站 */
const idx = SIM.stations();
const stations = [];
for (const nm in idx) {
  const e = idx[nm];
  const seen = {}; let cnt = 0;
  e.entries.forEach(en => { if (!seen[en.line.name]) { seen[en.line.name] = 1; cnt++; } });
  stations.push({ n: nm, x: project(e.x, e.y)[0], y: project(e.x, e.y)[1], lines: cnt });
}

/* ------------------------------------------------------------------ 列车 */
const trains = SIM.trainsAt(time, dayKey, date, null);
const out = [];
trains.forEach(tr => {
  const g = paths.find(p => p.svcId === tr.svc.id);
  if (!g) return;
  const pos = SIM.pointAt(tr.svc, tr.dirKey, tr.progress);
  let li = pos.i * SAMPLES + Math.round(pos.u * SAMPLES);
  li = Math.max(0, Math.min(g.pts.length - 1, li));
  const p = g.pts[li];
  const pn = g.pts[Math.min(g.pts.length - 1, li + 1)] || g.pts[li - 1] || p;
  out.push({ x: p[0], y: p[1], dx: pn[0] - p[0], dy: pn[1] - p[1], color: tr.line.color, rev: tr.dirKey === 'rev' });
});

/* --------------------------------------------------------------- 运行摘要 */
const summary = [];
DATA.lines.forEach(L => {
  const st = SIM.lineStat(L, time, dayKey, date);
  summary.push({
    name: L.name, color: L.color, trains: st.trains, running: st.running,
    hwMin: st.headwayMin, hwMax: st.headwayMax,
    fwd: st.svcInfo[0] ? { first: st.svcInfo[0].fwd.first, last: st.svcInfo[0].fwd.last } : null,
    rev: st.svcInfo[0] ? { first: st.svcInfo[0].rev.first, last: st.svcInfo[0].rev.last } : null
  });
});

const payload = {
  meta: {
    dayKey, dow, time, hhmm, W, H,
    dayLabel: SIM.dayLabel(dayKey),
    dateLabel: date.getFullYear() + '-' + SIM.pad2(date.getMonth() + 1) + '-' + SIM.pad2(date.getDate()),
    generated: DATA.meta.generated,
    trains: out.length
  },
  paths, stations, trains: out, summary
};

fs.writeFileSync(outFile, JSON.stringify(payload));
console.log('snapshot ' + hhmm + ' ' + dayKey + ' -> ' + outFile +
  '  列车 ' + out.length + ' 列, 线路路径 ' + paths.length + ' 条, 车站 ' + stations.length + ' 座');
