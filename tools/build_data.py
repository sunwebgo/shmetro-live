# -*- coding: utf-8 -*-
"""
多城市地铁动态线路图 —— 前端数据构建

支持: 上海 / 苏州(含有轨电车) / 杭州

数据来源
--------
上海:
  首末班车      m.shmetro.com/interface/metromap/metromap.aspx?func=fltime&line=N
  列车间隔      service.shmetro.com/hcskb/index.htm (列车间隔表, 人工整理为 HEADWAY_SH)
苏州(地铁):
  首末班车      www.sz-mtr.com/admin/time_table/getTimetableDtoByTimeId.do
  行车间隔      DTO 内 guideDescZh 文本(如"工作日早高峰行车间隔约2-4分钟...")
苏州(有轨电车):
  站点/走向     OpenStreetMap Overpass(route=tram, 苏州高新区有轨电车1/2号线)
  班次          参考公开信息建模
杭州:
  首末班车      www.hzmetro.com/api/operation/all (subwaySiteDetail)
  行车间隔      参考公开信息建模
三城共用:
  站点经纬度/线路几何/线路色  高德地铁图 map.amap.com/service/subway?srhdata={adcode}_drw_{city}.json

说明
----
- 首末班车尽可能取官方数据; 无官方来源的(电车班次、杭州/部分苏州行车间隔)按公开信息建模,
  并在页面"数据说明"中标注。
- 站间运行时分: 优先用官方逐站首班车时刻的差分推导; 若时刻不单调(如上海存在多点首班车),
  退回"停车35秒 + 里程/旅行速度"模型。
"""
import json
import math
import os
import re
import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw")
OFFICIAL = os.path.join(RAW, "official")
SZ_DTO = os.path.join(RAW, "sz_dto")
OUT = os.path.join(BASE, "data", "metro-data.js")

DWELL = 35.0
DEFAULT_SPEED = 48.0


# =============================================================== 通用工具
def sec_of(hhmm):
    if hhmm is None:
        return None
    s = str(hhmm).strip()
    if s in ("", "--", "-", "×", "〇", "null", "None"):
        return None
    s = s.split("#")[0].strip()          # "23:19#23:49" 取第一班
    m = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", s)
    if not m:
        return None
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3) or 0)


def norm_name(name):
    if not name:
        return ""
    s = str(name).strip()
    s = re.sub(r"[（(][^）)]*[）)]", "", s)
    for w in ("站", "始发", "·", "・", "‧", " "):
        s = s.replace(w, "")
    s = re.sub(r"[\s\u3000]+", "", s)
    alias = {
        "浦东南路原东昌路": "浦东南路",
        "一大会址新天地": "新天地",
        "上海松江": "松江",
        "唯亭花桥": "唯亭",
        "唯亭苏州新区火车站": "唯亭",
    }
    return alias.get(s, s)


def haversine(a, b):
    R = 6371.0088
    lng1, lat1 = a
    lng2, lat2 = b
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lng2 - lng1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def dists_of(stations):
    return [round(haversine((stations[i - 1]["x"], stations[i - 1]["y"]),
                            (stations[i]["x"], stations[i]["y"])), 3)
            for i in range(1, len(stations))]


def model_offsets(stations, speed_kmh):
    ds = dists_of(stations)
    v = speed_kmh * 1000.0 / 3600.0
    offs = [0.0]
    t = 0.0
    for d in ds:
        t += d * 1000.0 / v + DWELL
        offs.append(t)
    return offs, ds


def data_offsets(stations, times_by_name):
    """用官方逐站首班车时刻推导站间运行时分。

    官方数据里终点站的时刻常写作 "--"(终到), 这里按相邻站的平均用时外推补齐;
    若已知点不足、非单调或总时长异常, 返回 None 由调用方退回模型。
    """
    pts = [times_by_name.get(norm_name(s["n"])) for s in stations]
    n = len(pts)
    known = [i for i, t in enumerate(pts) if t is not None]
    if len(known) < 3 or len(known) < n * 0.6:
        return None
    for a, b in zip(known, known[1:]):
        if pts[b] <= pts[a]:
            return None
    span = (pts[known[-1]] - pts[known[0]]) / max(1, known[-1] - known[0])
    if span < 25 or span > 600:
        return None
    for i in range(n):
        if pts[i] is not None:
            continue
        left = [k for k in known if k < i]
        right = [k for k in known if k > i]
        if left:
            pts[i] = pts[left[-1]] + span * (i - left[-1])
        elif right:
            pts[i] = pts[right[0]] - span * (right[0] - i)
    for i in range(1, n):
        if pts[i] <= pts[i - 1]:
            pts[i] = pts[i - 1] + max(25.0, span * 0.5)
    total = pts[-1] - pts[0]
    if not (6 * 60 <= total <= 180 * 60):
        return None
    return [float(t - pts[0]) for t in pts]


def make_service(sid, name, stations, speed, dir_names, loop=False,
                 fwd=None, rev=None, hw=None, hw_rev=None, fwd_times=None):
    if loop:
        stations = list(stations) + [dict(stations[0])]

    model_off, ds = model_offsets(stations, speed)
    offs = None
    if fwd_times:
        cand = data_offsets(stations, fwd_times)
        if cand is not None and len(cand) == len(stations):
            offs = cand
    src = "official" if offs is not None else "model"
    if offs is None:
        offs = model_off

    svc = {
        "id": sid, "name": name,
        "from": stations[0]["n"], "to": stations[-1]["n"],
        "loop": bool(loop),
        "dirNames": dir_names,
        "st": [[s["n"], s["x"], s["y"]] for s in stations],
        "off": [int(round(v)) for v in offs],
        "total": int(round(offs[-1])),
        "dists": ds,
        "speed": speed,
        "timeSrc": src,
        "hw": hw, "hwRev": hw_rev or hw,
    }
    for key, val in (("fwd", fwd), ("rev", rev)):
        v = val or {}
        alt = v.get("alt")
        if alt:
            alt = {"first": int(alt.get("first") or 0), "last": int(alt.get("last") or 0)}
        svc[key] = {
            "first": int(v.get("first") or 5 * 3600 + 30 * 60),
            "last": int(v.get("last") or 22 * 3600 + 30 * 60),
            "wd": v.get("wd") or [0] * 7,
            "dd": v.get("dd") or [],
            "alt": alt,
            "found": bool(v.get("found", True)),
        }
    return svc


