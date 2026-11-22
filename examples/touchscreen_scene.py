"""Touch screen kaise kaam karti hai -- a 29 s vertical YouTube Short (Urdu voice-over), night look.

World units: 4K px at zoom 1. Rendered at 1080x1920, so zoom 1 shows 3840 x 6827 world px.
Captions sit in the lower third, so every hero is framed in the upper ~60% of the frame:
camera y = hero_y + 819 / zoom puts the hero at 38% of frame height.
"""
import math
import random
import re

import skia
from engine import (BigText, Counter, Film, Item, Stamp, clamp, draw_label, draw_text, ease_in_out,
                    ease_out_back, ease_out_cubic, paint, partial_path, ramp)

CYAN = (80, 220, 255)
YELLOW = (255, 206, 46)
RED = (240, 60, 56)
WHITE = (246, 246, 250)

PW, PH, PR = 2300, 4700, 320                      # phone body
SX0, SY0, SX1, SY1 = -1060, -2260, 1060, 2260     # screen rect
COLS = [-940 + i * 235 for i in range(9)]
ROWS = [-2115 + j * 235 for j in range(19)]
P = (COLS[5], ROWS[11])                            # the touch point (235, 470)


def hero_cam(x, y, z):
    return x, y + 819 / z


def pulse(t, period):
    return 0.5 + 0.5 * math.sin(t * 2 * math.pi / period)


# ---------------------------------------------------------------- items
class Phone(Item):
    z = 10

    def draw(self, c, res, t):
        body = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-PW / 2, -PH / 2, PW, PH), PR, PR)
        c.save(); c.translate(40, 90); c.drawRRect(body, paint((0, 0, 0), 0.7, blur=120)); c.restore()
        g = skia.GradientShader.MakeLinear([skia.Point(-PW / 2, -PH / 2), skia.Point(PW / 2, PH / 2)],
                                           [skia.Color(58, 62, 74), skia.Color(20, 22, 28), skia.Color(44, 48, 58)], [0, 0.55, 1])
        p = skia.Paint(AntiAlias=True); p.setShader(g); c.drawRRect(body, p)
        c.drawRRect(body, paint((150, 160, 185), 0.55, stroke=16))
        for (y0, h) in ((-1350, 420), (-820, 300), (-430, 300)):          # side buttons
            c.drawRoundRect(skia.Rect.MakeXYWH(-PW / 2 - 26, y0, 30, h), 12, 12, paint((70, 75, 90), 1))
        scr = skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(SX0, SY0, SX1, SY1), 220, 220)
        c.drawRRect(scr, paint((3, 6, 12), 1))


