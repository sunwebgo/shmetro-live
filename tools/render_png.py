# -*- coding: utf-8 -*-
"""把 snapshot.js 导出的绘制数据渲染成 PNG(用于目视校验)。

配色与网页的浅色主题保持一致。

用法: python render_png.py <snapshot.json> <out.png>
"""
import json
import math
import sys
import os
from PIL import Image, ImageDraw, ImageFont

SS = 2  # 超采样倍数(抗锯齿)

C_BG_TOP = (255, 255, 255)
C_BG_BOT = (230, 237, 246)
C_TXT = (22, 35, 58)
C_TXT2 = (130, 152, 173)
C_PANEL = (255, 255, 255)
C_BORDER = (220, 228, 238)


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def disp_color(h):
    """与前端一致: 白底上过浅的官方色适当加深。"""
    return _shade(h, _lum_factor(h))


def _shade(h, f):
    r, g, b = hex2rgb(h)
    if f == 1.0:
        return (r, g, b)
    return (round(r * f), round(g * f), round(b * f))


def _lum_factor(h):
    r, g, b = hex2rgb(h)
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    return 0.68 if lum > 205 else (0.80 if lum > 180 else (0.90 if lum > 160 else 1.0))


def train_color(h):
    """列车用同色系的更深色(不用白描边, 否则会把线路切成虚线)。"""
    return _shade(h, _lum_factor(h) * 0.62)


def load_font(size):
    for p in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc",
              r"C:\Windows\Fonts\simhei.ttf", r"C:\Windows\Fonts\simsun.ttc"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def bg_gradient(W, H, ss):
    """自上而下的浅色渐变, 近似网页的径向背景。"""
    img = Image.new("RGB", (1, H * ss))
    px = img.load()
    for y in range(H * ss):
        t = y / max(1, H * ss - 1)
        # 中间偏亮、上下略深
        k = 0.5 - abs(t - 0.45) * 1.1
        f = max(0.0, min(1.0, k))
        c = tuple(int(C_BG_BOT[i] + (C_BG_TOP[i] - C_BG_BOT[i]) * f) for i in range(3))
        px[0, y] = c
    return img.resize((W * ss, H * ss), Image.BILINEAR)


def main():
    src = sys.argv[1]
    dst = sys.argv[2]
    d = json.load(open(src, encoding="utf-8"))
    W, H = d["meta"]["W"], d["meta"]["H"]
    img = bg_gradient(W, H, SS)
    dr = ImageDraw.Draw(img, "RGBA")

    def S(v):
        return v * SS

    # ---- 线路 ----
    for p in d["paths"]:
        col = disp_color(p["color"])
        pts = [(S(x), S(y)) for x, y in p["pts"]]
        dr.line(pts, fill=col + (243,), width=int(3.8 * SS), joint="curve")
        for (x, y) in (pts[0], pts[-1]):
            r = 1.9 * SS
            dr.ellipse([x - r, y - r, x + r, y + r], fill=col + (243,))

    # ---- 车站: 只画换乘站(单线站画点会把线路切成虚线段) ----
    for s in d["stations"]:
        if s["lines"] < 2:
            continue
        x, y = S(s["x"]), S(s["y"])
        r = 3.2 * SS
        dr.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, 255),
                   outline=(63, 88, 114, 255), width=max(1, int(1.7 * SS)))

    # ---- 列车: 白色车厢 + 线路色描边 ----
    for t in d["trains"]:
        x, y = S(t["x"]), S(t["y"])
        ang = math.atan2(t["dy"], t["dx"])
        if t["rev"]:
            ang += math.pi
        L, Wd = 8.4 * SS, 5.2 * SS
        ca, sa = math.cos(ang), math.sin(ang)
        corners = []
        for cx, cy in ((-L / 2, -Wd / 2 + 0.7), (L / 2 - 0.7, -Wd / 2 + 0.7),
                       (L / 2 - 0.7, Wd / 2 - 0.7), (-L / 2, Wd / 2 - 0.7)):
            corners.append((x + cx * ca - cy * sa, y + cx * sa + cy * ca))
        col = train_color(t["color"])
        dr.polygon(corners, fill=(255, 255, 255, 255), outline=col + (255,),
                   width=max(2, int(1.3 * SS)))

    # ---- 标题卡 ----
    f1 = load_font(int(22 * SS))
    f2 = load_font(int(13 * SS))
    m = d["meta"]
    title = "%s 2D 动态线路图 · %s %s" % (m.get("cityName") or "城市轨道", m["dateLabel"], m["dayLabel"])
    dr.rounded_rectangle([S(14), S(14), S(452), S(78)], radius=S(10),
                         fill=C_PANEL + (242,), outline=C_BORDER + (255,), width=max(1, int(SS)))
    dr.text((S(28), S(22)), title, font=f1, fill=C_TXT + (255,))
    dr.text((S(28), S(52)), "时刻 %s   在线列车 %d 列   数据生成 %s"
            % (m["hhmm"], m["trains"], m["generated"]), font=f2, fill=C_TXT2 + (255,))

    # ---- 右下角线路统计 ----
    rows = [s for s in d["summary"] if s["running"]]
    rows.sort(key=lambda r: -r["trains"])
    rows = rows[:22]
    bw, bh = 320, 30 + 18 * max(1, len(rows))
    x0, y0 = W - bw - 14, H - bh - 14
    dr.rounded_rectangle([S(x0), S(y0), S(W - 14), S(H - 14)], radius=S(10),
                         fill=C_PANEL + (240,), outline=C_BORDER + (255,), width=max(1, int(SS)))
    dr.text((S(x0 + 12), S(y0 + 8)), "运行中线路 / 当前发车间隔 / 在线列车",
            font=f2, fill=C_TXT2 + (255,))
    for i, r in enumerate(rows):
        yy = y0 + 30 + 18 * i
        dr.rounded_rectangle([S(x0 + 12), S(yy + 5), S(x0 + 26), S(yy + 9)], radius=S(2),
                             fill=hex2rgb(r["color"]) + (255,))
        dr.text((S(x0 + 32), S(yy)), r["name"], font=f2, fill=C_TXT + (255,))
        hw = "%ds" % r["hwMin"] if r["hwMin"] == r["hwMax"] else "%d~%ds" % (r["hwMin"], r["hwMax"])
        dr.text((S(x0 + 158), S(yy)), hw, font=f2, fill=C_TXT2 + (255,))
        dr.text((S(x0 + bw - 44), S(yy)), "%d 列" % r["trains"], font=f2, fill=C_TXT + (255,))

    img = img.resize((W, H), Image.LANCZOS)
    img.save(dst)
    print("saved %s  %dx%d  trains=%d" % (dst, W, H, d["meta"]["trains"]))


if __name__ == "__main__":
    main()
