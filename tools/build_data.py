# -*- coding: utf-8 -*-
"""
构建上海地铁动态线路图所需的前端数据。

数据来源
--------
1) 站点经纬度 / 线路几何 / 线路色  <- 高德地图地铁图接口
   https://map.amap.com/service/subway?_1469083463978&srhdata=3100_drw_shanghai.json
   (原始文件: data/raw/t.json)
2) 各线路各站各方向首末班车时间    <- 上海地铁官方接口
   https://m.shmetro.com/interface/metromap/metromap.aspx?func=fltime&line=N
   (备用域名 marketing.cyberspaceit.cn; 原始文件: data/raw/official/fltime_N.txt)
3) 各线路行车间隔(列车间隔)分时段表  <- 上海地铁官网"首末班车时刻表"页
   https://service.shmetro.com/hcskb/index.htm
   (原始文件: data/raw/hcskb_0.html; 已人工整理为下面的 HEADWAY 表)

说明
----
- 站间运行时间: 官方未提供逐站运行时分，这里按"停车 35s + 里程/旅行速度"建模，
  并按线路调整旅行速度(16号线/磁浮/市域机场线为高速线)。目的总运行时分与公开
  的全程时长量级一致，属于"建模值"，不是官方逐站时刻表。
- 首末班车: 直接取官方 fltime 数据(含周五/周六延时运营的分钟增量与特定日期增量)。
- 行车间隔: 取自官方列车间隔表; 表中给出区间(range)的"其余时段"按线性过渡处理。
"""
import json
import math
import os
import re
import io
import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw")
OFFICIAL = os.path.join(RAW, "official")
OUT = os.path.join(BASE, "data", "metro-data.js")

# ---------------------------------------------------------------- 基础工具
def sec_of(hhmm):
    """'05:30' -> 19800 ; 无效返回 None"""
    if not hhmm:
        return None
    hhmm = hhmm.strip()
    if hhmm in ("--", "--:--", ""):
        return None
    m = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", hhmm)
    if not m:
        return None
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3) or 0)


def norm_name(name):
    """站名归一化，便于跨数据源匹配。"""
    if not name:
        return ""
    s = name.strip()
    s = re.sub(r"[（(][^）)]*[）)]", "", s)      # 去掉括号注释
    s = s.replace("站", "").replace("始发", "")
    s = s.replace("·", "").replace("・", "").replace("‧", "")
    s = re.sub(r"[\s\u3000]+", "", s)
    # 少量官方与高德的异名
    alias = {
        "浦东南路原东昌路": "浦东南路",
        "一大会址新天地": "新天地",
        "上海松江": "松江",
    }
    return alias.get(s, s)


def haversine(a, b):
    """两点球面距离(km)。a/b = (lng, lat)"""
    R = 6371.0088
    lng1, lat1 = a
    lng2, lat2 = b
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lng2 - lng1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


# ---------------------------------------------------------------- 官方线路色
# 官方兜底色值(与 m.shmetro.com 接口 func=lines 一致); 若 data/raw/api_lines.txt
# 存在则优先使用该文件(可重新抓取更新)。
FALLBACK_COLORS = {
    1: "#e3002b", 2: "#8cc220", 3: "#fcd600", 4: "#461d84", 5: "#944d9a",
    6: "#d40068", 7: "#ed6f00", 8: "#0094d8", 9: "#87caed", 10: "#c6afd4",
    11: "#871c2b", 12: "#007a60", 13: "#e999c0", 14: "#616020", 15: "#c8b38e",
    16: "#98d1c0", 17: "#bb796f", 18: "#C09453", 41: "#b5b6b6", 51: "#cccccc",
}


def load_official_colors():
    p = os.path.join(RAW, "api_lines.txt")
    if os.path.exists(p):
        try:
            data = json.loads(open(p, encoding="utf-8").read().strip())
            return {int(r["line_no"]): r["color"].lower() for r in data}
        except Exception:
            pass
    return {k: v.lower() for k, v in FALLBACK_COLORS.items()}


# ---------------------------------------------------------------- 高德线路数据
def load_amap():
    p = os.path.join(RAW, "amap_shanghai_subway.json")
    d = json.load(open(p, encoding="utf-8"))
    return d["l"]