class Grid(Item):
    """The electrode grid under the glass: rows and columns draw on, then signal pulses run along them.
    scan_t0..lock_t: a scan bar sweeps the rows; lock_t: the touched row and column light up yellow."""
    z = 20

    def __init__(self, t_in, pulse_t, scan_t0, lock_t, t_lock_out):
        super().__init__(t_in)
        self.pulse_t, self.scan_t0, self.lock_t, self.t_lock_out = pulse_t, scan_t0, lock_t, t_lock_out

    def draw(self, c, res, t):
        u = ease_in_out(ramp(t, self.t_in, 1.1))
        if u <= 0:
            return
        c.save(); c.clipRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(SX0, SY0, SX1, SY1), 220, 220), True)
        base = paint(CYAN, 0.30, stroke=9); glow = paint(CYAN, 0.22, stroke=34, blur=22)
        for i, x in enumerate(COLS):
            k = clamp(u * 1.6 - i * 0.07)
            if k > 0:
                pth = skia.Path(); pth.moveTo(x, SY0); pth.lineTo(x, SY1)
                seg = partial_path(pth, k); c.drawPath(seg, glow); c.drawPath(seg, base)
        for j, y in enumerate(ROWS):
            k = clamp(u * 1.6 - j * 0.035)
            if k > 0:
                pth = skia.Path(); pth.moveTo(SX0, y); pth.lineTo(SX1, y)
                seg = partial_path(pth, k); c.drawPath(seg, glow); c.drawPath(seg, base)
        if u > 0.6:
            na = (u - 0.6) / 0.4
            for x in COLS:
                for y in ROWS:
                    c.drawCircle(x, y, 16, paint(CYAN, 0.55 * na))
        # signal pulses running along the wires
        pa = ramp(t, self.pulse_t, 0.6)
        if pa > 0:
            sp = 1500.0
            span_y, span_x = SY1 - SY0, SX1 - SX0
            for i, x in enumerate(COLS):
                for k in range(2):
                    y = SY0 + ((t * sp + i * 613 + k * span_y / 2) % span_y)
                    for tr in range(4):
                        c.drawCircle(x, y - tr * 55, 26 - tr * 5, paint(CYAN, 0.6 * pa * (1 - tr / 4)))
                    c.drawCircle(x, y, 90, paint(CYAN, 0.4 * pa, blur=48)); c.drawCircle(x, y, 24, paint(WHITE, 0.95 * pa))
            for j, y in enumerate(ROWS):
                x = SX0 + ((t * sp * 0.8 + j * 377) % span_x)
                for tr in range(4):
                    c.drawCircle(x - tr * 50, y, 24 - tr * 5, paint(CYAN, 0.55 * pa * (1 - tr / 4)))
                c.drawCircle(x, y, 80, paint(CYAN, 0.36 * pa, blur=44)); c.drawCircle(x, y, 22, paint(WHITE, 0.9 * pa))
        # scan bar: row by row, fast, until the touch is found
        if self.scan_t0 <= t < self.lock_t + 0.25:
            sa = ramp(t, self.scan_t0, 0.3) * (1 - ramp(t, self.lock_t, 0.25))
            period = 0.55
            y = SY0 + ((t - self.scan_t0) % period) / period * (SY1 - SY0)
            c.drawRect(skia.Rect.MakeLTRB(SX0, y - 90, SX1, y + 90), paint(CYAN, 0.25 * sa, blur=60))
            c.drawLine(SX0, y, SX1, y, paint(WHITE, 0.9 * sa, stroke=14))
            if abs(y - P[1]) < 140:
                c.drawCircle(P[0], P[1], 150, paint(YELLOW, 0.9 * sa, blur=50))
        # lock: the touched row and column, a ring with ticks
        la = ease_out_cubic(ramp(t, self.lock_t, 0.35)) * (1 - ramp(t, self.t_lock_out, 0.4))
        if la > 0:
            yl = paint(YELLOW, 0.95 * la, stroke=16); yg = paint(YELLOW, 0.35 * la, stroke=60, blur=36)
            for a, b in (((P[0], SY0), (P[0], SY1)), ((SX0, P[1]), (SX1, P[1]))):
                c.drawLine(*a, *b, yg); c.drawLine(*a, *b, yl)
            r = 330 + 220 * (1 - la)
            c.drawCircle(P[0], P[1], r, paint(YELLOW, la, stroke=18))
            for ang in range(0, 360, 90):
                ca, sa_ = math.cos(math.radians(ang)), math.sin(math.radians(ang))
                c.drawLine(P[0] + ca * (r - 70), P[1] + sa_ * (r - 70), P[0] + ca * (r + 90), P[1] + sa_ * (r + 90), yl)
        c.restore()


