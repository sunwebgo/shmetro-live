# -*- coding: utf-8 -*-
"""把 snapshot.js 导出的绘制数据渲染成 PNG(用于目视校验)。

用法: python render_png.py <snapshot.json> <out.png>
"""
import json
import math
import sys
import os
from PIL import Image, ImageDraw, ImageFont

SS = 2  # 超采样倍数(抗锯齿)


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def load_font(size):
    for p in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc",
              r"C:\Windows\Fonts\simhei.ttf", r"C:\Windows\Fonts\simsun.ttc"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def main():
    src = sys.argv[1]
    dst = sys.argv[2]
    d = json.load(open(src, encoding="utf-8"))
    W, H = d["meta"]["W"], d["meta"]["H"]
    img = Image.new("RGB", (W * SS, H * SS), (13, 17, 23))
    dr = ImageDraw.Draw(img, "RGBA")

    def S(v):
        return v * SS

    # ---- 线路 ----
    for p in d["paths"]:
        col = hex2rgb(p["color"])
        pts = [(S(x), S(y)) for x, y in p["pts"]]
        dr.line(pts, fill=col + (235,), width=int(3.4 * SS), joint="curve")
        # 线端补圆, 避免尖角
        for (x, y) in (pts[0], pts[-1]):
            r = 1.7 * SS
            dr.ellipse([x - r, y - r, x + r, y + r], fill=col + (235,))

    # ---- 车站 ----
    for s in d["stations"]:
        x, y = S(s["x"]), S(s["y"])
        big = s["lines"] > 1
        r = (3.1 if big else 2.1) * SS
        dr.ellipse([x - r, y - r, x + r, y + r], fill=(13, 17, 23, 255),
                   outline=(230, 237, 243, 255), width=int((1.7 if big else 1.2) * SS))

    # ---- 列车 ----
    for t in d["trains"]:
        x, y = S(t["x"]), S(t["y"])
        ang = math.atan2(t["dy"], t["dx"])
        if t["rev"]:
            ang += math.pi
        L, Wd = 6.4 * SS, 3.8 * SS
        ca, sa = math.cos(ang), math.sin(ang)
        corners = []
        for cx, cy in ((-L / 2, -Wd / 2), (L / 2, -Wd / 2), (L / 2, Wd / 2), (-L / 2, Wd / 2)):
            corners.append((x + cx * ca - cy * sa, y + cx * sa + cy * ca))
        col = hex2rgb(t["color"])
        dr.polygon(corners, fill=col + (255,), outline=(255, 255, 255, 240), width=max(1, int(1.0 * SS)))
        # 车头方向标记
        nose = []
        for cx, cy in ((L / 2 - 0.4, 0), (L / 2 - 2.6, -Wd / 2 + 0.6), (L / 2 - 2.6, Wd / 2 - 0.6)):
            nose.append((x + cx * ca - cy * sa, y + cx * sa + cy * ca))
        dr.polygon(nose, fill=(255, 255, 255, 235))

    # ---- 标题 ----
    f1 = load_font(int(22 * SS))
    f2 = load_font(int(13 * SS))
    m = d["meta"]
    title = "%s 2D 动态线路图 · %s %s" % (m.get("cityName") or "城市轨道", m["dateLabel"], m["dayLabel"])
    dr.rectangle([S(14), S(14), S(430), S(74)], fill=(15, 22, 31, 225), outline=(34, 48, 63, 255))
    dr.text((S(26), S(20)), title, font=f1, fill=(230, 237, 243, 255))
    dr.text((S(26), S(50)), "时刻 %s   在线列车 %d 列   数据生成 %s"
            % (m["hhmm"], m["trains"], m["generated"]), font=f2, fill=(159, 176, 195, 255))

    # ---- 右下角线路统计 ----
    rows = [s for s in d["summary"] if s["running"]]
    rows.sort(key=lambda r: -r["trains"])
    bw, bh = 320, 26 + 18 * min(len(rows), 22)
    x0, y0 = W - bw - 14, H - bh - 14
    dr.rectangle([S(x0), S(y0), S(W - 14), S(H - 14)], fill=(15, 22, 31, 232), outline=(34, 48, 63, 255))
    dr.text((S(x0 + 10), S(y0 + 7)), "运行中线路 / 当前发车间隔 / 在线列车",
            font=f2, fill=(159, 176, 195, 255))
    for i, r in enumerate(rows[:22]):
        yy = y0 + 26 + 18 * i
        dr.rectangle([S(x0 + 10), S(yy + 5), S(x0 + 24), S(yy + 9)], fill=hex2rgb(r["color"]) + (255,))
        dr.text((S(x0 + 30), S(yy)), r["name"], font=f2, fill=(214, 226, 238, 255))
        hw = "%ds" % r["hwMin"] if r["hwMin"] == r["hwMax"] else "%d~%ds" % (r["hwMin"], r["hwMax"])
        dr.text((S(x0 + 110), S(yy)), hw, font=f2, fill=(140, 158, 176, 255))
        dr.text((S(x0 + bw - 40), S(yy)), "%d 列" % r["trains"], font=f2, fill=(230, 237, 243, 255))

    img = img.resize((W, H), Image.LANCZOS)
    img.save(dst)
    print("saved %s  %dx%d  trains=%d" % (dst, W, H, d["meta"]["trains"]))


if __name__ == "__main__":
    main()
