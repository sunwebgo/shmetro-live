/* =========================================================================
 * test_sim.js —— 仿真内核无头校验 (多城市)
 * ========================================================================= */
global.window = global;
require('../data/metro-data.js');
require('../js/sim.js');

const SIM = global.SIM;
const CITIES = global.METRO_CITIES;
let fail = 0;
const ok = (c, m) => { if (!c) { console.log('  ✗ ' + m); fail++; } };
const wk = m => console.log('  · ' + m);

// 2026-10-18 是周日
const dateOf = dow => new Date(2026, 9, 18 + dow);

console.log('== 1. 城市列表 ==');
const list = SIM.cities();
ok(CITIES.meta.cityOrder.length >= 3, '城市数量应 ≥ 3, 实际 ' + CITIES.meta.cityOrder.length);
list.forEach(c => wk(`${c.key.padEnd(14)} ${c.name.padEnd(6)} ${c.lines} 条线路`));
['shanghai', 'suzhou', 'suzhou_tram', 'hangzhou'].forEach(k => {
  ok(!!CITIES.cities[k], '缺少城市数据: ' + k);
});

console.log('\n== 2. 各城市数据结构 ==');
for (const c of list) {
  SIM.useCity(c.key);
  const D = SIM.data;
  let svcN = 0;
  D.lines.forEach(L => {
    svcN += L.services.length;
    L.services.forEach(s => {
      ok(s.st.length >= 2, `${c.name} ${L.name} 站点数不足`);
      ok(s.total > 0, `${c.name} ${L.name} 全程时间应 > 0`);
      ok(s.off.length === s.st.length, `${c.name} ${L.name} off 长度与站点数不一致`);
      for (let i = 1; i < s.off.length; i++) ok(s.off[i] >= s.off[i - 1], `${c.name} ${L.name} off 非单调`);
      ok(!!D.headways[s.hw], `${c.name} ${L.name} 缺少间隔方案 ${s.hw}`);
      ok(s.fwd.first > 0 && s.fwd.last > s.fwd.first, `${c.name} ${L.name} 首末班车异常`);
    });
  });
  ok(svcN > 0, c.name + ' 没有交路');
  wk(`${c.name.padEnd(6)} 线路 ${String(D.lines.length).padStart(2)} · 交路 ${String(svcN).padStart(2)} · 车站 ${Object.keys(SIM.stations()).length}`);
}

console.log('\n== 3. 发车表(4 种日期类型) ==');
['mon_thu', 'fri', 'sat', 'sun'].forEach(dk => {
  const dow = { mon_thu: 1, fri: 5, sat: 6, sun: 0 }[dk];
  const date = dateOf(dow);
  let total = 0;
  list.forEach(c => {
    SIM.useCity(c.key);
    SIM.data.lines.forEach(L => L.services.forEach(svc => {
      ['fwd', 'rev'].forEach(dir => {
        const deps = SIM.getDepartures(svc, dir, dk, date);
        total += deps.length;
        ok(deps.length > 3, `${c.name} ${L.name} ${dir} ${dk} 发车数过少`);
        for (let i = 1; i < deps.length; i++) {
          if (!(deps[i] > deps[i - 1])) { ok(false, `${c.name} ${L.name} 发车时刻非递增`); break; }
        }
      });
    }));
  });
  wk(`${dk.padEnd(8)} 全网发车 ${total} 列次`);
});

console.log('\n== 4. 上海间隔回归(与官方表比对) ==');
SIM.useCity('shanghai');
[
  ['1号线', 'mon_thu', 8 * 3600, 150], ['1号线', 'mon_thu', 12 * 3600, 300],
  ['1号线', 'sat', 12 * 3600, 240], ['2号线', 'mon_thu', 8 * 3600, 150],
  ['9号线', 'mon_thu', 8 * 3600, 180], ['12号线', 'mon_thu', 8 * 3600, 165],
].forEach(([name, day, t, want]) => {
  const L = SIM.data.lines.find(x => x.name === name);
  const svc = L.services[0];
  const hw = SIM.headwayAt(svc.hw, day, t, svc.fwd.first, svc.fwd.last);
  ok(hw === want, `${name} @${t / 3600}h 间隔应为 ${want}s, 实际 ${hw}s`);
});