# ---------------------------------------------------------------- 官方首末班车
def load_fltime(line_no):
    p = os.path.join(OFFICIAL, "fltime_%d.txt" % line_no)
    if not os.path.exists(p):
        return []
    txt = open(p, encoding="utf-8-sig").read().strip()
    if not txt:
        return []
    return json.loads(txt)


def parse_last_desc(desc):
    """官方 last_time_desc: {"weekday":[0,0,0,0,0,88,88],"dateday":[{"date":"12-31","adjust":"+78"}]}
    返回 (weekday[7], dateday列表) ; weekday 下标 0=周日 (与 JS getDay() 一致)"""
    if not desc:
        return [0] * 7, []
    try:
        o = json.loads(desc)
    except Exception:
        return [0] * 7, []
    wd = o.get("weekday") or [0] * 7
    wd = [int(x) for x in (list(wd) + [0] * 7)[:7]]
    dd = []
    for it in (o.get("dateday") or []):
        try:
            dd.append({"date": it["date"], "adjust": int(str(it["adjust"]).replace("+", ""))})
        except Exception:
            pass
    return wd, dd


def find_record(records, station_name, dest_name, dir_hint=None):
    """在 records 中找: 站名==station_name 且 description 含 dest_name 的记录。
    优先返回"始发"记录(firstarrival_time==0)，避免把终点到达时刻当成发车时刻。
    dir_hint: 环线用 '内'/'外' 匹配 description。"""
    ns = norm_name(station_name)
    cands = [r for r in records if norm_name(r.get("name")) == ns]
    if not cands:
        return None
    if dir_hint is not None:
        hit = [r for r in cands if dir_hint in (r.get("description") or "")]
        if hit:
            # 优先"全程"记录，其次始发记录
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


def station_extremes(records, station_name):
    """该站所有方向中最早的首班车 / 最晚的末班车，用作缺失值的兜底。"""
    ns = norm_name(station_name)
    f = [sec_of(r.get("first_time")) for r in records if norm_name(r.get("name")) == ns]
    l = [sec_of(r.get("last_time")) for r in records if norm_name(r.get("name")) == ns]
    f = [x for x in f if x is not None]
    l = [x for x in l if x is not None]
    return (min(f) if f else None), (max(l) if l else None)


def line_weekday_max(records):
    """整条线路各星期几的延时增量最大值。
    官方只在"延时运营区段"的车站上标注 last_time_desc, 例如 7 号线标注在祁华路,
    因此取全线最大值作为该线路的延时幅度。"""
    mx = [0] * 7
    for r in records:
        wd, _ = parse_last_desc(r.get("last_time_desc"))
        for i in range(7):
            if wd[i] > mx[i]:
                mx[i] = wd[i]
    return mx


# ---------------------------------------------------------------- 行车间隔表
# 来源: service.shmetro.com/hcskb (列车间隔表), 单位: 秒
# bands: (起, 止, 间隔秒) ; other: (最快, 最慢) 用于"其余时段/其他时段"线性过渡
def B(*bands):
    return list(bands)


def hm(h, m=0):
    """时:分 -> 当日秒数"""
    return h * 3600 + m * 60