class Glass(Item):
    """The glass and the home screen: lifts away (lift_t) to show the grid, comes back at back_t."""
    z = 30

    def __init__(self, lift_t, back_t):
        super().__init__(-1)
        self.lift_t, self.back_t = lift_t, back_t
        rnd = random.Random(4)
        pal = [(255, 120, 90), (90, 200, 140), (110, 150, 255), (250, 190, 70), (200, 110, 230), (70, 200, 220)]
        self.icons = [(-765 + col * 510, -900 + row * 520, rnd.choice(pal)) for row in range(4) for col in range(4)]

    def state(self, t):
        u = ease_in_out(ramp(t, self.lift_t, 1.0)) * (1 - ease_in_out(ramp(t, self.back_t, 0.9)))
        return u

    def draw(self, c, res, t):
        u = self.state(t)
        a = (1 - 0.93 * u) * (1 - ramp(t, self.lift_t + 1.2, 0.8) * (1 - ramp(t, self.back_t, 0.3)))
        if a <= 0.003:
            return
        c.save(); c.translate(0, -700 * u)
        s = 1 + 0.06 * u; c.scale(s, s)
        scr = skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(SX0, SY0, SX1, SY1), 220, 220)
        c.saveLayerAlpha(None, int(255 * a))
        g = skia.GradientShader.MakeLinear([skia.Point(0, SY0), skia.Point(0, SY1)],
                                           [skia.Color(40, 36, 92), skia.Color(14, 60, 110), skia.Color(10, 18, 40)], [0, 0.5, 1])
        p = skia.Paint(AntiAlias=True); p.setShader(g); c.drawRRect(scr, p)
        c.drawCircle(0, SY0 + 110, 46, paint((0, 0, 0), 1))                         # camera hole
        draw_text(c, res, "10:08", 0, -1450, 520, "cond", WHITE, 0.95, 0.02, "center")
        for (x, y, col) in self.icons:
            c.drawRoundRect(skia.Rect.MakeXYWH(x - 170, y - 170, 340, 340), 90, 90, paint(col, 0.92))
            c.drawRoundRect(skia.Rect.MakeXYWH(x - 170, y - 170, 340, 150), 90, 90, paint(WHITE, 0.12))
        c.drawRoundRect(skia.Rect.MakeXYWH(-950, 1700, 1900, 420), 140, 140, paint(WHITE, 0.14))
        for k in range(4):
            c.drawRoundRect(skia.Rect.MakeXYWH(-765 + k * 510 - 150, 1760, 300, 300), 80, 80, paint(pal_dock(k), 0.95))
        # glass sheen
        sh = skia.GradientShader.MakeLinear([skia.Point(SX0, SY0), skia.Point(SX1, SY0 + 1600)],
                                            [skia.Color(255, 255, 255, 46), skia.Color(255, 255, 255, 0)], [0, 1])
        p2 = skia.Paint(AntiAlias=True); p2.setShader(sh); c.drawRRect(scr, p2)
        c.restore()
        if u > 0.02:                                  # the lifted glass edge catches light
            c.drawRRect(scr, paint(WHITE, 0.5 * u * a, stroke=14))
        c.restore()


def pal_dock(k):
    return [(90, 200, 140), (110, 150, 255), (255, 120, 90), (250, 190, 70)][k]


class Finger(Item):
    """A finger (or a gloved one) from the lower right: slides in to land on `tip`, presses, slides out."""
    z = 50

    def __init__(self, tip, t_in, land, t_leave, glove=False, angle=-28):
        super().__init__(t_in)
        self.tip, self.land, self.t_leave, self.glove, self.angle = tip, land, t_leave, glove, angle

    def visible(self, t):
        return self.t_in - 0.01 <= t <= self.t_leave + 0.9

    def draw(self, c, res, t):
        come = ease_out_cubic(ramp(t, self.t_in, self.land - self.t_in))
        go = ease_in_out(ramp(t, self.t_leave, 0.8))
        k = (1 - come) + go                      # 0 = pressed on the point, 1 = off screen
        press = ramp(t, self.land - 0.05, 0.12) * (1 - ramp(t, self.land + 0.1, 0.25))
        th = math.radians(self.angle)
        dx, dy = -math.sin(th), math.cos(th)
        x, y = self.tip[0] + dx * 3600 * k, self.tip[1] + dy * 3600 * k
        hover = clamp(k * 3)
        s = 1.0 + 0.1 * hover - 0.03 * press
        W = 740 if self.glove else 560
        L = 4200
        c.save(); c.translate(x, y); c.rotate(self.angle); c.scale(s, s)
        body = skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(-W / 2, -W / 2, W / 2, L), W / 2, W / 2)
        c.save(); c.translate(90 + 260 * hover, 160 + 300 * hover)
        c.drawRRect(body, paint((0, 0, 0), 0.6 - 0.25 * hover, blur=70 + 120 * hover)); c.restore()
        if self.glove:
            cols = [skia.Color(92, 26, 34), skia.Color(150, 48, 58), skia.Color(84, 22, 30)]
        else:
            cols = [skia.Color(178, 118, 88), skia.Color(236, 182, 148), skia.Color(170, 112, 84)]
        g = skia.GradientShader.MakeLinear([skia.Point(-W / 2, 0), skia.Point(W / 2, 0)], cols, [0, 0.45, 1])
        p = skia.Paint(AntiAlias=True); p.setShader(g); c.drawRRect(body, p)
        if self.glove:
            c.save(); c.clipRRect(body, True)
            for yy in range(-W // 2, L, 64):
                c.drawLine(-W / 2, yy, 0, yy + 30, paint((60, 14, 20), 0.45, stroke=14)); c.drawLine(0, yy + 30, W / 2, yy, paint((60, 14, 20), 0.45, stroke=14))
            c.drawRect(skia.Rect.MakeLTRB(-W / 2 - 30, 2700, W / 2 + 30, L), paint((70, 18, 26), 1))
            for xx in range(-int(W / 2), int(W / 2), 52):
                c.drawLine(xx, 2700, xx, L, paint((40, 8, 14), 0.6, stroke=14))
            c.restore()
        else:
            nail = skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(-190, -230, 190, 330), 170, 170)
            c.drawRRect(nail, paint((246, 206, 196), 0.95))
            c.drawRRect(nail, paint((200, 140, 120), 0.6, stroke=10))
            c.drawRoundRect(skia.Rect.MakeLTRB(-120, -190, -20, 200), 50, 50, paint(WHITE, 0.35))
            for yy in (1150, 1210, 2350, 2410):
                pth = skia.Path(); pth.moveTo(-W / 2 + 80, yy); pth.quadTo(0, yy + 50, W / 2 - 80, yy)
                c.drawPath(pth, paint((150, 96, 72), 0.55, stroke=10))
        c.restore()


