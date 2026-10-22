/* =========================================================================
 * sim.js —— 上海地铁列车运行仿真内核
 * 输入: window.SHMETRO_DATA (由 tools/build_data.py 生成)
 * 输出: 任意时刻、任意日期类型下, 每条线路每个方向每一列车的在线位置
 *
 * 运行规则(全部来自官方公布数据):
 *   1) 首末班车时间: 官方 fltime 接口(含周五/周六延时运营的分钟增量与特定日期增量)
 *   2) 发车间隔: 官方"列车间隔"表, 分 工作日/周五/双休日/延时运营 四种时段方案
 *   3) 站间运行时分: 停车 35s + 里程 / 线路旅行速度 (模型值)
 *   4) 首班车起, 按当时适用的间隔逐列发车, 直至末班车
 * ========================================================================= */
(function (global) {
  'use strict';

  var DATA = global.SHMETRO_DATA || { lines: [], headways: {} };
  var DAY_KEYS = ['sun', 'mon_thu', 'mon_thu', 'mon_thu', 'mon_thu', 'fri', 'sat'];

  /* ------------------------------------------------------------------ 缓存 */
  var depCache = Object.create(null);      // 发车时刻表缓存
  var statCache = Object.create(null);     // 服务统计缓存

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

  /** 该日期该线路适用的间隔方案(工作日/周五/双休日) */
  function daySpecOf(hw, dayKey) {
    if (!hw) return null;
    if (dayKey === 'fri') return hw.friday || hw.weekday;
    if (dayKey === 'sat' || dayKey === 'sun') return hw.weekend || hw.weekday;
    return hw.weekday || hw.weekend;
  }

  /** 特定日期增量(如 12-31 延时), 单位分钟 */
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
  /**
   * 某一时刻实际适用的发车间隔(秒)。
   * 命中固定时段则取该时段值; 否则在"其余时段(lo~hi)"之间线性过渡:
   *   - 首个时段之前: 由 hi 收窄到 lo
   *   - 末个时段之后: 由 lo 放宽到 hi
   *   - 两个时段之间: V 形过渡
   * 周五/周六 22:30 之后切换到延时运营间隔。
   */
  function headwayAt(hwKey, dayKey, t, serviceStart, serviceEnd) {
    var hw = DATA.headways[hwKey];
    if (!hw) return 300;
    if ((dayKey === 'fri' || dayKey === 'sat') && hw.extended) {
      var eb = hw.extended.bands[0];
      if (t >= eb.t0) {
        var eDs = hw.extended;
        var eLo = eDs.other[0], eHi = eDs.other[1];
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
  function getDepartures(svc, dirKey, dayKey, date) {
    var key = cacheKey(svc, dirKey, dayKey, date);
    var cached = depCache[key];
    if (cached) return cached;

    var d = svc[dirKey];
    var adj = 0;
    if (d.wd && d.wd[date.getDay()]) adj += d.wd[date.getDay()];
    adj += dateAdjustMin(d.dd, date);

    var first = d.first;
    var last = d.last + adj * 60;
    var hwKey = dirKey === 'rev' ? (svc.hwRev || svc.hw) : svc.hw;

    var out = [], t = first, guard = 0;
    while (t <= last && guard++ < 6000) {
      out.push(t);
      var h = headwayAt(hwKey, dayKey, t, first, last);
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

  /** 列车在其路径上的当前位置: 返回 {i, u} — 第 i 段(i→i+1) 上的比例 u */
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
  var _pool = [];
  /**
   * 返回该时刻在线列车数组。每项: {svc, line, dirKey, dep, progress, idx}
   */
  function trainsAt(time, dayKey, date, lineFilter) {
    var res = [];
    var lines = DATA.lines;
    for (var li = 0; li < lines.length; li++) {
      var line = lines[li];
      if (lineFilter && lineFilter !== line.name) continue;
      for (var si = 0; si < line.services.length; si++) {
        var svc = line.services[si];
        var total = svc.total;
        for (var k = 0; k < 2; k++) {
          var dirKey = k === 0 ? 'fwd' : 'rev';
          var deps = getDepartures(svc, dirKey, dayKey, date);
          // 发车时刻表已排序, 用二分定位窗口内的列车
          var loT = time - total, hiT = time;
          var a = lowerBound(deps, loT);
          for (var j = a; j < deps.length; j++) {
            var t0 = deps[j];
            if (t0 > hiT) break;
            res.push({
              svc: svc, line: line, dirKey: dirKey,
              dep: t0, progress: time - t0, idx: j
            });
          }
        }
      }
    }
    _pool = res;
    return res;
  }

  function lowerBound(arr, v) {
    var lo = 0, hi = arr.length;
    while (lo < hi) { var m = (lo + hi) >> 1; if (arr[m] < v) lo = m + 1; else hi = m; }
    return lo;
  }

  /* -------------------------------------------------------- 线路当前概况 */
  /** 某线路当前时刻的运行概况 */
  function lineStat(line, time, dayKey, date) {
    var key = line.name + '|' + dayKey + '|' + Math.floor(time / 60) + '|' + date.getMonth() + '-' + date.getDate();
    if (statCache[key]) return statCache[key];

    var trains = 0, hwMin = Infinity, hwMax = 0, running = false;
    var svcInfo = [];
    for (var i = 0; i < line.services.length; i++) {
      var svc = line.services[i];
      var info = { svc: svc, fwd: {}, rev: {}, online: 0, onlineFwd: 0, onlineRev: 0 };
      for (var k = 0; k < 2; k++) {
        var dirKey = k === 0 ? 'fwd' : 'rev';
        var d = svc[dirKey];
        var deps = getDepartures(svc, dirKey, dayKey, date);
        info[dirKey].first = deps.length ? deps[0] : d.first;
        info[dirKey].last = deps.length ? deps[deps.length - 1] : d.last;
        var hwKey = dirKey === 'rev' ? (svc.hwRev || svc.hw) : svc.hw;
        var h = headwayAt(hwKey, dayKey, time, info[dirKey].first, info[dirKey].last);
        info[dirKey].headway = h;
        if (time >= info[dirKey].first - 120 && time <= info[dirKey].last + svc.total) {
          running = true;
          hwMin = Math.min(hwMin, h);
          hwMax = Math.max(hwMax, h);
        }
        // 在线列车数
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
      headwayMin: isFinite(hwMin) ? hwMin : 0,
      headwayMax: hwMax
    };
    statCache[key] = out;
    return out;
  }

  /* ------------------------------------------------------------ 车站到站 */
  /** 车站站台/线路索引, 惰性建立 */
  var _stationIndex = null;
  function stationIndex() {
    if (_stationIndex) return _stationIndex;
    var idx = Object.create(null);
    var lines = DATA.lines;
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

  /**
   * 某车站接下来 n 班列车(按到达时间排序)。
   * 每条线路每个方向分别取若干班, 返回 {line, svc, dirKey, arrive, isTerminus, destName}
   */
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
        // 该方向上的到达时刻 = 发车时刻 + 行驶到本站的用时
        var travel = dirKey === 'fwd' ? svc.off[en.k] : (svc.total - svc.off[en.k]);
        var deps = getDepartures(svc, dirKey, dayKey, date);
        var n = 0;
        var start = lowerBound(deps, time - travel);
        for (var j = start; j < deps.length && n < perDir; j++) {
          var arrive = deps[j] + travel;
          if (arrive < time - 30) continue;
          out.push({
            line: en.line, svc: svc, dirKey: dirKey, arrive: arrive,
            wait: arrive - time,
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
    data: DATA,
    dayKeyOf: dayKeyOf,
    dayLabel: dayLabel,
    headwayAt: headwayAt,
    daySpecOf: daySpecOf,
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