HEADWAY_SPEC = {
    # 1号线 莘庄～富锦路
    "1A": {
        "weekday": {"bands": B((hm(7), hm(9), 150), (hm(9), hm(17), 300), (hm(17), hm(19), 180)),
                    "other": (240, 540), "src": "工作日 早高峰2分30秒/平峰5分/晚高峰3分/其余4~9分"},
        "friday": {"bands": B((hm(7), hm(9), 150), (hm(9), hm(15), 300), (hm(15), hm(19), 180)),
                   "other": (240, 540), "src": "周五 晚高峰提前到15:00"},
        "weekend": {"bands": B((hm(9), hm(20), 240)), "other": (360, 720),
                    "src": "周六日 高峰4分/其余6~12分"},
        "extended": {"bands": B((hm(22, 30), hm(30), 750)), "other": (750, 750),
                     "src": "周五周六延时 10~15分"},
    },
    # 2号线 蟠祥路·国家会计学院～浦东1号2号航站楼 (按淞虹路～广兰路主段取值)
    "2A": {
        "weekday": {"bands": B((hm(7, 30), hm(10), 150), (hm(10), hm(17), 300), (hm(17), hm(20, 30), 180)),
                    "other": (300, 600), "src": "工作日 主段早高峰2分30秒/平峰5分/晚高峰3分/其他5~10分"},
        "weekend": {"bands": B((hm(8, 30), hm(20, 30), 240)), "other": (300, 600),
                    "src": "周六日 高峰4分/其他5~10分"},
        "extended": {"bands": B((hm(23), hm(30), 900)), "other": (900, 900),
                     "src": "周五周六延时 10~20分(广兰路～徐泾东)"},
    },
    # 3号线 上海南站～江杨北路
    "3A": {
        "weekday": {"bands": B((hm(7, 30), hm(9, 30), 400), (hm(9, 30), hm(17), 480), (hm(17), hm(19, 30), 300)),
                    "other": (480, 600), "src": "工作日 早高峰往江杨北路6分40秒/平峰8分/晚高峰5分"},
        "weekend": {"bands": B((hm(8), hm(20), 480)), "other": (420, 600),
                    "src": "周六日 高峰6分30秒~13分(取中)"},
    },
    # 4号线 环线 (内圈/外圈分别取值)
    "4A": {
        "weekday": {"bands": B((hm(7, 30), hm(9), 240), (hm(9), hm(17), 480), (hm(17), hm(19, 30), 300)),
                    "other": (420, 900), "src": "工作日 内圈早高峰4分/平峰8分/晚高峰5分/其他7~15分"},
        "weekend": {"bands": B((hm(8), hm(20), 390)), "other": (420, 900),
                    "src": "周六日 高峰6分30秒/其他7~15分"},
    },
    "4B": {
        "weekday": {"bands": B((hm(7, 30), hm(9), 400), (hm(9), hm(17), 480), (hm(17), hm(19, 30), 300)),
                    "other": (420, 900), "src": "工作日 外圈早高峰6分40秒/平峰8分/晚高峰5分"},
        "weekend": {"bands": B((hm(8), hm(20), 390)), "other": (420, 900),
                    "src": "周六日 高峰6分30秒"},
    },
    # 5号线 主线 莘庄↔奉贤新城 (外段 东川路～奉贤新城 间隔)
    "5A": {
        "weekday": {"bands": B((hm(7), hm(9, 30), 225), (hm(9, 30), hm(17), 720), (hm(17), hm(20), 270)),
                    "other": (450, 720), "src": "工作日 东川路～奉贤新城 早高峰3分45秒/平峰12分/晚高峰4分30秒"},
        "weekend": {"bands": B((hm(7), hm(20), 540)), "other": (450, 720),
                    "src": "周六日 高峰9分"},
    },
    # 5号线 支线 莘庄↔闵行开发区
    "5B": {
        "weekday": {"bands": B((hm(7), hm(9, 30), 450), (hm(9, 30), hm(17), 720), (hm(17), hm(20), 540)),
                    "other": (450, 720), "src": "工作日 东川路～闵行开发区 早高峰7分30秒/平峰12分/晚高峰9分"},
        "weekend": {"bands": B((hm(7), hm(20), 540)), "other": (450, 720),
                    "src": "周六日 高峰9分"},
    },
    # 6号线 港城路～东方体育中心 (按巨峰路～高青路主段)
    "6A": {
        "weekday": {"bands": B((hm(7, 20), hm(9), 150), (hm(9), hm(16, 30), 390), (hm(16, 30), hm(19), 225)),
                    "other": (300, 720), "src": "工作日 早高峰2分/平峰6分30秒/晚高峰2分30秒~3分45秒"},
        "weekend": {"bands": B((hm(8, 30), hm(20, 30), 240)), "other": (300, 720),
                    "src": "周六日 高峰4分/其他5~12分"},
    },
    # 7号线 美兰湖～花木路
    "7A": {
        "weekday": {"bands": B((hm(7, 30), hm(9), 180), (hm(9), hm(17, 30), 420), (hm(17, 30), hm(19), 240)),
                    "other": (300, 660), "src": "工作日 早高峰2分~3分30秒/平峰7分/晚高峰2分30秒~5分30秒"},
        "weekend": {"bands": B((hm(8), hm(20), 420)), "other": (300, 660),
                    "src": "周六日 高峰6分~9分"},
        "extended": {"bands": B((hm(22, 30), hm(30), 1080)), "other": (1080, 1080),
                     "src": "周五周六延时 平均18分"},
    },
    # 8号线 市光路～沈杜公路
    "8A": {
        "weekday": {"bands": B((hm(7, 15), hm(9, 20), 150), (hm(9, 20), hm(17), 300), (hm(17), hm(19, 20), 200)),
                    "other": (300, 720), "src": "工作日 早高峰2分~2分30秒/平峰4分20秒~8分40秒/晚高峰2分45秒~5分30秒"},
        "weekend": {"bands": B((hm(8), hm(19), 280)), "other": (300, 720),
                    "src": "周六日 高峰3分40秒~5分30秒"},
        "extended": {"bands": B((hm(22, 30), hm(30), 750)), "other": (750, 750),
                     "src": "周五周六延时 10~15分"},
    },
    # 9号线 上海松江站～曹路
    "9A": {
        "weekday": {"bands": B((hm(7, 30), hm(9), 180), (hm(9), hm(17), 360), (hm(17), hm(19, 30), 210)),
                    "other": (360, 600), "src": "工作日 早高峰1分50秒~5分30秒/平峰6分/晚高峰2分15秒~6分"},
        "weekend": {"bands": B((hm(8), hm(20), 300)), "other": (360, 600),
                    "src": "周六日 高峰5分/其他6~10分"},
        "extended": {"bands": B((hm(22, 55), hm(30), 1020)), "other": (1020, 1020),
                     "src": "周五周六延时 16~18分(佘山～杨高中路)"},
    },
    # 10号线 虹桥火车站↔基隆路
    "10A": {
        "weekday": {"bands": B((hm(7, 30), hm(9), 240), (hm(9), hm(17, 30), 300), (hm(17, 30), hm(20), 270)),
                    "other": (300, 480), "src": "工作日 虹桥火车站～龙溪路 早高峰3~5分/平峰6分/晚高峰4分30秒"},
        "weekend": {"bands": B((hm(7), hm(22, 30), 360)), "other": (300, 480),
                    "src": "周六日 高峰6分"},
        "extended": {"bands": B((hm(22, 30), hm(30), 870)), "other": (870, 870),
                     "src": "周五周六延时 14~15分"},
    },
    # 10号线 航中路↔基隆路
    "10B": {
        "weekday": {"bands": B((hm(7, 30), hm(9), 480), (hm(9), hm(17, 30), 540), (hm(17, 30), hm(20), 420)),
                    "other": (300, 660), "src": "工作日 航中路～龙溪路 早高峰6分45秒~9分/平峰12分/晚高峰9分"},
        "weekend": {"bands": B((hm(7), hm(22, 30), 600)), "other": (300, 660),
                    "src": "周六日 高峰10分"},
        "extended": {"bands": B((hm(22, 30), hm(30), 870)), "other": (870, 870),
                     "src": "周五周六延时"},
    },
    # 11号线 嘉定北↔迪士尼
    "11A": {
        "weekday": {"bands": B((hm(7, 30), hm(9), 330), (hm(9), hm(18), 450), (hm(18), hm(19), 330)),
                    "other": (420, 600), "src": "工作日 嘉定北～嘉定新城 早高峰5~10分/平峰12分/晚高峰6~7分"},
        "weekend": {"bands": B((hm(8), hm(20), 450)), "other": (480, 720),
                    "src": "周六日 高峰10分/其余10~12分"},
    },
    # 11号线 花桥↔迪士尼
    "11B": {
        "weekday": {"bands": B((hm(7, 30), hm(9), 330), (hm(9), hm(18), 450), (hm(18), hm(19), 330)),
                    "other": (420, 600), "src": "工作日 花桥～嘉定新城 早高峰7分30秒~10分/平峰12分"},
        "weekend": {"bands": B((hm(8), hm(20), 450)), "other": (480, 720),
                    "src": "周六日 高峰10分"},
    },
    # 12号线 七莘路～金海路
    "12A": {
        "weekday": {"bands": B((hm(7, 30), hm(9, 30), 165), (hm(9, 30), hm(16, 30), 420), (hm(16, 30), hm(20), 225)),
                    "other": (360, 540), "src": "工作日 早高峰2分45秒/平峰7分/晚高峰3分45秒"},
        "weekend": {"bands": B((hm(8), hm(19), 360)), "other": (480, 660),
                    "src": "周六日 高峰6分/其余8~11分"},
    },
    # 13号线 金运路～张江路
    "13A": {
        "weekday": {"bands": B((hm(7, 30), hm(9, 30), 220), (hm(9, 30), hm(17), 420), (hm(17), hm(19, 30), 240)),
                    "other": (360, 600), "src": "工作日 早高峰2分45秒/平峰7分/晚高峰3分"},
        "weekend": {"bands": B((hm(8, 30), hm(20, 30), 360)), "other": (360, 600),
                    "src": "周六日 高峰6分/其余6~10分"},
        "extended": {"bands": B((hm(22, 30), hm(30), 1020)), "other": (1020, 1020),
                     "src": "周五周六延时 15~20分"},
    },
    # 14号线 封浜～桂桥路
    "14A": {
        "weekday": {"bands": B((hm(7), hm(9, 30), 240), (hm(9, 30), hm(16, 40), 510), (hm(16, 40), hm(20), 320)),
                    "other": (300, 720), "src": "工作日 真新新村～蓝天路 早高峰3分/平峰8分30秒/晚高峰4分"},
        "weekend": {"bands": B((hm(7), hm(21), 420)), "other": (300, 720),
                    "src": "周六日 高峰7分/其他5~12分"},
    },
    # 15号线 紫竹高新区～顾村公园
    "15A": {
        "weekday": {"bands": B((hm(7, 20), hm(9, 20), 300), (hm(9, 20), hm(16, 30), 480), (hm(16, 30), hm(20), 360)),
                    "other": (300, 780), "src": "工作日 双柏路～古浪路 早高峰3分~3分40秒/平峰8分/晚高峰4分30秒"},
        "weekend": {"bands": B((hm(7), hm(20, 20), 450)), "other": (360, 780),
                    "src": "周六日 高峰7分30秒/其余6~13分"},
    },
    # 16号线 龙阳路～滴水湖
    "16A": {
        "weekday": {"bands": B((hm(7, 30), hm(10, 30), 210), (hm(10, 30), hm(16, 30), 450), (hm(16, 30), hm(21, 30), 240)),
                    "other": (480, 720), "src": "工作日 早高峰3分30秒/平峰7分30秒/晚高峰4分/其余8~12分"},
        "weekend": {"bands": B((hm(7), hm(20, 30), 360)), "other": (300, 720),
                    "src": "周六日 高峰6分/其余5~12分"},
    },
    # 17号线 虹桥火车站～西岑
    "17A": {
        "weekday": {"bands": B((hm(7), hm(9, 30), 240), (hm(9, 30), hm(17), 600), (hm(17), hm(20), 360)),
                    "other": (480, 660), "src": "工作日 淀山湖大道～虹桥火车站 早高峰3分/平峰10分/晚高峰4分"},
        "weekend": {"bands": B((hm(7, 30), hm(21), 420)), "other": (420, 840),
                    "src": "周六日 高峰7分/其余7~14分"},
    },
    # 18号线 康文路～航头
    "18A": {
        "weekday": {"bands": B((hm(7, 30), hm(9), 240), (hm(9), hm(17), 480), (hm(17), hm(19, 10), 280)),
                    "other": (420, 780), "src": "工作日 沈梅路～长江南路 早高峰2分45秒/平峰8分/晚高峰3分30秒"},
        "weekend": {"bands": B((hm(7), hm(21), 390)), "other": (480, 900),
                    "src": "周六日 高峰6分30秒/其余8~15分"},
    },
    # 浦江线 沈杜公路～汇臻路
    "41A": {
        "weekday": {"bands": B((hm(7), hm(9), 255), (hm(9), hm(18), 600), (hm(18), hm(20), 300)),
                    "other": (600, 600), "src": "工作日 早高峰4分15秒/平峰10分/晚高峰5分"},
        "weekend": {"bands": B((hm(7), hm(20), 600)), "other": (600, 600),
                    "src": "周六日 全天约10分"},
    },
    # 市域机场线 虹桥2号航站楼～浦东1号2号航站楼
    "51A": {
        "weekday": {"bands": B((hm(6), hm(23), 900)), "other": (900, 900), "src": "官方: 全天平均15分"},
        "weekend": {"bands": B((hm(6), hm(23), 900)), "other": (900, 900), "src": "官方: 全天平均15分"},
    },
    # 磁浮线 (参考公开信息)
    "cfA": {
        "weekday": {"bands": B((hm(6, 45), hm(21, 40), 900)), "other": (900, 900), "src": "参考公开信息: 约15分一班"},
        "weekend": {"bands": B((hm(6, 45), hm(21, 40), 900)), "other": (900, 900), "src": "参考公开信息: 约15分一班"},
    },
}