class Sparks(Item):
    """Charge flowing from the grid into the fingertip; blocked=True stops it at the glove and turns it red."""
    z = 55

    def __init__(self, t_in, t_out, blocked=False, n=46, seed=3):
        super().__init__(t_in, t_out)
        self.blocked = blocked
        rnd = random.Random(seed)
        self.p = []
        for _ in range(n):
            ang = rnd.uniform(0, 2 * math.pi); r = rnd.uniform(650, 1250)
            self.p.append((P[0] + math.cos(ang) * r, P[1] + math.sin(ang) * r, rnd.uniform(0, 1), rnd.uniform(0.7, 1.1),
                           rnd.uniform(-0.35, 0.35)))

    def draw(self, c, res, t):
        a = ramp(t, self.t_in, 0.4) * self.fade(t)
        if a <= 0:
            return
        if not self.blocked:
            h = 0.6 + 0.4 * pulse(t, 0.45)
            c.drawCircle(P[0], P[1], 330, paint(CYAN, 0.45 * a * h, blur=110))
            c.drawCircle(P[0], P[1], 280 + 60 * pulse(t, 0.45), paint(WHITE, 0.6 * a, stroke=12))
        else:
            hit = pulse(t, 0.3)
            c.drawCircle(P[0], P[1], 340, paint(RED, 0.75 * a * (0.5 + 0.5 * hit), stroke=26))
            c.drawCircle(P[0], P[1], 340, paint(RED, 0.3 * a, stroke=90, blur=50))
        for (ox, oy, ph, sp, bend) in self.p:
            u = ((t - self.t_in) * sp / 0.95 + ph) % 1.0
            vx, vy = P[0] - ox, P[1] - oy
            nx, ny = -vy, vx
            if not self.blocked:
                e = u ** 1.6
                x = ox + vx * e + nx * bend * math.sin(math.pi * e)
                y = oy + vy * e + ny * bend * math.sin(math.pi * e)
                col, al = (CYAN if u < 0.7 else WHITE), a * math.sin(math.pi * clamp(u * 1.05))
            else:
                stop = 1 - 340 / math.hypot(vx, vy)
                if u < 0.65:
                    e = (u / 0.65) ** 1.4 * stop
                    col = CYAN
                else:
                    e = stop * (1 - 0.55 * ease_out_cubic((u - 0.65) / 0.35))
                    col = RED
                x = ox + vx * e + nx * bend * 0.6 * math.sin(math.pi * e)
                y = oy + vy * e + ny * bend * 0.6 * math.sin(math.pi * e)
                al = a * (1 - clamp((u - 0.75) / 0.25))
            c.drawCircle(x, y, 75, paint(col, 0.35 * al, blur=42))
            c.drawCircle(x, y, 24, paint(WHITE if col != RED else (255, 170, 160), 0.95 * al))


