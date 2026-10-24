/* =========================================================================
 * test_ui.js —— 用最小 DOM/Canvas 桩在 Node 中执行 js/app.js,
 * 检查前端逻辑(渲染、面板、交互)是否有运行时错误。
 * ========================================================================= */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..');
let fail = 0;
const ok = (c, m) => { if (!c) { console.log('  ✗ ' + m); fail++; } };
const wk = m => console.log('  · ' + m);

/* ---------------------------------------------------------------- Canvas 桩 */
const ctxCalls = {};
function makeCtx() {
  const rec = name => (...a) => { ctxCalls[name] = (ctxCalls[name] || 0) + 1; return undefined; };
  return {
    clearRect: rec('clearRect'), setTransform: rec('setTransform'), beginPath: rec('beginPath'),
    moveTo: rec('moveTo'), lineTo: rec('lineTo'), arc: rec('arc'), arcTo: rec('arcTo'),
    closePath: rec('closePath'), fill: rec('fill'), stroke: rec('stroke'),
    fillText: rec('fillText'), save: rec('save'), restore: rec('restore'),
    translate: rec('translate'), rotate: rec('rotate'), rect: rec('rect'),
    measureText: () => ({ width: 20 }),
    fillStyle: '', strokeStyle: '', lineWidth: 1, globalAlpha: 1, font: '',
    textBaseline: '', lineCap: '', lineJoin: ''
  };
}

/* ------------------------------------------------------------------ DOM 桩 */
const listeners = { window: {}, canvas: {}, slider: {} };
function makeEl(id, tag) {
  const el = {
    id: id || '', tagName: (tag || 'div').toUpperCase(),
    _html: '', textContent: '', value: '0', checked: false,
    style: {}, className: '', dataset: {},
    children: [],
    classList: {
      _s: new Set(),
      add(c) { this._s.add(c); }, remove(c) { this._s.delete(c); },
      toggle(c, on) { if (on === undefined) { this._s.has(c) ? this._s.delete(c) : this._s.add(c); } else if (on) this._s.add(c); else this._s.delete(c); },
      contains(c) { return this._s.has(c); }
    },
    get innerHTML() { return this._html; },
    set innerHTML(v) { this._html = String(v); },
    appendChild(c) { this.children.push(c); return c; },
    addEventListener(ev, fn) {
      const key = id === 'map' ? 'canvas' : (id === 'timeSlider' ? 'slider' : 'window');
      (listeners[key][ev] = listeners[key][ev] || []).push(fn);
    },
    removeEventListener() { },
    getBoundingClientRect() { return { left: 0, top: 0, width: 1180, height: 900 }; },
    querySelectorAll() { return []; },
    getAttribute(k) { const kk = String(k).replace(/^data-/, ''); return el.dataset[kk] !== undefined ? el.dataset[kk] : null; },
    setAttribute(k, v) { el.dataset[String(k).replace(/^data-/, '')] = v; },
    focus() { }
  };
  Object.defineProperty(el, 'clientWidth', { get: () => 1180 });
  Object.defineProperty(el, 'clientHeight', { get: () => 900 });
  if (id === 'map') el.getContext = () => el._ctx || (el._ctx = makeCtx());
  return el;
}

const els = {};
const IDS = ['map', 'clockTime', 'clockDate', 'liveFlag', 'statTrains', 'statLines', 'statNext',
  'legend', 'lineList', 'stationHint', 'stationBody', 'srcList', 'noteList', 'genInfo',
  'footRight', 'btnPlay', 'btnNow', 'timeSlider', 'chkLabels', 'chkTrails', 'timeMarks',
  'speedGroup', 'dayGroup', 'panelLines', 'panelStation', 'panelAbout', 'errbar', 'cityTabs'];
IDS.forEach(id => { els[id] = makeEl(id); });