def std_headway(peak, off, eve=None, night=None, two_day=False,
                weekend_peak=None, weekend_off=None):
    """构造标准行车间隔方案。two_day=True 表示周五至周日有独立班表。"""
    eve = eve or peak
    night = night or int(off * 1.5)
    spec = {
        "weekday": {
            "bands": [{"t0": 7 * 3600, "t1": 9 * 3600 + 1800, "h": int(peak)},
                      {"t0": 9 * 3600 + 1800, "t1": 17 * 3600, "h": int(off)},
                      {"t0": 17 * 3600, "t1": 19 * 3600 + 1800, "h": int(eve)}],
            "other": [int(off * 1.3), int(night)],
        }
    }
    if not two_day:
        spec["weekend"] = {
            "bands": [{"t0": 8 * 3600, "t1": 20 * 3600, "h": int((peak + off) / 2)}],
            "other": [int(off), int(night)],
        }
    else:
        wp = int(weekend_peak or peak * 1.2)
        wo = int(weekend_off or off)
        spec["weekend"] = {
            "bands": [{"t0": 7 * 3600, "t1": 21 * 3600, "h": wp}],
            "other": [wo, int(night)],
        }
    return spec


def cn_duration(text):
    """从中文时间描述里取 (最小秒, 最大秒)。支持 '2-4分钟' / '2分35秒-4分钟' / '6分钟'。"""
    if not text:
        return None
    s = text.replace("约", "").replace(" ", "")
    vals = []
    for a, b in re.findall(r"(\d+)(?:分|分钟)?(?:(\d+)秒)?", s):
        a = int(a)
        b = int(b) if b else 0
        if a > 30:
            continue
        v = a * 60 + b
        if 30 <= v <= 3600:
            vals.append(v)
    if not vals:
        return None
    return (min(vals), max(vals))


def headway_from_desc(desc):
    out = {}
    if not desc:
        return out
    for key, label in (("peak", "早高峰"), ("eve", "晚高峰"), ("off", "平峰")):
        m = re.search(label + r"[^。；;]*?行车间隔约?([0-9分秒\-~—至]+(?:分钟|分|秒)?)", desc)
        if not m:
            continue
        rng = cn_duration(m.group(1))
        if rng:
            out[key] = int(sum(rng) / 2)
    return out


def load_amap(fname):
    d = json.load(open(os.path.join(RAW, fname), encoding="utf-8"))
    return d["l"]


def load_json(p):
    if not os.path.exists(p):
        return {}
    txt = open(p, encoding="utf-8-sig").read().strip()
    return json.loads(txt) if txt else {}


def amap_stations(e):
    out = []
    for s in (e.get("st") or []):
        sl = (s.get("sl") or "").split(",")
        if len(sl) != 2:
            continue
        try:
            out.append({"n": s.get("n"), "x": round(float(sl[0]), 6), "y": round(float(sl[1]), 6)})
        except ValueError:
            pass
    return out


# =============================================================== 上海
FALLBACK_COLORS_SH = {
    1: "#e3002b", 2: "#8cc220", 3: "#fcd600", 4: "#461d84", 5: "#944d9a",
    6: "#d40068", 7: "#ed6f00", 8: "#0094d8", 9: "#87caed", 10: "#c6afd4",
    11: "#871c2b", 12: "#007a60", 13: "#e999c0", 14: "#616020", 15: "#c8b38e",
    16: "#98d1c0", 17: "#bb796f", 18: "#C09453", 41: "#b5b6b6", 51: "#cccccc",
}


def load_official_colors():
    p = os.path.join(RAW, "api_lines.txt")
    if os.path.exists(p):
        try:
            return {int(r["line_no"]): r["color"].lower()
                    for r in json.loads(open(p, encoding="utf-8").read().strip())}
        except Exception:
            pass
    return {k: v.lower() for k, v in FALLBACK_COLORS_SH.items()}


def hm(h, m=0):
    return h * 3600 + m * 60


def B(*bands):
    return [{"t0": int(a), "t1": int(b), "h": int(c)} for a, b, c in bands]


def ds_(bands, other):
    return {"bands": bands, "other": [int(other[0]), int(other[1])]}


