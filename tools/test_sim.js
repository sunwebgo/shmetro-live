/* 无头校验: 在 Node 中加载 sim.js, 检查发车表/间隔/在线列车/到站推算的正确性 */
global.window = global;
require('../data/metro-data.js');
require('../js/sim.js');

const SIM = global.SIM;
const DATA = global.SHMETRO_DATA;
let fail = 0, warn = 0;
const ok = (c, m) => { if (!c) { console.log('  ✗ ' + m); fail++; } };
const wk = k => console.log('  · ' + k);

/* 构造某一天(以星期为准)的 Date */
function dateOf(dow) {
  // 2026-10-18 是周日
  const d = new Date(2026, 9, 18 + dow);
  return d;
}
const DAYS = { mon_thu: 1, fri: 5, sat: 6, sun: 0 };

console.log('== 1. 数据完整性 ==');
ok(DATA.lines.length === 21, '线路数应为 21, 实际 ' + DATA.lines.length);
let svcN = 0, stN = 0;
DATA.lines.forEach(L => {
  svcN += L.services.length;
  L.services.forEach(s => {
    ok(s.st.length >= 2, L.name + ' 站点数不足');
    ok(s.total > 0, L.name + ' 全程时间应 > 0');
    ok(s.off.length === s.st.length, L.name + ' off 长度应与站点数一致');
    for (let i = 1; i < s.off.length; i++) ok(s.off[i] >= s.off[i - 1], L.name + ' off 应单调不减');
    ok(s.fwd.first > 0 && s.fwd.last > s.fwd.first, L.name + ' 首末班车异常');
    ok(s.rev.first > 0 && s.rev.last > s.rev.first, L.name + ' 反向首末班车异常');
    stN += s.st.length;
  });
});
wk('交路 ' + svcN + ' 个, 站点记录 ' + stN + ' 条, 唯一车站 ' + Object.keys(SIM.stations()).length + ' 座');

console.log('== 2. 各线路发车间隔(与官方表比对) ==');
const expect = [
  ['1号线', 'mon_thu', 8 * 3600, 150, '工作日早高峰 2分30秒'],
  ['1号线', 'mon_thu', 12 * 3600, 300, '工作日平峰 5分'],
  ['1号线', 'sat', 12 * 3600, 240, '周六日高峰 4分'],
  ['2号线', 'mon_thu', 8 * 3600, 150, '工作日早高峰 2分30秒'],
  ['5号线', 'mon_thu', 8 * 3600, 225, '工作日早高峰 3分45秒(往奉贤新城)', '奉贤新城'],
  ['5号线', 'mon_thu', 8 * 3600, 450, '工作日早高峰 7分30秒(往闵行开发区)', '闵行开发区'],
  ['9号线', 'mon_thu', 8 * 3600, 180, '工作日早高峰 3分'],
  ['11号线', 'mon_thu', 8 * 3600, 330, '工作日早高峰 5分30秒'],
  ['12号线', 'mon_thu', 8 * 3600, 165, '工作日早高峰 2分45秒'],
  ['16号线', 'mon_thu', 8 * 3600, 210, '工作日早高峰 3分30秒'],
  ['浦江线', 'mon_thu', 8 * 3600, 255, '工作日早高峰 4分15秒'],
];
expect.forEach(([name, day, t, want, desc, dest]) => {
  const L = DATA.lines.find(x => x.name === name);
  if (!L) { ok(false, '找不到 ' + name); return; }
  const svc = dest ? L.services.find(s => s.to === dest) : L.services[0];
  if (!svc) { ok(false, name + ' 找不到交路 ' + dest); return; }
  const hw = SIM.headwayAt(svc.hw, day, t, svc.fwd.first, svc.fwd.last);
  ok(hw === want, name + ' @' + (t / 3600) + 'h 间隔应为 ' + want + 's(' + desc + '), 实际 ' + hw + 's');
});
wk(expect.length + ' 项间隔断言完成');

console.log('== 3. 发车表顺序与边界 ==');
Object.keys(DAYS).forEach(dk => {
  const date = dateOf(DAYS[dk]);
  let total = 0;
  DATA.lines.forEach(L => {
    L.services.forEach(svc => {
      ['fwd', 'rev'].forEach(dir => {
        const deps = SIM.getDepartures(svc, dir, dk, date);
        total += deps.length;
        ok(deps.length > 5, L.name + ' ' + dir + ' ' + dk + ' 发车数过少: ' + deps.length);
        ok(deps[0] === svc[dir].first, L.name + ' ' + dir + ' 首班车应等于官方值');
        const adj = (svc[dir].wd[date.getDay()] || 0) * 60;
        ok(deps[deps.length - 1] <= svc[dir].last + adj + 1,
          L.name + ' ' + dir + ' 末班车超出: ' + deps[deps.length - 1] + ' > ' + (svc[dir].last + adj));
        for (let i = 1; i < deps.length; i++) {
          if (!(deps[i] > deps[i - 1])) { ok(false, L.name + ' 发车时刻非递增'); break; }
        }
      });
    });
  });
  wk(dk + ' 单日全网发车 ' + total + ' 列次');
});