/* tab / 按钮集合 */
function mkNodeList(arr) { return arr; }
const tabs = ['panelLines', 'panelStation', 'panelAbout'].map((p, i) => {
  const e = makeEl('tab' + i, 'button');
  e.dataset.tab = p;
  return e;
});
const speedBtns = [1, 60, 300, 900].map(s => {
  const e = makeEl('spd' + s, 'button');
  e.dataset.speed = String(s);
  return e;
});
const dayBtns = ['auto', 'mon_thu', 'fri', 'sat', 'sun'].map(d => {
  const e = makeEl('day' + d, 'button');
  e.dataset.day = d;
  return e;
});
const panels = tabs.map(t => els[t.dataset.tab]);

const document = {
  getElementById: id => els[id] || null,
  querySelectorAll: sel => {
    if (sel === '.tab') return tabs;
    if (sel === '.panel') return panels;
    if (sel === '.btn.spd') return speedBtns;
    if (sel === '.btn.day') return dayBtns;
    return [];
  },
  createElement: t => makeEl('', t),
  addEventListener: () => { },
  body: makeEl('body')
};

/* --------------------------------------------------------------- window 桩 */
let rafQueue = [];
const win = {
  document,
  devicePixelRatio: 1,
  performance: { now: () => Date.now() },
  requestAnimationFrame: fn => { rafQueue.push(fn); return rafQueue.length; },
  addEventListener: (ev, fn) => { (listeners.window[ev] = listeners.window[ev] || []).push(fn); },
  removeEventListener: () => { },
  Intl, Date, Math, JSON, console, Object, Array, String, Number, isFinite, Set, Map, parseFloat, parseInt
};
win.window = win;

/* ------------------------------------------------------------------- 执行 */
console.log('== 前端脚本加载 ==');
const sandbox = vm.createContext(win);
['data/metro-data.js', 'js/sim.js', 'js/app.js'].forEach(f => {
  const code = fs.readFileSync(path.join(ROOT, f), 'utf8');
  try {
    vm.runInContext(code, sandbox, { filename: f });
    wk(f + ' 载入成功 (' + (code.length / 1024).toFixed(1) + ' KB)');
  } catch (e) {
    ok(false, f + ' 载入失败: ' + e.message + '\n' + (e.stack || '').split('\n').slice(0, 3).join('\n'));
  }
});

const APP = win.__METRO_APP__;
ok(!!APP, '未暴露 __METRO_APP__ 调试入口');
if (!APP) { process.exit(1); }

console.log('== 首帧渲染 ==');
try {
  for (let i = 0; i < 3 && rafQueue.length; i++) {
    const fn = rafQueue.shift();
    fn(Date.now());
  }
  wk('requestAnimationFrame 回调执行正常');
} catch (e) {
  ok(false, '渲染循环抛错: ' + e.message + '\n' + (e.stack || '').split('\n').slice(0, 4).join('\n'));
}

ok((ctxCalls.stroke || 0) > 0, '未产生任何 stroke 调用(线路未绘制)');
ok((ctxCalls.arc || 0) > 100, '车站绘制数量偏少: arc=' + (ctxCalls.arc || 0));
wk('绘制调用: stroke=' + ctxCalls.stroke + ' arc=' + ctxCalls.arc + ' fillText=' + (ctxCalls.fillText || 0));

console.log('== 几何构建 ==');
ok(APP.geom.paths.length > 0, '未构建线路几何');
let totalPts = 0;
APP.geom.paths.forEach(g => { totalPts += g.pts.length; ok(g.pts.length >= 9, '路径点过少: ' + g.pts.length); });
wk('交路路径 ' + APP.geom.paths.length + ' 条, 采样点合计 ' + totalPts);
ok(Object.keys(APP.geom.stationPts).length > 300, '车站点位偏少: ' + Object.keys(APP.geom.stationPts).length);