console.log('\n== 5. 苏州 周一至周四 / 周五至周日 两套班表 ==');
SIM.useCity('suzhou');
{
  const mon = dateOf(1), sat = dateOf(6);
  let diff = 0, checked = 0;
  SIM.data.lines.forEach(L => L.services.forEach(svc => {
    if (!svc.fwd.alt) return;
    checked++;
    const a = SIM.getDepartures(svc, 'fwd', 'mon_thu', mon);
    const b = SIM.getDepartures(svc, 'fwd', 'sat', sat);
    if (a[0] !== b[0] || a[a.length - 1] !== b[b.length - 1]) diff++;
  }));
  ok(checked > 0, '苏州应有带 alt 班表的线路');
  wk(`带周五至周日班表的线路 ${checked} 条, 其中首末班或班次不同的 ${diff} 条`);
  const L = SIM.data.lines.find(x => x.name === '1号线');
  const svc = L.services[0];
  const dm = SIM.getDepartures(svc, 'fwd', 'mon_thu', mon);
  const ds = SIM.getDepartures(svc, 'fwd', 'sat', sat);
  wk(`1号线 首班 周一 ${SIM.hhmm(dm[0])} / 周六 ${SIM.hhmm(ds[0])}; 末班 周一 ${SIM.hhmm(dm[dm.length - 1])} / 周六 ${SIM.hhmm(ds[ds.length - 1])}`);
  ok(dm[0] === svc.fwd.first, '苏州1号线周一首班应等于官方值');
  ok(ds[0] === (svc.fwd.alt ? svc.fwd.alt.first : svc.fwd.first), '苏州1号线周六首班应等于周五至周日班表');
}

console.log('\n== 6. 高峰在线列车 ==');
for (const c of list) {
  SIM.useCity(c.key);
  const date = dateOf(1);
  let peak = 0, peakAt = 0;
  for (let t = 6 * 3600; t <= 20 * 3600; t += 300) {
    const n = SIM.trainsAt(t, 'mon_thu', date, null).length;
    if (n > peak) { peak = n; peakAt = t; }
  }
  ok(peak > 5, `${c.name} 高峰在线列车过少: ${peak}`);
  wk(`${c.name.padEnd(6)} 高峰 ${String(peak).padStart(4)} 列 @ ${SIM.hhmm(peakAt)}`);
}

console.log('\n== 7. 位置与 NaN 检查 ==');
{
  let bad = 0, n = 0;
  for (const c of list) {
    SIM.useCity(c.key);
    const date = dateOf(1);
    for (let t = 0; t < 86400; t += 1800) {
      SIM.trainsAt(t, 'mon_thu', date, null).forEach(tr => {
        const p = SIM.pointAt(tr.svc, tr.dirKey, tr.progress);
        n++;
        if (!isFinite(p.i) || !isFinite(p.u) || p.u < -1e-9 || p.u > 1 + 1e-9) bad++;
      });
    }
  }
  ok(bad === 0, `位置计算异常 ${bad} 处 / 共 ${n} 次`);
  wk(`三城 48 个时刻共 ${n} 次位置计算, 异常 ${bad}`);
}

console.log('\n== 8. 车站到站推算 ==');
{
  const cases = [
    ['shanghai', '人民广场'], ['shanghai', '徐家汇'],
    ['suzhou', '东方之门'], ['suzhou', '狮子山'],
    ['hangzhou', '武林广场'], ['hangzhou', '龙翔桥'],
    ['suzhou_tram', '苏州乐园'],
  ];
  cases.forEach(([city, st]) => {
    SIM.useCity(city);
    const e = SIM.stationByName(st);
    if (!e) { ok(false, `${city} 找不到车站 ${st}`); return; }
    const arrs = SIM.stationArrivals(st, 8 * 3600, 'mon_thu', dateOf(1), 3);
    ok(arrs.length > 0, `${city} ${st} 无到站信息`);
    if (arrs.length) {
      for (let i = 1; i < arrs.length; i++) ok(arrs[i].arrive >= arrs[i - 1].arrive, `${city} ${st} 到站未排序`);
      wk(`${city.padEnd(12)} ${st.padEnd(6)} 下一班 ${arrs[0].dirName} ${SIM.hhmm(arrs[0].arrive)} (${Math.round(arrs[0].wait)}s)`);
    }
  });
}

console.log('\n===============================');
console.log(fail === 0 ? '✅ 全部校验通过' : `❌ 失败 ${fail} 项`);
console.log('===============================');
process.exit(fail === 0 ? 0 : 1);