# 线路旅行速度(km/h)与停站时间(秒)。默认 48 km/h / 35 s。
LINE_SPEED = {
    "16号线": 72.0,
    "磁浮线": 200.0,
    "市域机场线": 100.0,
    "5号线": 52.0,
    "17号线": 58.0,
}
DEFAULT_SPEED = 48.0
DWELL = 35.0

# 高德线路名 -> 官方线路编号 / 显示名 / 间隔方案
#   hw = ["XX"]                     全线同一间隔方案
#   hw = {"fwd":..,"rev":..}         环线: 内圈/外圈 间隔不同
#   hw = {"by_dest":{站名:方案key},  多交路: 按该交路终点选方案
#         "default":key}
LINE_META = {
    "1号线":  dict(no=1,  name="1号线",  hw=["1A"]),
    "2号线":  dict(no=2,  name="2号线",  hw=["2A"]),
    "3号线":  dict(no=3,  name="3号线",  hw=["3A"]),
    "4号线":  dict(no=4,  name="4号线",  hw={"fwd": "4A", "rev": "4B"}),   # fwd=内圈 rev=外圈
    "5号线":  dict(no=5,  name="5号线",  hw={"by_dest": {"奉贤新城": "5A", "闵行开发区": "5B"}, "default": "5A"}),
    "6号线":  dict(no=6,  name="6号线",  hw=["6A"]),
    "7号线":  dict(no=7,  name="7号线",  hw=["7A"]),
    "8号线":  dict(no=8,  name="8号线",  hw=["8A"]),
    "9号线":  dict(no=9,  name="9号线",  hw=["9A"]),
    "10号线": dict(no=10, name="10号线", hw={"by_dest": {"航中路": "10B", "虹桥火车站": "10A"}, "default": "10A"}),
    "11号线": dict(no=11, name="11号线", hw={"by_dest": {"嘉定北": "11A", "花桥": "11B"}, "default": "11A"}),
    "12号线": dict(no=12, name="12号线", hw=["12A"]),
    "13号线": dict(no=13, name="13号线", hw=["13A"]),
    "14号线": dict(no=14, name="14号线", hw=["14A"]),
    "15号线": dict(no=15, name="15号线", hw=["15A"]),
    "16号线": dict(no=16, name="16号线", hw=["16A"]),
    "17号线": dict(no=17, name="17号线", hw=["17A"]),
    "18号线": dict(no=18, name="18号线", hw=["18A"]),
    "浦江线": dict(no=41, name="浦江线", hw=["41A"]),
    "市域机场线": dict(no=51, name="市域机场线", hw=["51A"]),
    "磁浮线": dict(no=None, name="磁浮线", hw=["cfA"]),
}