class FailTap(Item):
    """A tap that does nothing: a grey ring that dies, and a red cross."""
    z = 56

    def __init__(self, t_in, t_out):
        super().__init__(t_in, t_out)

    def draw(self, c, res, t):
        u = ramp(t, self.t_in, 0.6); a = self.fade(t)
        if u <= 0:
            return
        r = 200 + 450 * ease_out_cubic(u)
        c.drawCircle(P[0], P[1], r, paint(WHITE, 0.6 * (1 - u) * a, stroke=16))
        k = ease_out_back(ramp(t, self.t_in + 0.25, 0.3))
        if k > 0:
            cx, cy, s = P[0] - 520, P[1] - 520, 170 * k
            c.drawCircle(cx, cy, 240 * k, paint(RED, 0.95 * a))
            pp = paint(WHITE, a, stroke=46)
            c.drawLine(cx - s * 0.6, cy - s * 0.6, cx + s * 0.6, cy + s * 0.6, pp)
            c.drawLine(cx + s * 0.6, cy - s * 0.6, cx - s * 0.6, cy + s * 0.6, pp)


class Tag(Item):
    """A small series tag: colour bar with condensed caps."""
    z = 72

    def __init__(self, text, x, y, size, t_in, t_out=None, rgb=RED, text_rgb=WHITE):
        super().__init__(t_in, t_out)
        self.text, self.x, self.y, self.size, self.rgb, self.text_rgb = text, x, y, size, rgb, text_rgb

    def draw(self, c, res, t):
        a = ramp(t, self.t_in, 0.25) * self.fade(t)
        if a > 0:
            draw_label(c, res, self.text, self.x, self.y, a=a, size=self.size, reveal=ramp(t, self.t_in, 0.45),
                       rgb=self.rgb, text_rgb=self.text_rgb)