console.log('== 4. 周五/周六延时运营 ==');
{
  const fri = dateOf(5), sat = dateOf(6), mon = dateOf(1);
  ['1号线', '7号线', '8号线', '9号线', '10号线', '13号线'].forEach(nm => {
    const L = DATA.lines.find(x => x.name === nm);
    const svc = L.services[0];
    const df = SIM.getDepartures(svc, 'fwd', 'fri', fri);
    const dm = SIM.getDepartures(svc, 'fwd', 'mon_thu', mon);
    const lf = df[df.length - 1], lm = dm[dm.length - 1];
    ok(lf > lm + 20 * 60, nm + ' 周五末班车应明显晚于周一~周四 (' + SIM.hhmm(lf) + ' vs ' + SIM.hhmm(lm) + ')');
    wk(nm + ' 末班车 周一~周四 ' + SIM.hhmm(lm) + ' → 周五 ' + SIM.hhmm(lf) + ' / 周六 ' +
      SIM.hhmm(SIM.getDepartures(svc, 'fwd', 'sat', sat).slice(-1)[0]));
  });
}

console.log('== 5. 在线列车与位置 ==');
{
  let peak = 0, peakAt = 0, night = 0;
  [['mon_thu', 1], ['fri', 5], ['sat', 6], ['sun', 0]].forEach(([dk, dow]) => {
    const date = dateOf(dow);
    for (let t = 0; t < 86400; t += 300) {
      const list = SIM.trainsAt(t, dk, date, null);
      if (list.length > peak) { peak = list.length; peakAt = t; }
      list.forEach(tr => {
        const pos = SIM.pointAt(tr.svc, tr.dirKey, tr.progress);
        ok(isFinite(pos.i) && isFinite(pos.u), '位置计算出现 NaN');
        ok(pos.u >= -1e-9 && pos.u <= 1 + 1e-9, '段内比例越界 ' + pos.u);
        ok(tr.progress >= -1e-6 && tr.progress <= tr.svc.total + 1e-6, '运行进度越界');
      });
    }
  });
  wk('全网同时在线上限 ' + peak + ' 列 (发生于 ' + SIM.hhmm(peakAt) + ')');
  ok(peak > 200, '高峰同时在线的列车数偏少: ' + peak);
  ok(peak < 2000, '高峰同时在线的列车数异常偏多: ' + peak);

  // 各线路高峰在线数
  console.log('  各线路高峰在线列车数:');
  const date = dateOf(1);
  DATA.lines.forEach(L => {
    const st = SIM.lineStat(L, 8 * 3600, 'mon_thu', date);
    console.log('    ' + L.name.padEnd(8) + ' ' + String(st.trains).padStart(4) + ' 列  ' +
      '间隔 ' + (st.headwayMin === st.headwayMax ? st.headwayMin : st.headwayMin + '~' + st.headwayMax) + 's  ' +
      (st.running ? '运行中' : '停运'));
  });
}

console.log('== 6. 车站到站推算 ==');
{
  const date = dateOf(1);
  const t = 8 * 3600;
  ['人民广场', '徐家汇', '世纪大道', '虹桥火车站', '龙阳路', '莘庄', '临港大道'].forEach(nm => {
    const e = SIM.stationByName(nm);
    ok(!!e, '车站不存在: ' + nm);
    if (!e) return;
    const arrs = SIM.stationArrivals(nm, t, 'mon_thu', date, 3);
    ok(arrs.length > 0, nm + ' 早高峰无到站信息');
    if (arrs.length) {
      ok(arrs[0].arrive >= t - 30, nm + ' 首条到站时间早于当前时刻');
      for (let i = 1; i < arrs.length; i++) ok(arrs[i].arrive >= arrs[i - 1].arrive, nm + ' 到站未排序');
      wk(nm + ' (' + e.entries.length + ' 个站台) 下一班 ' + arrs[0].dirName + ' ' +
        SIM.hhmm(arrs[0].arrive) + ' 还有 ' + Math.round(arrs[0].wait) + 's 路=' + arrs[0].svc.from + '→' + arrs[0].svc.to);
    }
  });
}

console.log('== 7. 环线(4号线) ==');
{
  const L = DATA.lines.find(x => x.name === '4号线');
  const svc = L.services[0];
  ok(svc.loop === true, '4号线应标记为环线');
  ok(svc.st[0][0] === svc.st[svc.st.length - 1][0], '环线首末站应相同');
  ok(svc.dirNames[0] === '内圈' && svc.dirNames[1] === '外圈', '4号线方向名应为 内圈/外圈');
  const date = dateOf(1);
  const st = SIM.lineStat(L, 8 * 3600, 'mon_thu', date);
  wk('4号线 内圈 ' + st.svcInfo[0].onlineFwd + ' 列 / 外圈 ' + st.svcInfo[0].onlineRev + ' 列, 全程 ' +
    Math.round(svc.total / 60) + ' 分钟');
  ok(st.svcInfo[0].onlineFwd >= 10, '4号线内圈高峰在线列车偏少');
}

console.log('\n===============================');
console.log(fail === 0 ? '✅ 全部校验通过' : '❌ 失败 ' + fail + ' 项');
console.log('===============================');
process.exit(fail === 0 ? 0 : 1);
