/* =========================================================================
 * sim.js —— 城市轨道交通列车运行仿真内核 (多城市)
 * 输入: window.METRO_CITIES (由 tools/build_data.py 生成)
 * 输出: 任意城市、任意时刻、任意日期类型下, 每条线路每个方向每一列车的位置
 *
 * 运行规则:
 *   1) 首末班车时间: 官方数据; 苏州区分「周一至周四」与「周五至周日」两套班表(fwd.alt)
 *   2) 发车间隔: 官方间隔表(上海/苏州) 或 公开信息典型值(杭州/电车)
 *   3) 站间运行时分: 官方逐站首班车差分 或 停车35s + 里程/旅行速度
 *   4) 首班车起, 按当时适用的间隔逐列发车, 直至末班车
 * ========================================================================= */
(function (global) {
  'use strict';

  var CITIES = global.METRO_CITIES || { meta: { cityOrder: [] }, cities: {} };
  var DAY_KEYS = ['sun', 'mon_thu', 'mon_thu', 'mon_thu', 'mon_thu', 'fri', 'sat'];

  var cityKey = (CITIES.meta && CITIES.meta.cityOrder && CITIES.meta.cityOrder[0]) || null;
  var DATA = cityKey ? CITIES.cities[cityKey] : { lines: [], headways: {} };

  /* ------------------------------------------------------------------ 缓存 */
  var depCache = Object.create(null);
  var statCache = Object.create(null);
  var _stationIndex = null;

  function resetCaches() {
    depCache = Object.create(null);
    statCache = Object.create(null);
    _stationIndex = null;
  }

  function useCity(key) {
    if (!key || !CITIES.cities[key]) return false;
    if (key === cityKey) return true;
    cityKey = key;
    DATA = CITIES.cities[key];
    resetCaches();
    return true;
  }

  function cityList() {
    return (CITIES.meta.cityOrder || []).map(function (k) {
      var c = CITIES.cities[k];
      return { key: k, name: c.name, fullName: c.fullName, lines: c.lines.length };
    });
  }

  function cacheKey(svc, dirKey, dayKey, date) {
    return svc.id + '|' + dirKey + '|' + dayKey + '|' + date.getMonth() + '-' + date.getDate();
  }

  /* ------------------------------------------------------------- 日期/时段 */
  function dayKeyOf(date, override) {
    if (override && override !== 'auto') return override;
    return DAY_KEYS[date.getDay()];
  }

  function dayLabel(k) {
    return { mon_thu: '周一~周四', fri: '周五', sat: '周六', sun: '周日' }[k] || k;
  }

  function daySpecOf(hw, dayKey) {
    if (!hw) return null;
    if (dayKey === 'fri') return hw.friday || hw.weekend || hw.weekday;
    if (dayKey === 'sat' || dayKey === 'sun') return hw.weekend || hw.weekday;
    return hw.weekday || hw.weekend;
  }

  function dateAdjustMin(dd, date) {
    if (!dd || !dd.length) return 0;
    var key = pad2(date.getMonth() + 1) + '-' + pad2(date.getDate());
    for (var i = 0; i < dd.length; i++) if (dd[i].date === key) return dd[i].adjust || 0;
    return 0;
  }

  function pad2(n) { return (n < 10 ? '0' : '') + n; }

  function hhmm(sec) {
    sec = Math.round(sec);
    var s = ((sec % 86400) + 86400) % 86400;
    return pad2(Math.floor(s / 3600)) + ':' + pad2(Math.floor(s % 3600 / 60));
  }
  function hhmmss(sec) {
    sec = Math.round(sec);
    var s = ((sec % 86400) + 86400) % 86400;
    return pad2(Math.floor(s / 3600)) + ':' + pad2(Math.floor(s % 3600 / 60)) + ':' + pad2(s % 60);
  }

  /* ------------------------------------------------------------- 间隔取值 */
  function headwayAt(hwKey, dayKey, t, serviceStart, serviceEnd) {
    var hw = (DATA.headways || {})[hwKey];
    if (!hw) return 300;
    if ((dayKey === 'fri' || dayKey === 'sat') && hw.extended) {
      var eb = hw.extended.bands[0];
      if (t >= eb.t0) {
        var eDs = hw.extended, eLo = eDs.other[0], eHi = eDs.other[1];
        if (t >= eb.t1) {
          var kk = clamp01((t - eb.t1) / Math.max(600, serviceEnd - eb.t1));
          return Math.round(eLo + (eHi - eLo) * kk);
        }
        return eb.h;
      }
    }
    var ds = daySpecOf(hw, dayKey);
    if (!ds || !ds.bands || !ds.bands.length) return 300;
    var bands = ds.bands, lo = ds.other[0], hi = ds.other[1];

    for (var i = 0; i < bands.length; i++) {
      if (t >= bands[i].t0 && t < bands[i].t1) return bands[i].h;
    }
    if (t < bands[0].t0) {
      var a = Math.max(serviceStart, bands[0].t0 - 7200), b = bands[0].t0;
      return Math.round(hi + (lo - hi) * clamp01((t - a) / Math.max(1, b - a)));
    }
    var last = bands[bands.length - 1];
    if (t >= last.t1) {
      var a2 = last.t1, b2 = Math.max(serviceEnd, a2 + 1);
      return Math.round(lo + (hi - lo) * clamp01((t - a2) / Math.max(1, b2 - a2)));
    }
    for (var j = 0; j < bands.length - 1; j++) {
      var g0 = bands[j].t1, g1 = bands[j + 1].t0;
      if (t >= g0 && t < g1) {
        var mid = (g0 + g1) / 2;
        var k = t < mid ? (t - g0) / Math.max(1, mid - g0) : (g1 - t) / Math.max(1, g1 - mid);
        return Math.round(lo + (hi - lo) * clamp01(k));
      }
    }
    return lo;
  }

  function clamp01(x) { return x < 0 ? 0 : (x > 1 ? 1 : x); }

  /* --------------------------------------------------------------- 发车表 */
  /** 该方向在给定日期类型下的首末班车(秒) */
  function spanOf(svc, dirKey, dayKey, date) {
    var d = svc[dirKey];
    var first = d.first, last = d.last;
    if (d.alt && (dayKey === 'fri' || dayKey === 'sat' || dayKey === 'sun')) {
      first = d.alt.first || first;
      last = d.alt.last || last;
    }
    var adj = 0;
    if (d.wd && d.wd[date.getDay()]) adj += d.wd[date.getDay()];
    adj += dateAdjustMin(d.dd, date);
    return { first: first, last: last + adj * 60 };
  }

  function getDepartures(svc, dirKey, dayKey, date) {
    var key = cacheKey(svc, dirKey, dayKey, date);
    var cached = depCache[key];
    if (cached) return cached;

    var sp = spanOf(svc, dirKey, dayKey, date);
    var hwKey = dirKey === 'rev' ? (svc.hwRev || svc.hw) : svc.hw;

    var out = [], t = sp.first, guard = 0;
    while (t <= sp.last && guard++ < 6000) {
      out.push(t);
      var h = headwayAt(hwKey, dayKey, t, sp.first, sp.last);
      t += Math.max(30, h);
    }
    depCache[key] = out;
    return out;
  }

  /* ------------------------------------------------------------- 位置换算 */
  function segmentOf(off, v) {
    var lo = 0, hi = off.length - 1;
    if (v <= off[0]) return 0;
    if (v >= off[hi]) return hi - 1;
    while (hi - lo > 1) {
      var mid = (lo + hi) >> 1;
      if (off[mid] <= v) lo = mid; else hi = mid;
    }
    return lo;
  }

  function pointAt(svc, dirKey, progress) {
    var off = svc.off, total = svc.total;
    var v = dirKey === 'rev' ? (total - progress) : progress;
    if (v < 0) v = 0;
    if (v > total) v = total;
    var i = segmentOf(off, v);
    var d = off[i + 1] - off[i];
    var u = d > 0 ? (v - off[i]) / d : 0;
    return { i: i, u: u };
  }

  /* ------------------------------------------------------- 某时刻在线列车 */
  function trainsAt(time, dayKey, date, lineFilter) {
    var res = [];
    var lines = DATA.lines || [];
    for (var li = 0; li < lines.length; li++) {
      var line = lines[li];
      if (lineFilter && lineFilter !== line.name) continue;
      for (var si = 0; si < line.services.length; si++) {
        var svc = line.services[si];
        var total = svc.total;
        for (var k = 0; k < 2; k++) {
          var dirKey = k === 0 ? 'fwd' : 'rev';
          var deps = getDepartures(svc, dirKey, dayKey, date);
          var a = lowerBound(deps, time - total);
          for (var j = a; j < deps.length; j++) {
            var t0 = deps[j];
            if (t0 > time) break;
            res.push({ svc: svc, line: line, dirKey: dirKey, dep: t0, progress: time - t0, idx: j });
          }
        }
      }
    }
    return res;
  }

  function lowerBound(arr, v) {
    var lo = 0, hi = arr.length;
    while (lo < hi) { var m = (lo + hi) >> 1; if (arr[m] < v) lo = m + 1; else hi = m; }
    return lo;
  }

  /* -------------------------------------------------------- 线路当前概况 */
  function lineStat(line, time, dayKey, date) {
    var key = (cityKey || '') + '|' + line.name + '|' + dayKey + '|' + Math.floor(time / 60) +
      '|' + date.getMonth() + '-' + date.getDate();
    if (statCache[key]) return statCache[key];

    var trains = 0, hwMin = Infinity, hwMax = 0, running = false, svcInfo = [];
    for (var i = 0; i < line.services.length; i++) {
      var svc = line.services[i];
      var info = { svc: svc, fwd: {}, rev: {}, online: 0, onlineFwd: 0, onlineRev: 0 };
      for (var k = 0; k < 2; k++) {
        var dirKey = k === 0 ? 'fwd' : 'rev';
        var deps = getDepartures(svc, dirKey, dayKey, date);
        var sp = spanOf(svc, dirKey, dayKey, date);
        info[dirKey].first = deps.length ? deps[0] : sp.first;
        info[dirKey].last = deps.length ? deps[deps.length - 1] : sp.last;
        var hwKey = dirKey === 'rev' ? (svc.hwRev || svc.hw) : svc.hw;
        var h = headwayAt(hwKey, dayKey, time, sp.first, sp.last);
        info[dirKey].headway = h;
        if (time >= info[dirKey].first - 120 && time <= info[dirKey].last + svc.total) {
          running = true;
          hwMin = Math.min(hwMin, h);
          hwMax = Math.max(hwMax, h);
        }
        var n = 0;
        var a = lowerBound(deps, time - svc.total);
        for (var j = a; j < deps.length; j++) {
          if (deps[j] > time) break;
          n++;
        }
        info[dirKey].online = n;
        trains += n;
        if (k === 0) info.onlineFwd = n; else info.onlineRev = n;
      }
      info.online = info.onlineFwd + info.onlineRev;
      svcInfo.push(info);
    }
    var out = {
      line: line, trains: trains, running: running, svcInfo: svcInfo,
      headwayMin: isFinite(hwMin) ? hwMin : 0, headwayMax: hwMax
    };
    statCache[key] = out;
    return out;
  }

  /* ------------------------------------------------------------ 车站到站 */
  function stationIndex() {
    if (_stationIndex) return _stationIndex;
    var idx = Object.create(null);
    var lines = DATA.lines || [];
    for (var li = 0; li < lines.length; li++) {
      var line = lines[li];
      for (var si = 0; si < line.services.length; si++) {
        var svc = line.services[si];
        for (var k = 0; k < svc.st.length; k++) {
          var name = svc.st[k][0];
          var e = idx[name] || (idx[name] = { name: name, x: svc.st[k][1], y: svc.st[k][2], entries: [] });
          e.entries.push({ line: line, svc: svc, k: k });
        }
      }
    }
    _stationIndex = idx;
    return idx;
  }

  function stations() { return stationIndex(); }
  function stationByName(n) { return stationIndex()[n]; }

  function stationArrivals(stationName, time, dayKey, date, perDir) {
    perDir = perDir || 3;
    var st = stationByName(stationName);
    if (!st) return [];
    var seen = Object.create(null);
    var out = [];
    for (var i = 0; i < st.entries.length; i++) {
      var en = st.entries[i];
      for (var k = 0; k < 2; k++) {
        var dirKey = k === 0 ? 'fwd' : 'rev';
        var key = en.svc.id + '|' + dirKey;
        if (seen[key]) continue;
        seen[key] = 1;

        var svc = en.svc;
        var travel = dirKey === 'fwd' ? svc.off[en.k] : (svc.total - svc.off[en.k]);
        var deps = getDepartures(svc, dirKey, dayKey, date);
        var n = 0;
        var start = lowerBound(deps, time - travel);
        for (var j = start; j < deps.length && n < perDir; j++) {
          var arrive = deps[j] + travel;
          if (arrive < time - 30) continue;
          out.push({
            line: en.line, svc: svc, dirKey: dirKey, arrive: arrive, wait: arrive - time,
            destName: dirKey === 'fwd'
              ? (svc.loop ? svc.dirNames[0] : svc.to)
              : (svc.loop ? svc.dirNames[1] : svc.from),
            dirName: dirKey === 'fwd' ? svc.dirNames[0] : svc.dirNames[1],
            isTerminus: (dirKey === 'fwd' ? en.k === svc.st.length - 1 : en.k === 0)
          });
          n++;
        }
      }
    }
    out.sort(function (a, b) { return a.arrive - b.arrive; });
    return out;
  }

  /* --------------------------------------------------------------- 导出 */
  global.SIM = {
    get data() { return DATA; },
    get cityKey() { return cityKey; },
    cities: cityList,
    useCity: useCity,
    dayKeyOf: dayKeyOf,
    dayLabel: dayLabel,
    headwayAt: headwayAt,
    daySpecOf: daySpecOf,
    spanOf: spanOf,
    getDepartures: getDepartures,
    trainsAt: trainsAt,
    pointAt: pointAt,
    lineStat: lineStat,
    stationArrivals: stationArrivals,
    stations: stations,
    stationByName: stationByName,
    hhmm: hhmm,
    hhmmss: hhmmss,
    pad2: pad2
  };
})(window);