console.log('== 面板内容 ==');
const t0 = APP.state.time;
APP.state.time = 8 * 3600;
APP.state.live = false;
APP.draw();
APP.updatePanels();
ok(els.lineList.innerHTML.indexOf('号线') >= 0, '线路列表未渲染');
ok(els.legend.innerHTML.indexOf('线路') >= 0, '图例未渲染');
ok(/^\d+$/.test(els.statTrains.textContent) && +els.statTrains.textContent > 100,
  '早高峰在线列车数异常: ' + els.statTrains.textContent);
wk('08:00 在线列车 ' + els.statTrains.textContent + ' 列, 运行线路 ' + els.statLines.textContent + ' 条');
wk('线路列表长度 ' + els.lineList.innerHTML.length + ' 字符');

console.log('== 车站面板 ==');
APP.state.selStation = '人民广场';
APP.updatePanels();
ok(els.stationBody.innerHTML.indexOf('人民广场') >= 0, '车站信息未渲染');
ok(els.stationBody.innerHTML.indexOf('到站时刻') >= 0, '到站表未渲染');
ok(els.statNext.textContent.indexOf('下一班') >= 0, '下一班摘要未渲染: ' + els.statNext.textContent);
wk(els.statNext.textContent);

console.log('== 交互: 点击车站 ==');
try {
  const p = APP.project(121.475108, 31.232687);   // 人民广场经纬度
  const click = (name, x, y) => {
    (listeners.canvas[name] || []).forEach(fn => fn({ clientX: x, clientY: y, preventDefault() { } }));
    (listeners.window[name] || []).forEach(fn => fn({ clientX: x, clientY: y }));
  };
  APP.state.selStation = null;
  click('mousedown', p[0], p[1]);
  click('mouseup', p[0], p[1]);
  ok(APP.state.selStation === '人民广场' || APP.state.selLine,
    '点击人民广场未选中任何对象 (selStation=' + APP.state.selStation + ', selLine=' + APP.state.selLine + ')');
  wk('点击命中: 车站=' + APP.state.selStation + ' 线路=' + APP.state.selLine);
} catch (e) {
  ok(false, '点击交互抛错: ' + e.message);
}

console.log('== 交互: 缩放与拖拽 ==');
try {
  (listeners.canvas.wheel || []).forEach(fn => fn({ deltaY: -240, clientX: 500, clientY: 400, preventDefault() { } }));
  const z1 = APP.state ? null : null;
  ok(APP.geom.paths.length > 0, '缩放后几何未重建');
  (listeners.canvas.mousedown || []).forEach(fn => fn({ clientX: 100, clientY: 100 }));
  (listeners.window.mousemove || []).forEach(fn => fn({ clientX: 160, clientY: 140 }));
  (listeners.window.mouseup || []).forEach(fn => fn({ clientX: 160, clientY: 140 }));
  wk('缩放/拖拽无异常');
} catch (e) {
  ok(false, '缩放/拖拽抛错: ' + e.message + '\n' + (e.stack || '').split('\n').slice(0, 3).join('\n'));
}

console.log('== 控件 ==');
try {
  els.btnPlay.onclick && els.btnPlay.onclick();
  speedBtns[2].onclick && speedBtns[2].onclick();
  dayBtns[2].onclick && dayBtns[2].onclick();      // 周五
  els.btnNow.onclick && els.btnNow.onclick();
  els.chkLabels.onchange && els.chkLabels.onchange({ target: { checked: true } });
  els.chkTrails.onchange && els.chkTrails.onchange({ target: { checked: false } });
  (listeners.window.resize || []).forEach(fn => fn({}));
  APP.state.live = false;
  APP.state.time = 8 * 3600;
  APP.draw();
  wk('按钮/复选框/窗口缩放均无异常, 当前速度=' + APP.state.speed + ' 日期类型=' + APP.state.dayOverride);
} catch (e) {
  ok(false, '控件交互抛错: ' + e.message + '\n' + (e.stack || '').split('\n').slice(0, 4).join('\n'));
}