HEADWAY_SH = {
    "1A": {"weekday": ds_(B((hm(7), hm(9), 150), (hm(9), hm(17), 300), (hm(17), hm(19), 180)), (240, 540)),
           "friday": ds_(B((hm(7), hm(9), 150), (hm(9), hm(15), 300), (hm(15), hm(19), 180)), (240, 540)),
           "weekend": ds_(B((hm(9), hm(20), 240)), (360, 720)),
           "extended": ds_(B((hm(22, 30), hm(30), 750)), (750, 750)),
           "src": "工作日 早高峰2分30秒/平峰5分/晚高峰3分/其余4~9分"},
    "2A": {"weekday": ds_(B((hm(7, 30), hm(10), 150), (hm(10), hm(17), 300), (hm(17), hm(20, 30), 180)), (300, 600)),
           "weekend": ds_(B((hm(8, 30), hm(20, 30), 240)), (300, 600)),
           "extended": ds_(B((hm(23), hm(30), 900)), (900, 900)),
           "src": "工作日 主段早高峰2分30秒/平峰5分/晚高峰3分"},
    "3A": {"weekday": ds_(B((hm(7, 30), hm(9, 30), 400), (hm(9, 30), hm(17), 480), (hm(17), hm(19, 30), 300)), (480, 600)),
           "weekend": ds_(B((hm(8), hm(20), 480)), (420, 600)),
           "src": "工作日 早高峰往江杨北路6分40秒/平峰8分/晚高峰5分"},
    "4A": {"weekday": ds_(B((hm(7, 30), hm(9), 240), (hm(9), hm(17), 480), (hm(17), hm(19, 30), 300)), (420, 900)),
           "weekend": ds_(B((hm(8), hm(20), 390)), (420, 900)),
           "src": "工作日 内圈早高峰4分/平峰8分/晚高峰5分"},
    "4B": {"weekday": ds_(B((hm(7, 30), hm(9), 400), (hm(9), hm(17), 480), (hm(17), hm(19, 30), 300)), (420, 900)),
           "weekend": ds_(B((hm(8), hm(20), 390)), (420, 900)),
           "src": "工作日 外圈早高峰6分40秒"},
    "5A": {"weekday": ds_(B((hm(7), hm(9, 30), 225), (hm(9, 30), hm(17), 720), (hm(17), hm(20), 270)), (450, 720)),
           "weekend": ds_(B((hm(7), hm(20), 540)), (450, 720)),
           "src": "工作日 东川路～奉贤新城 早高峰3分45秒/平峰12分"},
    "5B": {"weekday": ds_(B((hm(7), hm(9, 30), 450), (hm(9, 30), hm(17), 720), (hm(17), hm(20), 540)), (450, 720)),
           "weekend": ds_(B((hm(7), hm(20), 540)), (450, 720)),
           "src": "工作日 东川路～闵行开发区 早高峰7分30秒"},
    "6A": {"weekday": ds_(B((hm(7, 20), hm(9), 150), (hm(9), hm(16, 30), 390), (hm(16, 30), hm(19), 225)), (300, 720)),
           "weekend": ds_(B((hm(8, 30), hm(20, 30), 240)), (300, 720)),
           "src": "工作日 早高峰2分/平峰6分30秒"},
    "7A": {"weekday": ds_(B((hm(7, 30), hm(9), 180), (hm(9), hm(17, 30), 420), (hm(17, 30), hm(19), 240)), (300, 660)),
           "weekend": ds_(B((hm(8), hm(20), 420)), (300, 660)),
           "extended": ds_(B((hm(22, 30), hm(30), 1080)), (1080, 1080)),
           "src": "工作日 早高峰2分~3分30秒/平峰7分"},
    "8A": {"weekday": ds_(B((hm(7, 15), hm(9, 20), 150), (hm(9, 20), hm(17), 300), (hm(17), hm(19, 20), 200)), (300, 720)),
           "weekend": ds_(B((hm(8), hm(19), 280)), (300, 720)),
           "extended": ds_(B((hm(22, 30), hm(30), 750)), (750, 750)),
           "src": "工作日 早高峰2分~2分30秒/平峰4分20秒~8分40秒"},
    "9A": {"weekday": ds_(B((hm(7, 30), hm(9), 180), (hm(9), hm(17), 360), (hm(17), hm(19, 30), 210)), (360, 600)),
           "weekend": ds_(B((hm(8), hm(20), 300)), (360, 600)),
           "extended": ds_(B((hm(22, 55), hm(30), 1020)), (1020, 1020)),
           "src": "工作日 早高峰1分50秒~5分30秒/平峰6分"},
    "10A": {"weekday": ds_(B((hm(7, 30), hm(9), 240), (hm(9), hm(17, 30), 300), (hm(17, 30), hm(20), 270)), (300, 480)),
            "weekend": ds_(B((hm(7), hm(22, 30), 360)), (300, 480)),
            "extended": ds_(B((hm(22, 30), hm(30), 870)), (870, 870)),
            "src": "工作日 虹桥火车站～龙溪路 早高峰3~5分/平峰6分"},
    "10B": {"weekday": ds_(B((hm(7, 30), hm(9), 480), (hm(9), hm(17, 30), 540), (hm(17, 30), hm(20), 420)), (300, 660)),
            "weekend": ds_(B((hm(7), hm(22, 30), 600)), (300, 660)),
            "extended": ds_(B((hm(22, 30), hm(30), 870)), (870, 870)),
            "src": "工作日 航中路～龙溪路 早高峰6分45秒~9分/平峰12分"},
    "11A": {"weekday": ds_(B((hm(7, 30), hm(9), 330), (hm(9), hm(18), 450), (hm(18), hm(19), 330)), (420, 600)),
            "weekend": ds_(B((hm(8), hm(20), 450)), (480, 720)),
            "src": "工作日 嘉定北～嘉定新城 早高峰5~10分/平峰12分"},
    "11B": {"weekday": ds_(B((hm(7, 30), hm(9), 330), (hm(9), hm(18), 450), (hm(18), hm(19), 330)), (420, 600)),
            "weekend": ds_(B((hm(8), hm(20), 450)), (480, 720)),
            "src": "工作日 花桥～嘉定新城 早高峰7分30秒~10分/平峰12分"},
    "12A": {"weekday": ds_(B((hm(7, 30), hm(9, 30), 165), (hm(9, 30), hm(16, 30), 420), (hm(16, 30), hm(20), 225)), (360, 540)),
            "weekend": ds_(B((hm(8), hm(19), 360)), (480, 660)),
            "src": "工作日 早高峰2分45秒/平峰7分"},
    "13A": {"weekday": ds_(B((hm(7, 30), hm(9, 30), 220), (hm(9, 30), hm(17), 420), (hm(17), hm(19, 30), 240)), (360, 600)),
            "weekend": ds_(B((hm(8, 30), hm(20, 30), 360)), (360, 600)),
            "extended": ds_(B((hm(22, 30), hm(30), 1020)), (1020, 1020)),
            "src": "工作日 早高峰2分45秒/平峰7分"},
    "14A": {"weekday": ds_(B((hm(7), hm(9, 30), 240), (hm(9, 30), hm(16, 40), 510), (hm(16, 40), hm(20), 320)), (300, 720)),
            "weekend": ds_(B((hm(7), hm(21), 420)), (300, 720)),
            "src": "工作日 真新新村～蓝天路 早高峰3分/平峰8分30秒"},
    "15A": {"weekday": ds_(B((hm(7, 20), hm(9, 20), 300), (hm(9, 20), hm(16, 30), 480), (hm(16, 30), hm(20), 360)), (300, 780)),
            "weekend": ds_(B((hm(7), hm(20, 20), 450)), (360, 780)),
            "src": "工作日 双柏路～古浪路 早高峰3分~3分40秒/平峰8分"},
    "16A": {"weekday": ds_(B((hm(7, 30), hm(10, 30), 210), (hm(10, 30), hm(16, 30), 450), (hm(16, 30), hm(21, 30), 240)), (480, 720)),
            "weekend": ds_(B((hm(7), hm(20, 30), 360)), (300, 720)),
            "src": "工作日 早高峰3分30秒/平峰7分30秒"},
    "17A": {"weekday": ds_(B((hm(7), hm(9, 30), 240), (hm(9, 30), hm(17), 600), (hm(17), hm(20), 360)), (480, 660)),
            "weekend": ds_(B((hm(7, 30), hm(21), 420)), (420, 840)),
            "src": "工作日 淀山湖大道～虹桥火车站 早高峰3分/平峰10分"},
    "18A": {"weekday": ds_(B((hm(7, 30), hm(9), 240), (hm(9), hm(17), 480), (hm(17), hm(19, 10), 280)), (420, 780)),
            "weekend": ds_(B((hm(7), hm(21), 390)), (480, 900)),
            "src": "工作日 沈梅路～长江南路 早高峰2分45秒/平峰8分"},
    "41A": {"weekday": ds_(B((hm(7), hm(9), 255), (hm(9), hm(18), 600), (hm(18), hm(20), 300)), (600, 600)),
            "weekend": ds_(B((hm(7), hm(20), 600)), (600, 600)),
            "src": "工作日 早高峰4分15秒/平峰10分"},
    "51A": {"weekday": ds_(B((hm(6), hm(23), 900)), (900, 900)),
            "weekend": ds_(B((hm(6), hm(23), 900)), (900, 900)),
            "src": "官方: 全天平均15分"},
    "cfA": {"weekday": ds_(B((hm(6, 45), hm(21, 40), 900)), (900, 900)),
            "weekend": ds_(B((hm(6, 45), hm(21, 40), 900)), (900, 900)),
            "src": "参考公开信息: 约15分一班"},
}