# ---------------------------------------------------------------- film
def build_film(doc):
    L, E = doc.L, doc.E
    strip = lambda s: re.sub(r"[\s،۔؟,.!?]", "", s)

    import json, pathlib
    wt_path = pathlib.Path(__file__).with_name("audio") / "word_times.json"
    word_times = json.load(open(wt_path)) if wt_path.exists() else {}

    def W(i, word, nth=0):
        """When `word` is spoken in line i: measured word timings if present, else its letter share of the line."""
        hits = [x["t"] for x in word_times.get(str(i), []) if x["w"].strip("،۔؟?,.") == word]
        if len(hits) > nth:
            return L(i) + hits[nth] + 0.03
        vo = doc.seg[i]["vo"]; idx, start = -1, 0
        for _ in range(nth + 1):
            idx = vo.find(word, start); start = idx + 1
            if idx < 0:
                raise ValueError(f"{word!r} not in line {i}")
        return L(i) + (E(i) - L(i)) * len(strip(vo[:idx])) / max(1, len(strip(vo))) + 0.04

    film = Film(doc.duration, fps=30, look="night")
    film.fade_in, film.fade_out = 0.25, 0.7

    t_why = W(1, "کیوں")
    t_lift = W(2, "نیچے")
    t_grid = W(2, "بجلی") - 0.1
    t_net = W(2, "تاروں")
    t_pulse = L(3) + 0.1
    t_land = W(4, "لگتے")
    t_spark = W(4, "تھوڑی") - 0.2
    t_sau = W(5, "سو")
    t_lock = W(5, "کہاں")
    t_glove_land = W(6, "دستانہ") + 0.45
    t_block = W(6, "راستہ")
    t_no = W(6, "پتہ")

    film.add(Phone(-1))
    film.add(Grid(t_grid, t_pulse, L(5) + 0.15, t_lock, L(6) + 0.2))
    film.add(Glass(t_lift, L(7) + 0.3))

    # 1  hook: a gloved tap that does nothing
    film.add(Tag("HOW IT WORKS", 0, -3380, 220, 0.15, t_out=E(1) + 0.2))
    film.add(Finger(P, 0.3, 1.05, E(1) - 0.35, glove=True))
    film.add(FailTap(1.07, E(1)))
    film.add(BigText("WHY?", 0, -2500, 800, t_why - 0.05, t_out=E(1) + 0.1, rgb=YELLOW, hit=0.55))
    film.cue("click", 1.07, 0.6)

    # 2  the grid under the glass
    film.add(BigText("TOUCH GRID", 0, -2650, 430, t_net - 0.05, t_out=E(3) - 0.3, rgb=CYAN, rules=True, type_on=0.45))
    film.cue("shimmer", t_grid, 0.5)
    film.cue("riser", L(2) - 1.0, 0.35, dur=1.0)

    # 4  a bare finger: charge flows into it
    film.add(Finger(P, L(4) + 0.05, t_land, L(6) - 0.25))
    film.add(Sparks(t_spark, L(6) - 0.3))
    film.cue("pop", t_land, 0.7)
    film.cue("shimmer", t_spark, 0.45)

    # 5  the chip scans and finds it
    film.add(Counter(0, -1750, 560, 120, t_sau - 0.1, dur=0.9, suffix="+", caption="TIMES EVERY SECOND", rgb=YELLOW,
                     t_out=t_lock - 0.25))
    film.add(Tag("TOUCH FOUND", P[0] - 40, P[1] - 900, 170, t_lock + 0.2, t_out=L(6) + 0.1, rgb=YELLOW, text_rgb=(20, 20, 24)))
    film.cue("impact", t_lock, 0.45)

    # 6  the glove blocks it
    film.add(Finger(P, L(6) + 0.05, t_glove_land, L(7) - 0.1, glove=True))
    film.add(Sparks(t_block - 0.15, L(7) - 0.1, blocked=True, seed=8))
    film.add(Stamp("NO TOUCH", P[0] - 120, P[1] - 1000, size=300, rot=-7, t_in=t_no, t_out=L(7) + 0.2, rgb=RED))
    film.cue("pop", t_glove_land, 0.6)

    # 7  close
    film.add(BigText("FOLLOW", 0, -2560, 650, L(7) + 0.25, rgb=(20, 20, 24), bar=YELLOW, bar_h=0.92, shadow=False,
                     grunge=False, hit=0.5))
    film.add(Tag("MORE HOW IT WORKS", 0, -3520, 190, W(7, "فالو"), rgb=RED))
    film.cue("boom", t_why - 0.05, 0.5)
    film.room_tone = [[0, film.duration]]

    # camera (hero at 38% of frame height so the captions below never cover it)
    def sh(t, x, y, z, rot=0.0):
        film.cam(t, *hero_cam(x, y, z), z, rot)
        film.focus(t, x, y - 600 / z, 3800 / z, 0.25)
    sh(0.0, 0, -700, 0.84, 0.6)
    sh(E(1) - 0.2, 0, -650, 0.86, -0.4)
    sh(L(2) + 0.5, 0, -150, 0.76, 0.3)
    sh(E(2), 0, -50, 0.84, -0.5)
    sh(L(3) + 0.6, 120, 250, 1.15, -1.0)
    sh(E(3), 200, 350, 1.3, 0.6)
    sh(t_land + 0.3, P[0], P[1], 1.75, -0.8)
    sh(E(4), P[0], P[1] + 40, 2.0, 0.5)
    sh(L(5) + 0.6, 0, -200, 0.86, 0.3)
    sh(t_lock - 0.2, 0, -150, 0.92, -0.3)
    sh(t_lock + 0.4, P[0], P[1] - 150, 1.45, -0.6)
    sh(E(5), P[0], P[1] - 180, 1.55, 0.2)
    sh(t_glove_land + 0.2, P[0], P[1] - 250, 1.45, 0.8)
    sh(E(6), P[0], P[1] - 300, 1.6, -0.4)
    sh(L(7) + 0.6, 0, -450, 0.8, 0.2)
    sh(film.duration, 0, -420, 0.76, -0.2)
    return film