console.log('== 各时段全量绘制(24 小时逐 15 分钟) ==');
try {
  let minT = 1e9, maxT = 0;
  for (let t = 0; t < 86400; t += 900) {
    APP.state.time = t;
    APP.draw();
  }
  wk('24 小时 × 96 个时刻绘制完成, 无异常');
} catch (e) {
  ok(false, '全时段绘制抛错: ' + e.message + '\n' + (e.stack || '').split('\n').slice(0, 4).join('\n'));
}

console.log('== 说明面板 ==');
ok(els.srcList.innerHTML.indexOf('http') >= 0, '数据来源未渲染');
ok(els.noteList.innerHTML.length > 20, '口径说明未渲染');
ok(els.footRight.textContent.indexOf('车站') >= 0, '页脚统计未渲染: ' + els.footRight.textContent);
wk(els.footRight.textContent);

console.log('== 城市切换 ==');
try {
  ok(els.cityTabs.innerHTML.indexOf('data-city') >= 0, '城市切换按钮未渲染');
  const before = els.footRight.textContent;
  const keys = ['suzhou', 'hangzhou', 'shanghai'];
  keys.forEach(k => {
    APP.state.live = false;
    APP.state.time = 8 * 3600;
    APP.useCity(k);
    APP.draw();
    const foot = els.footRight.textContent;
    ok(foot.length > 0 && foot.indexOf('车站') >= 0, k + ' 切换后页脚未更新');
    ok(els.lineList.innerHTML.length > 200, k + ' 切换后线路列表为空');
    ok(els.legend.innerHTML.indexOf('data-line') >= 0, k + ' 切换后图例为空');
    ok(els.statTrains.textContent !== '' && +els.statTrains.textContent > 0,
      k + ' 切换后在线列车为 0: ' + els.statTrains.textContent);
    wk(k.padEnd(14) + foot + ' → 08:00 在线 ' + els.statTrains.textContent + ' 列');
  });
  ok(els.footRight.textContent === before, '切回上海后页脚应与初始一致');
} catch (e) {
  ok(false, '城市切换抛错: ' + e.message + '\n' + (e.stack || '').split('\n').slice(0, 4).join('\n'));
}

console.log('== 每个城市全时段绘制 ==');
try {
  ['shanghai', 'suzhou', 'hangzhou'].forEach(k => {
    APP.useCity(k);
    APP.state.live = false;
    for (let t = 0; t < 86400; t += 3600) {
      APP.state.time = t;
      APP.draw();
    }
  });
  wk('3 个数据集 × 24 个时刻绘制完成, 无异常');
  APP.useCity('suzhou');
  ok(els.lineList.innerHTML.indexOf('有轨电车') >= 0, '苏州线路列表应包含有轨电车');
  ok(els.lineList.innerHTML.indexOf('高新有轨电车1号线') >= 0, '苏州应包含高新有轨电车1号线');
} catch (e) {
  ok(false, '全时段绘制抛错: ' + e.message + '\n' + (e.stack || '').split('\n').slice(0, 4).join('\n'));
}

console.log('== 样式表关键规则 ==');
{
  const css = fs.readFileSync(path.join(ROOT, 'css/style.css'), 'utf8');
  // 三个面板是 position:absolute 叠放的, 基础规则必须 display:none, 否则会互相覆盖
  ok(/\.panel\s*\{[^}]*display\s*:\s*none/.test(css),
    '.panel 缺少 display:none —— 三个面板会叠在一起, 侧栏文字错乱且标签失效');
  ok(/\.panel\.active\s*\{[^}]*display\s*:\s*block/.test(css), '.panel.active 需要 display:block');
  ok(/\.panels\s*\{[^}]*position\s*:\s*relative/.test(css), '.panels 需要 position:relative');
  ok(/\.layout\s*\{[^}]*grid-template-columns/.test(css), '.layout 需要 grid 布局');
  wk('面板显隐/定位规则正常');
}

console.log('\n===============================');
console.log(fail === 0 ? '✅ 前端脚本校验通过' : '❌ 失败 ' + fail + ' 项');
console.log('===============================');
process.exit(fail === 0 ? 0 : 1);