SH_LINE_META = {
    "1号线": dict(no=1, hw=["1A"]), "2号线": dict(no=2, hw=["2A"]),
    "3号线": dict(no=3, hw=["3A"]), "4号线": dict(no=4, hw={"fwd": "4A", "rev": "4B"}),
    "5号线": dict(no=5, hw={"by_dest": {"奉贤新城": "5A", "闵行开发区": "5B"}, "default": "5A"}),
    "6号线": dict(no=6, hw=["6A"]), "7号线": dict(no=7, hw=["7A"]),
    "8号线": dict(no=8, hw=["8A"]), "9号线": dict(no=9, hw=["9A"]),
    "10号线": dict(no=10, hw={"by_dest": {"航中路": "10B", "虹桥火车站": "10A"}, "default": "10A"}),
    "11号线": dict(no=11, hw={"by_dest": {"嘉定北": "11A", "花桥": "11B"}, "default": "11A"}),
    "12号线": dict(no=12, hw=["12A"]), "13号线": dict(no=13, hw=["13A"]),
    "14号线": dict(no=14, hw=["14A"]), "15号线": dict(no=15, hw=["15A"]),
    "16号线": dict(no=16, hw=["16A"]), "17号线": dict(no=17, hw=["17A"]),
    "18号线": dict(no=18, hw=["18A"]),
    "浦江线": dict(no=41, hw=["41A"]), "市域机场线": dict(no=51, hw=["51A"]),
    "磁浮线": dict(no=None, hw=["cfA"]),
}

SH_SPEED = {"16号线": 72.0, "磁浮线": 200.0, "市域机场线": 100.0, "5号线": 52.0, "17号线": 58.0}
SH_MANUAL_FL = {
    "磁浮线": {"fwd": {"first": 6 * 3600 + 45 * 60, "last": 21 * 3600 + 40 * 60},
               "rev": {"first": 7 * 3600 + 2 * 60, "last": 21 * 3600 + 55 * 60}},
}


def parse_last_desc(desc):
    if not desc:
        return [0] * 7, []
    try:
        o = json.loads(desc)
    except Exception:
        return [0] * 7, []
    wd = [int(x) for x in (list(o.get("weekday") or []) + [0] * 7)[:7]]
    dd = []
    for it in (o.get("dateday") or []):
        try:
            dd.append({"date": it["date"], "adjust": int(str(it["adjust"]).replace("+", ""))})
        except Exception:
            pass
    return wd, dd


def station_extremes(records, station_name):
    ns = norm_name(station_name)
    f = [sec_of(r.get("first_time")) for r in records if norm_name(r.get("name")) == ns]
    l = [sec_of(r.get("last_time")) for r in records if norm_name(r.get("name")) == ns]
    f = [x for x in f if x is not None]
    l = [x for x in l if x is not None]
    return (min(f) if f else None), (max(l) if l else None)


def line_weekday_max(records):
    mx = [0] * 7
    for r in records:
        wd, _ = parse_last_desc(r.get("last_time_desc"))
        for i in range(7):
            if wd[i] > mx[i]:
                mx[i] = wd[i]
    return mx