def pick_hw(meta, dest_name, direction):
    hw = meta["hw"]
    if isinstance(hw, list):
        return hw[0]
    if "fwd" in hw:
        return hw["fwd"] if direction == "fwd" else hw["rev"]
    if "by_dest" in hw:
        return hw["by_dest"].get(dest_name, hw.get("default"))
    return hw

# 手工指定首末班车(仅用于官方接口未覆盖的磁浮线)
MANUAL_FL = {
    "磁浮线": {
        "fwd": {"first": 6 * 3600 + 45 * 60, "last": 21 * 3600 + 40 * 60},
        "rev": {"first": 7 * 3600 + 2 * 60,  "last": 21 * 3600 + 55 * 60},
    }
}


def build_run_offsets(stations, speed_kmh):
    """返回累计运行时间(秒)数组与各段距离。"""
    dists = []
    for i in range(1, len(stations)):
        dists.append(haversine((stations[i - 1]["x"], stations[i - 1]["y"]),
                               (stations[i]["x"], stations[i]["y"])))
    v = speed_kmh * 1000.0 / 3600.0     # m/s
    offs = [0.0]
    t = 0.0
    for d in dists:
        t += d * 1000.0 / v + DWELL
        offs.append(t)
    return offs, dists


def headways_for_json():
    """把 bands 由元组转成 {t0,t1,h} 对象, 便于前端直接读取属性。"""
    out = {}
    for k, spec in HEADWAY_SPEC.items():
        o = {}
        for day, ds in spec.items():
            o[day] = {
                "bands": [{"t0": int(b[0]), "t1": int(b[1]), "h": int(b[2])} for b in ds["bands"]],
                "other": [int(ds["other"][0]), int(ds["other"][1])],
                "src": ds.get("src", "")
            }
        out[k] = o
    return out


