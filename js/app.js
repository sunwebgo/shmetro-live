/* =========================================================================
 * app.js —— Canvas 2D 动态城市轨道线路图 (上海 / 苏州 / 杭州)
 * ========================================================================= */
(function () {
  'use strict';

  var CITIES = window.METRO_CITIES;
  if (!CITIES || !CITIES.cities) {
    document.body.innerHTML = '<p style="padding:30px;color:#f66">缺少 data/metro-data.js, 请先运行 tools/build_data.py</p>';
    return;
  }
  var DATA = CITIES.cities[CITIES.meta.cityOrder[0]];

  var TZ = 'Asia/Shanghai';
  var SAMPLES = 8;               // 每段曲线的采样点数
  var DPR = Math.min(2, window.devicePixelRatio || 1);

  var canvas = document.getElementById('map');
  var ctx = canvas.getContext('2d');

  /* ------------------------------------------------------- 线路显示色调整 */
  // 浅色主题下, 官方色里的浅色(3号线黄/16号线浅绿等)在白底上过淡, 按亮度适当加深;
  // 列车用同色系的更深色, 避免白色描边把线路切成虚线段。结果按线路缓存。
  function hexToRgb(h) {
    h = (h || '#888888').replace('#', '');
    if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
    return [parseInt(h.substr(0, 2), 16), parseInt(h.substr(2, 2), 16), parseInt(h.substr(4, 2), 16)];
  }
  function shadeHex(hex, f) {
    if (f === 1) return hex;
    var c = hexToRgb(hex);
    return 'rgb(' + c.map(function (v) { return Math.round(v * f); }).join(',') + ')';
  }
  function lumFactor(hex) {
    var c = hexToRgb(hex);
    var lum = 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2];
    return lum > 205 ? 0.68 : (lum > 180 ? 0.80 : (lum > 160 ? 0.90 : 1));
  }
  function dispColorOf(hex) { return shadeHex(hex, lumFactor(hex)); }
  function dispColor(line) {
    if (!line._dc) { line._dc = dispColorOf(line.color); line._lf = lumFactor(line.color); }
    return line._dc;
  }
  function trainColor(line) {
    if (!line._tc) {
      dispColor(line);
      line._tc = shadeHex(line.color, line._lf * 0.62);
    }
    return line._tc;
  }

  /* ==================================================================== 状态 */
  var state = {
    time: 6 * 3600,          // 当前推演时刻(秒)
    live: true,              // 是否跟随真实时间
    playing: true,
    speed: 60,
    dayOverride: 'auto',
    date: new Date(),        // 运行日期(用于确定星期)
    selLine: null,
    selStation: null,
    hoverStation: null,
    showLabels: false,
    showDir: true,
    hidden: {},              // 隐藏的线路
    lastReal: performance.now()
  };

  /* ================================================================ 几何/投影 */
  var view = { z: 1, tx: 0, ty: 0 };
  var proj = { k: 1, cx: 0, cy: 0, lng0: 0, lat0: 0 };
  var geom = { key: '', paths: [], stationPts: {}, bounds: null };

  function computeBounds() {
    var b = { x0: 1e9, x1: -1e9, y0: 1e9, y1: -1e9 };
    DATA.lines.forEach(function (L) {
      L.services.forEach(function (s) {
        s.st.forEach(function (p) {
          if (p[1] < b.x0) b.x0 = p[1];
          if (p[1] > b.x1) b.x1 = p[1];
          if (p[2] < b.y0) b.y0 = p[2];
          if (p[2] > b.y1) b.y1 = p[2];
        });
      });
    });
    return b;
  }

  function setupProjection() {
    var b = computeBounds();
    geom.bounds = b;
    proj.lat0 = (b.y0 + b.y1) / 2;
    proj.lng0 = (b.x0 + b.x1) / 2;
    proj.cx = 0; proj.cy = 0;
    var w = canvas.clientWidth, h = canvas.clientHeight;
    var cosL = Math.cos(proj.lat0 * Math.PI / 180);
    var wW = (b.x1 - b.x0) * cosL;
    var wH = (b.y1 - b.y0);
    proj.k = Math.min(w / Math.max(1e-6, wW), h / Math.max(1e-6, wH)) * 0.9;
    view.z = 1; view.tx = 0; view.ty = 0;
  }

  /** 经纬度 -> 画布坐标 */
  function project(lng, lat) {
    var cosL = Math.cos(proj.lat0 * Math.PI / 180);
    var wx = (lng - proj.lng0) * cosL;
    var wy = (lat - proj.lat0);
    var x = canvas.clientWidth / 2 + wx * proj.k * view.z + view.tx;
    var y = canvas.clientHeight / 2 - wy * proj.k * view.z + view.ty;
    return [x, y];
  }
  function unproject(x, y) {
    var cosL = Math.cos(proj.lat0 * Math.PI / 180);
    var wx = (x - canvas.clientWidth / 2 - view.tx) / (proj.k * view.z);
    var wy = -(y - canvas.clientHeight / 2 - view.ty) / (proj.k * view.z);
    return { lng: proj.lng0 + wx / cosL, lat: proj.lat0 + wy };
  }

  function crPoint(p0, p1, p2, p3, t) {
    var t2 = t * t, t3 = t2 * t;
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3);
  }

  /** 建立(并缓存)每条交路在屏幕坐标下的平滑折线 */
  function rebuildGeometry() {
    var key = view.z.toFixed(4) + ',' + view.tx.toFixed(1) + ',' + view.ty.toFixed(1) + ',' +
      canvas.clientWidth + 'x' + canvas.clientHeight;
    if (geom.key === key) return;
    geom.key = key;

    geom.paths = [];
    DATA.lines.forEach(function (L) {
      L.services.forEach(function (s) {
        var pts = s.st, m = pts.length;
        var loop = !!s.loop;
        function at(j) {
          if (loop) { var mm = m - 1; return pts[((j % mm) + mm) % mm]; }
          return pts[Math.max(0, Math.min(m - 1, j))];
        }
        var line = [];
        for (var i = 0; i < m - 1; i++) {
          var p0 = at(i - 1), p1 = at(i), p2 = at(i + 1), p3 = at(i + 2);
          for (var j = 0; j < SAMPLES; j++) {
            var u = j / SAMPLES;
            var lng = crPoint(p0[1], p1[1], p2[1], p3[1], u);
            var lat = crPoint(p0[2], p1[2], p2[2], p3[2], u);
            line.push(project(lng, lat));
          }
        }
        var lastP = pts[m - 1];
        line.push(project(lastP[1], lastP[2]));
        geom.paths.push({ svc: s, line: s.name, color: L.color, dc: dispColor(L), pts: line, loop: loop });
      });
    });

    geom.stationPts = {};
    var idx = SIM.stations();
    for (var nm in idx) {
      var e = idx[nm];
      var seen = {}, cnt = 0;
      e.entries.forEach(function (en) { if (!seen[en.line.name]) { seen[en.line.name] = 1; cnt++; } });
      geom.stationPts[nm] = { p: project(e.x, e.y), lines: cnt, entries: e.entries };
    }
  }

  /* ==================================================================== 绘制 */
  function resize() {
    var w = canvas.clientWidth, h = canvas.clientHeight;
    canvas.width = Math.round(w * DPR);
    canvas.height = Math.round(h * DPR);
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    geom.key = '';
  }

  function draw() {
    var w = canvas.clientWidth, h = canvas.clientHeight;
    ctx.clearRect(0, 0, w, h);
    rebuildGeometry();

    var dayKey = SIM.dayKeyOf(state.date, state.dayOverride);
    var trains = SIM.trainsAt(state.time, dayKey, state.date, null);

    // ---- 线路 ----
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    // ---- 线路 ----
    geom.paths.forEach(function (g) {
      if (state.hidden[g.line]) return;
      var dim = state.selLine && state.selLine !== g.line;
      var selected = state.selLine === g.line;
      ctx.globalAlpha = dim ? 0.16 : 0.95;
      ctx.strokeStyle = g.dc;
      ctx.lineWidth = selected ? 5.2 : 3.8;
      ctx.beginPath();
      var pts = g.pts;
      ctx.moveTo(pts[0][0], pts[0][1]);
      for (var i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
      ctx.stroke();
    });
    ctx.globalAlpha = 1;

    // ---- 车站 ----
    var selName = state.selStation;
    for (var nm in geom.stationPts) {
      var sp = geom.stationPts[nm];
      var hidden = true;
      sp.entries.forEach(function (en) { if (!state.hidden[en.line.name]) hidden = false; });
      if (hidden) continue;
      var isSel = nm === selName, isHov = nm === state.hoverStation;
      var multi = sp.lines > 1;
      // 单线站不画点: 线路本身即表示走线, 画点会把线切成虚线段;
      // 只在换乘站 / 悬停 / 选中时绘制标记。
      if (!multi && !isSel && !isHov) continue;
      var r = 3.2;
      if (isSel || isHov) r += 1.6;
      ctx.beginPath();
      ctx.arc(sp.p[0], sp.p[1], r, 0, Math.PI * 2);
      ctx.fillStyle = '#ffffff';
      ctx.fill();
      ctx.lineWidth = (isSel || isHov) ? 2.0 : 1.7;
      ctx.strokeStyle = (isSel || isHov) ? '#2563eb' : '#3f5872';
      ctx.stroke();
    }

    // ---- 站名 ----
    if (state.showLabels || view.z > 2.4) {
      ctx.font = '10px "Microsoft YaHei",sans-serif';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = 'rgba(30,45,66,.80)';
      for (var nm2 in geom.stationPts) {
        var sp2 = geom.stationPts[nm2];
        if (sp2.lines < 2 && view.z < 3) continue;
        if (isOffscreen(sp2.p)) continue;
        ctx.fillText(nm2, sp2.p[0] + 5, sp2.p[1] - 5);
      }
    }

    // ---- 列车 ----
    var drawn = 0;
    for (var t = 0; t < trains.length; t++) {
      var tr = trains[t];
      if (state.hidden[tr.line.name]) continue;
      var g = null;
      for (var q = 0; q < geom.paths.length; q++) if (geom.paths[q].svc === tr.svc) { g = geom.paths[q]; break; }
      if (!g) continue;
      var pos = SIM.pointAt(tr.svc, tr.dirKey, tr.progress);
      var li = pos.i * SAMPLES + Math.round(pos.u * SAMPLES);
      if (li < 0) li = 0;
      if (li > g.pts.length - 1) li = g.pts.length - 1;
      var p = g.pts[li];
      var pn = g.pts[Math.min(g.pts.length - 1, li + 1)] || g.pts[li - 1] || p;
      var ang = Math.atan2(pn[1] - p[1], pn[0] - p[0]);
      if (tr.dirKey === 'rev') ang += Math.PI;
      if (isOffscreen(p)) continue;

      var dim2 = state.selLine && state.selLine !== tr.line.name;
      ctx.save();
      ctx.translate(p[0], p[1]);
      ctx.rotate(ang);
      ctx.globalAlpha = dim2 ? 0.22 : 1;
      // 白色车厢 + 线路色描边: 线路保持连续, 列车又能清楚看到
      var len = 8.4, wid = 5.2;
      ctx.beginPath();
      roundRect(-len / 2, -wid / 2 + 0.7, len - 1.4, wid - 1.4, 2.0);
      ctx.fillStyle = '#ffffff';
      ctx.fill();
      ctx.lineWidth = 1.3;
      ctx.strokeStyle = dim2 ? '#c3cedb' : trainColor(tr.line);
      ctx.stroke();
      if (state.showDir) {
        ctx.beginPath();
        ctx.moveTo(len / 2 - 1.1, 0);
        ctx.lineTo(len / 2 - 3.4, -wid / 2 + 1.5);
        ctx.lineTo(len / 2 - 3.4, wid / 2 - 1.5);
        ctx.closePath();
        ctx.fillStyle = dim2 ? '#d5dee8' : trainColor(tr.line);
        ctx.fill();
      }
      ctx.restore();
      drawn++;
    }
    ctx.globalAlpha = 1;

    // ---- 数量 / 时间显示 ----
    document.getElementById('statTrains').textContent = drawn;
    var runningLines = 0;
    DATA.lines.forEach(function (L) {
      var s = SIM.lineStat(L, state.time, dayKey, state.date);
      if (s.running) runningLines++;
    });
    document.getElementById('statLines').textContent = runningLines;

    // ---- 非运营时段提示 ----
    var nb = document.getElementById('nightbar');
    if (nb) {
      if (drawn === 0) {
        nb.style.display = 'block';
        var next = nextServiceStart(dayKey);
        nb.textContent = '当前时刻全线无列车运行（' + SIM.hhmm(state.time) + '）。' +
          (next ? '最近一班首班车约 ' + SIM.hhmm(next) + '，' : '') + '可拖动时间轴查看早高峰运行情况。';
      } else nb.style.display = 'none';
    }
  }

  /** 全网下一个首班车时刻(按 5 分钟步进粗查, 结果按 10 分钟粒度缓存) */
  var _nextSvc = { key: '', val: null };
  function nextServiceStart(dayKey) {
    var key = dayKey + '|' + Math.floor(state.time / 600);
    if (_nextSvc.key === key) return _nextSvc.val;
    var found = null;
    for (var d = 0; d < 120; d++) {
      var t = state.time + d * 300;
      var dk = dayKey;
      if (t >= 86400) { t -= 86400; dk = 'mon_thu'; }
      if (SIM.trainsAt(t, dk, state.date, null).length > 0) { found = t; break; }
    }
    _nextSvc.key = key; _nextSvc.val = found;
    return found;
  }

  function isOffscreen(p) {
    return p[0] < -40 || p[1] < -40 || p[0] > canvas.clientWidth + 40 || p[1] > canvas.clientHeight + 40;
  }

  function roundRect(x, y, w, h, r) {
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  /* =============================================================== 时间推进 */
  function shanghaiNow() {
    try {
      var f = new Intl.DateTimeFormat('en-GB', {
        timeZone: TZ, hour12: false,
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', second: '2-digit'
      });
      var o = {};
      f.formatToParts(new Date()).forEach(function (p) { o[p.type] = p.value; });
      var d = new Date(+o.year, +o.month - 1, +o.day, +o.hour % 24, +o.minute, +o.second);
      return { date: d, sec: (+o.hour % 24) * 3600 + (+o.minute) * 60 + (+o.second) };
    } catch (e) {
      var n = new Date();
      return { date: n, sec: n.getHours() * 3600 + n.getMinutes() * 60 + n.getSeconds() };
    }
  }

  function tick() {
    var now = performance.now();
    var dt = (now - state.lastReal) / 1000;
    state.lastReal = now;

    if (state.live) {
      var s = shanghaiNow();
      state.date = s.date;
      state.time = s.sec;
    } else if (state.playing) {
      state.time += dt * state.speed;
      if (state.time >= 86400) state.time -= 86400;
      if (state.time < 0) state.time += 86400;
    }

    updateClock();
    if (!state.live) {
      var sl = document.getElementById('timeSlider');
      if (document.activeElement !== sl) sl.value = Math.round(state.time) % 86400;
    }
    draw();
    requestAnimationFrame(tick);
  }

  var lastPanel = 0;
  function updateClock() {
    var sec = state.live ? shanghaiNow().sec : state.time;
    document.getElementById('clockTime').textContent = SIM.hhmmss(sec);
    var d = state.date;
    var wd = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][d.getDay()];
    document.getElementById('clockDate').textContent =
      d.getFullYear() + '-' + SIM.pad2(d.getMonth() + 1) + '-' + SIM.pad2(d.getDate()) + ' ' + wd;
    var flag = document.getElementById('liveFlag');
    flag.textContent = state.live ? '实时' : (state.playing ? '推演 ' + state.speed + '×' : '推演 暂停');
    flag.className = 'liveflag' + (state.live ? '' : ' sim');

    var now = performance.now();
    if (now - lastPanel > 260) { lastPanel = now; updatePanels(); }
  }

  /* ==================================================================== 面板 */
  function updatePanels() {
    var dayKey = SIM.dayKeyOf(state.date, state.dayOverride);
    renderLineList(dayKey);
    renderLegend(dayKey);
    renderStation(dayKey);
  }

  function renderLegend(dayKey) {
    var el = document.getElementById('legend');
    var html = '<h4>线路（点击显隐）</h4>';
    DATA.lines.forEach(function (L) {
      var st = SIM.lineStat(L, state.time, dayKey, state.date);
      html += '<div class="row' + (state.hidden[L.name] ? ' off' : '') + '" data-line="' + esc(L.name) + '">' +
        '<span class="sw" style="background:' + dispColor(L) + '"></span>' +
        '<span>' + esc(L.name) + '</span>' +
        '<span class="cnt">' + (st.running ? st.trains + '列' : '—') + '</span></div>';
    });
    el.innerHTML = html;
    Array.prototype.forEach.call(el.querySelectorAll('.row'), function (r) {
      r.onclick = function () {
        var n = r.getAttribute('data-line');
        state.hidden[n] = !state.hidden[n];
        geom.key = '';
        renderLegend(dayKey);
      };
    });
  }

  function renderLineList(dayKey) {
    var box = document.getElementById('lineList');
    var html = '';
    DATA.lines.forEach(function (L) {
      var st = SIM.lineStat(L, state.time, dayKey, state.date);
      var hwTxt = st.running
        ? (st.headwayMin === st.headwayMax ? fmtHw(st.headwayMin) : fmtHw(st.headwayMin) + '~' + fmtHw(st.headwayMax))
        : '非运营时段';
      html += '<div class="lrow' + (state.selLine === L.name ? ' sel' : '') + '" data-line="' + esc(L.name) + '">';
      html += '<div class="h"><span class="badge" style="background:' + dispColor(L) + '">' + esc(L.name.replace('号线', '')) + '</span>';
      html += '<span class="nm">' + esc(L.name) + '</span>';
      html += '<span class="cnt">' + (st.running ? st.trains + ' 列在线' : '停运') + '</span></div>';
      html += '<div class="meta"><span><i>当前间隔</i> ' + hwTxt + '</span>' +
        '<span><i>在线</i> 上行 ' + totalOf(st, 'fwd') + ' / 下行 ' + totalOf(st, 'rev') + '</span></div>';
      st.svcInfo.forEach(function (si) {
        html += '<div class="svc"><div><span>' + esc(svcLabel(si.svc)) + '</span>' +
          '<span>' + SIM.hhmm(si.fwd.first) + '~' + SIM.hhmm(si.fwd.last) + ' / ' +
          SIM.hhmm(si.rev.first) + '~' + SIM.hhmm(si.rev.last) + '</span></div>' +
          '<div><span>' + esc(si.svc.dirNames[0]) + ' ' + si.onlineFwd + '列 · ' +
          esc(si.svc.dirNames[1]) + ' ' + si.onlineRev + '列</span>' +
          '<span>全程约 ' + Math.round(si.svc.total / 60) + ' 分</span></div></div>';
      });
      html += '</div>';
    });
    box.innerHTML = html;
    Array.prototype.forEach.call(box.querySelectorAll('.lrow'), function (r) {
      r.onclick = function () {
        var n = r.getAttribute('data-line');
        state.selLine = (state.selLine === n) ? null : n;
        renderLineList(dayKey); renderLegend(dayKey);
      };
    });
  }

  function totalOf(st, dirKey) {
    var t = 0;
    st.svcInfo.forEach(function (si) { t += si[dirKey].online; });
    return t;
  }

  function svcLabel(svc) {
    if (svc.loop) return svc.name + ' 环线';
    return svc.from + ' ↔ ' + svc.to;
  }

  function fmtHw(sec) {
    if (!sec) return '—';
    var m = Math.floor(sec / 60), s = Math.round(sec % 60);
    return m + '分' + (s ? s + '秒' : '');
  }

  function renderStation(dayKey) {
    var body = document.getElementById('stationBody');
    var hint = document.getElementById('stationHint');
    if (!state.selStation) {
      hint.textContent = '在地图上点击任意车站，查看该站各线路两个方向的下一班列车。';
      body.innerHTML = '';
      document.getElementById('statNext').textContent = '未选择车站';
      return;
    }
    var e = SIM.stationByName(state.selStation);
    if (!e) { body.innerHTML = '<div class="empty">未找到车站</div>'; return; }
    hint.textContent = '点击地图空白处可取消选择。';

    var arrs = SIM.stationArrivals(state.selStation, state.time, dayKey, state.date, 4);
    var lineset = {};
    e.entries.forEach(function (en) { lineset[en.line.name] = en.line; });

    var html = '<div class="sthead"><div class="t">' + esc(state.selStation) + '</div>' +
      '<div class="s">经停线路：' + Object.keys(lineset).join('、') + '</div></div>';

    if (!arrs.length) {
      html += '<div class="empty">当前时刻该站无列车运行（可能处于运营时段之外）</div>';
    } else {
      var groups = {};
      arrs.forEach(function (a) { (groups[a.line.name] = groups[a.line.name] || []).push(a); });
      Object.keys(groups).forEach(function (ln) {
        var L = lineset[ln];
        html += '<div class="arrgrp"><div class="gt"><span class="badge" style="background:' + dispColor(L) + '">' +
          esc(ln.replace('号线', '')) + '</span>' + esc(ln) + '</div>';
        html += '<table class="arrtbl"><thead><tr><th>方向</th><th>列车</th><th>到站时刻</th><th>还有</th></tr></thead><tbody>';
        groups[ln].forEach(function (a, i) {
          html += '<tr class="' + (i === 0 ? 'next' : '') + '">' +
            '<td>' + esc(a.dirName) + (a.isTerminus ? ' <span class="tag">终到</span>' : '') + '</td>' +
            '<td>' + esc(svcLabel(a.svc)) + '</td>' +
            '<td>' + SIM.hhmmss(a.arrive) + '</td>' +
            '<td>' + waitTxt(a.wait) + '</td></tr>';
        });
        html += '</tbody></table></div>';
      });
    }
    body.innerHTML = html;

    var first = arrs[0];
    document.getElementById('statNext').textContent = first
      ? state.selStation + '：下一班 ' + first.dirName + ' ' + SIM.hhmm(first.arrive) + '（' + waitTxt(first.wait) + '）'
      : state.selStation + '：当前无列车';
  }

  function waitTxt(sec) {
    if (sec < 0) return '已到站';
    if (sec < 60) return Math.round(sec) + ' 秒';
    var m = Math.floor(sec / 60), s = Math.round(sec % 60);
    return m + ' 分' + (s ? s + ' 秒' : '');
  }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  /* ==================================================================== 交互 */
  var drag = null;

  canvas.addEventListener('mousedown', function (ev) {
    drag = { x: ev.clientX, y: ev.clientY, tx: view.tx, ty: view.ty, moved: 0 };
    canvas.classList.add('dragging');
  });
  window.addEventListener('mousemove', function (ev) {
    if (drag) {
      var dx = ev.clientX - drag.x, dy = ev.clientY - drag.y;
      drag.moved = Math.max(drag.moved, Math.abs(dx) + Math.abs(dy));
      view.tx = drag.tx + dx; view.ty = drag.ty + dy;
      geom.key = '';
      return;
    }
    var rect = canvas.getBoundingClientRect();
    var hit = hitStation(ev.clientX - rect.left, ev.clientY - rect.top);
    if ((hit && hit.name) !== (state.hoverStation && state.hoverStation)) {
      state.hoverStation = hit ? hit.name : null;
      canvas.style.cursor = hit ? 'pointer' : 'grab';
    }
  });
  window.addEventListener('mouseup', function (ev) {
    canvas.classList.remove('dragging');
    if (drag && drag.moved < 5) {
      var rect = canvas.getBoundingClientRect();
      var x = ev.clientX - rect.left, y = ev.clientY - rect.top;
      var hit = hitStation(x, y);
      if (hit) { state.selStation = hit.name; switchTab('panelStation'); }
      else {
        var ln = hitLine(x, y);
        if (ln) { state.selLine = (state.selLine === ln) ? null : ln; }
        else { state.selStation = null; state.selLine = null; }
      }
      renderLegend(SIM.dayKeyOf(state.date, state.dayOverride));
      renderLineList(SIM.dayKeyOf(state.date, state.dayOverride));
    }
    drag = null;
  });

  canvas.addEventListener('wheel', function (ev) {
    ev.preventDefault();
    var rect = canvas.getBoundingClientRect();
    var mx = ev.clientX - rect.left, my = ev.clientY - rect.top;
    var before = unproject(mx, my);
    var f = Math.exp(-ev.deltaY * 0.0016);
    view.z = Math.max(0.6, Math.min(14, view.z * f));
    geom.key = '';
    // 让缩放围绕鼠标位置
    var b = computeBounds();
    var cosL = Math.cos(proj.lat0 * Math.PI / 180);
    var wx = (before.lng - proj.lng0) * cosL, wy = (before.lat - proj.lat0);
    var nx = canvas.clientWidth / 2 + wx * proj.k * view.z + view.tx;
    var ny = canvas.clientHeight / 2 - wy * proj.k * view.z + view.ty;
    view.tx += mx - nx; view.ty += my - ny;
  }, { passive: false });

  function hitStation(x, y) {
    var best = null, bd = 13 * 13;
    for (var nm in geom.stationPts) {
      var sp = geom.stationPts[nm];
      if (state.hidden[sp.entries[0].line.name]) continue;
      var dx = sp.p[0] - x, dy = sp.p[1] - y, d = dx * dx + dy * dy;
      if (d < bd) { bd = d; best = sp; best.name = nm; }
    }
    return best;
  }

  function hitLine(x, y) {
    var best = null, bd = 8 * 8;
    geom.paths.forEach(function (g) {
      if (state.hidden[g.line]) return;
      var pts = g.pts;
      for (var i = 0; i < pts.length; i += 2) {
        var dx = pts[i][0] - x, dy = pts[i][1] - y, d = dx * dx + dy * dy;
        if (d < bd) { bd = d; best = g.line; }
      }
    });
    return best;
  }

  /* ==================================================================== 控件 */
  function switchTab(id) {
    Array.prototype.forEach.call(document.querySelectorAll('.tab'), function (t) {
      t.classList.toggle('active', t.getAttribute('data-tab') === id);
    });
    Array.prototype.forEach.call(document.querySelectorAll('.panel'), function (p) {
      p.classList.toggle('active', p.id === id);
    });
  }
  Array.prototype.forEach.call(document.querySelectorAll('.tab'), function (t) {
    t.onclick = function () { switchTab(t.getAttribute('data-tab')); };
  });

  var btnPlay = document.getElementById('btnPlay');
  btnPlay.onclick = function () {
    if (state.live) { state.live = false; state.playing = true; }
    else state.playing = !state.playing;
    btnPlay.textContent = state.playing ? '⏸ 暂停' : '▶ 播放';
  };

  document.getElementById('btnNow').onclick = function () {
    state.live = true;
    state.playing = true;
    btnPlay.textContent = '⏸ 暂停';
    setActive('.spd', null);
  };

  Array.prototype.forEach.call(document.querySelectorAll('.btn.spd'), function (b) {
    b.onclick = function () {
      state.speed = +b.getAttribute('data-speed');
      state.live = false;
      state.playing = true;
      btnPlay.textContent = '⏸ 暂停';
      setActive('.spd', b);
    };
  });

  Array.prototype.forEach.call(document.querySelectorAll('.btn.day'), function (b) {
    b.onclick = function () {
      state.dayOverride = b.getAttribute('data-day');
      if (state.dayOverride !== 'auto') {
        // 让"运行日期"按所选星期类型对齐, 便于查看周五/周六延时运营
        var want = { mon_thu: 1, fri: 5, sat: 6, sun: 0 }[state.dayOverride];
        var d = new Date(state.date.getTime());
        var delta = (want - d.getDay() + 7) % 7;
        d.setDate(d.getDate() + delta);
        state.date = d;
      }
      setActive('.day', b);
      geom.key = '';
      updatePanels();
    };
  });

  function setActive(sel, el) {
    Array.prototype.forEach.call(document.querySelectorAll(sel), function (x) {
      x.classList.toggle('active', x === el);
    });
  }

  var slider = document.getElementById('timeSlider');
  slider.addEventListener('input', function () {
    state.live = false;
    state.playing = false;
    btnPlay.textContent = '▶ 播放';
    state.time = +slider.value;
  });

  document.getElementById('chkLabels').onchange = function (e) { state.showLabels = e.target.checked; };
  document.getElementById('chkTrails').onchange = function (e) { state.showDir = e.target.checked; };

  /* ================================================================ 时间刻度 */
  (function () {
    var el = document.getElementById('timeMarks');
    var h = [];
    for (var i = 0; i <= 24; i += 3) h.push('<span>' + SIM.pad2(i % 24) + ':00</span>');
    el.innerHTML = h.join('');
  })();

  /* ================================================================== 说明 */
  function renderAbout() {
    var m = DATA.meta || {};
    document.getElementById('srcList').innerHTML = (m.sources || []).map(function (x) {
      return '<li>' + esc(x.name) + '<br><a href="' + esc(x.url) + '" target="_blank" rel="noopener">' + esc(x.url) + '</a></li>';
    }).join('');
    document.getElementById('noteList').innerHTML = (m.notes || []).map(function (x) {
      return '<li>' + esc(x) + '</li>';
    }).join('');
    document.getElementById('genInfo').textContent =
      '数据生成时间：' + (m.generated || CITIES.meta.generated) + '（时区 ' + (m.timezone || CITIES.meta.timezone) + '）';
    var svc = 0;
    DATA.lines.forEach(function (L) { svc += L.services.length; });
    var stn = Object.keys(SIM.stations()).length;
    document.getElementById('footRight').textContent =
      DATA.name + ' · ' + DATA.lines.length + ' 条线路 · ' + svc + ' 个交路 · ' + stn + ' 座车站';
  }

  /* ================================================================ 城市切换 */
  function renderCityTabs() {
    var el = document.getElementById('cityTabs');
    if (!el) return;
    el.innerHTML = SIM.cities().map(function (c) {
      return '<button class="btn city' + (c.key === SIM.cityKey ? ' active' : '') + '" data-city="' +
        esc(c.key) + '">' + esc(c.name) + '<i>' + c.lines + '</i></button>';
    }).join('');
    Array.prototype.forEach.call(el.querySelectorAll('.btn.city'), function (b) {
      b.onclick = function () { useCity(b.getAttribute('data-city')); };
    });
  }

  function useCity(key) {
    if (!SIM.useCity(key)) return;
    DATA = SIM.data;
    state.selLine = null;
    state.selStation = null;
    state.hoverStation = null;
    state.hidden = {};
    geom.key = '';
    setupProjection();
    renderCityTabs();
    renderAbout();
    updatePanels();
    draw();
  }

  /* ================================================================== 启动 */
  window.addEventListener('resize', function () { resize(); setupProjection(); geom.key = ''; });
  resize();
  SIM.useCity(SIM.cityKey);
  DATA = SIM.data;
  setupProjection();
  var s0 = shanghaiNow();
  state.date = s0.date;
  state.time = s0.sec;
  renderCityTabs();
  renderAbout();
  updatePanels();
  // 调试/自动化测试入口
  window.__METRO_APP__ = {
    state: state, draw: draw, updatePanels: updatePanels, geom: geom,
    project: project, rebuild: function () { geom.key = ''; rebuildGeometry(); },
    switchTab: switchTab, useCity: useCity, renderAbout: renderAbout,
    setup: function () { resize(); setupProjection(); geom.key = ''; }
  };
  requestAnimationFrame(tick);
})();