def find_record(records, station_name, dest_name, dir_hint=None):
    ns = norm_name(station_name)
    cands = [r for r in records if norm_name(r.get("name")) == ns]
    if not cands:
        return None
    if dir_hint is not None:
        hit = [r for r in cands if dir_hint in (r.get("description") or "")]
        if hit:
            for r in hit:
                if "全程" in (r.get("description") or "") and sec_of(r.get("first_time")):
                    return r
            for r in hit:
                if int(r.get("firstarrival_time") or 0) == 0 and sec_of(r.get("first_time")):
                    return r
            return hit[0]
    nd = norm_name(dest_name)
    hit = [r for r in cands if nd and nd in norm_name(r.get("description"))]
    if not hit:
        return None
    for r in hit:
        if int(r.get("firstarrival_time") or 0) == 0:
            return r
    return hit[0]


def pick_hw(meta, dest_name, direction):
    hw = meta["hw"]
    if isinstance(hw, list):
        return hw[0]
    if "fwd" in hw:
        return hw["fwd"] if direction == "fwd" else hw["rev"]
    if "by_dest" in hw:
        return hw["by_dest"].get(dest_name, hw.get("default"))
    return hw


def build_shanghai():
    colors = load_official_colors()
    entries = load_amap("amap_shanghai_subway.json")
    fl_cache = {n: load_json(os.path.join(OFFICIAL, "fltime_%d.txt" % n))
                for n in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 41, 51]}

    groups = {}
    for e in entries:
        groups.setdefault(e["ln"], []).append(e)

    lines, diag = [], []
    for lname, ents in groups.items():
        meta = SH_LINE_META.get(lname)
        if not meta:
            continue
        no = meta["no"]
        color = colors.get(no) or ("#" + (ents[0].get("cl") or "888888").lower())
        records = fl_cache.get(no, [])
        lwmax = line_weekday_max(records)

        for si, e in enumerate(ents):
            stations = amap_stations(e)
            if len(stations) < 2:
                continue
            loop = str(e.get("lo", "0")) == "1"
            origin, dest = stations[0]["n"], stations[-1]["n"]
            dir_names = ["内圈", "外圈"] if loop else ["往" + dest, "往" + origin]

            if isinstance(meta["hw"], dict) and "fwd" in meta["hw"]:
                hw_f, hw_r = meta["hw"]["fwd"], meta["hw"]["rev"]
            else:
                hw_f = hw_r = pick_hw(meta, dest, "fwd")

            def fl(s_origin, s_dest, dir_hint=None):
                if lname in SH_MANUAL_FL:
                    mf = SH_MANUAL_FL[lname]
                    side = "fwd" if s_origin == origin else "rev"
                    return mf[side]["first"], mf[side]["last"], [0] * 7, [], True
                r = find_record(records, s_origin, s_dest, dir_hint)
                f = l = None
                wd, dd = [0] * 7, []
                if r:
                    f = sec_of(r.get("first_time"))
                    l = sec_of(r.get("last_time"))
                    wd, dd = parse_last_desc(r.get("last_time_desc"))
                ok = f is not None
                ext = HEADWAY_SH.get(hw_f, {}).get("extended") or HEADWAY_SH.get(hw_r, {}).get("extended")
                if ext and not any(wd) and any(lwmax):
                    wd = list(lwmax)
                if f is None or l is None:
                    ef, el = station_extremes(records, s_origin)
                    f = f if f is not None else ef
                    l = l if l is not None else el
                return f, l, wd, dd, ok

            if loop:
                f1, l1, w1, d1, ok1 = fl(origin, dest, "内")
                f2, l2, w2, d2, ok2 = fl(origin, dest, "外")
            else:
                f1, l1, w1, d1, ok1 = fl(origin, dest)
                f2, l2, w2, d2, ok2 = fl(dest, origin)

            svc = make_service(
                "%s-%d" % (no if no else "cf", si), lname, stations,
                SH_SPEED.get(lname, DEFAULT_SPEED), dir_names, loop=loop,
                fwd={"first": f1, "last": l1, "wd": w1, "dd": d1, "found": ok1},
                rev={"first": f2, "last": l2, "wd": w2, "dd": d2, "found": ok2},
                hw=hw_f, hw_rev=hw_r)
            lines.append({"no": no if no else 900, "name": lname, "color": color, "services": [svc]})
            diag.append("%-9s svc%d %-13s -> %-13s st=%2d run=%3dmin %s fwd %s/%s rev %s/%s hw=%s" % (
                lname, si, origin, dest, len(svc["st"]), svc["total"] // 60, svc["timeSrc"],
                fmt(svc["fwd"]["first"]), fmt(svc["fwd"]["last"]),
                fmt(svc["rev"]["first"]), fmt(svc["rev"]["last"]), hw_f))

    lines.sort(key=lambda L: L["no"])
    return {
        "key": "shanghai", "name": "上海", "fullName": "上海地铁",
        "lines": lines, "headways": HEADWAY_SH,
        "meta": {
            "sources": [
                {"name": "上海地铁官网 首末班车时刻表 / 列车间隔表", "url": "https://service.shmetro.com/hcskb/index.htm"},
                {"name": "上海地铁首末班车接口", "url": "https://m.shmetro.com/interface/metromap/metromap.aspx?func=fltime&line=N"},
                {"name": "高德地图 上海地铁线路与站点坐标", "url": "https://map.amap.com/service/subway?srhdata=3100_drw_shanghai.json"},
            ],
            "notes": [
                "首末班车时间与列车间隔取自上海地铁官方公布数据, 含周五/周六延时运营。",
                "站间运行时分采用建模值(停车35秒 + 里程/旅行速度); 上海存在多点首班车, 不宜用首班车差分。",
                "2号线、16号线的大站车/区间车未单独建模。",
            ],
        },
        "diag": diag,
    }