def main():
    colors = load_official_colors()
    entries = load_amap()

    # 官方首末班车缓存
    fl_cache = {}
    for no in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 41, 51]:
        fl_cache[no] = load_fltime(no)

    # 按线路分组高德条目
    groups = {}
    for e in entries:
        groups.setdefault(e["ln"], []).append(e)

    lines_out = []
    diag = []
    for lname, ents in groups.items():
        meta = LINE_META.get(lname)
        if not meta:
            continue
        no = meta["no"]
        color = colors.get(no) if no else None
        if not color:
            color = "#" + (ents[0].get("cl") or "888888").lower()
        records = fl_cache.get(no, [])
        line_wd_max = line_weekday_max(records)

        services = []
        for si, e in enumerate(ents):
            st = e.get("st") or []
            if len(st) < 2:
                continue
            loop = str(e.get("lo", "0")) == "1"
            stations = []
            for s in st:
                sl = (s.get("sl") or "").split(",")
                if len(sl) != 2:
                    continue
                try:
                    x, y = float(sl[0]), float(sl[1])
                except ValueError:
                    continue
                stations.append({"n": s.get("n"), "x": round(x, 6), "y": round(y, 6)})
            if len(stations) < 2:
                continue
            if loop:
                # 环线: 末尾补回首站, 形成闭合环
                stations.append(dict(stations[0]))

            speed = LINE_SPEED.get(lname, DEFAULT_SPEED)
            offs, dists = build_run_offsets(stations, speed)
            total = offs[-1]

            origin = stations[0]["n"]
            dest = stations[-1]["n"]
            # 环路: 方向名为 内圈/外圈
            if loop:
                d_fwd_name, d_rev_name = "内圈", "外圈"
            else:
                d_fwd_name, d_rev_name = "往" + dest, "往" + origin

            def fl(s_origin, s_dest, dir_hint=None):
                """取 s_origin 站 往 s_dest 的首末班车, 返回 (first, last, wd, dd, ok)"""
                if lname in MANUAL_FL:
                    mf = MANUAL_FL[lname]
                    side = "fwd" if s_origin == stations[0]["n"] else "rev"
                    return mf[side]["first"], mf[side]["last"], [0] * 7, [], True
                r = find_record(records, s_origin, s_dest, dir_hint)
                f = l = None
                wd, dd = [0] * 7, []
                if r:
                    f = sec_of(r.get("first_time"))
                    l = sec_of(r.get("last_time"))
                    wd, dd = parse_last_desc(r.get("last_time_desc"))
                ok = f is not None
                # 该交路是否有延时运营方案; 有则套用全线最大延时幅度
                ext = HEADWAY_SPEC.get(hw_fwd, {}).get("extended") or \
                      HEADWAY_SPEC.get(hw_rev, {}).get("extended")
                if ext and not any(wd):
                    if any(line_wd_max):
                        wd = list(line_wd_max)
                if f is None or l is None:
                    ef, el = station_extremes(records, s_origin)
                    if f is None:
                        f = ef
                    if l is None:
                        l = el
                    if not dd:
                        for rr in records:
                            if norm_name(rr.get("name")) == norm_name(s_origin):
                                w2, d2 = parse_last_desc(rr.get("last_time_desc"))
                                if any(w2) or d2:
                                    wd, dd = w2, d2
                                    break
                return f, l, wd, dd, ok

            # 该交路对应的行车间隔方案
            if isinstance(meta["hw"], dict) and "fwd" in meta["hw"]:
                hw_fwd, hw_rev = meta["hw"]["fwd"], meta["hw"]["rev"]
            else:
                k = pick_hw(meta, dest, "fwd")
                hw_fwd = hw_rev = k

            if loop:
                f1, l1, wd1, dd1, ok1 = fl(origin, dest, "内")
                f2, l2, wd2, dd2, ok2 = fl(origin, dest, "外")
            else:
                f1, l1, wd1, dd1, ok1 = fl(origin, dest)
                f2, l2, wd2, dd2, ok2 = fl(dest, origin)

            def mk(f, l, wd, dd, ok):
                return {"first": int(f) if f is not None else 5 * 3600 + 30 * 60,
                        "last": int(l) if l is not None else 22 * 3600 + 30 * 60,
                        "wd": wd, "dd": dd, "found": bool(ok)}

            services.append({
                "id": "%s-%d" % (no if no else lname, si),
                "name": meta["name"],
                "from": origin,
                "to": dest,
                "loop": loop,
                "dirNames": [d_fwd_name, d_rev_name],
                "st": [[s["n"], s["x"], s["y"]] for s in stations],
                "off": [int(round(v)) for v in offs],
                "total": int(round(total)),
                "dists": [round(d, 3) for d in dists],
                "fwd": mk(f1, l1, wd1, dd1, ok1),
                "rev": mk(f2, l2, wd2, dd2, ok2),
                "hw": hw_fwd,
                "hwRev": hw_rev,
                "speed": speed,
            })
            diag.append("%-8s svc%d %-14s -> %-14s st=%2d len=%5.1fkm run=%3dmin  fwd %s/%s%s  rev %s/%s%s  hw=%s/%s" % (
                meta["name"], si, origin, dest, len(stations),
                sum(dists), total / 60.0,
                fmt(f1), fmt(l1), "" if ok1 else "(兜底)",
                fmt(f2), fmt(l2), "" if ok2 else "(兜底)",
                hw_fwd, hw_rev))

        if not services:
            continue

        lines_out.append({
            "no": no if no else -1,
            "name": meta["name"],
            "color": color,
            "services": services,
        })

    lines_out.sort(key=lambda L: (L["no"] if L["no"] > 0 else 900))

    payload = {
        "meta": {
            "title": "上海地铁 2D 动态线路图",
            "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "timezone": "Asia/Shanghai",
            "sources": [
                {"name": "上海地铁官网 首末班车时刻表 / 列车间隔表",
                 "url": "https://service.shmetro.com/hcskb/index.htm"},
                {"name": "上海地铁首末班车接口",
                 "url": "https://m.shmetro.com/interface/metromap/metromap.aspx?func=fltime&line=N"},
                {"name": "高德地图 上海地铁线路与站点坐标",
                 "url": "https://map.amap.com/service/subway?srhdata=3100_drw_shanghai.json"},
            ],
            "notes": [
                "首末班车时间与列车间隔来自上海地铁官方公布数据。",
                "站间运行时间为建模值(停车35秒 + 里程/旅行速度)，非官方逐站时刻表。",
                "周五、周六 1/7/8/9/10/13 号线等实施延时运营，已体现在数据中。",
                "磁浮线班次为参考公开信息估算。",
            ],
            "dwell": DWELL,
        },
        "headways": headways_for_json(),
        "lines": lines_out,
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    js = "/* 由 tools/build_data.py 自动生成，请勿手工修改 */\nwindow.SHMETRO_DATA = " + \
         json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n"
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(js)

    report = "\n".join(diag)
    with open(os.path.join(BASE, "data", "build-report.txt"), "w", encoding="utf-8") as f:
        f.write(report + "\n\n")
        f.write("输出: %s\n大小: %.1f KB\n线路数: %d\n" % (OUT, len(js) / 1024.0, len(lines_out)))
        tot = sum(len(L["services"]) for L in lines_out)
        f.write("服务(路径)数: %d\n" % tot)
    print(report)
    print("\n输出 %s  %.1f KB  线路 %d" % (OUT, len(js) / 1024.0, len(lines_out)))


def fmt(s):
    if s is None:
        return "--:--"
    return "%02d:%02d" % (int(s) // 3600 % 24, int(s) // 60 % 60)


if __name__ == "__main__":
    main()