# =============================================================== 苏州
SZ_LINE_TO_API = {"1号线": "1", "2号线": "2", "3号线": "3_11", "4号线": "4",
                  "5号线": "5", "6号线": "6", "7号线": "7", "8号线": "8", "11号线": "3_11"}
SZ_SPEED = {"11号线": 55.0, "3号线": 46.0, "5号线": 46.0}


def build_suzhou():
    entries = load_amap("amap_suzhou.json")
    groups = {}
    for e in entries:
        groups.setdefault(e["ln"], []).append(e)

    lines, diag, headways = [], [], {}
    for lname, ents in groups.items():
        api_line = SZ_LINE_TO_API.get(lname)
        if not api_line:
            continue
        wd_dto = load_json(os.path.join(SZ_DTO, "%s_周一至周四时刻表.json" % api_line))
        if not wd_dto:
            wd_dto = load_json(os.path.join(SZ_DTO, "%s_周一至周日时刻表.json" % api_line))
        alt_dto = load_json(os.path.join(SZ_DTO, "%s_周五至周日时刻表.json" % api_line))
        src_dto = wd_dto or alt_dto
        if not src_dto:
            diag.append("SZ %-8s 无官方时刻表, 跳过" % lname)
            continue

        id2name = {}
        for dto in (wd_dto, alt_dto):
            for s in dto.get("stations", []):
                id2name[s["stationId"]] = norm_name(s["stationNameZh"])

        def dir_data(dto, want_dest):
            """返回 (方向名, {站名: 首班秒}, {站名: 末班秒})"""
            first, last, dname = {}, {}, None
            if not dto:
                return dname, first, last
            for f in dto.get("timetableFrequency", []):
                for td in (f.get("timetableDirection") or []):
                    dn = td.get("directionNameZh") or ""
                    if want_dest and norm_name(want_dest) not in norm_name(dn):
                        continue
                    dname = dn
                    for it in (td.get("timetableFirstLastTimes") or []):
                        nm = id2name.get(it.get("stationId"))
                        t = sec_of(it.get("tfltTime"))
                        if not nm or t is None:
                            continue
                        if f.get("frequencyNameZh") == "首班车":
                            first[nm] = t
                        elif f.get("frequencyNameZh") == "末班车":
                            last[nm] = t
            return dname, first, last

        desc = src_dto.get("guideDescZh") or ""
        hwd = headway_from_desc(desc)
        hw_key = "SZ_" + lname
        two_day = bool(wd_dto and alt_dto)
        if hwd.get("peak"):
            headways[hw_key] = std_headway(hwd.get("peak", 240), hwd.get("off", 360), hwd.get("eve"),
                                           two_day=two_day,
                                           weekend_peak=int(hwd["peak"] * 1.2),
                                           weekend_off=int(hwd.get("off", 360) * 1.1))
            headways[hw_key]["src"] = desc.split("注：")[0].strip()
        else:
            headways[hw_key] = std_headway(240, 400, two_day=two_day)
            headways[hw_key]["src"] = "参考公开信息"

        for si, e in enumerate(ents):
            stations = amap_stations(e)
            if len(stations) < 2:
                continue
            origin, dest = stations[0]["n"], stations[-1]["n"]

            fdn, wf, wl = dir_data(wd_dto, dest)
            rdn, wr, wlr = dir_data(wd_dto, origin)
            _, af, al = dir_data(alt_dto, dest)
            _, ar, alr = dir_data(alt_dto, origin)

            def pick(m, key, agg):
                v = m.get(norm_name(key))
                if v is not None:
                    return v
                vs = [x for x in m.values() if x is not None]
                if not vs:
                    return None
                return agg(vs)

            f1 = pick(wf, origin, min) or 6 * 3600
            l1 = pick(wl, origin, max) or 22 * 3600 + 30 * 60
            f2 = pick(wr, dest, min) or 6 * 3600
            l2 = pick(wlr, dest, max) or 22 * 3600 + 30 * 60

            alt_f = None
            if af:
                alt_f = {"first": pick(af, origin, min) or f1, "last": pick(al, origin, max) or l1}
            alt_r = None
            if ar:
                alt_r = {"first": pick(ar, dest, min) or f2, "last": pick(alr, dest, max) or l2}

            svc = make_service(
                "sz-%s-%d" % (re.sub(r"\D", "", lname) or "x", si), lname, stations,
                SZ_SPEED.get(lname, DEFAULT_SPEED),
                [fdn or ("往" + dest), rdn or ("往" + origin)],
                fwd={"first": f1, "last": l1, "alt": alt_f, "found": bool(wf)},
                rev={"first": f2, "last": l2, "alt": alt_r, "found": bool(wr)},
                hw=hw_key, fwd_times=wf)
            lines.append({"no": int(re.sub(r"\D", "", lname) or 900), "name": lname,
                          "color": "#" + (e.get("cl") or "888888").lower(), "services": [svc]})
            diag.append("SZ %-7s %-14s -> %-14s st=%2d run=%3dmin %s fwd %s/%s alt %s" % (
                lname, origin, dest, len(svc["st"]), svc["total"] // 60, svc["timeSrc"],
                fmt(f1), fmt(l1), fmt(alt_f["first"]) if alt_f else "-"))

    lines.sort(key=lambda L: L["no"])
    return {
        "key": "suzhou", "name": "苏州", "fullName": "苏州轨道交通",
        "lines": lines, "headways": headways,
        "meta": {
            "sources": [
                {"name": "苏州轨道交通 官网时刻表", "url": "https://www.sz-mtr.com/service/guide/time/"},
                {"name": "苏州轨道交通 时刻表接口", "url": "https://www.sz-mtr.com/admin/time_table/getTimetableDtoByTimeId.do"},
                {"name": "高德地图 苏州地铁线路与站点坐标", "url": "https://map.amap.com/service/subway?srhdata=3205_drw_suzhou.json"},
            ],
            "notes": [
                "首末班车时间取自苏州轨道交通官网时刻表接口, 区分「周一至周四」与「周五至周日」两套班表。",
                "行车间隔由官网公布的行车间隔描述文本解析(如“工作日早高峰行车间隔约2-4分钟”), 取区间中值。",
                "3号线与11号线贯通运行, 已作为同一交路处理。",
                "站间运行时分由官方逐站首班车时刻差分推导。",
            ],
        },
        "diag": diag,
    }


def build_suzhou_tram():
    p = os.path.join(RAW, "suzhou_tram_stops.json")
    if not os.path.exists(p):
        return None
    data = json.load(open(p, encoding="utf-8"))
    lines, diag = [], []
    hw = {"TRAM": std_headway(600, 900, two_day=True, weekend_peak=720, weekend_off=900)}
    hw["TRAM"]["src"] = "参考公开信息: 高峰约10分/平峰约15分"

    for i, L in enumerate(data.get("lines", [])):
        stops = [s for s in L.get("stops", []) if s.get("name") and s.get("lat")]
        if len(stops) < 3:
            continue
        # 站序已由 tools/order_tram_stops.js 按 OSM 线路几何投影确定
        use = stops
        gap = 0.0
        for j in range(1, len(use)):
            gap = max(gap, haversine((use[j - 1]["lon"], use[j - 1]["lat"]),
                                     (use[j]["lon"], use[j]["lat"])))
        if gap > 4.0:
            diag.append("TRAM %s 站序可疑(最大间距 %.1fkm), 跳过" % (L["name"], gap))
            continue
        stations = [{"n": s["name"], "x": round(s["lon"], 6), "y": round(s["lat"], 6)} for s in use]
        svc = make_service("tram-%d" % i, L["name"], stations, 22.0,
                           ["往" + stations[-1]["n"], "往" + stations[0]["n"]],
                           fwd={"first": 6 * 3600, "last": 22 * 3600, "found": False},
                           rev={"first": 6 * 3600 + 600, "last": 22 * 3600 + 600, "found": False},
                           hw="TRAM")
        lines.append({"no": 100 + i, "name": L["name"],
                      "color": L.get("color") or "#B5CD56", "services": [svc]})
        diag.append("TRAM %-16s st=%2d 最大间距%.1fkm run=%2dmin" % (
            L["name"], len(stations), gap, svc["total"] // 60))

    if not lines:
        return None
    return {
        "key": "suzhou_tram", "name": "苏州电车", "fullName": "苏州高新区有轨电车",
        "lines": lines, "headways": hw,
        "meta": {
            "sources": [
                {"name": "OpenStreetMap route=tram (苏州高新区有轨电车1/2号线)", "url": "https://overpass-api.de/"},
            ],
            "notes": [
                "站点与走向来自 OpenStreetMap 有轨电车线路关系数据。",
                "班次为参考公开信息建模(首末班约 06:00–22:00, 高峰约10分/平峰约15分), 非官方时刻表。",
                "站间运行时分按有轨电车旅行速度 22km/h 建模。",
            ],
        },
        "diag": diag,
    }


# =============================================================== 杭州
HZ_SKIP = {"绍兴1号线", "杭海城际"}
HZ_SPEED = {"19号线": 80.0, "16号线": 65.0, "1号线": 55.0}
HZ_HW = {
    "1号线": (150, 300), "2号线": (180, 330), "3号线": (210, 360), "4号线": (180, 330),
    "5号线": (180, 330), "6号线": (240, 400), "7号线": (240, 420), "8号线": (300, 480),
    "9号线": (300, 480), "10号线": (300, 480), "16号线": (360, 540), "19号线": (360, 540),
}


def build_hangzhou():
    entries = load_amap("amap_hangzhou.json")
    api = load_json(os.path.join(RAW, "hz_all.json")).get("data") or {}
    detail = api.get("subwaySiteDetail") or {}
    line_list = api.get("lineList") or []

    key2name = {}
    for L in line_list:
        key2name[L.get("otherName") or L.get("lineName")] = L.get("lineName")

    groups = {}
    for e in entries:
        if e["ln"] in HZ_SKIP:
            continue
        groups.setdefault(e["ln"], []).append(e)

    lines, diag, headways = [], [], {}
    for lname, ents in groups.items():
        keys = [k for k in detail.keys() if key2name.get(k) == lname]
        if not keys:
            diag.append("HZ %-8s 无官方时刻表, 跳过" % lname)
            continue

        # 每个接口 key 的站名集合(用于支线匹配)
        key_names = {}
        for k in keys:
            s = set()
            for d in detail[k]:
                for st in d.get("allStation", []):
                    s.add(norm_name(st.get("sitName")))
            key_names[k] = s

        for si, e in enumerate(ents):
            stations = amap_stations(e)
            if len(stations) < 2:
                continue
            names = set(norm_name(s["n"]) for s in stations)
            best, best_score = None, -1
            for k in keys:
                inter = len(names & key_names[k])
                union = max(1, len(names | key_names[k]))
                if inter / union > best_score:
                    best, best_score = k, inter / union
            if not best:
                continue
            dirs = detail[best]

            def pick_dir(want):
                wn = norm_name(want)
                for d in dirs:
                    t = (d.get("title") or "").replace("往", "").replace("方向", "")
                    if norm_name(t) == wn or wn in norm_name(t) or norm_name(t) in wn:
                        return d
                return None

            origin, dest = stations[0]["n"], stations[-1]["n"]
            d_fwd, d_rev = pick_dir(dest), pick_dir(origin)

            def times_of(d):
                first, last = {}, {}
                for st in (d or {}).get("allStation", []):
                    nm = norm_name(st.get("sitName"))
                    first[nm] = sec_of(st.get("startTime"))
                    last[nm] = sec_of(st.get("endTime"))
                return first, last

            fw, lw = times_of(d_fwd)
            fv, lv = times_of(d_rev)

            def pick_t(m, key, agg, fallback):
                v = m.get(norm_name(key))
                if v is not None:
                    return v
                vs = [x for x in m.values() if x is not None]
                return agg(vs) if vs else fallback

            hz_peak, hz_off = HZ_HW.get(lname, (300, 480))
            hw_key = "HZ_" + lname
            if hw_key not in headways:
                headways[hw_key] = std_headway(hz_peak, hz_off, two_day=False)
                headways[hw_key]["src"] = "参考公开信息: 高峰约%d分/平峰约%d分" % (
                    max(1, hz_peak // 60), max(1, hz_off // 60))

            svc = make_service(
                "hz-%s-%d" % (re.sub(r"\D", "", lname) or "x", si), lname, stations,
                HZ_SPEED.get(lname, DEFAULT_SPEED),
                ["往" + dest, "往" + origin],
                fwd={"first": pick_t(fw, origin, min, 6 * 3600),
                     "last": pick_t(lw, origin, max, 22 * 3600 + 30 * 60), "found": bool(d_fwd)},
                rev={"first": pick_t(fv, dest, min, 6 * 3600),
                     "last": pick_t(lv, dest, max, 22 * 3600 + 30 * 60), "found": bool(d_rev)},
                hw=hw_key, fwd_times=fw)
            lines.append({"no": int(re.sub(r"\D", "", lname) or 900), "name": lname,
                          "color": "#" + (e.get("cl") or "888888").lower(), "services": [svc]})
            diag.append("HZ %-7s svc%d %-14s -> %-14s st=%2d run=%3dmin %s fwd %s/%s" % (
                lname, si, origin, dest, len(svc["st"]), svc["total"] // 60, svc["timeSrc"],
                fmt(svc["fwd"]["first"]), fmt(svc["fwd"]["last"])))

    lines.sort(key=lambda L: L["no"])
    return {
        "key": "hangzhou", "name": "杭州", "fullName": "杭州地铁",
        "lines": lines, "headways": headways,
        "meta": {
            "sources": [
                {"name": "杭州地铁官网 线网图/时刻表接口", "url": "https://www.hzmetro.com/api/operation/all"},
                {"name": "高德地图 杭州地铁线路与站点坐标", "url": "https://map.amap.com/service/subway?srhdata=3301_drw_hangzhou.json"},
            ],
            "notes": [
                "各站首末班车时间取自杭州地铁官网接口(逐站、逐方向)。",
                "官网接口未提供行车间隔, 图中间隔为参考公开信息的典型值(骨干线高峰约2.5~3分, 一般线3~5分)。",
                "接口当前返回周末时刻表, 工作日与之差异通常在数分钟内。",
                "绍兴1号线为绍兴市线路、杭海城际为城际铁路, 未纳入杭州地铁统计。",
            ],
        },
        "diag": diag,
    }


# =============================================================== 主流程
def fmt(s):
    if s is None:
        return "--:--"
    return "%02d:%02d" % (int(s) // 3600 % 24, int(s) // 60 % 60)


def merge_lines(lines):
    """同一线路名的多条交路(支线/贯通段)合并为一个线路对象。"""
    by = {}
    for L in lines:
        k = L["name"]
        if k in by:
            by[k]["services"].extend(L["services"])
        else:
            by[k] = {"no": L["no"], "name": L["name"],
                     "color": L["color"], "services": list(L["services"])}
    return sorted(by.values(), key=lambda L: L["no"])


def main():
    cities, diags = [], []

    shanghai = build_shanghai()
    suzhou = build_suzhou()
    tram = build_suzhou_tram()
    hangzhou = build_hangzhou()

    # 有轨电车并入苏州, 作为同城线路一起展示 (no=100+ 排在最后)
    if tram and suzhou:
        suzhou["lines"].extend(tram["lines"])
        suzhou["headways"].update(tram["headways"])
        suzhou["meta"]["sources"].extend(tram["meta"]["sources"])
        suzhou["meta"]["notes"].extend(tram["meta"]["notes"])
        suzhou.setdefault("diag", []).extend(tram.get("diag") or [])
        suzhou["fullName"] = "苏州轨道交通（含高新区有轨电车）"

    for c in (shanghai, suzhou, hangzhou):
        if not c or not c.get("lines"):
            continue
        diags.extend(c.pop("diag", []) or [])
        c["lines"] = merge_lines(c["lines"])
        cities.append(c)

    payload = {
        "meta": {
            "title": "长三角地铁 2D 动态线路图",
            "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "timezone": "Asia/Shanghai",
            "dwell": DWELL,
            "cityOrder": [c["key"] for c in cities],
        },
        "cities": {c["key"]: {k: v for k, v in c.items() if k != "key"} for c in cities},
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    js = ("/* 由 tools/build_data.py 自动生成, 请勿手工修改 */\n"
          "window.METRO_CITIES = " +
          json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(js)

    with open(os.path.join(BASE, "data", "build-report.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(diags) + "\n\n")
        for c in cities:
            svc = sum(len(L["services"]) for L in c["lines"])
            stn = len({s[0] for L in c["lines"] for s in L["services"][0]["st"]})
            f.write("%-10s 线路 %2d 条, 交路 %2d 个\n" % (c["name"], len(c["lines"]), svc))
        f.write("\n输出 %s  %.1f KB\n" % (OUT, len(js) / 1024.0))

    print("\n".join(diags))
    print()
    for c in cities:
        svc = sum(len(L["services"]) for L in c["lines"])
        print("%-10s 线路 %2d, 交路 %2d" % (c["name"], len(c["lines"]), svc))
    print("\n输出 %s  %.1f KB" % (OUT, len(js) / 1024.0))


if __name__ == "__main__":
    main()
