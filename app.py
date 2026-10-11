# =====================================================================
#  LIGHT LAB 11.0 "INFINITE" — reflection • refraction • mixing
#  NEW vs 10.0:
#   • FLUX LAB pack (10 new free levels): portal routes, recombiner
#     forging, focus mixing, filter ladders, zigzag drops, finale
#   • ENDLESS MODE: procedural levels, infinite count, deterministic
#     per number (same level for everyone, forever — ghosts & solution
#     codes work!). 4 generator archetypes, all solvable BY
#     CONSTRUCTION (the solution is built first, then scrambled):
#       MAZE   – chain of N scrambled mirrors
#       RELAY  – two colored sources routed onto one exact-mix target
#       FAN    – prism fan simulated with real Snell math; targets
#                placed on actual fan rays, prism rotated to hide them
#       SPLIT  – splitter tree, straight/reflected/deflected legs,
#                optional filter-dyed colored legs
#     Difficulty tiers every 5 levels: more mirrors, more targets,
#     wilder scrambles
#   • ENDLESS tab in level select with per-level stars & par times
#   • 2 new achievements (23): Forgemaster, Tenacity
#   • FIX: colored beams hitting a non-recombiner glass could crash
#     the tracer/caustics (missing attribute) — fixed
#  pip install pygame    (pygame-ce works too)    Python 3.8+
# =====================================================================
import os
os.environ["SDL_VIDEO_CENTERED"] = "1"
import pygame, math, json, random, sys, base64, array, datetime
from pygame.math import Vector2 as V2

pygame.mixer.pre_init(22050, -16, 2, 256)
pygame.init()
SOUND_OK = pygame.mixer.get_init() is not None
if SOUND_OK: pygame.mixer.set_num_channels(24)

W, H = 1280, 720

def make_icon():
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.rect(s, (16, 22, 44), (0, 0, 32, 32), border_radius=7)
    pygame.draw.line(s, (255, 255, 255), (3, 27), (14, 16), 3)
    for i, c in enumerate([(255,64,64),(255,150,40),(255,232,70),(90,240,110),
                           (70,200,255),(110,120,255),(190,80,255)]):
        pygame.draw.line(s, c, (17, 15), (29, 3 + i*4), 2)
    pygame.draw.circle(s, (255, 208, 84), (16, 15), 3)
    return s
pygame.display.set_icon(make_icon())

screen = pygame.display.set_mode((W, H), pygame.RESIZABLE)
pygame.display.set_caption("LIGHT LAB 11.0 — Reflection, Refraction & Infinity")
clock = pygame.time.Clock()
canvas = pygame.Surface((W, H))
TOP, BOT = 56, 64

def present():
    ww, wh = screen.get_size()
    if ww <= 0 or wh <= 0: return
    sc = min(ww / W, wh / H)
    sw, sh = max(1, int(W * sc)), max(1, int(H * sc))
    if (sw, sh) == (ww, wh): screen.blit(canvas, (0, 0))
    else:
        screen.fill((0, 0, 0))
        screen.blit(pygame.transform.smoothscale(canvas, (sw, sh)),
                    ((ww - sw) // 2, (wh - sh) // 2))
    pygame.display.flip()

def to_game(pos):
    ww, wh = screen.get_size()
    sc = min(ww / W, wh / H) or 1.0
    ox, oy = (ww - W * sc) / 2, (wh - H * sc) / 2
    return (int((pos[0] - ox) / sc), int((pos[1] - oy) / sc))

def F(size, bold=False):
    return pygame.font.SysFont("consolas,menlo,dejavusansmono,arial", size, bold=bold)
F13, F14, F16, F18, F22, F40 = F(13), F(14), F(16), F(18), F(22, True), F(40, True)

BGc    = (10, 13, 26);  GRIDc  = (24, 30, 54)
PANELc = (22, 28, 52);  BTNc   = (32, 42, 74); BTN_Hc = (56, 72, 120)
EDGEc  = (86, 104, 156);TEXTc  = (215, 224, 255); DIMc = (122, 134, 176)
GOLD   = (255, 208, 84);WHITE  = (255, 255, 255)
SPECTRUM = [(255,64,64),(255,150,40),(255,232,70),(90,240,110),
            (70,200,255),(110,120,255),(190,80,255)]
CNAME    = ["RED","ORANGE","YELLOW","GREEN","CYAN","BLUE","VIOLET"]
SOURC_COLORS = [WHITE] + SPECTRUM

RED, ORANGE, YELLOW = SPECTRUM[0], SPECTRUM[1], SPECTRUM[2]
GREEN, CYAN, BLUE, VIOLET = SPECTRUM[3], SPECTRUM[4], SPECTRUM[5], SPECTRUM[6]
COMP_OF = {RED:"R", ORANGE:"GR", YELLOW:"GR", GREEN:"G",
           CYAN:"BG", BLUE:"B", VIOLET:"BR", WHITE:"BGR"}
COMP_TO = {"R":RED, "G":GREEN, "B":BLUE,
           "GR":YELLOW, "BG":CYAN, "BR":VIOLET, "BGR":WHITE}
COMP_SET = {c: frozenset(v) for c, v in COMP_OF.items()}
COMP_NAME = {"R":"RED", "G":"GREEN", "B":"BLUE"}
PRIM = {"R":RED, "G":GREEN, "B":BLUE}

def mix_colors(a, b):
    if a == b: return a
    key = "".join(sorted(COMP_SET[a] | COMP_SET[b]))
    return COMP_TO.get(key, WHITE)

EPS = 0.01
MAX_BEAMS, MAX_DEPTH, MIN_I = 1400, 26, 0.035
CAUST_W = 30
MIX_GATE = 0.20
MIX_VIS  = 0.35

# ------------------------------------------------------------- math
def unit(v):  return v.normalize() if v.length_squared() > 1e-12 else V2(1, 0)
def rot(v, a):
    c, s = math.cos(a), math.sin(a)
    return V2(v.x*c - v.y*s, v.x*s + v.y*c)
def ip(v):    return (int(v.x), int(v.y))
def ippi(ps): return [ip(p) for p in ps]
def dim(c, k):
    return (min(255, int(c[0]*k)), min(255, int(c[1]*k)), min(255, int(c[2]*k)))

def ray_segment(p, d, a, b):
    ab = b - a
    den = d.x*ab.y - d.y*ab.x
    if abs(den) < 1e-9: return None
    ap = a - p
    t = (ap.x*ab.y - ap.y*ab.x) / den
    s = (ap.x*d.y - ap.y*d.x) / den
    return t if (t > EPS and 0.0 <= s <= 1.0) else None

def ray_circle(p, d, c, r):
    oc = p - c; b = oc.dot(d)
    disc = b*b - (oc.length_squared() - r*r)
    if disc < 0: return None
    s = math.sqrt(disc)
    for t in (-b - s, -b + s):
        if t > EPS: return t
    return None

def reflect(d, n): return d - 2.0*d.dot(n)*n
def refract(d, n, eta):
    cosi = -d.dot(n)
    k = 1.0 - eta*eta*(1.0 - cosi*cosi)
    if k < 0: return None
    return d*eta + n*(eta*cosi - math.sqrt(k))

def dist_pt_seg(p, a, b):
    ab = b - a; L2 = ab.length_squared()
    if L2 < 1e-12: return (p - a).length()
    t = max(0.0, min(1.0, (p - a).dot(ab)/L2))
    return (p - (a + ab*t)).length()

def seg_x(a1, b1, a2, b2, margin=6.0):
    d1 = b1 - a1; d2 = b2 - a2
    den = d1.x*d2.y - d1.y*d2.x
    if abs(den) < 1e-9: return None
    ap = a2 - a1
    t = (ap.x*d2.y - ap.y*d2.x) / den
    u = (ap.x*d1.y - ap.y*d1.x) / den
    l1 = d1.length(); l2 = d2.length()
    if not (margin < t*l1 < l1-margin and margin < u*l2 < l2-margin): return None
    return a1 + d1*t

def fmt_time(sec): return f"{int(sec)//60}:{int(sec)%60:02d}"

# =====================================================================
#  AUDIO ENGINE
# =====================================================================
SR = 22050
_sc = {}
def S(freq=440, ms=150, vol=0.3, wave="sine", duty=0.5, atk=0.004,
      sus=1.0, curve=1.5, bend=None, vib=0.0, vibf=6.0, det=0.0,
      harm=0.0, noise=0.0, nlp=0.5, pan=0.0):
    key = (round(freq,2), int(ms), round(vol,3), wave, round(duty,2),
           round(atk,4), round(sus,2), round(curve,2),
           None if bend is None else round(bend,3), round(vib,2),
           round(vibf,1), round(det,3), round(harm,2), round(noise,2),
           round(nlp,2), round(pan,2))
    if key in _sc: return _sc[key]
    n = max(8, int(SR*ms/1000))
    a_n = max(1, int(SR*atk))
    r_n = max(1, int(SR*min(0.09, ms/1000*0.35)))
    gl = math.cos((pan+1)*math.pi/4.0)
    gr = math.sin((pan+1)*math.pi/4.0)
    f2 = freq*(1.0+det)
    buf = array.array("h"); ph = 0.0; ph2 = 0.0; nz = 0.0
    TAU = 2*math.pi
    for i in range(n):
        t = i/n
        f = freq * (bend ** t) if bend else freq
        if vib: f *= 1.0 + vib*math.sin(TAU*vibf*i/SR)
        ph += TAU*f/SR
        p = ph % TAU
        if wave == "sine":   v = math.sin(p)
        elif wave == "square": v = 1.0 if p < TAU*duty else -1.0
        elif wave == "tri":  v = 2/math.pi*math.asin(math.sin(p))
        else:                v = (p/math.pi % 2.0) - 1.0
        if det:
            ph2 += TAU*f2/SR
            v = 0.65*v + 0.35*math.sin(ph2)
        if harm:
            v = (v + harm*math.sin(2*p)) / (1.0+harm)
        if noise:
            nz += (random.uniform(-1,1) - nz) * nlp
            v = v*(1.0-noise) + noise*nz
        if i < a_n: e = i/a_n
        else:
            e = sus + (1.0-sus)*((1.0-(i-a_n)/max(1, n-a_n)) ** curve)
        if i > n-r_n: e *= (n-i)/r_n
        amp = int(32000 * vol * max(-1.0, min(1.0, v)) * e)
        buf.append(int(amp*gl)); buf.append(int(amp*gr))
    snd = pygame.mixer.Sound(buffer=buf.tobytes())
    if len(_sc) > 420: _sc.pop(next(iter(_sc)))
    _sc[key] = snd
    return snd

PENTA = [392.0, 440.0, 523.25, 587.33, 659.25, 783.99, 880.0, 1046.5]

def _d(freq, ms, vol, **kw):
    kw.update(freq=freq, ms=ms, vol=vol); return kw

SFX = {
 "hover":  lambda v: [(0, _d(2400, 12, .045*v, atk=.002))],
 "click":  lambda v: [(0, _d(1900, 26, .16*v, wave="square", duty=.32, bend=.8, atk=.001)),
                      (0, _d(3200, 10, .05*v, noise=.8, nlp=.7))],
 "grab":   lambda v: [(0, _d(300, 45, .12*v, wave="tri", bend=1.15))],
 "tick":   lambda v: [(0, _d(1700, 14, .06*v, atk=.001))],
 "place":  lambda v: [(0, _d(440, 55, .2*v, wave="tri", bend=1.5)),
                      (28, _d(660, 70, .18*v, harm=.4, bend=1.12)),
                      (0, _d(120, 60, .1*v, noise=.9, nlp=.15))],
 "delete": lambda v: [(0, _d(420, 150, .22*v, wave="saw", bend=.22)),
                      (0, _d(800, 90, .14*v, noise=.9, nlp=.4, bend=.3))],
 "undo":   lambda v: [(0, _d(260, 90, .18*v, wave="tri", bend=1.9))],
 "deny":   lambda v: [(0, _d(110, 160, .2*v, wave="square")),
                      (0, _d(116.5, 160, .2*v, wave="square"))],
 "reflect":lambda v: [(0, _d(1568, 60, .16*v, harm=.6, bend=.94, atk=.001)),
                      (0, _d(2349, 45, .09*v, bend=.9)),
                      (0, _d(4200, 14, .06*v, noise=.7, nlp=.8))],
 "glass":  lambda v: [(0, _d(1912, 70, .07*v, harm=.5, bend=1.06)),
                      (0, _d(2865, 50, .045*v))],
 "split":  lambda v: [(0, _d(1400, 60, .12*v, harm=.5)),
                      (10, _d(2100, 60, .08*v, bend=.92))],
 "disp":   lambda v: [(0, _d(2093, 45, .11*v, harm=.4)),
                      (30, _d(2637, 45, .1*v, harm=.4)),
                      (60, _d(3136, 60, .1*v, harm=.4))],
 "tir":    lambda v: [(0, _d(170, 90, .2*v, wave="tri", bend=.8)),
                      (0, _d(2637, 35, .08*v, bend=.85))],
 "thud":   lambda v: [(0, _d(90, 80, .16*v, noise=.85, nlp=.12))],
 "warp":   lambda v: [(0, _d(400, 130, .2*v, wave="square", bend=3.2)),
                      (90, _d(400, 110, .1*v, wave="square", bend=3.2)),
                      (180, _d(400, 100, .05*v, wave="square", bend=3.2))],
 "mixfx":  lambda v: [(0, _d(660, 70, .11*v, harm=.4)),
                      (40, _d(990, 90, .11*v, harm=.4)),
                      (80, _d(1320, 120, .09*v, harm=.4, sus=.6))],
 "recomb": lambda v: [(0, _d(523.25, 70, .12*v, harm=.4)),
                      (45, _d(783.99, 70, .12*v, harm=.4)),
                      (90, _d(1046.5, 160, .15*v, harm=.5, sus=.5)),
                      (90, _d(1568, 120, .06*v))],
 "ach":    lambda v: [(0, _d(392, 90, .18*v, wave="square", duty=.3)),
                      (70, _d(523.25, 90, .18*v, wave="square", duty=.3)),
                      (140, _d(659.25, 90, .18*v, wave="square", duty=.3)),
                      (210, _d(784, 230, .22*v, wave="square", duty=.35, harm=.4, sus=.6)),
                      (210, _d(329.63, 230, .1*v, wave="tri", sus=.6))],
 "shot":   lambda v: [(0, _d(1900, 20, .15*v, wave="square", duty=.3, bend=.8, atk=.001)),
                      (60, _d(1000, 40, .15*v, noise=.9, nlp=.5, bend=.5))],
 "whoosh": lambda v: [(0, _d(300, 220, .12*v, noise=.9, nlp=.3)),
                      (0, _d(220, 220, .06*v, bend=3.0, atk=.05))],
 "daily":  lambda v: [(0, _d(220, 420, .12*v, atk=.08, sus=.8)),
                      (0, _d(261.63, 420, .1*v, atk=.08, sus=.8)),
                      (0, _d(329.63, 420, .1*v, atk=.08, sus=.8)),
                      (240, _d(1760, 80, .07*v, harm=.5))],
 "unlock": lambda v: [(0, _d(523.25, 80, .18*v, wave="square", duty=.3)),
                      (80, _d(784, 80, .18*v, wave="square", duty=.3)),
                      (160, _d(1046.5, 90, .18*v, wave="square", duty=.3)),
                      (260, _d(1318.5, 260, .2*v, wave="square", duty=.35, harm=.4, sus=.55))],
 "ghost":  lambda v: [(0, _d(196, 300, .1*v, atk=.05, sus=.7)),
                      (60, _d(392, 240, .08*v, harm=.5, sus=.5)),
                      (180, _d(784, 60, .08*v, harm=.4))],
 "genfx":  lambda v: [(0, _d(330, 60, .1*v, wave="square", duty=.3, bend=1.5)),
                      (60, _d(660, 60, .1*v, wave="square", duty=.3, bend=1.5)),
                      (120, _d(990, 140, .12*v, harm=.4, sus=.5))],
}
SFX["locked"] = SFX["deny"]
POPS = [dict(freq=f, ms=140, vol=.3, wave="square", duty=.25, bend=.82,
             harm=.35, sus=.35, curve=2.4) for f in (880, 1100, 1320)]

SNDQ = []
def play(name, i=0, x=None, vol=1.0):
    if not (SOUND_OK and not state["save"]["muted"]): return
    m = state["save"].get("vol", 1.0)
    if m <= 0: return
    if len(SNDQ) > 220: return
    if name == "note":
        SNDQ.append((pygame.time.get_ticks(),
            S(freq=PENTA[i % len(PENTA)], ms=280, vol=.3*m, atk=.015,
              sus=.4, curve=2.2, harm=.5)))
        return
    fn = SFX.get(name)
    if fn is None: return
    pan = 0.0 if x is None else max(-1.0, min(1.0, (x/W)*2-1))
    now = pygame.time.get_ticks()
    for off, kw in fn(vol*m):
        kw = dict(kw); kw["pan"] = max(-1.0, min(1.0, kw.get("pan", 0.0)+pan))
        SNDQ.append((now+off, S(**kw)))

def play_seq(freqs, gap=110, kind="tri"):
    if not (SOUND_OK and not state["save"]["muted"]): return
    m = state["save"].get("vol", 1.0)
    if m <= 0: return
    now = pygame.time.get_ticks()
    SNDQ.append((now, S(freq=60, ms=350, vol=.14*m, noise=.95, nlp=.08)))
    for i, f in enumerate(freqs):
        t = now + i*gap
        SNDQ.append((t, S(freq=f, ms=160, vol=.22*m, wave="square", duty=.3,
                          harm=.3, sus=.5, curve=2.0)))
        SNDQ.append((t, S(freq=f/2, ms=200, vol=.15*m, wave="tri", sus=.5)))
        SNDQ.append((t, S(freq=6000, ms=25, vol=.05*m, noise=.9, nlp=.7)))
    t_end = now + len(freqs)*gap + 120
    for f in freqs:
        SNDQ.append((t_end, S(freq=f, ms=420, vol=.09*m, atk=.02, sus=.8, harm=.4)))

def update_sndq():
    now = pygame.time.get_ticks()
    for item in SNDQ[:]:
        if now >= item[0]: item[1].play(); SNDQ.remove(item)

MUS_STEP = {"menu": 170, "play": 127}
A2,C3,D3,E3,G3,A3,C4,D4,E4,G4,A4,C5,E5 = (110,130.81,146.83,164.81,196.0,
                                          220.0,261.63,293.66,329.63,392.0,
                                          440.0,523.25,659.25)
F2,G2 = 87.31, 98.0
def _bass(f, v=.15): return _d(f, 240, v, wave="tri", atk=.006, sus=.5)
def _kick(v=.2):     return _d(130, 100, v, bend=.35, atk=.001)
def _hat(v=.045):    return _d(6000, 30, v, noise=.9, nlp=.6)
def _ld(f, v=.055):  return _d(f, 200, v, wave="square", duty=.28, sus=.3)
def _arp(f, v=.1):   return _d(f, 300, v, wave="tri", atk=.01, sus=.4)

_MPLAY, _MMENU = {}, {}
for _s in range(0, 32, 4):
    _root = {0: A2, 8: F2, 16: C3, 24: G2}[_s]
    for _k in range(4): _MPLAY[_s+_k] = [_bass(_root)]
for _s in (0, 8, 16, 24): _MPLAY[_s].append(_kick())
for _s in (2, 6, 10, 14, 18, 22, 26, 30): _MPLAY.setdefault(_s, []).append(_hat())
for _s, _f in ((16,E4),(18,G4),(20,A4),(22,C5),(24,A4),(26,G4),(28,E4),(30,D4)):
    _MPLAY.setdefault(_s, []).append(_ld(_f))
_A = [A3,C4,E4,A4,C5,A4,E4,C4]
for _k in range(16):
    _MMENU.setdefault(_k*2, []).append(_arp(_A[_k % 8]))
_MMENU[0].append(_d(A2, 2600, .07, atk=.3, sus=.8))
_MMENU[12].append(_d(E5, 500, .05, harm=.6, sus=.6))
_MMENU[28].append(_d(C5, 500, .05, harm=.6, sus=.6))
MUS = {"menu": _MMENU, "play": _MPLAY}

def update_music():
    if not (SOUND_OK and not state["save"]["muted"]
            and state["save"].get("music", True)):
        state["mus_next"] = pygame.time.get_ticks() + 100
        return
    m = state["save"].get("vol", 1.0)
    if m <= 0:
        state["mus_next"] = pygame.time.get_ticks() + 100
        return
    now = pygame.time.get_ticks()
    song = "menu" if state["screen"] in ("menu", "select", "ach") else "play"
    if song != state["mus_song"]:
        state["mus_song"] = song; state["mus_step"] = 0
        state["mus_next"] = now + 60
    if len(SNDQ) > 150: return
    if state["mus_next"] < now - 500: state["mus_next"] = now
    step_ms = MUS_STEP[song]
    duck = 0.35 if now < state["duck_until"] else 1.0
    pat = MUS[song]
    while state["mus_next"] < now + 150:
        st = state["mus_step"] % len(pat)
        for kw in pat.get(st, []):
            kw = dict(kw); kw["vol"] = kw["vol"] * duck * 0.9 * m
            SNDQ.append((state["mus_next"], S(**kw)))
        state["mus_next"] += step_ms
        state["mus_step"] += 1

def copy_clip(txt):
    try:
        pygame.scrap.init(); pygame.scrap.put_text(txt); return True
    except Exception: return False

# ---------------------------------------------------------- objects
class Obj:
    kind = "?"
    def __init__(self, pos, angle=0.0):
        self.pos = V2(pos); self.angle = math.radians(angle)
        self.locked = False
    def hits(self, p, d): return []
    def contains(self, pt): return False
    def ser(self): return []

def sweep(s, pos, ang, length, col):
    T = state["t"]
    u = V2(math.cos(ang), math.sin(ang))
    q = (T * 90.0) % (length + 90) - 45
    a = max(-length/2, q - 16); b = min(length/2, q + 16)
    if b > a:
        pygame.draw.line(s, col, pos + u*a, pos + u*b, 1)

class Mirror(Obj):
    kind = "mirror"
    def __init__(self, pos, angle=0, length=170):
        super().__init__(pos, angle); self.length = length
    def ends(self):
        u = V2(math.cos(self.angle), math.sin(self.angle)) * (self.length/2)
        return self.pos - u, self.pos + u
    def hits(self, p, d):
        a, b = self.ends()
        t = ray_segment(p, d, a, b)
        return [] if t is None else [(t, unit(V2(-(b-a).y, (b-a).x)))]
    def contains(self, pt):
        a, b = self.ends(); return dist_pt_seg(pt, a, b) < 12
    def draw(self, s, sel):
        a, b = self.ends()
        pygame.draw.line(s, (58,66,100), a, b, 9)
        pygame.draw.line(s, (188,202,235), a, b, 5)
        pygame.draw.line(s, (255,255,255), a, b, 2)
        sweep(s, self.pos, self.angle, self.length, (210,225,255))
        if sel:
            for q in (a, b): pygame.draw.circle(s, GOLD, q, 7, 2)
    def ser(self):
        return ["M", round(self.pos.x), round(self.pos.y),
                round(math.degrees(self.angle), 1), round(self.length)]

class Wall(Mirror):
    kind = "wall"
    def draw(self, s, sel):
        a, b = self.ends(); u = unit(b - a); nrm = V2(-u.y, u.x)
        pygame.draw.line(s, (72,80,108), a, b, 12)
        pygame.draw.line(s, (120,130,160), a, b, 7)
        for i in range(-int(self.length/2)+8, int(self.length/2)-6, 18):
            q = self.pos + u*i
            pygame.draw.line(s, (46,52,80), q - nrm*4, q + nrm*4, 2)
        if sel:
            for q in (a, b): pygame.draw.circle(s, GOLD, q, 8, 2)
    def ser(self):
        return ["W", round(self.pos.x), round(self.pos.y),
                round(math.degrees(self.angle), 1), round(self.length)]

class Splitter(Mirror):
    kind = "splitter"
    def draw(self, s, sel):
        a, b = self.ends(); u = unit(b - a)
        for i in range(8):
            p0 = a + u*(self.length*i/8); p1 = a + u*(self.length*(i+0.6)/8)
            pygame.draw.line(s, (140,230,235), p0, p1, 5)
        pygame.draw.line(s, (220,255,255), a, b, 1)
        sweep(s, self.pos, self.angle, self.length, (200,250,255))
        if sel:
            for q in (a, b): pygame.draw.circle(s, GOLD, q, 7, 2)
    def ser(self):
        return ["S", round(self.pos.x), round(self.pos.y),
                round(math.degrees(self.angle), 1), round(self.length)]

class Glass(Obj):
    kind = "glass"; n = 1.50; dispersive = False; spread = 0.03
    recombiner = False
    def poly_local(self): return []
    def world_pts(self):
        return [self.pos + rot(v, self.angle) for v in self.poly_local()]
    def hits(self, p, d):
        pts = self.world_pts()
        cen = sum(pts, V2()) / len(pts)
        res = []
        for i in range(len(pts)):
            A, B = pts[i], pts[(i+1) % len(pts)]
            t = ray_segment(p, d, A, B)
            if t is None: continue
            e = B - A; n = unit(V2(e.y, -e.x))
            if n.dot((A+B)/2 - cen) < 0: n = -n
            res.append((t, n))
        res.sort(key=lambda h: h[0]); return res
    def draw(self, s, sel):
        pts = ippi(self.world_pts())
        pygame.draw.polygon(s, (150,200,255), pts, 2)
        if sel: pygame.draw.polygon(s, GOLD, pts, 4)
    def ser(self): return []

class GlassRect(Glass):
    def __init__(self, pos, angle=0, w=260, h=52):
        super().__init__(pos, angle); self.w, self.h = w, h
    def poly_local(self):
        w, h = self.w/2, self.h/2
        return [V2(-w,-h), V2(w,-h), V2(w,h), V2(-w,h)]
    def contains(self, pt):
        lp = rot(pt - self.pos, -self.angle)
        return abs(lp.x) <= self.w/2+6 and abs(lp.y) <= self.h/2+6
    def ser(self):
        return ["G", round(self.pos.x), round(self.pos.y),
                round(math.degrees(self.angle), 1), self.w, self.h, round(self.n, 3)]

class Filter(GlassRect):
    def __init__(self, pos, angle=0, w=140, h=26, ci=0):
        super().__init__(pos, angle, w, h)
        self.n = 1.45; self.ci = ci; self.tint = SPECTRUM[ci]
    def draw(self, s, sel):
        pts = ippi(self.world_pts())
        pygame.draw.polygon(s, self.tint, pts, 3)
        pygame.draw.line(s, self.tint, pts[0], pts[2], 1)
        if sel: pygame.draw.polygon(s, GOLD, pts, 4)
    def ser(self):
        return ["F", round(self.pos.x), round(self.pos.y),
                round(math.degrees(self.angle), 1), self.w, self.h,
                round(self.n, 3), self.ci]

class Prism(Glass):
    dispersive = True
    def __init__(self, pos, angle=0, side=240, n=1.52, spread=0.03):
        super().__init__(pos, angle)
        self.n, self.spread = n, spread
        R = side / math.sqrt(3)
        self.verts = [V2(R*math.cos(a), R*math.sin(a)) for a in
                      (math.radians(-90), math.radians(30), math.radians(150))]
    def poly_local(self): return self.verts
    def contains(self, pt):
        lp = rot(pt - self.pos, -self.angle); vs = self.verts
        cr = [(vs[(i+1)%3]-vs[i]).cross(lp-vs[i]) for i in range(3)]
        if all(c >= 0 for c in cr) or all(c <= 0 for c in cr): return True
        return any(dist_pt_seg(lp, vs[i], vs[(i+1)%3]) < 8 for i in range(3))
    def draw(self, s, sel):
        pts = ippi(self.world_pts()); n = len(pts)
        shift = int(state["t"] * 1.4)
        for i in range(n):
            c = SPECTRUM[(i + shift) % len(SPECTRUM)]
            pygame.draw.line(s, c, pts[i], pts[(i+1) % n], 2)
        if sel: pygame.draw.polygon(s, GOLD, pts, 4)
    def ser(self):
        return ["P", round(self.pos.x), round(self.pos.y),
                round(math.degrees(self.angle), 1), 240,
                round(self.n, 3), round(self.spread, 4)]

class Recombiner(Glass):
    recombiner = True
    def __init__(self, pos, angle=0, side=220, n=1.52, spread=-0.05):
        super().__init__(pos, angle)
        self.n, self.spread = n, spread
        R = side / math.sqrt(3)
        self.verts = [V2(R*math.cos(a), R*math.sin(a)) for a in
                      (math.radians(90), math.radians(-30), math.radians(-150))]
        self.side = side
    def poly_local(self): return self.verts
    def contains(self, pt):
        lp = rot(pt - self.pos, -self.angle); vs = self.verts
        cr = [(vs[(i+1)%3]-vs[i]).cross(lp-vs[i]) for i in range(3)]
        if all(c >= 0 for c in cr) or all(c <= 0 for c in cr): return True
        return any(dist_pt_seg(lp, vs[i], vs[(i+1)%3]) < 8 for i in range(3))
    def draw(self, s, sel):
        pts = ippi(self.world_pts()); n = len(pts); T = state["t"]
        shift = -int(T * 1.4)
        for i in range(n):
            c = SPECTRUM[(i + shift) % len(SPECTRUM)]
            pygame.draw.line(s, c, pts[i], pts[(i+1) % n], 2)
        cen = self.pos
        for k in range(3):
            a = T*1.2 + k*2.094
            d = V2(math.cos(a), math.sin(a))
            pygame.draw.line(s, SPECTRUM[(k*2) % 7], cen + d*17, cen + d*9, 1)
        pygame.draw.circle(s, (255,255,255), ip(cen), 3)
        if sel: pygame.draw.polygon(s, GOLD, pts, 4)
    def ser(self):
        return ["A", round(self.pos.x), round(self.pos.y),
                round(math.degrees(self.angle), 1), self.side,
                round(self.n, 3), round(self.spread, 4)]

class Ball(Glass):
    def __init__(self, pos, angle=0, r=95, n=1.5):
        super().__init__(pos, angle); self.r = r; self.n = n
    def hits(self, p, d):
        t = ray_circle(p, d, self.pos, self.r)
        return [] if t is None else [(t, unit(p + d*t - self.pos))]
    def draw(self, s, sel):
        pygame.draw.circle(s, (150,200,255), ip(self.pos), self.r, 2)
        if sel: pygame.draw.circle(s, GOLD, ip(self.pos), self.r+3, 3)
    def contains(self, pt): return (pt - self.pos).length() <= self.r + 6
    def ser(self):
        return ["B", round(self.pos.x), round(self.pos.y), 0,
                self.r, round(self.n, 3)]

class Lens(Glass):
    def __init__(self, pos, angle=0, w=260, h=110, n=1.5, segs=18):
        super().__init__(pos, angle); self.w, self.h = w, h; self.n = n
        pts = []
        for i in range(segs+1):
            x = -w/2 + w*i/segs
            y = -(h/2)*math.sqrt(max(0.0, 1-(2*x/w)**2)); pts.append(V2(x, y))
        for i in range(segs, -1, -1):
            x = -w/2 + w*i/segs
            y =  (h/2)*math.sqrt(max(0.0, 1-(2*x/w)**2)); pts.append(V2(x, y))
        self.verts = pts
    def poly_local(self): return self.verts
    def contains(self, pt):
        lp = rot(pt - self.pos, -self.angle)
        return (lp.x/(self.w/2+6))**2 + (lp.y/(self.h/2+6))**2 <= 1
    def ser(self):
        return ["L", round(self.pos.x), round(self.pos.y),
                round(math.degrees(self.angle), 1), self.w, self.h, round(self.n, 3)]

class Concave(Obj):
    kind = "mirror"
    def __init__(self, pos, angle=0, Rc=600, width=260, segs=14):
        super().__init__(pos, angle)
        self.Rc, self.width, self.segs = Rc, width, segs
    def world_pts(self):
        a = self.width/2; R = self.Rc; pts = []
        for i in range(self.segs+1):
            x = -a + 2*a*i/self.segs
            y = -(R - math.sqrt(max(0.0, R*R - x*x)))
            pts.append(self.pos + rot(V2(x, y), self.angle))
        return pts
    def hits(self, p, d):
        pts = self.world_pts(); res = []
        for i in range(self.segs):
            A, B = pts[i], pts[i+1]
            t = ray_segment(p, d, A, B)
            if t is not None:
                e = B - A; res.append((t, unit(V2(-e.y, e.x))))
        return res
    def contains(self, pt):
        pts = self.world_pts()
        return any(dist_pt_seg(pt, pts[i], pts[i+1]) < 12 for i in range(self.segs))
    def draw(self, s, sel):
        pts = ippi(self.world_pts())
        pygame.draw.lines(s, (58,66,100), False, pts, 9)
        pygame.draw.lines(s, (188,202,235), False, pts, 5)
        pygame.draw.lines(s, (255,255,255), False, pts, 2)
        sweep(s, self.pos, self.angle, self.width, (210,225,255))
        if sel: pygame.draw.lines(s, GOLD, False, pts, 3)
    def ser(self):
        return ["C", round(self.pos.x), round(self.pos.y),
                round(math.degrees(self.angle), 1), self.Rc, self.width]

class PortalPair(Obj):
    kind = "portal"; R = 26
    def __init__(self, pos, angle=0, h=115):
        super().__init__(pos, angle); self.h = h
    def ends(self):
        u = V2(math.cos(self.angle), math.sin(self.angle)) * self.h
        return self.pos - u, self.pos + u
    def hits(self, p, d):
        res = []
        for i, c in enumerate(self.ends()):
            t = ray_circle(p, d, c, self.R)
            if t is not None: res.append((t, i))
        res.sort(key=lambda hh: hh[0]); return res
    def contains(self, pt):
        return min((pt - c).length() for c in self.ends()) < self.R + 12
    def draw(self, s, sel):
        A, B = self.ends(); T = state["t"]
        pygame.draw.aaline(s, (58,78,120), A, B)
        for i, (c, col) in enumerate([(A, (90,220,255)), (B, (255,100,225))]):
            pygame.draw.circle(s, (30,40,70), c, self.R)
            pygame.draw.circle(s, col, c, self.R, 3)
            pygame.draw.circle(s, col, c, self.R-7, 1)
            for k in range(4):
                a = T*(1 if i == 0 else -1) + k*math.pi/2
                q = c + V2(math.cos(a), math.sin(a))*(self.R-3)
                pygame.draw.line(s, col, q, c + (q-c)*0.55, 2)
            for k in range(5):
                a = T*2.2*(1 if i == 0 else -1) + k*2*math.pi/5
                mp = c + V2(math.cos(a), math.sin(a))*(self.R*0.62)
                pygame.draw.circle(s, dim(col, 0.9), ip(mp), 2)
            if sel: pygame.draw.circle(s, GOLD, c, self.R+5, 2)
    def ser(self):
        return ["X", round(self.pos.x), round(self.pos.y),
                round(math.degrees(self.angle), 1), self.h]

class Source(Obj):
    kind = "source"
    def __init__(self, pos, angle=0, ci=0):
        super().__init__(pos, angle); self.ci = ci
    @property
    def color(self): return SOURC_COLORS[self.ci]
    def emit(self):
        d = V2(math.cos(self.angle), math.sin(self.angle))
        return self.pos + d*24, d
    def contains(self, pt): return (pt - self.pos).length() < 22
    def draw(self, s, sel):
        d = V2(math.cos(self.angle), math.sin(self.angle))
        tip = self.pos + d*30
        pygame.draw.line(s, self.color, self.pos + d*12, tip, 3)
        p = V2(-d.y, d.x)
        pygame.draw.polygon(s, self.color,
                            [ip(tip), ip(tip - d*10 + p*6), ip(tip - d*10 - p*6)])
        pygame.draw.circle(s, (40,48,80), ip(self.pos), 16)
        pygame.draw.circle(s, (70,82,130), ip(self.pos), 16, 2)
        pygame.draw.circle(s, self.color, ip(self.pos), 8)
        if sel: pygame.draw.circle(s, GOLD, ip(self.pos), 21, 2)
    def ser(self):
        return ["O", round(self.pos.x), round(self.pos.y),
                round(math.degrees(self.angle), 1), self.ci]

class Target(Obj):
    kind = "target"
    def __init__(self, pos, color=None):
        super().__init__(pos)
        self.color = color; self.R = 22 if color else 16
        self.lit = False; self.was_lit = False; self.litcolor = WHITE
        self.mix = ""
    def contains(self, pt): return (pt - self.pos).length() < self.R + 8
    def draw(self, s, sel):
        R = self.R; T = state["t"]
        ring = self.color if self.color else (96,110,150)
        if self.lit:
            pu = 1.0 + 0.12*math.sin(T*3.6)
            pygame.draw.circle(s, self.litcolor, ip(self.pos), int(R*1.6*pu), 2)
            pygame.draw.circle(s, self.litcolor, ip(self.pos), int(R*0.55))
        pygame.draw.circle(s, (26,32,54), ip(self.pos), R-3)
        pygame.draw.circle(s, ring, ip(self.pos), R, 3)
        if self.color:
            req = COMP_OF[self.color]
            for i, ch in enumerate(req):
                a = -math.pi/2 + (i - (len(req)-1)/2)*0.9
                dp = self.pos + V2(math.cos(a), math.sin(a))*(R*0.58)
                col = PRIM[ch]
                on = ch in self.mix
                pygame.draw.circle(s, col if on else dim(col, 0.35), ip(dp), 3)
        elif not self.lit:
            pygame.draw.circle(s, (96,110,150), ip(self.pos), 5)
        if sel: pygame.draw.circle(s, GOLD, ip(self.pos), R+6, 2)
    def ser(self):
        ci = -1 if self.color is None else SPECTRUM.index(self.color)
        return ["T", round(self.pos.x), round(self.pos.y), 0, ci]

objects = []
def sources(): return [o for o in objects if isinstance(o, Source)]
def targets(): return [o for o in objects if isinstance(o, Target)]

# ------------------------------------------- serialize / share codes
SER_LEN = {"M":5,"W":5,"S":5,"G":7,"F":8,"P":7,"B":6,"L":7,"C":6,
           "X":5,"O":5,"T":5,"A":7}

def _obj_from_ser(p):
    tag, x, y, a = p[0], p[1], p[2], p[3]
    if   tag == "M": return Mirror((x,y), a, p[4])
    elif tag == "W": return Wall((x,y), a, p[4])
    elif tag == "S": return Splitter((x,y), a, p[4])
    elif tag == "G":
        o = GlassRect((x,y), a, p[4], p[5]); o.n = p[6]; return o
    elif tag == "F": return Filter((x,y), a, p[4], p[5], p[7])
    elif tag == "P": return Prism((x,y), a, p[4], p[5], p[6])
    elif tag == "A":
        o = Recombiner((x,y), a, p[4]); o.n, o.spread = p[5], p[6]; return o
    elif tag == "B": return Ball((x,y), 0, p[4], p[5])
    elif tag == "L": return Lens((x,y), a, p[4], p[5], p[6])
    elif tag == "C": return Concave((x,y), a, p[4], p[5])
    elif tag == "X": return PortalPair((x,y), a, p[4])
    elif tag == "O": return Source((x,y), a, p[4])
    elif tag == "T":
        return Target((x,y), None if p[4] < 0 else SPECTRUM[p[4]])
    raise ValueError

def obj_from_ser(p):
    o = _obj_from_ser(p)
    nlen = SER_LEN.get(p[0], 99)
    if len(p) > nlen and p[nlen] == 1:
        o.locked = True
    return o

def encode_scene():
    parts = []
    for o in objects:
        p = o.ser()
        if o.locked: p.append(1)
        parts.append(p)
    return "LL2:" + base64.urlsafe_b64encode(
        json.dumps(parts, separators=(",", ":")).encode()).decode()

def decode_scene(code):
    code = code.strip()
    if not code.startswith("LL2:"): raise ValueError
    parts = json.loads(base64.urlsafe_b64decode(code[4:].encode()).decode())
    return [obj_from_ser(p) for p in parts]

def clone_obj(o):
    c = obj_from_ser(o.ser())
    c.locked = o.locked
    return c

# ------------------------------------------ solution codes & replay
def encode_solution():
    if state["mode"] != "level" or not state["rec"]: return ""
    data = {"p": state["pack"], "l": state["level"],
            "t": int(state["win_time"] - state["start_time"]),
            "e": state["rec"]}
    return "LLG:" + base64.urlsafe_b64encode(
        json.dumps(data, separators=(",", ":")).encode()).decode()

def decode_solution(code):
    try:
        code = code.strip()
        if not code.startswith("LLG:"): return None
        d = json.loads(base64.urlsafe_b64decode(code[4:].encode()).decode())
        if not isinstance(d.get("e"), list) or not d["e"]: return None
        return d
    except Exception:
        return None

def rec_commit():
    if state["mode"] != "level" or state["complete"] or state["replay"]:
        return
    o = state["sel"]
    if o is None or o not in objects or not movable(o): return
    if len(state["rec"]) >= 400: return
    state["rec"].append([pygame.time.get_ticks() - state["start_time"],
                         objects.index(o),
                         round(o.pos.x, 1), round(o.pos.y, 1),
                         round(math.degrees(o.angle), 2)])

def start_replay(sol):
    build_level(state["level"])
    ev = sorted([list(e) for e in sol["e"]], key=lambda e: e[0])
    kf = {}
    for e in ev:
        kf.setdefault(int(e[1]), []).append((e[0], e[2], e[3], e[4]))
    for lst in kf.values(): lst.sort()
    state["replay"] = {"ev": ev, "kf": kf, "i": 0,
                       "t0": pygame.time.get_ticks(),
                       "end_t": max((e[0] for e in ev), default=0),
                       "granted": False}
    play("ghost")
    say("GHOST REPLAY — Esc to stop", 2400)

def apply_replay():
    rp = state["replay"]
    now = pygame.time.get_ticks()
    rt = now - rp["t0"]
    while rp["i"] < len(rp["ev"]) and rp["ev"][rp["i"]][0] <= rt:
        rp["i"] += 1
    ended = True
    for idx, lst in rp["kf"].items():
        if idx >= len(objects): continue
        o = objects[idx]
        prev = None; nxt = None
        for e in lst:
            if e[0] <= rt: prev = e
            else: nxt = e; break
        if prev is None:
            ended = False
            continue
        if nxt is None:
            o.pos.update(prev[1], prev[2])
            o.angle = math.radians(prev[3])
        else:
            ended = False
            f = min(1.0, (rt - prev[0]) / max(1, nxt[0] - prev[0]))
            o.pos.x = prev[1] + (nxt[1] - prev[1]) * f
            o.pos.y = prev[2] + (nxt[2] - prev[2]) * f
            da = ((nxt[3] - prev[3] + 540.0) % 360.0) - 180.0
            o.angle = math.radians(prev[3] + da * f)
        o.pos.x = min(max(o.pos.x, 24), W-24)
        o.pos.y = min(max(o.pos.y, TOP+24), H-20)
    if ended and rt > rp["end_t"] + 700:
        state["replay"] = None
        if not rp["granted"]:
            grant("ghost")
        say("Replay finished", 1800)
    state["dirty"] = True

def ghost_for(pack, idx):
    gh = state["save"].get("ghosts", {})
    return gh.get(pack, {}).get(str(idx))

# ---------------------------------------------------------- effects
sparks = []
rings = []
bursts = []

def spawn_sparks(pos, n, col, cnt):
    if not state["save"]["fx"] or cnt <= 0: return
    for _ in range(cnt):
        ang = math.atan2(n.y, n.x) + random.uniform(-1.1, 1.1)
        sp = random.uniform(40, 160)
        sparks.append([V2(pos), V2(math.cos(ang)*sp, math.sin(ang)*sp),
                       random.uniform(0.25, 0.6), col])

def ring(pos, col, v=260, life=0.8, w=2, r0=8):
    rings.append({"pos": V2(pos), "col": col, "r": float(r0),
                  "v": float(v), "life": life, "age": 0.0, "w": w})

def spawn_burst(pos, col, n, spd=(60, 320)):
    if not state["save"]["fx"]: return
    for _ in range(n):
        ang = random.uniform(0, 6.283); sp = random.uniform(*spd)
        bursts.append([V2(pos), V2(math.cos(ang)*sp, math.sin(ang)*sp), col,
                       random.uniform(0.7, 1.5), 0.0, random.uniform(0, 6.28)])
    if len(bursts) > 700: del bursts[:len(bursts)-700]

def update_sparks(dt):
    for sp in sparks[:]:
        sp[0] += sp[1]*dt; sp[1] *= 0.90; sp[2] -= dt
        if sp[2] <= 0: sparks.remove(sp)
    if len(sparks) > 320: del sparks[:len(sparks)-320]

def update_fx(dt):
    for rg in rings[:]:
        rg["r"] += rg["v"]*dt; rg["age"] += dt
        if rg["age"] >= rg["life"]: rings.remove(rg)
    for bp in bursts[:]:
        bp[4] += dt
        if bp[4] >= bp[3]: bursts.remove(bp); continue
        bp[1].y += 250*dt
        bp[1] *= max(0.0, 1 - 1.3*dt)
        bp[0] += bp[1]*dt

dust = [{"p": V2(random.uniform(0,W), random.uniform(TOP,H)),
         "v": V2(random.uniform(-6,6), random.uniform(-4,4)),
         "a": random.uniform(20,60)} for _ in range(55)]
def update_dust(dt):
    for d in dust:
        d["p"] += d["v"]*dt
        if d["p"].x < 0: d["p"].x = W
        if d["p"].x > W: d["p"].x = 0
        if d["p"].y < TOP: d["p"].y = H
        if d["p"].y > H: d["p"].y = TOP

# ----------------------------------------------------- backdrops
def make_nebula(seed):
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    rng = random.Random(seed)
    for _ in range(8):
        cx, cy = rng.uniform(60, W-60), rng.uniform(TOP+60, H-60)
        r = rng.uniform(130, 330)
        col = rng.choice([(40,70,140),(90,50,130),(30,90,120)])
        for i in range(14):
            rr = int(r*(1 - i/14))
            if rr < 4: continue
            a = int(3 + 6*(i/14)**2)
            pygame.draw.circle(s, col + (a,),
                               (int(cx+rng.uniform(-50,50)),
                                int(cy+rng.uniform(-36,36))), rr)
    return s
NEB1 = make_nebula(3); NEB1.set_alpha(160)
NEB2 = make_nebula(9); NEB2.set_alpha(110)

_rng = random.Random(11)
STARS = [(_rng.uniform(0, W), _rng.uniform(TOP, H), _rng.choice((1,1,1,2)),
          _rng.uniform(30, 90), _rng.uniform(0, 6.28), _rng.uniform(0.5, 2.0))
         for _ in range(90)]

def draw_bg(s, T):
    ox = int(math.sin(T*0.05)*22); oy = int(math.cos(T*0.04)*16)
    s.blit(NEB1, (ox - 30, oy - 24))
    s.blit(NEB2, (W - 300 - ox, oy + 40))
    for (x, y, r, a0, ph, spd) in STARS:
        a = a0 + 22*math.sin(T*spd + ph)
        if a <= 5: continue
        c = (min(255,int(a)), min(255,int(a)+10), min(255,int(a)+30))
        s.fill(c, (int(x), int(y), r, r))
        if r == 2 and a > 72:
            s.fill(dim(c, 0.6), (int(x)-2, int(y), 5, 1))
            s.fill(dim(c, 0.6), (int(x), int(y)-2, 1, 5))

def draw_motes(s, T):
    for i in range(26):
        px = int((i*173 + math.sin(T*0.4 + i)*30) % W)
        py = int(H - ((T*(12 + (i % 5)*6) + i*97) % (H - TOP)))
        a = 38 + 26*math.sin(T*1.3 + i)
        if a > 8:
            s.fill((int(a), int(a)+14, int(a)+44), (px, py, 2, 2))

def make_vignette():
    small = pygame.Surface((64, 36), pygame.SRCALPHA)
    for th, a in ((4, 95), (6, 62), (8, 36), (10, 20)):
        pygame.draw.rect(small, (4, 6, 16, a), (0, 0, 64, 36), th)
    return pygame.transform.smoothscale(small, (W, H))
VIGNETTE = make_vignette()
FLASH_SURF = pygame.Surface((W, H), pygame.SRCALPHA)
FLASH_SURF.fill((255, 255, 255))

# ---------------------------------------------- render surfaces
light = pygame.Surface((W, H))
caust = pygame.Surface((W, H))
dyn   = pygame.Surface((W, H))
bq    = pygame.Surface((W//4, H//4))
bq_s  = pygame.Surface((W//4, H//4))
bq_d  = pygame.Surface((W//4, H//4))
glass_layer = pygame.Surface((W, H), pygame.SRCALPHA)

def draw_glass_fill(s, o):
    if isinstance(o, Ball):
        pygame.draw.circle(s, (120,180,255,34), ip(o.pos), o.r)
        pygame.draw.circle(s, (170,215,255,26), ip(o.pos), int(o.r*0.8))
        pygame.draw.circle(s, (215,238,255,20),
                           ip(o.pos - V2(o.r*0.32, o.r*0.32)), int(o.r*0.42))
        return
    if isinstance(o, Filter):
        pygame.draw.polygon(s, o.tint + (105,), ippi(o.world_pts()))
        wp = o.world_pts()
        pygame.draw.line(s, (255,255,255,36), ip(wp[0]), ip(wp[2]), 2)
        return
    wp = o.world_pts()
    pygame.draw.polygon(s, (120,180,255,34), ippi(wp))
    cen = sum(wp, V2()) / len(wp)
    inner = [cen + (p - cen)*0.82 for p in wp]
    pygame.draw.polygon(s, (190,225,255,24), ippi(inner))
    p1 = wp[0] + (wp[1]-wp[0])*0.32
    i2 = len(wp)//2
    p2 = wp[i2] + (wp[(i2+1) % len(wp)] - wp[i2])*0.68
    pygame.draw.line(s, (235,245,255,30), ip(p1), ip(p2), 2)

# ------------------------------------------------------- CAUSTICS
def n_eff(o, col):
    if o.dispersive and col in SPECTRUM:
        N = len(SPECTRUM)
        return o.n + (SPECTRUM.index(col) - (N-1)/2.0) * o.spread
    return o.n

def march_probe(p, d, col, I):
    segs = []; pools = []; last_air = None
    cur = 1.0; steps = 0; trav = 0.0
    d = unit(d)
    while steps < 6 and trav < 1500:
        steps += 1
        best = None
        for o in objects:
            for hit in o.hits(p, d):
                if best is None or hit[0] < best[0][0]: best = (hit, o)
        thit = None
        for tg in targets():
            h = ray_circle(p, d, tg.pos, tg.R)
            if h is not None and (thit is None or h < thit[0]): thit = (h, tg)
        use_t = thit is not None and (best is None or thit[0] < best[0][0])
        if best is None and thit is None:
            segs.append((p, p + d*1800))
            if cur == 1.0: last_air = (p, d)
            break
        if use_t:
            t, tg = thit
            if trav + t > 1500: break
            end = p + d*t; segs.append((p, end))
            pools.append((end, -d, col, min(1.0, I*1.25)))
            if cur == 1.0: last_air = (p, d)
            break
        (t, pay), o = best
        if trav + t > 1500:
            segs.append((p, p + d*(1500-trav)))
            if cur == 1.0: last_air = (p, d)
            break
        end = p + d*t; segs.append((p, end)); trav += t
        k = o.kind
        if k == "portal": break
        if k != "glass":
            pools.append((end, pay, col, I))
            if cur == 1.0: last_air = (p, d)
            break
        nn = pay if d.dot(pay) < 0 else -pay
        entering = d.dot(pay) < 0
        if o.recombiner:
            ne = max(1.02, n_eff(o, col))
            rr = refract(d, nn, 1.0/ne if entering else ne)
            if rr is None: rr = reflect(d, nn)
            elif not entering: break
            else: cur = ne; I *= 0.97
        elif entering:
            ne = n_eff(o, col)
            rr = refract(d, nn, 1.0/ne)
            if rr is None: rr = reflect(d, nn)
            else: cur = ne; I *= 0.97
        else:
            rr = refract(d, nn, cur)
            if rr is None: rr = reflect(d, nn)
            else: cur = 1.0; I *= 0.97
        rr = unit(rr)
        if cur == 1.0: last_air = (end, rr)
        p = end + rr*0.5; d = rr
    return segs, pools, last_air

def csplat(pos, col, k, rad):
    if k <= 0: return
    pygame.draw.circle(caust, dim(col, min(1.0, k)), ip(pos), rad)
    pygame.draw.circle(bq_s, dim(col, min(1.0, k)*0.8),
                       (int(pos.x/4), int(pos.y/4)), max(1, rad*2))

def build_caustics():
    caust.fill((0,0,0))
    state["caust_rays"] = 0
    if not state["save"].get("caustics", True): return
    fx = state["save"]["fx"]
    budget = 420
    for (ep, d, col, I, o) in state["caust_events"]:
        if budget <= 0: break
        perp = V2(-d.y, d.x)
        white = (col == WHITE)
        cols = SPECTRUM if (o.dispersive and white) else [col]
        M = 7 if len(cols) > 1 else 13
        for c in cols:
            sub = []
            for k2 in range(M):
                if budget <= 0: break
                off = (k2 - (M-1)/2.0) * (CAUST_W/(M-1))
                sp = ep + perp*off - d*8
                segs, pools, la = march_probe(sp, d, c, I)
                budget -= 1; state["caust_rays"] += 1
                sub.append((segs, pools, la))
                if fx:
                    for (a, b) in segs:
                        pygame.draw.line(caust, dim(c, 0.05), a, b, 1)
                for (hpt, nrm, hc, hI) in pools:
                    tang = V2(-nrm.y, nrm.x)
                    pygame.draw.line(caust, dim(hc, 0.30*hI),
                                     hpt - tang*8, hpt + tang*8, 3)
                    csplat(hpt, hc, 0.32*hI, 4)
            for i in range(len(sub)-1):
                la1 = sub[i][2]; la2 = sub[i+1][2]
                if la1 is None or la2 is None: continue
                (p1, d1), (p2, d2) = la1, la2
                den = d1.x*d2.y - d1.y*d2.x
                if abs(den) < 1e-6: continue
                dp = p2 - p1
                t1 = (dp.x*d2.y - dp.y*d2.x) / den
                t2 = (dp.x*d1.y - dp.y*d1.x) / den
                if not (2.0 < t1 < 2400 and 2.0 < t2 < 2400): continue
                kI = min(0.55, abs(den)*2.5) * I * 0.85
                if kI < 0.02: continue
                csplat(p1 + d1*t1, c, kI, 2)

def compute_mixpoints():
    pts = []
    bl = [bm for bm in state["beams"]
          if bm[3] >= MIX_VIS and (bm[1]-bm[0]).length() >= 60][:60]
    for i in range(len(bl)):
        a1, b1, c1, I1 = bl[i]
        for j in range(i+1, len(bl)):
            a2, b2, c2, I2 = bl[j]
            if c1 == c2: continue
            X = seg_x(a1, b1, a2, b2)
            if X is None: continue
            pts.append((X, mix_colors(c1, c2), min(I1, I2)))
            if len(pts) >= 40: return pts
    return pts

def rebuild_static():
    glass_layer.fill((0,0,0,0))
    for o in objects:
        if isinstance(o, Glass): draw_glass_fill(glass_layer, o)
    light.fill((0,0,0)); bq_s.fill((0,0,0))
    for (a, b, c, I) in state["beams"]:
        cc = dim(c, min(1.0, I))
        pygame.draw.line(light, dim(cc, 0.18), a, b, 11)
        pygame.draw.line(light, dim(cc, 0.45), a, b, 5)
        pygame.draw.line(light, cc, a, b, 2)
        pygame.draw.line(bq_s, dim(cc, 0.8),
                         (a.x/4, a.y/4), (b.x/4, b.y/4), 2)
    build_caustics()
    mixpts = compute_mixpoints()
    state["mixpts"] = mixpts
    for (X, mc, I) in mixpts:
        csplat(X, mc, 0.30*min(1.0, I+0.2), 4)
        pygame.draw.circle(bq_s, dim(mc, 0.5),
                           (int(X.x/4), int(X.y/4)), 3)
    if mixpts:
        now = pygame.time.get_ticks()
        if now - state["last_mix"] > 700:
            state["last_mix"] = now
            play("mixfx", x=mixpts[0][0].x)
    for (p, col, I, d) in state["flares"][:48]:
        L = 8 + 16*I
        dd = dim(col, min(1.0, I + 0.2))
        pygame.draw.line(light, dd, p - d*L, p + d*L, 1)
        pygame.draw.line(light, dd, p - V2(-d.y, d.x)*L,
                                  p + V2(-d.y, d.x)*L, 1)
        pygame.draw.circle(bq_s, dim(col, 0.7*I),
                           (int(p.x/4), int(p.y/4)), int(3 + 4*I))

def add_dot(p, col, rl=0, rb=0):
    if rl > 0: pygame.draw.circle(dyn, col, ip(p), rl)
    if rb > 0: pygame.draw.circle(bq_d, dim(col, 0.85),
                                  (int(p.x/4), int(p.y/4)), rb)

def draw_dynamics(T):
    dyn.fill((0,0,0)); bq_d.fill((0,0,0))
    beams = state["beams"]; fx = state["save"]["fx"]
    if fx:
        for (bi, off, sp, sz, wa, wp) in state["photons"]:
            if bi >= len(beams): continue
            a, b, c, I = beams[bi]
            L = (b - a).length()
            if L < 1: continue
            u = (b - a) / L
            pr = (off + sp*T) % L
            pos = a + u*pr + V2(-u.y, u.x) * (math.sin(T*3 + wp) * wa)
            add_dot(pos, dim(c, min(1.0, I + 0.2)), max(1, int(sz)), 2)
    for (X, mc, I) in state.get("mixpts", []):
        pu = 0.55 + 0.45*math.sin(T*4 + X.x*0.013)
        add_dot(X, dim(mc, 0.42*pu), int(7 + 3*pu), 3)
        for k in range(4):
            ang = T*1.5 + k*math.pi/2
            d = V2(math.cos(ang), math.sin(ang))
            pygame.draw.line(dyn, dim(mc, 0.55*pu),
                             X + d*5, X + d*(11 + 2*pu), 1)
    for i, (p, col, I, d) in enumerate(state["flares"][:26]):
        r = 5 + 3*math.sin(T*5 + i)
        pygame.draw.circle(dyn, dim(col, 0.5*I), ip(p), int(r), 1)
        add_dot(p, dim(col, 0.35*I), 0, 2)
    for src in sources():
        pu = 0.7 + 0.3*math.sin(T*2.5 + src.pos.x*0.013)
        add_dot(src.pos, dim(src.color, 0.26*pu), int(18 + 5*pu), 6)
        pygame.draw.circle(dyn, dim(src.color, 0.5), ip(src.pos), 9)
    for tg in targets():
        if not tg.lit: continue
        col = tg.litcolor
        add_dot(tg.pos, dim(col, 0.5), int(tg.R*1.5), 5)
        for k in range(6):
            ang = T*0.9 + k*math.pi/3
            d = V2(math.cos(ang), math.sin(ang))
            r0 = tg.R*1.15
            r1 = tg.R*(1.7 + 0.35*math.sin(T*2.4 + k))
            pygame.draw.line(dyn, dim(col, 0.45),
                             tg.pos + d*r0, tg.pos + d*r1, 1)
    for rg in rings:
        a = max(0.0, 1 - rg["age"]/rg["life"])
        if a <= 0: continue
        pygame.draw.circle(dyn, dim(rg["col"], 0.75*a),
                           ip(rg["pos"]), int(rg["r"]), rg["w"])
        pygame.draw.circle(bq_d, dim(rg["col"], 0.5*a),
                           (int(rg["pos"].x/4), int(rg["pos"].y/4)),
                           max(1, int(rg["r"]/4)), 1)
    if fx:
        for bp in bursts:
            a = 1 - bp[4]/bp[3]
            tw = 0.55 + 0.45*math.sin(bp[4]*22 + bp[5])
            add_dot(bp[0], dim(bp[2], max(0.0, a*tw)), 2, 1)
        for sp in sparks:
            a = max(0, min(255, int(255*sp[2]/0.6)))
            add_dot(sp[0], tuple(int(ch*a/255) for ch in sp[3]), 2, 1)

def draw_light_fx(s):
    bq.blit(bq_s, (0, 0))
    bq.blit(bq_d, (0, 0), special_flags=pygame.BLEND_ADD)
    b1 = pygame.transform.smoothscale(bq, (W//2, H//2))
    wide = pygame.transform.smoothscale(b1, (W, H))
    bq2 = bq.copy(); bq2.fill((100,100,100), special_flags=pygame.BLEND_MULT)
    b2 = pygame.transform.smoothscale(bq2, (W//8, H//8))
    wide2 = pygame.transform.smoothscale(b2, (W, H))
    area = pygame.Rect(0, TOP, W, H-TOP)
    s.blit(wide2, (0,0), area=area, special_flags=pygame.BLEND_ADD)
    s.blit(wide,  (0,0), area=area, special_flags=pygame.BLEND_ADD)
    s.blit(light, (0,0), area=area, special_flags=pygame.BLEND_ADD)
    s.blit(dyn,   (0,0), area=area, special_flags=pygame.BLEND_ADD)

# -------------------------------------------------- ray tracer (dirty)
def hitsfx(name, x, I, cd, vol=1.0):
    now = pygame.time.get_ticks()
    if I < 0.3: return
    if now - state["hitcd"].get(name, 0) < cd: return
    state["hitcd"][name] = now
    play(name, x=x, vol=vol*min(1.0, I))

def apply_tint(o, col, I, entering, pos, nn):
    tint = getattr(o, "tint", None)
    if tint is None or not entering: return col, I
    if col == tint: return col, I*0.97
    spawn_sparks(pos, nn, tint, 2)
    return tint, (I*0.90 if col == WHITE else I*0.05)

def group_staged(staged):
    groups = []; used = [False]*len(staged)
    for i in range(len(staged)):
        if used[i]: continue
        g = [staged[i]]; used[i] = True
        for j in range(i+1, len(staged)):
            if used[j]: continue
            a, b = staged[i], staged[j]
            if (a[0]-b[0]).length() < 16 and \
               math.acos(max(-1.0, min(1.0, a[1].dot(b[1])))) < 0.13:
                g.append(staged[j]); used[j] = True
        groups.append(g)
    return groups

def trace():
    beams = []; flares = []; caust_ev = []
    for tg in targets(): tg.lit = False
    queue = []
    for src in sources():
        p, d = src.emit(); queue.append((p, d, src.color, 1.0, 0))
    staged = []
    merged_any = False
    guard = 0
    while True:
        if not queue:
            if not staged: break
            for g in group_staged(staged):
                if len(g) >= 2:
                    comp = set()
                    for s in g: comp |= COMP_SET[s[2]]
                    mc = COMP_TO.get("".join(sorted(comp)), g[0][2])
                    acc = V2()
                    for s in g: acc += s[1]
                    D = unit(acc)
                    P = sum((s[0] for s in g), V2()) / len(g)
                    I = min(1.0, sum(s[3] for s in g) * 0.85)
                    dep = max(s[4] for s in g)
                    queue.append((P + D*3, D, mc, I, dep))
                    merged_any = True
                    ring(P, mc, v=170, life=0.5, r0=4)
                    if mc == WHITE and len({s[2] for s in g}) >= 3:
                        grant("recomb")
                else:
                    s = g[0]
                    queue.append((s[0] + s[1]*3, s[1], s[2], s[3], s[4]))
            staged = []
            if merged_any:
                now = pygame.time.get_ticks()
                if now - state["last_recomb"] > 500:
                    state["last_recomb"] = now
                    play("recomb")
            continue
        guard += 1
        if guard > 7000 or len(beams) >= MAX_BEAMS: break
        p, d, col, I, depth = queue.pop(0)
        if depth > MAX_DEPTH or I < MIN_I: continue
        d = unit(d)
        best = None
        for o in objects:
            for hit in o.hits(p, d):
                if best is None or hit[0] < best[0][0]: best = (hit, o)
        if best is None:
            beams.append((p, p + d*2600, col, I*0.55)); continue
        (t, payload), o = best
        end = p + d*t
        beams.append((p, end, col, I))
        flares.append((end, col, min(1.0, I + 0.15), d))
        if o.kind == "mirror":
            hitsfx("reflect", end.x, I, 90)
            nn = payload if d.dot(payload) < 0 else -payload
            r = reflect(d, nn)
            queue.append((end + r*0.6, r, col, I*0.96, depth+1))
            spawn_sparks(end, nn, col, 3)
        elif o.kind == "wall":
            hitsfx("thud", end.x, I, 130)
            spawn_sparks(end, payload, col, 5)
        elif o.kind == "splitter":
            hitsfx("split", end.x, I, 140)
            nn = payload if d.dot(payload) < 0 else -payload
            rf = reflect(d, nn)
            queue.append((end + rf*0.6, rf, col, I*0.50, depth+1))
            queue.append((end + d*0.7,  d,  col, I*0.45, depth+1))
            spawn_sparks(end, nn, col, 2)
        elif o.kind == "portal":
            grant("warp")
            now = pygame.time.get_ticks()
            if now - state["last_warp"] > 220:
                state["last_warp"] = now
                play("warp", x=end.x)
            A, B = o.ends()
            other = B if payload == 0 else A
            queue.append((other + d*(o.R+2), d, col, I*0.98, depth+1))
            spawn_sparks(end, -d, (90,220,255) if payload == 0 else (255,100,225), 4)
            spawn_sparks(other, d, (255,100,225) if payload == 0 else (90,220,255), 4)
        else:
            nn = payload if d.dot(payload) < 0 else -payload
            entering = d.dot(payload) < 0
            col, I = apply_tint(o, col, I, entering, end, nn)
            if entering:
                hitsfx("glass", end.x, I, 160)
                if I > 0.22 and depth < 10:
                    caust_ev.append((end, d, col, I, o))
            if entering and o.dispersive and col == WHITE:
                hitsfx("disp", end.x, I, 300, vol=1.3)
                N = len(SPECTRUM)
                for i, c in enumerate(SPECTRUM):
                    rr = refract(d, nn, 1.0/(o.n + (i-(N-1)/2)*o.spread))
                    if rr: queue.append((end + rr*0.7, rr, c, I*0.88, depth+1))
                rf = reflect(d, nn)
                queue.append((end + rf*0.7, rf, col, I*0.10, depth+1))
                spawn_sparks(end, nn, WHITE, 4)
            elif o.recombiner:
                ne = max(1.02, n_eff(o, col))
                rr = refract(d, nn, 1.0/ne if entering else ne)
                if rr is None:
                    rr = unit(reflect(d, nn))
                    queue.append((end + rr*0.6, rr, col, I*0.98, depth+1))
                    spawn_sparks(end, nn, col, 3)
                elif entering:
                    queue.append((end + rr*0.7, unit(rr), col, I*0.97, depth+1))
                else:
                    staged.append((end, unit(rr), col, I, depth+1))
                    spawn_sparks(end, unit(rr), col, 1)
            else:
                rr = refract(d, nn, 1.0/o.n if entering else o.n)
                if rr is not None:
                    queue.append((end + rr*0.7, rr, col, I*0.97, depth+1))
                    if I > 0.25 and depth < 14:
                        rf = reflect(d, nn)
                        queue.append((end + rf*0.7, rf, col, I*0.14, depth+1))
                else:
                    hitsfx("tir", end.x, I, 250)
                    grant("tir")
                    rf = reflect(d, nn)
                    queue.append((end + rf*0.7, rf, col, I*0.98, depth+1))
                    spawn_sparks(end, nn, col, 3)
                spawn_sparks(end, nn, col, 1)
    for tg in targets():
        got = set(); cols = set()
        for (a, b, c, I) in beams:
            if I < MIX_GATE: continue
            if dist_pt_seg(tg.pos, a, b) < tg.R:
                got |= COMP_SET[c]; cols.add(c)
        tg.mix = "".join(sorted(got))
        if len(cols) - (1 if WHITE in cols else 0) >= 3:
            grant("white3")
        if tg.color is None:
            tg.lit = bool(got)
            tg.litcolor = COMP_TO.get(tg.mix, WHITE)
        else:
            tg.lit = (tg.mix == COMP_OF[tg.color])
            tg.litcolor = COMP_TO.get(tg.mix, tg.color)
    pho = []
    if state["save"]["fx"]:
        for i, (a, b, c, I) in enumerate(beams):
            if I < 0.5: continue
            L = (b - a).length()
            if L < 90: continue
            for k in range(min(6, int(L // 150) + 1)):
                pho.append((i, random.uniform(0, L),
                            random.uniform(130, 260) * random.choice((-1, 1)),
                            random.uniform(1.5, 2.6),
                            random.uniform(1.0, 3.0),
                            random.uniform(0, 6.28)))
        if len(pho) > 320: pho = pho[:320]
    state["photons"] = pho
    state["flares"] = flares
    state["caust_events"] = caust_ev
    return beams

# --------------------------------------------- persistence & state
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "."
SAVE = os.path.join(HERE, "lightlab_save.json")
CUST = os.path.join(HERE, "lightlab_custom.json")
PREMIUM_CODES = {"PRISM", "LUMEN"}   # <- replace with your itch.io keys

def fresh_save():
    return {"unlocked": {"core": 0}, "stars": {}, "packs": {},
            "ghosts": {},
            "muted": False, "fx": True, "caustics": True, "music": True,
            "vol": 1.0,
            "ach": [], "daily": {"date": "", "best": None, "streak": 0}}

def migrate(sv):
    u = sv.get("unlocked")
    if isinstance(u, int): sv["unlocked"] = {"core": u}
    if not isinstance(sv.get("unlocked"), dict): sv["unlocked"] = {}
    sv["unlocked"].setdefault("core", 0)
    st = sv.get("stars")
    if not isinstance(st, dict): st = {}
    if "core" not in st:
        legacy = {str(k): v for k, v in st.items() if str(k).isdigit()}
        st = {"core": legacy} if legacy else {}
    for pid, d in st.items():
        if isinstance(d, dict):
            for k, v in d.items():
                if isinstance(v, int): d[k] = {"s": v, "t": None}
    sv["stars"] = st
    if not isinstance(sv.get("packs"), dict): sv["packs"] = {}
    if not isinstance(sv.get("ghosts"), dict): sv["ghosts"] = {}
    if not isinstance(sv.get("ach"), list): sv["ach"] = []
    if not isinstance(sv.get("vol"), (int, float)): sv["vol"] = 1.0
    return sv

def load_save():
    d = fresh_save()
    try:
        raw = json.load(open(SAVE))
        d["unlocked"] = raw.get("unlocked")
        d["stars"] = raw.get("stars")
        d["packs"] = raw.get("packs")
        d["ghosts"] = raw.get("ghosts")
        d["muted"] = bool(raw.get("muted", False))
        d["fx"] = bool(raw.get("fx", True))
        d["caustics"] = bool(raw.get("caustics", True))
        d["music"] = bool(raw.get("music", True))
        d["vol"] = raw.get("vol", 1.0)
        d["ach"] = list(raw.get("ach", []))
        dl = raw.get("daily") or {}
        d["daily"] = {"date": dl.get("date", ""), "best": dl.get("best"),
                      "streak": int(dl.get("streak", 0))}
    except Exception:
        pass
    return migrate(d)

def load_customs():
    try: return json.load(open(CUST))["levels"]
    except Exception: return []
def save_customs():
    try: json.dump({"levels": state["customs"]}, open(CUST, "w"))
    except Exception: pass

state = {"screen": "menu", "mode": "level", "pack": "core", "level": 0,
         "custom_idx": 0, "sel": None, "placing": None, "help": False,
         "complete": False, "win_time": 0, "win_stars": 0, "win_btns": [],
         "drag": None, "rotating": False, "modal": None, "code_buf": "",
         "name_buf": "", "unlock_buf": "", "rival_buf": "",
         "share_code": "", "last_level": 0, "start_time": 0,
         "paused": False, "paused_at": 0, "fps_show": False, "snap": False,
         "sel_scroll": 0, "save": load_save(), "customs": load_customs(),
         "editor_scene": "", "dirty": True, "beams": [], "undo": [],
         "pre_scene": None, "demo": [], "topbar": [], "custom_del": [],
         "trace_count": 0, "last_warp": 0, "wipe_arm": 0,
         "daily_par": 0, "daily_nb": 0, "daily_code": "",
         "flash": 0.0, "photons": [], "flares": [], "t": 0.0,
         "caust_events": [], "caust_rays": 0, "hitcd": {}, "last_tick": 0,
         "mixpts": [], "last_mix": 0, "last_recomb": 0,
         "mus_song": None, "mus_step": 0, "mus_next": 0, "duck_until": 0,
         "pack_rects": [], "rec": [], "replay": None, "sol_code": "",
         "floats": [], "endless_list": []}
def say(msg, dur=2200):
    state["floats"].append({"m": msg, "t0": pygame.time.get_ticks(),
                            "dur": dur, "ach": False})
    if len(state["floats"]) > 4: state["floats"].pop(0)
def persist():
    try: json.dump(state["save"], open(SAVE, "w"))
    except Exception: pass
def dirty(): state["dirty"] = True

# ------------------------------------------------------ achievements
ACH = [
 ("first",  "First Light",      "Complete LEVEL 1"),
 ("prism",  "Prismatic",        "Complete PRISM SPLIT"),
 ("star3",  "Perfectionist",    "Earn 3 stars on any level"),
 ("ten",    "Halfway There",    "Complete 10 levels"),
 ("all",    "Lab Certified",    "Complete every authored level"),
 ("stars30","Star Collector",   "Collect 30 stars total"),
 ("arch",   "Architect",        "Save a level in the editor"),
 ("pub",    "Publisher",        "Generate a share code"),
 ("cur",    "Curator",          "Play a custom level"),
 ("daily",  "Daily Devotee",    "Complete a Daily Lab"),
 ("tir",    "Impossible Angle", "Witness total internal reflection"),
 ("warp",   "Wormhole Admin",   "Send a beam through a portal"),
 ("mix1",   "Chromatologist",   "Light a target with MIXED light"),
 ("white3", "Full Spectrum",    "Build white from R+G+B beams"),
 ("recomb", "Newton's Ghost",   "Recombine a split rainbow into white"),
 ("pack2",  "Chroma Certified", "Complete the CHROMA LAB pack"),
 ("flux",   "Forgemaster",      "Complete the FLUX LAB pack"),
 ("endless10","Tenacity",       "Complete ENDLESS #10"),
 ("vip",    "Vault Keeper",     "Unlock the SPECTRUM VAULT"),
 ("codebrk","Codebreaker",      "Compare a rival Daily code"),
 ("ghost",  "Ghost Hunter",     "Watch a ghost replay to the end"),
 ("director","Director",        "Share your solution code"),
 ("autop",  "Autopilot",        "A ghost replay solves a level for you"),
]
def grant(aid):
    if aid in state["save"]["ach"]: return
    state["save"]["ach"].append(aid); persist()
    nm = dict((a, n) for a, n, _ in ACH)[aid]
    state["floats"].append({"m": f"ACHIEVEMENT — {nm}",
                            "t0": pygame.time.get_ticks(),
                            "dur": 3400, "ach": True})
    if len(state["floats"]) > 4: state["floats"].pop(0)
    play("ach")

def push_undo():
    state["undo"].append(encode_scene())
    if len(state["undo"]) > 60: state["undo"].pop(0)

def do_undo():
    if not state["undo"]:
        say("Nothing to undo"); return
    try:
        objs = decode_scene(state["undo"].pop())
        objects.clear(); objects.extend(objs)
        state["sel"] = None; dirty(); play("undo")
        say(f"Undo ({len(state['undo'])} left)")
    except Exception:
        say("Undo failed")

# ---------------------------------------------------- LEVEL PACKS
def G(pos, angle=0, w=260, h=52, n=1.5):
    g = GlassRect(pos, angle, w, h); g.n = n; return g
Rc_, Gr_, Bl_ = SPECTRUM[0], SPECTRUM[3], SPECTRUM[5]

def L1():  return [Source((150,360),0), Mirror((640,360),90), Target((880,570))]
def L2():  return [Source((150,210),0), Mirror((600,210),90), Mirror((930,430),0),
                   Target((1150,600)), Wall((760,650),0,280)]
def L3():  return [Source((150,330),10), G((660,430),0,300,60),
                   Target((1180,570)), Wall((1180,280),90,240)]
def L4():  return [Source((150,300),6), Target((560,343)),
                   Filter((760,364),0,ci=0), Target((1120,402),Rc_)]
def L5():  return [Source((150,360),0), Splitter((620,360),-20),
                   Target((1180,360)), Target((900,120))]
def L6():  return [Source((150,360),0), G((640,360),0,340,340,1.55),
                   Wall((890,300),90,300), Target((1130,600))]
def L7():  return [Source((150,360),0), Prism((620,400),0),
                   Target((1120,270),Rc_)]
def L8():  return [Source((150,360),0), Ball((700,360),0,120), Target((1010,430))]
def L9():  return [Source((150,360),0), Prism((600,390),0),
                   Target((1080,250),Rc_), Target((1150,540),Bl_)]
def L10(): return [Source((180,270),0), Source((180,450),0),
                   Concave((760,360),90,600,260), Target((460,360))]
def L11(): return [Source((150,360),0), Prism((600,400),0,240,1.52,0.05),
                   Target((1150,240),Rc_), Target((1180,560),Bl_),
                   Target((950,360))]
def L12(): return [Source((150,360),0), Lens((640,360),0,280,120),
                   Splitter((860,391),-14), Target((1010,420)), Target((1230,120))]
def L13(): return [Source((130,360),0), Mirror((420,180),45),
                   Mirror((700,560),-45), Mirror((980,180),45),
                   Target((1180,360)), Wall((420,660),0,300), Wall((980,620),90,200)]
def L14(): return [Source((150,360),0), Ball((640,360),0,100),
                   Splitter((930,390),-25), Target((1120,520)), Target((1240,150))]
def L15(): return [Source((150,380),0), Prism((560,400),0,240,1.52,0.045),
                   Prism((820,400),0,240,1.52,0.045), Target((1200,200),Rc_),
                   Target((1230,360),Gr_), Target((1200,540),Bl_)]
def L16(): return [Source((140,620),-28), Splitter((500,470),60),
                   Mirror((430,190),55), Prism((860,250),25,220,1.52,0.04),
                   Filter((1075,480),0,ci=3), Ball((980,620),0,80),
                   Target((1180,120),Rc_), Target((1150,300)),
                   Target((1235,520),Gr_), Target((700,690))]
def L17(): return [Source((140,380),0), PortalPair((640,360),0),
                   Wall((640,610),0,520), Mirror((950,380),90),
                   Target((1120,290))]
def L18(): return [Source((140,300),0), Splitter((520,300),-32),
                   PortalPair((800,470),40), Mirror((1020,240),20),
                   Target((1180,280)), Target((1180,600))]
def L19(): return [Source((150,360),0), Lens((560,360),0,260,110),
                   Concave((940,360),90,600,300), Splitter((1150,390),-40),
                   Target((760,180)), Target((1180,560))]
def L20(): return [Source((140,620),-26), PortalPair((520,430),25),
                   Prism((820,300),15,220,1.52,0.045), Filter((1050,560),0,ci=3),
                   Mirror((660,140),35), Target((1180,140),Rc_),
                   Target((1200,420),Bl_), Target((900,660),Gr_),
                   Target((420,180))]

CORE_LEVELS = [
 ("FIRST LIGHT",    L1,  20, "Right-drag the mirror to aim the bounce. Angle in = angle out."),
 ("DOUBLE BOUNCE",  L2,  30, "Two mirrors, and the wall blocks the low road."),
 ("THE BEND",       L3,  35, "Light bends TOWARD the normal entering glass, AWAY leaving."),
 ("PAINT IT RED",   L4,  25, "Colored targets need an EXACT component mix. The filter dyes white light red."),
 ("SPLIT DECISION", L5,  40, "The splitter passes half the beam through, reflects the rest."),
 ("TOTAL INTERNAL", L6,  50, "Steep rays inside glass bounce forever (TILT the big block)."),
 ("PRISM SPLIT",    L7,  60, "White light fans into a rainbow. Red bends least."),
 ("GLASS EYE",      L8,  60, "A ball lens focuses rays near its focal point."),
 ("DOUBLE RAINBOW", L9,  80, "One prism, two colors: aim both ends of the fan."),
 ("FOCUS",          L10, 45, "Parallel rays reunite at the focal point (about Rc/2)."),
 ("COLOR PICKING",  L11, 80, "Two exact colors + one white. Guide the fan carefully."),
 ("LENS & SPLITTER",L12, 85, "Focus with the lens, then skim part of the beam off."),
 ("ZIGZAG",         L13, 70, "Three mirrors. Fold the beam through the maze."),
 ("SPLIT FOCUS",    L14, 90, "Ball lens converges the beam; splitter sends part up."),
 ("CASCADE",        L15, 140,"Two prisms: dispersion compounds into a wide fan."),
 ("GRAND FINALE",   L16, 160,"Everything so far, at once. Good luck."),
 ("THIN AIR",       L17, 60, "PORTALS: a beam entering one ring exits the other."),
 ("WORMHOLE SPLIT", L18, 90, "Split first, then send one copy through the portal."),
 ("FUNNEL",         L19, 90, "Lens into concave mirror: fold the beam back on itself."),
 ("STARGATE",       L20, 170,"Portals + prisms + filters. The true finale."),
]

def C1(): return [Source((150,220),0,ci=1), Source((150,500),0,ci=4),
                  Mirror((620,220),45), Mirror((620,500),-45),
                  Target((620,360),YELLOW)]
def C2(): return [Source((150,160),0,ci=1), Source((150,360),0,ci=4),
                  Source((150,560),0,ci=6), Mirror((620,160),45),
                  Mirror((620,560),-45), Target((620,360))]
def C3(): return [Source((150,360),0), Prism((520,400),0),
                  Mirror((820,340),10), Target((1000,300),YELLOW)]
def C4(): return [Source((150,180),0,ci=1), Source((150,600),-8,ci=6),
                  Mirror((450,180),45), Mirror((450,420),45),
                  Mirror((900,420),-45), Wall((760,660),0,500),
                  Target((900,220),Rc_)]
def C5(): return [Source((140,250),6), Splitter((430,270),-32),
                  Filter((640,200),0,ci=0), Filter((640,340),0,ci=3),
                  Mirror((820,430),20), Wall((300,640),0,500),
                  Target((1060,290),YELLOW)]
def C6(): return [Source((140,200),0,ci=1), Source((140,520),0,ci=6),
                  Mirror((820,200),45), Mirror((820,520),-45),
                  Target((820,360),VIOLET)]
def C7(): return [Source((150,360),0), Prism((520,400),0),
                  Mirror((840,330),8), Mirror((860,430),-8),
                  Target((1080,300),YELLOW), Target((1080,470),CYAN)]
def C8(): return [Source((140,360),0), Splitter((380,360),-20),
                  Splitter((640,360),-20), Filter((660,160),0,ci=0),
                  Filter((900,360),0,ci=3), Filter((900,210),0,ci=6),
                  Mirror((820,120),25), Mirror((1050,170),55),
                  Mirror((1050,360),-45), Target((1050,320))]
def C9(): return [Source((150,360),0), Prism((620,400),0,240,1.52,0.045),
                  Mirror((850,350),6), Mirror((850,470),-6),
                  Target((1050,240),YELLOW), Target((1000,520),CYAN),
                  Target((1150,300),Rc_)]
def C10():return [Source((140,240),8), Source((140,500),-8),
                  Splitter((420,270),-25), Splitter((420,470),25),
                  Filter((620,170),0,ci=0), Filter((660,580),0,ci=6),
                  Prism((800,380),0,220,1.52,0.04),
                  Mirror((950,250),-15), Mirror((950,450),15),
                  Mirror((700,300),40),
                  Target((1150,180),VIOLET), Target((1150,560),CYAN),
                  Target((1150,360))]
def C11():return [Source((140,360),0), Prism((460,400),0,220,1.52,0.045),
                  Recombiner((760,380),0,200),
                  Wall((980,180),90,300), Wall((980,560),90,300),
                  Target((1140,370))]
def C12():return [Source((140,220),0,ci=1), Source((140,540),0,ci=5),
                  Mirror((560,220),40), Mirror((560,540),-40),
                  Recombiner((840,380),0,190),
                  Wall((1020,200),90,280), Wall((1020,560),90,280),
                  Target((1170,380),VIOLET)]

CHROMA_LEVELS = [
 ("FIRST MIX",      C1,  30, "YELLOW = RED+GREEN. Turn both beams onto the same line through the target."),
 ("WHITE ROOM",     C2,  40, "WHITE = RED+GREEN+BLUE. Green passes straight through — steer the other two onto its line."),
 ("ORANGE IS A LIE",C3,  70, "ORANGE already contains RED+GREEN. One orange ray alone lights a yellow target."),
 ("GATE CRASHER",   C4,  80, "Only EXACT red lights it. Blue bounces off your mirrors — keep its mess away."),
 ("FILTER FOUNDRY", C5, 110,"Split white, dye each half RED and GREEN, then cross them on the yellow target."),
 ("MAGENTA DUET",   C6,  45, "VIOLET = RED+BLUE."),
 ("TWIN PICKERS",   C7, 120,"One fan, two jobs: steer ORANGE to yellow, CYAN to cyan."),
 ("TRIPLE FILTER",  C8, 140,"Two splitters make three whites; dye them R, G, B; reunite all three."),
 ("RAINBOW ROUTER", C9, 130,"Three targets, one prism. Remember what each fan color is made of."),
 ("TRINITY",        C10,180,"VIOLET wants R+B, CYAN wants G+B, and something must stay white."),
 ("REUNION",        C11, 90,"NEWTON'S TRICK: the RECOMBINER merges a split rainbow back into WHITE. Thread the slit."),
 ("SPECTRAL SLIT",  C12,110,"RED + BLUE through a recombiner merge into VIOLET. Only a single beam fits the slit."),
]

# --- FLUX LAB: portals, recombiners, focus forging --------------------
def F1(): return [Source((150,240),0,ci=1), Source((150,420),0,ci=6),
                  Mirror((480,240),-20), Mirror((480,420),30),
                  Target((1000,420),VIOLET)]
def F2(): return [Source((140,360),0), Wall((760,360),90,720),
                  PortalPair((740,440),10), Target((1060,520))]
def F3(): return [Source((140,360),0), Splitter((420,360),10),
                  PortalPair((420,240),0), Mirror((420,100),20),
                  Target((960,100)), Target((1080,360))]
def F4(): return [Source((140,360),0), Prism((430,360),8,220,1.52,0.05),
                  Recombiner((740,360),0,200),
                  Wall((950,200),90,260), Wall((950,520),90,260),
                  Target((1120,360))]
def F5(): return [Source((140,360),0), Splitter((360,360),-30),
                  Prism((360,180),20,200,1.52,0.05),
                  Prism((700,360),15,200,1.52,0.05),
                  Target((880,80)), Target((1080,420))]
def F6(): return [Source((180,260),0,ci=1), Source((180,460),0,ci=6),
                  Concave((820,360),90,600,300), Target((520,300),VIOLET)]
def F7(): return [Source((140,360),0), Splitter((400,360),10),
                  Filter((400,240),90,ci=0), Mirror((400,140),20),
                  Target((800,140),RED),
                  Filter((660,360),0,ci=5), Target((1020,360),BLUE)]
def F8(): return [Source((140,180),0), Mirror((420,180),20),
                  Mirror((420,340),-70), Mirror((680,340),80),
                  Mirror((680,500),-30), Target((1000,500)),
                  Wall((860,180),90,240)]
def F9(): return [Source((140,360),0), Splitter((360,360),10),
                  Filter((360,240),90,ci=3), Target((360,140),GREEN),
                  Splitter((760,360),15),
                  Target((1080,360)), Mirror((760,220),20),
                  Target((1000,140))]
def F10():return [Source((150,240),0,ci=1), Source((150,540),0,ci=6),
                  Mirror((470,240),20), Mirror((470,540),-15),
                  Recombiner((800,560),0,180),
                  Wall((560,120),0,500),
                  Target((1150,640),VIOLET)]

FLUX_LEVELS = [
 ("RED MEETS BLUE", F1,  35, "VIOLET = RED+BLUE. Fold the red beam onto the blue line with two mirrors."),
 ("THROUGH THE WALL",F2, 40, "The wall only looks solid. Rotate the portal: enter one ring, exit the other past it."),
 ("SPLIT GATE",     F3,  55, "Half goes straight, half goes up — and through the portal."),
 ("NEWTON'S OVEN",  F4,  70, "Split white with the prism, then merge it back with the recombiner. Aim the fan."),
 ("TWIN FANS",      F5,  80, "Two prisms, two fans, two targets. Rotate each rainbow into place."),
 ("FOCUS FORGE",    F6,  60, "Parallel rays reunite near the focus. Steer the concave mirror until R+B meet on VIOLET."),
 ("FILTER LADDER",  F7,  70, "Dye each branch its own color — exact matches only."),
 ("ZIGZAG DROP",    F8,  75, "Four mirrors, a staircase of light."),
 ("TRIPLE GATE",    F9,  90, "One beam, three jobs: GREEN target and two whites."),
 ("FORGE FINALE",   F10,130,"Fold RED onto BLUE's line — the recombiner forges VIOLET."),
]

def V1(): return [Source((140,200),0,ci=1), Source((140,360),0,ci=4),
                  Source((140,520),0,ci=6), Mirror((620,200),45),
                  Mirror((620,520),-45), Wall((760,660),0,500),
                  Target((900,360))]
def V2(): return [Source((140,360),0), Splitter((400,360),-20),
                  Splitter((700,360),-20), Splitter((900,140),-40),
                  Filter((560,200),0,ci=0), Filter((880,360),0,ci=3),
                  Filter((920,210),0,ci=6),
                  Mirror((760,120),30), Mirror((1120,360),-45),
                  Mirror((1000,300),-60), Mirror((760,540),20),
                  Target((1150,220),YELLOW), Target((1150,420),CYAN),
                  Target((1150,620),VIOLET)]
def V3(): return [Source((140,300),0,ci=1), Source((140,560),0,ci=6),
                  G((640,360),0,340,340,1.55), Mirror((900,240),-40),
                  Target((1000,340),VIOLET), Target((1150,600))]
def V4(): return [Source((140,200),0,ci=1), Source((140,560),0,ci=6),
                  PortalPair((500,300),20), Wall((620,660),0,700),
                  Mirror((760,220),30), Mirror((780,480),-30),
                  Target((1100,240),VIOLET)]
def V5(): return [Source((150,360),0), Prism((480,400),0,240,1.52,0.05),
                  Prism((760,420),0,240,1.52,0.045),
                  Mirror((950,300),5), Mirror((950,470),-5),
                  Target((1150,240),YELLOW), Target((1150,480),CYAN),
                  Target((900,640))]
def V6(): return [Source((140,180),-6,ci=4), Source((140,360),0,ci=6),
                  Source((140,540),6,ci=7), Source((140,700),-24,ci=1),
                  Mirror((700,240),20), Mirror((700,480),-20),
                  Wall((980,120),90,240), Target((1000,360),Rc_)]
def V7(): return [Source((150,360),0), Ball((640,360),0,120),
                  Mirror((900,220),-30), Mirror((900,500),30),
                  Target((1080,300),YELLOW), Target((1080,430),CYAN)]
def V8(): return [Source((180,260),0,ci=1), Source((180,460),0,ci=6),
                  Concave((900,360),90,600,300), Target((460,360),VIOLET),
                  Wall((700,660),0,400)]
def V9(): return [Source((150,380),0), Prism((560,400),0,240,1.52,0.05),
                  Prism((820,400),0,240,1.52,0.05),
                  Target((1200,180),YELLOW), Target((1230,360),CYAN),
                  Target((1200,560),VIOLET)]
def V10():return [Source((140,240),8), Source((140,520),-8),
                  PortalPair((380,380),30), Splitter((560,240),-25),
                  Filter((720,140),0,ci=0), Filter((760,620),0,ci=6),
                  Prism((860,380),0,220,1.52,0.045),
                  Mirror((980,220),-20), Mirror((980,540),20),
                  Target((1180,160),VIOLET), Target((1180,360),YELLOW),
                  Target((1180,560),CYAN), Target((700,680))]

VAULT_LEVELS = [
 ("CROSSFIRE",      V1,  50, "Three colors, one point. You know this dance."),
 ("SPLIT DECISIONS",V2, 180,"Split red twice: one red for yellow, one for violet. The fan helps with cyan."),
 ("TIR TUNNEL",     V3, 150,"Total internal reflection is a perfect fold. VIOLET = R+B."),
 ("PORTAL PALETTE", V4, 130,"Walls mean nothing; mixing means everything."),
 ("PRISM GAUNTLET", V5, 150,"Two cascaded prisms, three mixed targets."),
 ("FILTER LOCK",    V6, 140,"Four sources, one EXACT red. Contamination is failure."),
 ("ORBITAL",        V7, 130,"The ball lens bends everything toward its axis — colors cross there."),
 ("CONCAVE MIX",    V8,  60, "Parallel rays reunite at the focus. Two colors, one point."),
 ("CASCADE MIX",    V9, 160,"Double dispersion, triple targets, exact mixes only."),
 ("VAULT FINALE",   V10,200,"Everything at once. Welcome to the end of the Vault."),
]

PACKS = [
 {"id": "core",   "name": "CORE OPTICS",   "desc": "The original 20 — mirrors, glass, prisms, portals.",
  "levels": CORE_LEVELS},
 {"id": "chroma", "name": "CHROMA LAB",    "desc": "Additive color: cross beams, and RECOMBINE them.",
  "levels": CHROMA_LEVELS},
 {"id": "flux",   "name": "FLUX LAB",      "desc": "Portals, recombiners and focus forging.",
  "levels": FLUX_LEVELS},
 {"id": "vault",  "name": "SPECTRUM VAULT","desc": "10 expert levels. Unlock with a code.",
  "levels": VAULT_LEVELS, "premium": True},
 {"id": "endless","name": "ENDLESS",       "desc": "Procedurally generated & deterministic by number — infinite levels, ghosts work!",
  "levels": None, "endless": True},
]

def cur_pack():
    for p in PACKS:
        if p["id"] == state["pack"]: return p
    return PACKS[0]
def pack_open(p):
    return (not p.get("premium")) or state["save"]["packs"].get(p["id"], False)
def unlocked_for(pid):
    return int(state["save"]["unlocked"].get(pid, 0))
def stars_of(pid, idx):
    d = state["save"]["stars"].get(pid, {})
    v = d.get(idx) if isinstance(d, dict) else 0
    if isinstance(v, dict): return int(v.get("s", 0))
    return int(v or 0)
def best_of(pid, idx):
    d = state["save"]["stars"].get(pid, {})
    v = d.get(idx) if isinstance(d, dict) else None
    if isinstance(v, dict): return v.get("t")
    return None
def pack_level_count(p):
    if p.get("endless"): return len(endless_levels())
    return len(p["levels"])
def total_stars():
    return sum(stars_of(pid, i) for p in PACKS
               for i in range(pack_level_count(p)))
def completed_count():
    return sum(len(d) for pid, d in state["save"]["stars"].items()
               if isinstance(d, dict) and pid != "endless")

# ----------------------------------------------------- DAILY LAB gen
SEG_CLEAR = 100
def gen_daily():
    ds = datetime.date.today().isoformat()
    seed = 0
    for c in ds: seed = (seed*131 + ord(c)) & 0x7fffffff
    rng = random.Random(seed)
    nb = 3 + min(3, datetime.date.today().weekday() // 2)
    for _try in range(600):
        pts = [V2(rng.uniform(100,260), rng.uniform(TOP+130, H-170))]
        a = rng.uniform(-0.5, 0.5); angs = []; ok = True
        for k in range(nb+1):
            if k > 0:
                a += rng.uniform(0.5, 1.15) * (1 if rng.random() < 0.5 else -1)
            angs.append(a)
            d = rng.uniform(280, 620) if k < nb else rng.uniform(240, 520)
            nxt = pts[-1] + V2(math.cos(a), math.sin(a)) * d
            if not (70 < nxt.x < W-70 and TOP+100 < nxt.y < H-120): ok = False; break
            if any((nxt - p).length() < 150 for p in pts): ok = False; break
            pts.append(nxt)
        if not ok: continue
        good = True
        for k in range(len(pts)-1):
            for j, pj in enumerate(pts):
                if j == k or j == k+1: continue
                if dist_pt_seg(pj, pts[k], pts[k+1]) < SEG_CLEAR: good = False; break
            if not good: break
        if not good: continue
        if (pts[-1] - pts[0]).length() < 420: continue
        out = [Source((pts[0].x, pts[0].y), 0)]
        mir = []
        for i in range(1, nb+1):
            vin  = V2(math.cos(angs[i-1]), math.sin(angs[i-1]))
            vout = V2(math.cos(angs[i]),   math.sin(angs[i]))
            n = unit(vin - vout)
            m = Mirror((pts[i].x, pts[i].y),
                       math.degrees(math.atan2(n.y, n.x) + math.pi/2), 150)
            mir.append(m); out.append(m)
        out.append(Target((pts[-1].x, pts[-1].y)))
        for m in mir:
            m.angle += math.radians(rng.uniform(0.5, 2.6)
                                    * (1 if rng.random() < 0.5 else -1))
        return out, 35 + 25*nb, nb
    return [Source((150,360),0), Mirror((640,360),90), Target((880,570))], 40, 1

B32 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
def daily_code(el, nb):
    packed = (nb - 3) * 600000 + min(599999, int(el * 10))
    cs = packed
    for ch in datetime.date.today().isoformat():
        cs = (cs * 31 + ord(ch)) & 0xFFFFFF
    v = (packed << 5) | (cs & 31)
    return "".join(B32[(v >> (5*(5-i))) & 31] for i in range(6))

def daily_decode(code):
    code = code.strip().upper()
    if len(code) != 6 or any(ch not in B32 for ch in code): return None
    v = 0
    for ch in code: v = (v << 5) | B32.index(ch)
    cs5 = v & 31; packed = v >> 5
    cs = packed
    for ch in datetime.date.today().isoformat():
        cs = (cs * 31 + ord(ch)) & 0xFFFFFF
    if (cs & 31) != cs5: return None
    rnb = packed // 600000 + 3
    rel = (packed % 600000) / 10.0
    if not (0 < rel < 60000): return None
    return rnb, rel

# =====================================================
#  ENDLESS PROCEDURAL GENERATOR — deterministic per level number
# =====================================================
def end_seed(i):
    h = 2166136261
    for ch in "LLX11-endless-" + str(i):
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return h

def _inb(p, m=80):
    return m < p.x < W-m and TOP+110 < p.y < H-110

def _mirror_at(path, j, length=145):
    vin  = unit(path[j] - path[j-1])
    vout = unit(path[j+1] - path[j])
    n = unit(vin - vout)
    return Mirror(path[j], math.degrees(math.atan2(n.y, n.x) + math.pi/2), length)

def _gen_maze(rng, nb, scr):
    """Source -> nb mirrors -> Target. Build the chain, then scramble."""
    for _ in range(400):
        pts = [V2(rng.uniform(100, 280), rng.uniform(TOP+140, H-180))]
        a = rng.uniform(-0.5, 0.5); ok = True
        for k in range(nb+1):
            if k > 0:
                a += rng.uniform(0.5, 1.15) * (1 if rng.random() < 0.5 else -1)
            d = rng.uniform(280, 620) if k < nb else rng.uniform(240, 520)
            nxt = pts[-1] + V2(math.cos(a), math.sin(a)) * d
            if not _inb(nxt): ok = False; break
            if any((nxt - p).length() < 150 for p in pts): ok = False; break
            pts.append(nxt)
        if not ok: continue
        good = True
        for k in range(len(pts)-1):
            for j, pj in enumerate(pts):
                if j == k or j == k+1: continue
                if dist_pt_seg(pj, pts[k], pts[k+1]) < 100: good = False; break
            if not good: break
        if not good: continue
        out = [Source((pts[0].x, pts[0].y), 0)]
        mir = []
        for j in range(1, nb+1):
            m = _mirror_at(pts, j); mir.append(m); out.append(m)
        out.append(Target((pts[-1].x, pts[-1].y)))
        for m in mir:
            m.angle += math.radians(rng.uniform(scr*0.4, scr)
                                    * (1 if rng.random() < 0.5 else -1))
        return out, 22 + 16*nb
    return None

def _path_to(rng, start, T, k, avoid):
    """Waypoints: start -> k mirror points -> T, with clearance."""
    pts = [V2(start)]
    for j in range(k):
        last = (j == k-1)
        for _ in range(60):
            if last:
                th = rng.uniform(0, 6.283); d = rng.uniform(230, 520)
                p = T - V2(math.cos(th), math.sin(th)) * d
            else:
                p = V2(rng.uniform(120, W-120), rng.uniform(TOP+140, H-160))
            if not _inb(p): continue
            if any((p - q).length() < 150 for q in pts): continue
            if any((p - q).length() < 95 for q in avoid): continue
            pts.append(p); break
        else:
            return None
    pts.append(V2(T))
    for s in range(len(pts)-1):
        A, B = pts[s], pts[s+1]
        for j, q in enumerate(pts):
            if q is A or q is B: continue
            if s == len(pts)-2 and j == len(pts)-1: continue
            if dist_pt_seg(q, A, B) < 100: return None
        for q in avoid:
            if dist_pt_seg(q, A, B) < 95: return None
    return pts

def _gen_relay(rng, m1, m2, scr):
    """Two colored sources routed onto one exact-mix target."""
    ci1, ci2, tcol = [(1, 4, YELLOW), (1, 6, VIOLET), (4, 6, CYAN)][rng.randrange(3)]
    for _ in range(200):
        T = V2(rng.uniform(W-430, W-140), rng.uniform(TOP+180, H-220))
        s1 = V2(rng.uniform(80, 180), rng.uniform(TOP+140, H-220))
        s2 = V2(rng.uniform(80, 180), rng.uniform(TOP+140, H-220))
        if (s1 - s2).length() < 140: continue
        pa = _path_to(rng, s1, T, m1, [])
        if pa is None: continue
        avoid = pa[1:-1] + [s1]
        pb = _path_to(rng, s2, T, m2, avoid)
        if pb is None: continue
        out = [Source(s1, 0, ci=ci1), Source(s2, 0, ci=ci2)]
        mir = []
        for path in (pa, pb):
            for j in range(1, len(path)-1):
                m = _mirror_at(path, j, 140)
                mir.append(m); out.append(m)
        out.append(Target(T, tcol))
        for m in mir:
            m.angle += math.radians(rng.uniform(scr*0.5, scr)
                                    * (1 if rng.random() < 0.5 else -1))
        return out, 28 + 15*(m1+m2)
    return None

def _fan_rays(prism, p, d):
    """Simulate a white beam through the prism with real Snell math.
    Returns [(color, exit_point, exit_dir)]."""
    res = []
    d = unit(d)
    hs = prism.hits(p, d)
    if not hs: return res
    t0, n0 = hs[0]
    entry = p + d*t0
    nn = n0 if d.dot(n0) < 0 else -n0
    for ci, c in enumerate(SPECTRUM):
        ne = prism.n + (ci - 3) * prism.spread
        r = refract(d, nn, 1.0/ne)
        if r is None: continue
        r = unit(r); q = entry + r*0.6; dd = r
        for _ in range(5):
            h2 = prism.hits(q, dd)
            if not h2: break
            t2, n2 = h2[0]
            ex = q + dd*t2
            n2n = n2 if dd.dot(n2) < 0 else -n2
            ro = refract(dd, n2n, ne)
            if ro is not None:
                res.append((c, ex, unit(ro))); break
            dd = unit(reflect(dd, n2n)); q = ex + dd*0.6
    return res

def _gen_fan(rng, ntar, tier):
    """White -> prism. Targets placed on ACTUAL fan rays (simulated),
    then the prism is rotated so the fan misses. Rotate it back."""
    for _ in range(150):
        py = rng.uniform(TOP+230, H-260)
        sp = V2(rng.uniform(80, 150), py)
        pc = V2(sp.x + rng.uniform(340, 520), py)
        if not _inb(pc): continue
        prism = Prism(pc, 0, 210, 1.52, rng.uniform(0.045, 0.06))
        rays = _fan_rays(prism, sp + V2(24, 0), V2(1, 0))
        if len(rays) < ntar + 1: continue
        picks = rng.sample(range(len(rays)), ntar)
        tps = []; ok = True
        for ri in picks:
            c, ex, ed = rays[ri]
            placed = False
            for _a in range(30):
                dd = rng.uniform(260, 500)
                tp = ex + ed*dd
                if not _inb(tp): continue
                if any((tp - q).length() < 130 for q in tps): continue
                if (tp - pc).length() < 190: continue
                tps.append(tp); placed = True; break
            if not placed: ok = False; break
        if not ok: continue
        out = [Source(sp, 0), prism]
        for tp, ri in zip(tps, picks):
            out.append(Target(tp, rays[ri][0]))
        prism.angle += math.radians(rng.uniform(0.35, 0.55 + 0.12*tier)
                                    * (1 if rng.random() < 0.5 else -1))
        return out, 30 + 22*ntar
    return None

def _gen_splitd(rng, ntar, colored):
    """Source -> splitter -> straight / reflected / deflected legs."""
    for _ in range(200):
        S = V2(rng.uniform(330, 440), rng.uniform(TOP+190, H-280))
        ths = rng.uniform(18, 38)
        d0 = V2(1, 0)
        n = V2(math.cos(math.radians(ths+90)), math.sin(math.radians(ths+90)))
        if n.dot(d0) > 0: n = -n
        r = reflect(d0, n)
        T1 = S + d0 * rng.uniform(360, 540)
        if not _inb(T1): continue
        D2 = rng.uniform(290, 440)
        T2 = S + r * D2
        if not _inb(T2): continue
        src = Source(S - d0*rng.uniform(220, 270), 0)
        if src.pos.x < 40: continue
        out = [src, Splitter(S, ths)]
        legs = [(d0, T1, None)]
        if colored:
            c2 = SPECTRUM[rng.choice((0, 3))]
            out.append(Filter(S + r*(D2*0.55),
                              math.degrees(math.atan2(r.y, r.x)),
                              ci=SPECTRUM.index(c2)))
            legs.append((r, T2, c2))
        else:
            legs.append((r, T2, None))
        if ntar >= 3:
            M = S + r * rng.uniform(170, 240)
            d3 = unit(V2(rng.choice(((1, 0.35), (1, -0.35), (0.4, 1), (0.4, -1)))))
            T3 = M + d3 * rng.uniform(300, 440)
            if not _inb(T3): continue
            n3 = unit(r - d3)
            ma = math.degrees(math.atan2(n3.y, n3.x) + math.pi/2)
            mir = Mirror(M, ma, 140)
            out.append(mir)
            if colored:
                c3 = SPECTRUM[rng.choice((0, 3, 5))]
                out.append(Filter(M + d3*130,
                                  math.degrees(math.atan2(d3.y, d3.x)),
                                  ci=SPECTRUM.index(c3)))
                legs.append((d3, T3, c3))
            else:
                legs.append((d3, T3, None))
        for dvec, T, col in legs:
            out.append(Target(T, col))
        out[1].angle += math.radians(rng.uniform(0.35, 0.9)
                                     * (1 if rng.random() < 0.5 else -1))
        for o in out:
            if isinstance(o, Mirror) and o is not out[1]:
                o.angle += math.radians(rng.uniform(0.35, 0.9)
                                        * (1 if rng.random() < 0.5 else -1))
        return out, 26 + 20*ntar
    return None

def gen_endless(i):
    """Deterministic endless level. Returns (objects, par, hint)."""
    rng = random.Random(end_seed(i))
    tier = min(6, i // 5)
    pool = ["maze", "split"]
    if tier >= 1: pool += ["relay", "fan"]
    if tier >= 3: pool += ["maze", "relay", "fan"]
    kind = rng.choice(pool)
    res = None; hint = ""
    if kind == "maze":
        nb = min(6, 2 + tier + (1 if rng.random() < 0.5 else 0))
        scr = 0.9 + 0.22*tier
        res = _gen_maze(rng, nb, scr)
        hint = f"{nb} scrambled mirrors. Chain them back onto the target."
    elif kind == "split":
        ntar = 2 if tier < 2 else 3
        res = _gen_splitd(rng, ntar, tier >= 2)
        hint = ("Splitter tree: straight leg + reflected leg"
                + (" + deflected leg." if ntar >= 3 else ".")
                + (" Colored legs need their filters kept in line."
                   if tier >= 2 else ""))
    elif kind == "relay":
        m1 = 1 + (1 if tier >= 2 else 0)
        m2 = 1 + (1 if tier >= 3 else 0)
        res = _gen_relay(rng, m1, m2, 0.9 + 0.2*tier)
        hint = "Two colors, one exact-mix target. Route both beams home."
    elif kind == "fan":
        ntar = 2 if tier < 3 else 3
        res = _gen_fan(rng, ntar, tier)
        hint = "A prism was knocked out of alignment. Rotate it until the fan finds every target."
    if res is None:
        res = _gen_maze(rng, 3, 1.0)
        hint = "Scrambled mirrors. Rebuild the path."
    if res is None:
        return [Source((150,360),0), Mirror((640,360),90), Target((880,570))], 40, hint
    objs, par = res
    return objs, par, f"ENDLESS #{i+1} — {hint}"

def endless_levels():
    """Cached meta list [(name, None, par, hint)] for the select grid."""
    n = min(60, max(unlocked_for("endless") + 1, 12))
    lst = state["endless_list"]
    while len(lst) < n:
        i = len(lst)
        _o, par, hint = gen_endless(i)
        lst.append((f"ENDLESS #{i+1}", None, par, hint))
    return lst[:n]

def stop_all():
    state.update(sel=None, placing=None, complete=False, drag=None,
                 rotating=False, undo=[], win_btns=[],
                 rec=[], sol_code="", replay=None)

def build_level(i):
    if state["pack"] == "endless":
        objs, par, hint = gen_endless(i)
        objects.clear(); objects.extend(objs)
        stop_all(); state.update(screen="play", mode="level", level=i,
                                 start_time=pygame.time.get_ticks()); dirty()
        return
    objects.clear(); objects.extend(cur_pack()["levels"][i][1]())
    stop_all(); state.update(screen="play", mode="level", level=i,
                             start_time=pygame.time.get_ticks()); dirty()

def cur_levels():
    p = cur_pack()
    if p.get("endless"): return endless_levels()
    return p["levels"]

def build_custom(j):
    objects.clear(); objects.extend(decode_scene(state["customs"][j]["code"]))
    stop_all(); grant("cur")
    state.update(screen="play", mode="custom", custom_idx=j,
                 start_time=pygame.time.get_ticks()); dirty()

def build_sandbox():
    objects.clear()
    objects.extend([Source((160,360),0), Mirror((420,240),35),
                    G((560,480),0), Prism((760,260),0),
                    Recombiner((940,420),0,190),
                    Ball((1120,600),0,70), Target((1180,300))])
    stop_all(); state.update(screen="play", mode="sandbox"); dirty()

def build_editor():
    objects.clear()
    objects.extend([Source((200,360),0), Target((900,360))])
    stop_all(); state.update(screen="play", mode="editor"); dirty()

def build_daily():
    objs, par, nb = gen_daily()
    objects.clear(); objects.extend(objs)
    stop_all(); state.update(screen="play", mode="daily", daily_par=par,
                             daily_nb=nb, daily_code="",
                             start_time=pygame.time.get_ticks()); dirty()
    play("daily")
    say("DAILY LAB — the mirrors were scrambled. Find the hidden path.", 4000)

def start_test():
    state["editor_scene"] = encode_scene()
    objects.clear(); objects.extend(decode_scene(state["editor_scene"]))
    stop_all(); state.update(mode="test",
                             start_time=pygame.time.get_ticks()); dirty()

def exit_test():
    objects.clear(); objects.extend(decode_scene(state["editor_scene"]))
    stop_all(); state.update(mode="editor", complete=False); dirty()

def build_demo():
    objects.clear()
    objs = [Source((180,620),-70,ci=1), Mirror((660,120),22),
            Source((300,150),55,ci=4),
            Splitter((980,300),-30), Prism((760,430),12,210),
            Ball((1140,560),0,80), Mirror((420,300),-60),
            Source((140,320),10,ci=0), Prism((400,370),0,190),
            Recombiner((640,380),0,180)]
    objects.extend(objs)
    state["demo"] = [objs[0], objs[4]]

def check_win():
    now = pygame.time.get_ticks()
    for i, tg in enumerate(targets()):
        if tg.lit and not tg.was_lit:
            play("note", i, x=tg.pos.x)
            ring(tg.pos, tg.litcolor, v=230, life=0.6, r0=tg.R)
            spawn_burst(tg.pos, tg.litcolor, 12, (50, 160))
            if tg.color is not None and len(tg.mix) > 1:
                grant("mix1")
        tg.was_lit = tg.lit
    if state["mode"] not in ("level", "custom", "test", "daily") or state["complete"]:
        return
    tgs = targets()
    if tgs and all(t.lit for t in tgs):
        state["complete"] = True; state["win_time"] = now
        el = (now - state["start_time"]) / 1000
        sv = state["save"]
        if state["mode"] == "level":
            pid = state["pack"]
            par = cur_levels()[state["level"]][2]
            stars = 3 if el <= par else 2 if el <= par*1.9 else 1
            state["win_stars"] = stars
            sv["unlocked"][pid] = min(max(unlocked_for(pid), state["level"]+1),
                                      max(0, len(cur_levels())-1))
            sd = sv["stars"].setdefault(pid, {})
            k = str(state["level"])
            prev = sd.get(k)
            if isinstance(prev, dict):
                ns = max(int(prev.get("s", 0)), stars)
                ot = prev.get("t")
                nt = el if ot is None else min(ot, el)
            else:
                ns = max(int(prev or 0), stars); nt = el
            sd[k] = {"s": ns, "t": nt}
            persist()
            sol = encode_solution()
            state["sol_code"] = sol
            if sol:
                gh = sv.setdefault("ghosts", {}).setdefault(pid, {})
                pd = decode_solution(gh.get(k, ""))
                if pd is None or pd.get("t", 1e18) > el:
                    gh[k] = sol; persist()
            if pid == "core":
                if state["level"] == 0: grant("first")
                if state["level"] == 6: grant("prism")
            if pid == "chroma" and state["level"] == len(CHROMA_LEVELS)-1:
                grant("pack2")
            if pid == "flux" and state["level"] == len(FLUX_LEVELS)-1:
                grant("flux")
            if pid == "endless" and state["level"] >= 9:
                grant("endless10")
            if stars == 3: grant("star3")
            if completed_count() >= 10: grant("ten")
            total = sum(len(p["levels"]) for p in PACKS
                        if pack_open(p) and not p.get("endless"))
            if completed_count() >= total and total > 0: grant("all")
            if total_stars() >= 30: grant("stars30")
        elif state["mode"] == "daily":
            state["win_stars"] = 3 if el <= state["daily_par"] else \
                                 2 if el <= state["daily_par"]*1.9 else 1
            state["daily_code"] = daily_code(el, state["daily_nb"])
            today = datetime.date.today().isoformat()
            yest = (datetime.date.today()
                    - datetime.timedelta(days=1)).isoformat()
            d = sv["daily"]
            if d.get("date") == today:
                d["best"] = min(d.get("best") or el, el)
            else:
                d["streak"] = (d.get("streak", 0) + 1) if d.get("date") == yest else 1
                d["date"] = today; d["best"] = el
            persist(); grant("daily")
        else:
            state["win_stars"] = 0
            if state["mode"] == "custom":
                c = state["customs"][state["custom_idx"]]
                c["best"] = min(c.get("best") or 1e9, el); save_customs()
        if state["replay"]:
            grant("autop")
            state["replay"] = None
        state["flash"] = 1.0
        for tg in tgs:
            spawn_burst(tg.pos, tg.litcolor, 46)
            ring(tg.pos, tg.litcolor, v=560, life=1.0, w=3, r0=tg.R)
        cen = sum((t.pos for t in tgs), V2()) / len(tgs)
        ring(cen, GOLD, v=720, life=1.1, w=4)
        m = state["save"].get("vol", 1.0)
        state["duck_until"] = now + 2800
        play_seq([523.25, 659.25, 783.99, 1046.5, 1318.5], gap=110)
        for i in range(state["win_stars"]):
            pop = dict(POPS[i]); pop["vol"] = pop["vol"] * m
            SNDQ.append((now + 500 + i*340, S(**pop)))

# ------------------------------------------------------------- UI
def go_prev():
    if state["level"] > 0: build_level(state["level"]-1)
    else: say("Already at the first level")
def can_next():
    if state["mode"] != "level": return False
    n = state["level"] + 1
    return n < len(cur_levels()) and n <= unlocked_for(state["pack"])
def go_next():
    n = state["level"] + 1
    if n < len(cur_levels()) and n <= unlocked_for(state["pack"]): build_level(n)
    elif n < len(cur_levels()):
        say("LOCKED — light every target first"); play("locked")
    else: say("Pack complete! Try another pack, the EDITOR or DAILY LAB.")

def scene_valid():
    return (any(isinstance(o, Source) for o in objects) and
            any(isinstance(o, Target) for o in objects))

def btn_play():     state["screen"] = "select"
def btn_daily():    build_daily()
def btn_sandbox():
    state["last_level"] = state["level"]; build_sandbox()
def btn_back_lvl():
    build_level(min(state["last_level"], len(cur_levels())-1))
def btn_editor():   build_editor()
def btn_test():
    if not scene_valid():
        say("Need at least one SOURCE and one TARGET"); play("locked"); return
    start_test()
def btn_exit_test(): exit_test()
def btn_save_open():
    if not scene_valid():
        say("Need at least one SOURCE and one TARGET"); play("locked"); return
    state["name_buf"] = f"MY LEVEL {len(state['customs'])+1}"
    state["modal"] = "name"
def btn_save_confirm():
    name = state["name_buf"].strip()[:24] or f"MY LEVEL {len(state['customs'])+1}"
    state["customs"].append({"name": name, "code": encode_scene(), "best": None})
    save_customs(); state["modal"] = None
    grant("arch")
    say(f"Saved '{name}' — find it in level select"); play("place")
def btn_help():     state["help"] = not state["help"]
def btn_menu():
    play("whoosh")
    state["screen"] = "menu"; stop_all(); build_demo()
def btn_select():
    state["screen"] = "select"; stop_all()
def btn_ach():      state["screen"] = "ach"; stop_all()
def btn_quit():     pygame.quit(); sys.exit()
def btn_mute():
    state["save"]["muted"] = not state["save"]["muted"]; persist(); play("click")
def btn_music():
    state["save"]["music"] = not state["save"].get("music", True)
    persist(); play("click")
    say(f"Music {'ON' if state['save']['music'] else 'OFF'}")
VOLS = [1.0, 0.75, 0.5, 0.25, 0.0]
def btn_vol():
    cur = state["save"].get("vol", 1.0)
    i = 0
    for j, v in enumerate(VOLS):
        if abs(v - cur) < 0.01: i = j; break
    state["save"]["vol"] = VOLS[(i+1) % len(VOLS)]
    persist(); play("click")
def btn_hint():
    if state["mode"] == "level":
        say("HINT: " + cur_levels()[state["level"]][3], 7000)
    elif state["mode"] == "daily":
        say("HINT: mirror angles were scrambled from one hidden solution — "
            "look for the natural zigzag.", 6000)
    elif state["mode"] == "test":
        say("TEST MODE — Esc returns to the editor", 3000)
def btn_reset():
    m = state["mode"]
    if m == "sandbox": build_sandbox()
    elif m == "custom": build_custom(state["custom_idx"])
    elif m == "daily": build_daily()
    elif m == "test": start_test()
    elif m == "level": build_level(state["level"])
def btn_share():
    state["share_code"] = encode_scene(); state["modal"] = "share"; grant("pub")
def btn_solshare():
    if state["sol_code"]:
        state["share_code"] = state["sol_code"]
        state["modal"] = "share"
        grant("director")
def btn_ghost():
    code = ghost_for(state["pack"], state["level"])
    sol = decode_solution(code or "")
    if sol is None:
        say("No ghost for this level"); play("locked"); return
    if sol.get("p") != state["pack"] or sol.get("l") != state["level"]:
        say("Ghost is for a different level"); play("locked"); return
    start_replay(sol)
def btn_ghost_win():
    sol = decode_solution(state["sol_code"] or "")
    if sol is None:
        say("No recording for this solve"); play("locked"); return
    start_replay(sol)
def btn_load_open():
    state["code_buf"] = ""; state["modal"] = "load"
def btn_load_confirm():
    try:
        push_undo()
        objects.clear(); objects.extend(decode_scene(state["code_buf"]))
        state["modal"] = None; state["sel"] = None
        say("Scene loaded!"); play("place"); dirty()
    except Exception:
        say("Invalid code"); play("locked")
def btn_copy():
    ok = copy_clip(state["share_code"])
    say("Copied!" if ok else "Clipboard blocked — select the text manually")
def btn_clear():
    push_undo(); objects.clear(); state["sel"] = None; dirty(); play("delete")
def btn_tab(pid):
    p = next(pp for pp in PACKS if pp["id"] == pid)
    if pack_open(p):
        state["pack"] = pid; state["sel_scroll"] = 0
        play("click")
    else:
        state["unlock_buf"] = ""; state["modal"] = "unlock"; play("click")
def btn_unlock_confirm():
    code = state["unlock_buf"].strip().upper()
    if code in PREMIUM_CODES:
        state["save"]["packs"]["vault"] = True; persist()
        state["modal"] = None; state["pack"] = "vault"; state["sel_scroll"] = 0
        grant("vip"); play("unlock")
        say("SPECTRUM VAULT unlocked!")
    else:
        say("Invalid code"); play("locked")
def btn_rival_open():
    state["rival_buf"] = ""; state["modal"] = "rival"; play("click")
def btn_rival_confirm():
    res = daily_decode(state["rival_buf"])
    if res is None:
        say("Invalid code for today's Daily"); play("locked"); return
    rnb, rel = res
    grant("codebrk"); play("unlock")
    mine = state["save"]["daily"].get("best")
    state["modal"] = None
    if mine is None:
        say(f"Rival: {fmt_time(rel)} with {rnb} mirrors — play today's Daily to compare!", 5000)
        return
    d = mine - rel
    if d > 0.05:
        say(f"You're {fmt_time(d)} FASTER than the rival ({fmt_time(rel)}, {rnb} mirrors)", 5000)
    elif d < -0.05:
        say(f"Rival is {fmt_time(-d)} faster ({fmt_time(rel)}, {rnb} mirrors) — beat them!", 5000)
    else:
        say("Dead heat! Exactly the same time as your rival", 5000)
def btn_wipe():
    now = pygame.time.get_ticks()
    if state["wipe_arm"] and now - state["wipe_arm"] < 3500:
        sv = state["save"]
        sv.update(unlocked={"core": 0}, stars={}, ach=[], ghosts={},
                  daily={"date": "", "best": None, "streak": 0})
        state["endless_list"] = []
        persist(); state["wipe_arm"] = 0
        say("Progress wiped"); play("delete")
    else:
        state["wipe_arm"] = now
        say("Click ERASE again within 3s to confirm", 2600); play("locked")

class Btn:
    def __init__(self, rect, label, cb, dyn=None):
        self.rect = pygame.Rect(rect); self.label = label; self.cb = cb
        self.dyn = dyn; self._hov = False
    def draw(self, s, mouse, locked=False):
        lab = self.dyn() if self.dyn else self.label
        hov = self.rect.collidepoint(mouse) and not locked
        if hov and not self._hov: play("hover")
        self._hov = hov
        pygame.draw.rect(s, BTN_Hc if hov else BTNc, self.rect, border_radius=8)
        pygame.draw.rect(s, (200,210,255) if hov else EDGEc, self.rect, 1, border_radius=8)
        t = F16.render(lab, True, DIMc if locked else TEXTc)
        s.blit(t, t.get_rect(center=self.rect.center))
    def hit(self, pos): return self.rect.collidepoint(pos)

def daily_done_today():
    return state["save"]["daily"].get("date") == datetime.date.today().isoformat()

MENU_BTNS = []
_y = 206
for _lbl, _cb in [("PLAY", btn_play), ("DAILY LAB", btn_daily), ("EDITOR", btn_editor),
                  ("SANDBOX", btn_sandbox), ("AWARDS", btn_ach), ("HELP", btn_help),
                  ("SOUND", btn_mute), ("MUSIC", btn_music), ("VOLUME", btn_vol),
                  ("QUIT", btn_quit)]:
    MENU_BTNS.append(Btn((W//2-110, _y, 220, 40), _lbl, _cb)); _y += 46
MENU_BTNS[1].dyn = lambda: "DAILY ✓" if daily_done_today() else "DAILY LAB"
MENU_BTNS[4].dyn = lambda: f"AWARDS {len(state['save']['ach'])}/{len(ACH)}"
MENU_BTNS[6].dyn = lambda: "SOUND: OFF" if state["save"]["muted"] else "SOUND: ON"
MENU_BTNS[7].dyn = lambda: "MUSIC: OFF" if not state["save"].get("music", True) else "MUSIC: ON"
MENU_BTNS[8].dyn = lambda: ("VOLUME: MUTED"
    if state["save"].get("vol", 1.0) <= 0
    else f"VOLUME {int(round(state['save'].get('vol', 1.0)*100))}%")

def make_topbar():
    m = state["mode"]; out = []; xs = W - 16
    def add(lbl, cb, w, dyn=None):
        nonlocal xs
        r = pygame.Rect(0, 12, w, 32); r.right = xs; xs -= (w + 8)
        out.append(Btn(r, lbl, cb, dyn))
    if m == "level":
        add("NEXT >", go_next, 84); add("< PREV", go_prev, 84)
        add("HINT", btn_hint, 72)
        if ghost_for(state["pack"], state["level"]):
            add("▶ GHOST", btn_ghost, 94)
    if m == "sandbox":
        add("LEVELS", btn_back_lvl, 88)
        add("CODE", btn_share, 72); add("LOAD", btn_load_open, 72)
    if m == "editor":
        add("TEST", btn_test, 72); add("SAVE", btn_save_open, 72)
        add("CODE", btn_share, 72); add("LOAD", btn_load_open, 72)
        add("CLEAR", btn_clear, 76)
    if m == "test":
        add("EDITING", btn_exit_test, 96)
    if m == "daily":
        add("HINT", btn_hint, 72)
    if m != "test":
        add("RESET", btn_reset, 76)
    add("HELP", btn_help, 72)
    add("MENU", btn_exit_test if m == "test" else btn_select, 76)
    return out

PALETTE = [("MIRROR",  lambda p: Mirror(p,30)),
           ("SPLIT",   lambda p: Splitter(p,30)),
           ("WALL",    lambda p: Wall(p,90,220)),
           ("GLASS",   lambda p: G(p,0)),
           ("LENS",    lambda p: Lens(p,0)),
           ("PRISM",   lambda p: Prism(p,0)),
           ("BALL",    lambda p: Ball(p,0,90)),
           ("RECOMB",  lambda p: Recombiner(p,0)),
           ("PORTAL",  lambda p: PortalPair(p,0)),
           ("FILTER",  lambda p: Filter(p,0)),
           ("SOURCE",  lambda p: Source(p,0)),
           ("TARGET",  lambda p: Target(p))]
PAL_RECTS = []
px = 10
for label, fac in PALETTE:
    PAL_RECTS.append((pygame.Rect(px, H-BOT+10, 96, 46), label, fac)); px += 100

def _ic_mirror(s,r):  pygame.draw.line(s,(220,230,255),(r.x+8,r.centery),(r.x+38,r.centery),4)
def _ic_split(s,r):
    for i in range(4):
        x0=r.x+8+i*9; pygame.draw.line(s,(140,230,235),(x0,r.centery),(x0+5,r.centery),3)
def _ic_wall(s,r):    pygame.draw.line(s,(120,130,160),(r.x+8,r.centery),(r.x+38,r.centery),9)
def _ic_glass(s,r):   pygame.draw.rect(s,(150,200,255),(r.x+10,r.centery-9,26,18),2)
def _ic_lens(s,r):    pygame.draw.ellipse(s,(150,200,255),(r.x+12,r.centery-12,24,24),2)
def _ic_prism(s,r):   pygame.draw.polygon(s,(150,200,255),[(r.x+22,r.y+8),(r.x+8,r.bottom-10),(r.x+36,r.bottom-10)],2)
def _ic_ball(s,r):    pygame.draw.circle(s,(150,200,255),(r.x+22,r.centery),11,2)
def _ic_recomb(s,r):
    pygame.draw.polygon(s,(150,200,255),
                        [(r.x+22,r.bottom-8),(r.x+8,r.centery-2),(r.x+36,r.centery-2)],2)
    for i in range(3):
        pygame.draw.circle(s,SPECTRUM[i*2],(r.x+13+i*10,r.y+9),2)
def _ic_portal(s,r):
    pygame.draw.circle(s,(90,220,255),(r.x+14,r.centery),7,2)
    pygame.draw.circle(s,(255,100,225),(r.x+34,r.centery),7,2)
    pygame.draw.line(s,(90,120,180),(r.x+20,r.centery),(r.x+28,r.centery),1)
def _ic_filter(s,r):
    pygame.draw.rect(s,SPECTRUM[0],(r.x+10,r.centery-8,26,16),0)
    pygame.draw.rect(s,(255,255,255),(r.x+10,r.centery-8,26,16),1)
def _ic_source(s,r):
    pygame.draw.circle(s,(70,82,130),(r.x+22,r.centery),10,2)
    pygame.draw.circle(s,WHITE,(r.x+22,r.centery),5)
def _ic_target(s,r):
    pygame.draw.circle(s,GOLD,(r.x+22,r.centery),9,2)
    pygame.draw.circle(s,(120,130,170),(r.x+22,r.centery),3)
ICONS = {n: f for n, f in [("MIRROR",_ic_mirror),("SPLIT",_ic_split),("WALL",_ic_wall),
        ("GLASS",_ic_glass),("LENS",_ic_lens),("PRISM",_ic_prism),("BALL",_ic_ball),
        ("RECOMB",_ic_recomb),("PORTAL",_ic_portal),("FILTER",_ic_filter),
        ("SOURCE",_ic_source),("TARGET",_ic_target)]}

def draw_star(s, center, r, filled, scale=1.0):
    rr = r*scale; pts = []
    for i in range(10):
        ang = math.radians(-90 + i*36)
        rad = rr if i % 2 == 0 else rr*0.45
        pts.append((center[0]+rad*math.cos(ang), center[1]+rad*math.sin(ang)))
    pygame.draw.polygon(s, GOLD if filled else (60,70,100), pts)

def draw_lock(s, pos):
    lx, ly = int(pos.x) - 6, int(pos.y) - 30
    pygame.draw.arc(s, (150,165,205), (lx+2, ly-6, 8, 9), 0, math.pi, 2)
    pygame.draw.rect(s, (150,165,205), (lx, ly, 12, 9), 1, border_radius=2)
    s.fill((150,165,205), (lx+5, ly+3, 2, 4))

HELP_LINES = [
 ("LIGHT LAB 11.0 — HELP", GOLD), ("", 0),
 ("GOAL: bend, bounce, split, dye, MIX and RECOMBINE light", TEXTc), ("", 0),
 ("MIXING TABLE (additive — beams combining on a target)", GOLD),
 ("   RED + GREEN = YELLOW      GREEN + BLUE = CYAN", TEXTc),
 ("   RED + BLUE  = VIOLET      R+G+B = WHITE", TEXTc),
 ("   ORANGE = RED+GREEN already — one orange ray lights yellow!", GOLD),
 ("   colored targets light ONLY on an exact mix", DIMc),
 ("", 0),
 ("RECOMBINER   apex-down prism. Beams exiting together MERGE:", GOLD),
 ("   a split rainbow that enters aligned comes out WHITE.", TEXTc),
 ("", 0),
 ("ENDLESS      procedurally generated levels — deterministic", GOLD),
 ("   by number, so they're identical for everyone and ghost", TEXTc),
 ("   replays & solution codes work. Difficulty ramps up", TEXTc),
 ("   every 5 levels: mazes, relays, prism fans, splitters.", TEXTc),
 ("", 0),
 ("GHOSTS       winning records your moves; ▶ GHOST replays", GOLD),
 ("   your best as a hint. SOLUTION codes share the solve.", GOLD),
 ("", 0),
 ("PACKS        CORE OPTICS, CHROMA LAB & FLUX LAB free.", GOLD),
 ("             SPECTRUM VAULT unlocks with a code (DLC-style).", GOLD),
 ("DAILY LAB    new puzzle daily; RESULT codes + RIVAL compare.", GOLD),
 ("", 0),
 ("EDITOR       MENU > EDITOR: build, TEST it, SAVE it (Ctrl+S).", TEXTc),
 ("", 0),
 ("CONTROLS", GOLD),
 ("Left-drag: move   Right-drag: rotate   Wheel: fine rotate", TEXTc),
 ("Ctrl+Z: undo      Ctrl+D: duplicate     Arrows: nudge", TEXTc),
 ("L: lock object    G: grid snap   C: cycle color", TEXTc),
 ("+/-: index   ,/.: dispersion   Del: delete", TEXTc),
 ("R: reset   N: next   P: pause   H: help   M: music", TEXTc),
 ("F2: particles   F3: telemetry   F4: caustics", DIMc),
 ("F11: fullscreen   F12: screenshot", DIMc), ("", 0),
 ("Esc: back / close", DIMc),
]

# ---------------------------------------------------------- drawing
def draw_grid(s):
    for gx in range(20, W, 40):
        for gy in range(TOP+20, H, 40):
            s.fill(GRIDc, (gx, gy, 2, 2))

def draw_dust(s):
    beams = [bm for bm in state["beams"] if bm[3] > 0.5][:24]
    for d in dust:
        boost = 0.0
        if beams:
            dd = min(dist_pt_seg(d["p"], a, b) for (a, b, c, I) in beams)
            boost = max(0.0, 1.0 - dd/50)
        a = d["a"]*(1 + 2.2*boost)
        col = (min(255,int(a)), min(255,int(a)+14),
               min(255,int(a)+44+int(60*boost)))
        sz = 3 if boost > 0.4 else 2
        s.fill(col, (int(d["p"].x), int(d["p"].y), sz, sz))

def draw_title(s, txt, font, center):
    t = font.render(txt, True, GOLD)
    sh = pygame.transform.smoothscale(t, (int(t.get_width()*0.5), int(t.get_height()*0.5)))
    sh = pygame.transform.smoothscale(sh, t.get_size())
    s.blit(sh, sh.get_rect(center=center), special_flags=pygame.BLEND_ADD)
    fr = [(font.render(txt, True, (255,70,70)),  (-3, 0)),
          (font.render(txt, True, (70,255,120)), (0, -2)),
          (font.render(txt, True, (90,120,255)), (3, 0))]
    base = font.render(txt, True, (255,250,235))
    rect = base.get_rect(center=center)
    for img, off in fr:
        s.blit(img, rect.move(off), special_flags=pygame.BLEND_ADD)
    s.blit(base, rect)

def draw_ui_menu(s, mouse):
    draw_bg(s, state["t"])
    s.blit(glass_layer, (0, 0))
    draw_light_fx(s)
    for o in objects:
        o.draw(s, False)
    s.blit(caust, (0,0), area=pygame.Rect(0,TOP,W,H-TOP),
           special_flags=pygame.BLEND_ADD)
    draw_motes(s, state["t"])
    sh = pygame.Surface((W,H), pygame.SRCALPHA); sh.fill((6,8,18,150)); s.blit(sh,(0,0))
    s.blit(VIGNETTE, (0,0))
    draw_title(s, "LIGHT LAB", F40, (W//2, 120))
    t = F18.render("reflection • refraction • mixing • ENDLESS levels", True, DIMc)
    s.blit(t, t.get_rect(center=(W//2, 165)))
    nlv = sum(pack_level_count(p) for p in PACKS if not p.get("endless"))
    t = F16.render(f"{nlv}+ authored levels • ∞ generated   •   stars {total_stars()}   •   "
                   f"daily streak {state['save']['daily'].get('streak', 0) if daily_done_today() else 0}",
                   True, DIMc)
    s.blit(t, t.get_rect(center=(W//2, 192)))
    for b in MENU_BTNS: b.draw(s, mouse)
    t = F14.render("v11.0 'INFINITE' — made with pygame", True, (90,100,135))
    s.blit(t, (16, H-24))

def pack_tabs():
    rects = []
    x = 60
    for p in PACKS:
        rects.append((pygame.Rect(x, 142, 226, 38), p)); x += 236
    return rects

def select_layout():
    cells = []; x0, y0, cw, ch, gp = 60, 214, 232, 100, 14
    lv = cur_levels()
    for i in range(len(lv)):
        r = pygame.Rect(x0 + (i%5)*(cw+gp), y0 + (i//5)*(ch+gp) - state["sel_scroll"], cw, ch)
        cells.append(("b", i, r))
    y2 = y0 + ((len(lv)+4)//5)*(ch+gp) + 18 - state["sel_scroll"]
    for j in range(len(state["customs"])):
        r = pygame.Rect(x0 + (j%5)*(cw+gp), y2 + (j//5)*(ch+gp), cw, ch)
        cells.append(("c", j, r))
    return cells

def select_maxscroll():
    lv = cur_levels()
    rows_b = (len(lv)+4)//5
    rows_c = (len(state["customs"])+4)//5 if state["customs"] else 0
    content = 214 + rows_b*114 + (18 + rows_c*114 + 20 if rows_c else 0) + 20
    return max(0, content - (H - 100))

def draw_ui_select(s, mouse):
    draw_bg(s, state["t"]); s.blit(VIGNETTE, (0,0))
    s.blit(F22.render("SELECT LEVEL", True, GOLD), (60, 96))
    BACK_BTN.draw(s, mouse)
    state["pack_rects"] = pack_tabs()
    for (r, p) in state["pack_rects"]:
        sel = p["id"] == state["pack"]; open_ = pack_open(p)
        hov = r.collidepoint(mouse)
        pygame.draw.rect(s, BTN_Hc if (sel or (hov and open_)) else BTNc,
                         r, border_radius=8)
        pygame.draw.rect(s, GOLD if sel else (EDGEc if open_ else (70,80,110)),
                         r, 2 if sel else 1, border_radius=8)
        n_stars = sum(stars_of(p["id"], i) for i in range(pack_level_count(p)))
        lab = p["name"] if open_ else p["name"] + " [LOCKED]"
        s.blit(F14.render(lab, True, TEXTc if open_ else DIMc), (r.x+10, r.y+5))
        s.blit(F14.render(f"{n_stars}/{pack_level_count(p)*3} ★", True, DIMc),
               (r.x+10, r.y+19))
    p = cur_pack()
    s.blit(F14.render(p["desc"], True, DIMc), (60, 188))
    state["custom_del"] = []
    lv = cur_levels()
    is_endless = p.get("endless")
    if state["customs"]:
        y2 = 214 + ((len(lv)+4)//5)*114 + 18 - state["sel_scroll"]
        s.blit(F16.render("YOUR LEVELS", True, TEXTc), (60, y2-30))
    for kind, idx, r in select_layout():
        if r.bottom < 130 or r.top > H: continue
        if kind == "b":
            locked = idx > unlocked_for(state["pack"])
            hov = r.collidepoint(mouse) and not locked
            pygame.draw.rect(s, BTN_Hc if hov else BTNc, r, border_radius=10)
            pygame.draw.rect(s, (200,210,255) if hov else EDGEc, r, 1, border_radius=10)
            label = (f"#{idx+1}" if is_endless else f"{idx+1}. {lv[idx][0]}")
            s.blit(F16.render(label, True, DIMc if locked else TEXTc),
                   (r.x+14, r.y+12))
            stars = stars_of(state["pack"], idx)
            for k in range(3):
                draw_star(s, (r.x+26+k*28, r.y+58), 11, k < stars)
            best = best_of(state["pack"], idx)
            par = f"PAR {fmt_time(lv[idx][2])}"
            if best is not None: par += f"   BEST {fmt_time(best)}"
            s.blit(F14.render(par, True, DIMc), (r.x+118 if best is None else r.x+14,
                                                 r.y+48 if best is None else r.y+74))
            if locked:
                cx, cy = r.right-36, r.centery
                pygame.draw.rect(s, (90,100,140), (cx-10, cy-4, 20, 16), 2, border_radius=4)
                pygame.draw.arc(s, (90,100,140), (cx-7, cy-14, 14, 16), 0, math.pi, 3)
        else:
            c = state["customs"][idx]
            hov = r.collidepoint(mouse)
            pygame.draw.rect(s, BTN_Hc if hov else (28,36,66), r, border_radius=10)
            pygame.draw.rect(s, (140,230,235) if hov else (70,110,130), r, 1, border_radius=10)
            s.blit(F16.render(c["name"][:22], True, TEXTc), (r.x+12, r.y+10))
            best = c.get("best")
            s.blit(F14.render("CUSTOM" + (f" — best {fmt_time(best)}" if best else ""),
                              True, DIMc), (r.x+12, r.y+36))
            dx = pygame.Rect(r.right-30, r.y+6, 24, 20)
            hovx = dx.collidepoint(mouse)
            pygame.draw.rect(s, (120,50,60) if hovx else (70,40,50), dx, border_radius=5)
            s.blit(F14.render("X", True, TEXTc), dx.move(8, 2))
            state["custom_del"].append((dx, idx))

def draw_ui_ach(s, mouse):
    draw_bg(s, state["t"]); s.blit(VIGNETTE, (0,0))
    s.blit(F22.render("AWARDS", True, GOLD), (60, 96))
    BACK_BTN.draw(s, mouse)
    got = state["save"]["ach"]
    s.blit(F16.render(f"{len(got)}/{len(ACH)} unlocked", True, DIMc), (230, 104))
    x0, y0, tw, th, gx, gy = 70, 150, 270, 72, 10, 8
    for i, (aid, nm, ds) in enumerate(ACH):
        r = pygame.Rect(x0 + (i%4)*(tw+gx), y0 + (i//4)*(th+gy), tw, th)
        has = aid in got
        hov = r.collidepoint(mouse)
        pygame.draw.rect(s, BTN_Hc if (has and hov) else (BTNc if has else (20,24,40)),
                         r, border_radius=10)
        pygame.draw.rect(s, GOLD if has else EDGEc, r, 2 if has else 1, border_radius=10)
        s.blit(F16.render(nm, True, TEXTc if has else DIMc), (r.x+14, r.y+8))
        s.blit(F13.render(ds, True, DIMc if has else (70,78,104)), (r.x+14, r.y+36))
        cx, cy = r.right-22, r.centery
        col = GOLD if has else (60,70,100)
        pygame.draw.circle(s, col, (cx, cy), 11, 2)
        if has:
            pygame.draw.line(s, col, (cx-5, cy), (cx-1, cy+5), 3)
            pygame.draw.line(s, col, (cx-1, cy+5), (cx+6, cy-5), 3)
    WIPE_BTN.draw(s, mouse)
    t = F14.render("Erase wipes stars, awards, ghosts & daily streak (customs kept)",
                   True, (90,100,135))
    s.blit(t, (WIPE_BTN.rect.right + 16, WIPE_BTN.rect.centery - 8))

def draw_topbar(s, mouse):
    pygame.draw.rect(s, PANELc, (0,0,W,TOP))
    pygame.draw.line(s, EDGEc, (0,TOP), (W,TOP), 1)
    s.blit(F22.render("LIGHT LAB", True, GOLD), (16,14))
    m = state["mode"]
    if m == "level":
        lv = cur_levels()
        tgs = targets(); litc = sum(1 for t in tgs if t.lit)
        best = best_of(state["pack"], state["level"])
        extra = f"   BEST {fmt_time(best)}" if best is not None else ""
        pname = cur_pack()["name"]
        ttl = f"{pname}  {state['level']+1} — {lv[state['level']][0]}" \
            if state["pack"] == "endless" else \
            f"{pname}  {state['level']+1}/{len(lv)} — {lv[state['level']][0]}"
        s.blit(F16.render(ttl, True, TEXTc), (196,8))
        s.blit(F16.render(f"TARGETS {litc}/{len(tgs)}{extra}", True,
                          GOLD if tgs and litc == len(tgs) else DIMc), (196,30))
        el = ((state["win_time"] if state["complete"] else pygame.time.get_ticks())
              - state["start_time"]) / 1000
        par = lv[state["level"]][2]
        s.blit(F16.render(f"TIME {fmt_time(el)}  PAR {fmt_time(par)}", True,
                          GOLD if el <= par else TEXTc), (560,18))
    elif m == "custom":
        c = state["customs"][state["custom_idx"]]
        tgs = targets(); litc = sum(1 for t in tgs if t.lit)
        s.blit(F16.render(f"CUSTOM — {c['name']}", True, TEXTc), (196,8))
        s.blit(F16.render(f"TARGETS {litc}/{len(tgs)}", True, DIMc), (196,30))
    elif m == "daily":
        tgs = targets(); litc = sum(1 for t in tgs if t.lit)
        stk = state["save"]["daily"].get("streak", 0)
        s.blit(F16.render(f"DAILY LAB — {datetime.date.today().isoformat()}"
                          f"  ({state['daily_nb']} mirrors)", True, GOLD), (196,8))
        s.blit(F16.render(f"TARGETS {litc}/{len(tgs)}   STREAK {stk}", True, DIMc), (196,30))
        el = ((state["win_time"] if state["complete"] else pygame.time.get_ticks())
              - state["start_time"]) / 1000
        s.blit(F16.render(f"TIME {fmt_time(el)}  PAR {fmt_time(state['daily_par'])}",
                          True, GOLD if el <= state["daily_par"] else TEXTc), (560,18))
    elif m == "test":
        s.blit(F16.render("TESTING YOUR LEVEL — Esc to return to editor",
                          True, GOLD), (196,18))
    elif m == "editor":
        s.blit(F16.render("EDITOR — build, then TEST, then SAVE (Ctrl+S). L = lock",
                          True, TEXTc), (196,8))
        s.blit(F16.render("Sources & targets ARE movable here. C = cycle colors.",
                          True, DIMc), (196,30))
    else:
        s.blit(F16.render("SANDBOX — build your own optics", True, TEXTc), (196,8))
        s.blit(F16.render("Cross beams to MIX colors. RECOMB merges them. G = snap.",
                          True, DIMc), (196,30))
    if state["replay"]:
        t = F16.render("▶ REPLAY", True, (140,230,235))
        r = t.get_rect(midright=(W-460, H//2))
        s.blit(t, r)
    for b in state["topbar"]:
        b.draw(s, mouse, locked=(b.label == "NEXT >" and not can_next()))

def draw_palette(s, mouse):
    pygame.draw.rect(s, PANELc, (0,H-BOT,W,BOT))
    pygame.draw.line(s, EDGEc, (0,H-BOT), (W,H-BOT), 1)
    for (r, label, fac) in PAL_RECTS:
        hov = r.collidepoint(mouse); act = state["placing"] is fac
        pygame.draw.rect(s, BTN_Hc if (hov or act) else BTNc, r, border_radius=8)
        pygame.draw.rect(s, GOLD if act else EDGEc, r, 1, border_radius=8)
        ICONS[label](s, r)
        s.blit(F14.render(label, True, TEXTc), (r.x+44, r.centery-9))
    if state["snap"]:
        s.blit(F14.render("SNAP", True, GOLD), (W-60, H-BOT+16))

def draw_chip(s):
    msg = None
    if state["placing"]:
        label = next((l for l,f in PALETTE if f is state["placing"]), "")
        msg = f"Click to place {label} — right-click cancels (Shift-click = several)"
    else:
        o = state["sel"]
        if isinstance(o, Recombiner):
            msg = "RECOMBINER — beams exiting together MERGE (R+G+B=WHITE). Del: delete"
        elif isinstance(o, PortalPair):
            msg = "PORTAL — beams teleport between rings. Del: delete"
        elif isinstance(o, Filter):
            msg = f"FILTER {CNAME[o.ci]} — C: change color   Del: delete"
        elif isinstance(o, Prism):
            msg = f"PRISM — n={o.n:.2f}  dispersion={o.spread:.3f}  [,/.] tune"
        elif isinstance(o, Glass):
            msg = f"GLASS — n = {o.n:.2f}   [+/-] change index   Del: delete"
        elif isinstance(o, Target) and o.color:
            req = "+".join(COMP_NAME[c] for c in COMP_OF[o.color])
            got = ("   now: " + "+".join(COMP_NAME[c] for c in o.mix)) if o.mix \
                  else "   (dark)"
            msg = f"TARGET needs exactly {req}{got}"
        elif isinstance(o, Source) and state["mode"] in ("sandbox","editor"):
            msg = "SOURCE color " + ("WHITE (R+G+B)" if o.ci == 0 else CNAME[o.ci-1]) \
                  + " — C: cycle"
        elif o is not None and getattr(o, "locked", False):
            msg = "LOCKED — L to unlock, Del to delete"
    if msg:
        t = F16.render(msg, True, TEXTc)
        r = t.get_rect(topleft=(16, TOP+10)).inflate(12, 8)
        pygame.draw.rect(s, (16,22,44), r, border_radius=8)
        s.blit(t, (r.x+6, r.y+4))

def draw_modal(s, mouse):
    sh = pygame.Surface((W,H), pygame.SRCALPHA); sh.fill((6,8,18,200)); s.blit(sh,(0,0))
    if state["modal"] == "share":
        is_sol = state["share_code"].startswith("LLG:")
        r = pygame.Rect(0,0,780,320); r.center = (W//2, H//2)
        pygame.draw.rect(s,(16,22,44),r,border_radius=14)
        pygame.draw.rect(s,EDGEc,r,1,border_radius=14)
        s.blit(F22.render("SOLUTION CODE" if is_sol else "SHARE CODE",
                          True, GOLD), (r.x+26, r.y+18))
        s.blit(F14.render("Recipient picks LOAD CODE on the same level and pastes"
                          if is_sol else
                          "Send this code to a friend — they press LOAD and paste it.",
                          True, DIMc), (r.x+26, r.y+52))
        box = pygame.Rect(r.x+26, r.y+76, r.w-52, 150)
        pygame.draw.rect(s,(8,11,26),box,border_radius=8)
        y = box.y+8
        for i in range(0, len(state["share_code"]), 66):
            s.blit(F14.render(state["share_code"][i:i+66], True, TEXTc), (box.x+8, y))
            y += 20
            if y > box.bottom-20: break
        mb = {"copy": pygame.Rect(r.x+26, r.bottom-56, 150, 38),
              "close": pygame.Rect(r.right-176, r.bottom-56, 150, 38)}
    elif state["modal"] == "load":
        r = pygame.Rect(0,0,780,240); r.center = (W//2, H//2)
        pygame.draw.rect(s,(16,22,44),r,border_radius=14)
        pygame.draw.rect(s,EDGEc,r,1,border_radius=14)
        s.blit(F22.render("LOAD CODE", True, GOLD), (r.x+26, r.y+18))
        s.blit(F14.render("Scene code (LL2:…) loads a scene. Solution code (LLG:…)",
                          True, DIMc), (r.x+26, r.y+52))
        s.blit(F14.render("on a pack level plays it as a ghost replay.", True, DIMc),
               (r.x+26, r.y+70))
        box = pygame.Rect(r.x+26, r.y+90, r.w-52, 44)
        pygame.draw.rect(s,(8,11,26),box,border_radius=8)
        pygame.draw.rect(s,EDGEc,box,1,border_radius=8)
        caret = "|" if (pygame.time.get_ticks()//400) % 2 else ""
        s.blit(F16.render(state["code_buf"][-60:]+caret, True, TEXTc), (box.x+10, box.y+11))
        mb = {"ok": pygame.Rect(r.x+26, r.bottom-56, 150, 38),
              "cancel": pygame.Rect(r.right-176, r.bottom-56, 150, 38)}
    elif state["modal"] == "unlock":
        r = pygame.Rect(0,0,620,240); r.center = (W//2, H//2)
        pygame.draw.rect(s,(16,22,44),r,border_radius=14)
        pygame.draw.rect(s,GOLD,r,2,border_radius=14)
        s.blit(F22.render("SPECTRUM VAULT", True, GOLD), (r.x+26, r.y+18))
        s.blit(F14.render("10 expert levels. Enter your unlock code (from the", True, DIMc),
               (r.x+26, r.y+52))
        s.blit(F14.render("store page / download key) and press Enter.", True, DIMc),
               (r.x+26, r.y+70))
        box = pygame.Rect(r.x+26, r.y+90, r.w-52, 44)
        pygame.draw.rect(s,(8,11,26),box,border_radius=8)
        pygame.draw.rect(s,EDGEc,box,1,border_radius=8)
        caret = "|" if (pygame.time.get_ticks()//400) % 2 else ""
        s.blit(F16.render(state["unlock_buf"].upper()+caret, True, TEXTc),
               (box.x+10, box.y+11))
        mb = {"ok": pygame.Rect(r.x+26, r.bottom-56, 150, 38),
              "cancel": pygame.Rect(r.right-176, r.bottom-56, 150, 38)}
    elif state["modal"] == "rival":
        r = pygame.Rect(0,0,620,240); r.center = (W//2, H//2)
        pygame.draw.rect(s,(16,22,44),r,border_radius=14)
        pygame.draw.rect(s,GOLD,r,2,border_radius=14)
        s.blit(F22.render("RIVAL CODE", True, GOLD), (r.x+26, r.y+18))
        s.blit(F14.render("Enter a friend's RESULT CODE from today's Daily Lab.", True, DIMc),
               (r.x+26, r.y+52))
        s.blit(F14.render("Codes only work on the day they were earned!", True, DIMc),
               (r.x+26, r.y+70))
        box = pygame.Rect(r.x+26, r.y+90, r.w-52, 44)
        pygame.draw.rect(s,(8,11,26),box,border_radius=8)
        pygame.draw.rect(s,EDGEc,box,1,border_radius=8)
        caret = "|" if (pygame.time.get_ticks()//400) % 2 else ""
        s.blit(F16.render(state["rival_buf"].upper()+caret, True, TEXTc),
               (box.x+10, box.y+11))
        mb = {"ok": pygame.Rect(r.x+26, r.bottom-56, 150, 38),
              "cancel": pygame.Rect(r.right-176, r.bottom-56, 150, 38)}
    else:
        r = pygame.Rect(0,0,560,220); r.center = (W//2, H//2)
        pygame.draw.rect(s,(16,22,44),r,border_radius=14)
        pygame.draw.rect(s,GOLD,r,1,border_radius=14)
        s.blit(F22.render("SAVE LEVEL", True, GOLD), (r.x+26, r.y+18))
        s.blit(F14.render("Name your level — it will appear in level select.",
                          True, DIMc), (r.x+26, r.y+52))
        box = pygame.Rect(r.x+26, r.y+84, r.w-52, 44)
        pygame.draw.rect(s,(8,11,26),box,border_radius=8)
        pygame.draw.rect(s,EDGEc,box,1,border_radius=8)
        caret = "|" if (pygame.time.get_ticks()//400) % 2 else ""
        s.blit(F16.render(state["name_buf"][:28]+caret, True, TEXTc), (box.x+10, box.y+11))
        mb = {"ok": pygame.Rect(r.x+26, r.bottom-56, 150, 38),
              "cancel": pygame.Rect(r.right-176, r.bottom-56, 150, 38)}
    labels = {"copy":"COPY","close":"CLOSE",
              "ok":{"load":"LOAD","name":"SAVE","unlock":"UNLOCK",
                    "rival":"COMPARE"}[state["modal"]],"cancel":"CANCEL"}
    state["modal_btns"] = mb
    for key, br in mb.items():
        hov = br.collidepoint(mouse)
        pygame.draw.rect(s, BTN_Hc if hov else BTNc, br, border_radius=8)
        pygame.draw.rect(s, EDGEc, br, 1, border_radius=8)
        t = F16.render(labels[key], True, TEXTc)
        s.blit(t, t.get_rect(center=br.center))

def draw_win(s):
    m = state["mode"]; T = state["t"]
    t = (pygame.time.get_ticks() - state["win_time"]) / 1000
    r = pygame.Rect(0,0,620,210); r.center = (W//2, H//2-60)
    pygame.draw.rect(s, (18,24,46), r, border_radius=14)
    pulse = 0.75 + 0.25*math.sin(T*3.2)
    pygame.draw.rect(s, dim(GOLD, pulse), r, 2, border_radius=14)
    title = ("LEVEL COMPLETE!" if m == "level" else
             "DAILY COMPLETE!" if m == "daily" else
             "CUSTOM LEVEL COMPLETE!" if m == "custom" else "TEST COMPLETE!")
    t1 = F40.render(title, True, GOLD)
    s.blit(t1, t1.get_rect(center=(W//2, r.y+42)))
    el = (state["win_time"] - state["start_time"]) / 1000
    msg = f"TIME {fmt_time(el)}"
    if m == "level":
        msg += f"   PAR {fmt_time(cur_levels()[state['level']][2])}"
        best = best_of(state["pack"], state["level"])
        if best is not None: msg += f"   BEST {fmt_time(best)}"
    if m == "daily": msg += f"   PAR {fmt_time(state['daily_par'])}"
    if m == "test":  msg += "   — keep tweaking in the editor"
    t2 = F18.render(msg, True, TEXTc)
    s.blit(t2, t2.get_rect(center=(W//2, r.y+80)))
    if m in ("level", "daily"):
        for i in range(3):
            cx = W//2 + (i-1)*76; cy = r.y+120
            if t > 0.35 + 0.33*i:
                k = min(1.0, (t - (0.35+0.33*i)) / 0.16)
                draw_star(s, (cx,cy), 21, i < state["win_stars"],
                          1.0 + 0.35*math.sin(k*math.pi))
    else:
        t3 = F16.render("Nice work!", True, DIMc)
        s.blit(t3, t3.get_rect(center=(W//2, r.y+120)))
    if m == "daily" and state.get("daily_code"):
        t3 = F16.render("RESULT CODE  " + state["daily_code"]
                        + "   — swap with friends!", True, GOLD)
        s.blit(t3, t3.get_rect(center=(W//2, r.bottom-16)))
    if m == "level" and state.get("sol_code"):
        t3 = F16.render("Your solve was recorded — GHOST replays it, SOLUTION shares it",
                        True, DIMc)
        s.blit(t3, t3.get_rect(center=(W//2, r.bottom-16)))
    btns = []
    by = r.bottom + 22
    if m == "level":
        defs = [("REPLAY", lambda: build_level(state["level"]))]
        if can_next(): defs.append(("NEXT >", go_next))
        if state.get("sol_code"):
            defs.append(("▶ GHOST", btn_ghost_win))
            defs.append(("SOLUTION", btn_solshare))
        defs.append(("PACKS", btn_select))
    elif m == "daily":
        defs = [("REPLAY", build_daily), ("RIVAL", btn_rival_open),
                ("MENU", btn_select)]
    elif m == "custom":
        defs = [("REPLAY", lambda: build_custom(state["custom_idx"])),
                ("MENU", btn_select)]
    else:
        defs = [("BACK TO EDITOR", btn_exit_test)]
    total = len(defs)*150 + (len(defs)-1)*16
    bx = W//2 - total//2
    for lbl, cb in defs:
        br = pygame.Rect(bx, by, 150, 42); bx += 166
        hov = br.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(s, BTN_Hc if hov else BTNc, br, border_radius=8)
        pygame.draw.rect(s, (200,210,255) if hov else EDGEc, br, 1, border_radius=8)
        tt = F16.render(lbl, True, TEXTc)
        s.blit(tt, tt.get_rect(center=br.center))
        btns.append((br, cb))
    state["win_btns"] = btns

def draw_pause(s):
    sh = pygame.Surface((W,H), pygame.SRCALPHA); sh.fill((4,6,14,170)); s.blit(sh,(0,0))
    t = F40.render("PAUSED", True, GOLD)
    s.blit(t, t.get_rect(center=(W//2, H//2-20)))
    t = F18.render("click or press any key to resume  •  P toggles pause", True, DIMc)
    s.blit(t, t.get_rect(center=(W//2, H//2+30)))

def draw_floats(s):
    now = pygame.time.get_ticks()
    y = TOP + 40
    for f in state["floats"]:
        age = (now - f["t0"]) / 1000
        if age*1000 >= f["dur"]: continue
        k = min(1.0, age/0.22); ease = 1 - (1-k)**3
        oy = int((1-ease) * -24)
        rem = f["dur"]/1000 - age
        a = 255 if rem > 0.35 else max(0, int(255*rem/0.35))
        t = F16.render(f["m"], True, GOLD if f["ach"] else TEXTc)
        t.set_alpha(a)
        wpad = 34 if f["ach"] else 24
        bg = t.get_rect(midtop=(W//2, y+oy)).inflate(wpad, 10)
        bgs = pygame.Surface(bg.size, pygame.SRCALPHA)
        pygame.draw.rect(bgs, (16,22,44,210), bgs.get_rect(), border_radius=8)
        if f["ach"]:
            pygame.draw.rect(bgs, GOLD, bgs.get_rect(), 1, border_radius=8)
        s.blit(bgs, bg)
        s.blit(t, t.get_rect(midtop=(W//2, y+oy)))
        y += 38

def render(beams):
    mouse = pygame.mouse.get_pos()
    T = state["t"]
    canvas.fill(BGc)
    s = canvas
    if state["screen"] == "play":
        state["topbar"] = make_topbar()
        draw_bg(s, T)
        if state["save"]["fx"]: draw_dust(s)
        draw_grid(s)
        s.blit(glass_layer, (0,0))
        draw_light_fx(s)
        for o in objects:
            hov = o.contains(V2(mouse)) and o is not state["sel"] and selectable(o)
            if hov:
                if isinstance(o, Glass):
                    pygame.draw.polygon(s, (255,255,255), ippi(o.world_pts()), 1)
                elif hasattr(o, "ends"):
                    a,b = o.ends(); pygame.draw.line(s,(255,255,255),a,b,1)
            o.draw(s, o is state["sel"])
        for o in objects:
            if o.locked: draw_lock(s, o.pos)
        s.blit(caust, (0,0), area=pygame.Rect(0,TOP,W,H-TOP),
               special_flags=pygame.BLEND_ADD)
        if state["placing"] and TOP < mouse[1] < H-BOT:
            state["placing"]((mouse[0], mouse[1])).draw(s, False)
        if (not state["complete"] and not state["paused"] and not state["placing"]
                and not state["replay"] and mouse[1] > TOP):
            mx, my = mouse
            pygame.draw.circle(s, (150,180,230), (mx, my), 9, 1)
            for dx, dy in ((-1,0),(1,0),(0,-1),(0,1)):
                pygame.draw.line(s, (150,180,230),
                                 (mx+dx*5, my+dy*5), (mx+dx*12, my+dy*12), 1)
        s.blit(VIGNETTE, (0,0))
        if state["flash"] > 0:
            FLASH_SURF.set_alpha(int(90 * min(1.0, state["flash"])))
            s.blit(FLASH_SURF, (0,0))
        draw_topbar(s, mouse)
        if state["mode"] in ("sandbox", "editor"): draw_palette(s, mouse)
        draw_chip(s)
        if state["complete"]: draw_win(s)
        if state["fps_show"]:
            rp = "REPLAY" if state["replay"] else "-----"
            dbg = (f"FPS {clock.get_fps():.0f}  beams {len(beams)}  "
                   f"photons {len(state['photons'])}  caustR {state['caust_rays']}  "
                   f"nexus {len(state['mixpts'])}  obj {len(objects)}  "
                   f"rec {len(state['rec'])}  [{rp}]  traces {state['trace_count']}  "
                   f"sndq {len(SNDQ)}")
            t = F14.render(dbg, True, (120,200,140))
            r = t.get_rect(topright=(W-14, TOP+10)).inflate(10,6)
            pygame.draw.rect(s, (10,14,28), r, border_radius=6)
            s.blit(t, (r.x+5, r.y+3))
        if state["paused"]: draw_pause(s)
    elif state["screen"] == "select":
        state["topbar"] = []
        draw_ui_select(s, mouse)
    elif state["screen"] == "ach":
        state["topbar"] = []
        draw_ui_ach(s, mouse)
    else:
        state["topbar"] = []
        draw_ui_menu(s, mouse)
    if state["help"]:
        sh = pygame.Surface((W,H), pygame.SRCALPHA); sh.fill((6,8,18,200))
        s.blit(sh,(0,0))
        r = pygame.Rect(0,0,740,620); r.center = (W//2,H//2)
        pygame.draw.rect(s,(16,22,44),r,border_radius=14)
        pygame.draw.rect(s,EDGEc,r,1,border_radius=14)
        y = r.y+14
        for txt,col in HELP_LINES:
            if txt: s.blit(F16.render(txt,True,col),(r.x+26,y))
            y += 24
    if state["modal"]: draw_modal(s, mouse)
    draw_floats(s)
    present()

# ------------------------------------------------------------ input
def selectable(o):
    m = state["mode"]
    if m == "test": return False
    if m in ("sandbox", "editor"): return True
    return isinstance(o, (Mirror, Glass, Splitter, Concave, PortalPair)) \
        and not isinstance(o, Wall)

def movable(o):
    return selectable(o) and not getattr(o, "locked", False)

def rotate_sel(deg):
    o = state["sel"]
    if o is None or isinstance(o, (Target, Source)) or not movable(o): return
    o.angle += math.radians(deg)
    rec_commit(); dirty()

def snap_pos(p):
    if not state["snap"]: return p
    return V2(round(p.x/20)*20, round(p.y/20)*20)

def handle_keydown(e):
    if state["replay"]:
        if e.key == pygame.K_ESCAPE:
            state["replay"] = None
            say("Replay stopped", 1500)
        return
    if state["modal"] in ("load", "name", "unlock", "rival"):
        bufk = {"load":"code_buf","name":"name_buf",
                "unlock":"unlock_buf","rival":"rival_buf"}[state["modal"]]
        if e.key == pygame.K_RETURN:
            if state["modal"] == "load": btn_load_confirm()
            elif state["modal"] == "name": btn_save_confirm()
            elif state["modal"] == "unlock": btn_unlock_confirm()
            else: btn_rival_confirm()
        elif e.key == pygame.K_BACKSPACE:
            state[bufk] = state[bufk][:-1]
        elif e.key == pygame.K_ESCAPE:
            state["modal"] = None
        elif e.key == pygame.K_v and (e.mod & pygame.KMOD_CTRL) \
                and state["modal"] != "unlock":
            try:
                state[bufk] = (state[bufk] + pygame.scrap.get_text())[:6000]
            except Exception: pass
        return
    if state["modal"]:
        if e.key == pygame.K_ESCAPE: state["modal"] = None
        return
    if state["paused"]:
        state["paused"] = False
        state["start_time"] += pygame.time.get_ticks() - state["paused_at"]
        return
    k = e.key; mod = e.mod
    if k == pygame.K_z and (mod & pygame.KMOD_CTRL): do_undo(); return
    if k == pygame.K_s and (mod & pygame.KMOD_CTRL) and state["mode"] == "editor":
        btn_save_open(); return
    if k == pygame.K_d and (mod & pygame.KMOD_CTRL):
        o = state["sel"]
        if o is not None and selectable(o):
            push_undo()
            c = clone_obj(o); c.pos += V2(26, 26)
            objects.append(c); state["sel"] = c
            play("place"); dirty()
        return
    if k == pygame.K_F11:
        pygame.display.toggle_fullscreen(); return
    if k == pygame.K_F3: state["fps_show"] = not state["fps_show"]; return
    if k == pygame.K_F2:
        state["save"]["fx"] = not state["save"]["fx"]; persist()
        say(f"Particles & motes {'ON' if state['save']['fx'] else 'OFF'}"); return
    if k == pygame.K_F4:
        state["save"]["caustics"] = not state["save"]["caustics"]
        persist(); dirty()
        say(f"Caustics {'ON' if state['save']['caustics'] else 'OFF'}"); return
    if k == pygame.K_m:
        btn_music(); return
    if k == pygame.K_l and state["screen"] == "play" \
            and state["mode"] in ("sandbox", "editor"):
        o = state["sel"]
        if o is not None:
            o.locked = not o.locked
            play("click"); dirty()
            say("Object LOCKED" if o.locked else "Object unlocked", 1200)
        return
    if k == pygame.K_g and state["mode"] in ("sandbox", "editor"):
        state["snap"] = not state["snap"]
        say(f"Grid snap {'ON' if state['snap'] else 'OFF'}"); play("click"); return
    if k == pygame.K_p and state["screen"] == "play":
        state["paused"] = True; state["paused_at"] = pygame.time.get_ticks(); return
    if k == pygame.K_ESCAPE:
        if state["placing"]: state["placing"] = None
        elif state["help"]:  state["help"] = False
        elif state["complete"] and state["mode"] == "test": btn_exit_test()
        elif state["mode"] == "test": btn_exit_test()
        elif state["sel"]:   state["sel"] = None
        elif state["screen"] == "play": btn_select()
        elif state["screen"] == "ach":  btn_menu()
        elif state["screen"] == "select": btn_menu()
        return
    if state["screen"] != "play": return
    if   k == pygame.K_h: btn_help()
    elif k == pygame.K_r: btn_reset()
    elif k == pygame.K_n and state["mode"] == "level": go_next()
    elif k == pygame.K_TAB:
        if state["mode"] in ("level", "custom"): btn_sandbox()
        elif state["mode"] == "sandbox": btn_back_lvl()
    elif k in (pygame.K_DELETE, pygame.K_BACKSPACE):
        if state["sel"] in objects and selectable(state["sel"]):
            push_undo()
            objects.remove(state["sel"]); state["sel"] = None
            play("delete"); dirty()
    elif k in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
        if isinstance(state["sel"], Glass):
            state["sel"].n = min(2.6, state["sel"].n + 0.05); dirty()
    elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):
        if isinstance(state["sel"], Glass):
            state["sel"].n = max(1.05, state["sel"].n - 0.05); dirty()
    elif k == pygame.K_COMMA:
        if isinstance(state["sel"], (Prism, Recombiner)):
            state["sel"].spread = max(-0.2, state["sel"].spread - 0.005); dirty()
    elif k == pygame.K_PERIOD:
        if isinstance(state["sel"], (Prism, Recombiner)):
            state["sel"].spread = min(0.2, state["sel"].spread + 0.005); dirty()
    elif k == pygame.K_c:
        o = state["sel"]
        if isinstance(o, Filter):
            o.ci = (o.ci+1) % len(SPECTRUM); o.tint = SPECTRUM[o.ci]
            play("click"); dirty()
        elif isinstance(o, Target) and state["mode"] in ("sandbox","editor"):
            seq = [None] + SPECTRUM
            cur = seq.index(o.color) if o.color in seq else 0
            o.color = seq[(cur+1) % len(seq)]
            o.R = 22 if o.color else 16; o.mix = ""
            play("click"); dirty()
        elif isinstance(o, Source) and state["mode"] in ("sandbox","editor"):
            o.ci = (o.ci+1) % len(SOURC_COLORS); play("click"); dirty()
    elif k == pygame.K_q: rotate_sel(-3)
    elif k == pygame.K_e: rotate_sel(3)
    elif k in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
        o = state["sel"]
        if o is not None and movable(o):
            d = 1 if mod & pygame.KMOD_SHIFT else 4
            o.pos += V2(d if k == pygame.K_RIGHT else -d if k == pygame.K_LEFT else 0,
                        d if k == pygame.K_DOWN  else -d if k == pygame.K_UP   else 0)
            o.pos = snap_pos(o.pos)
            rec_commit(); dirty()
    elif k == pygame.K_F12:
        play("shot")
        pygame.image.save(canvas, os.path.join(HERE, f"lightlab_{pygame.time.get_ticks()}.png"))
        say("Screenshot saved")

def on_down(e):
    pos = e.pos; m = V2(pos)
    if state["replay"]: return
    if state["paused"]:
        state["paused"] = False
        state["start_time"] += pygame.time.get_ticks() - state["paused_at"]
        return
    if state["modal"]:
        for key, br in state.get("modal_btns", {}).items():
            if br.collidepoint(pos):
                play("click")
                if key == "copy": btn_copy()
                elif key == "close": state["modal"] = None
                elif key == "ok":
                    if state["modal"] == "load": btn_load_confirm()
                    elif state["modal"] == "name": btn_save_confirm()
                    elif state["modal"] == "unlock": btn_unlock_confirm()
                    else: btn_rival_confirm()
                elif key == "cancel": state["modal"] = None
                return
        return
    if state["help"]:
        state["help"] = False; return
    if state["screen"] == "menu":
        for b in MENU_BTNS:
            if b.hit(pos): play("click"); b.cb(); return
        return
    if state["screen"] == "ach":
        if BACK_BTN.hit(pos): play("click"); btn_menu(); return
        if WIPE_BTN.hit(pos): btn_wipe(); return
        return
    if state["screen"] == "select":
        if BACK_BTN.hit(pos): play("click"); btn_menu(); return
        for (r, p) in state.get("pack_rects", []):
            if r.collidepoint(pos): btn_tab(p["id"]); return
        for (dx, j) in state["custom_del"]:
            if dx.collidepoint(pos):
                del state["customs"][j]; save_customs()
                say("Custom level deleted"); play("delete"); return
        for kind, idx, r in select_layout():
            if r.collidepoint(pos):
                if kind == "b":
                    if idx <= unlocked_for(state["pack"]):
                        play("click"); build_level(idx)
                    else:
                        say("LOCKED — finish earlier levels"); play("locked")
                else:
                    play("click"); build_custom(idx)
                return
        return
    if state["complete"]:
        for r, cb in state.get("win_btns", []):
            if r.collidepoint(pos): play("click"); cb(); return
        return
    for b in state["topbar"]:
        if b.hit(pos):
            if b.label == "NEXT >" and not can_next():
                say("LOCKED — light every target first"); play("locked"); return
            play("click"); b.cb(); return
    if pos[1] < TOP: return
    if state["mode"] in ("sandbox", "editor") and pos[1] > H-BOT:
        for (r, label, fac) in PAL_RECTS:
            if r.collidepoint(pos):
                state["placing"] = None if state["placing"] is fac else fac
                play("click"); return
        return
    if e.button == 1:
        if state["placing"]:
            push_undo()
            ymax = H-(BOT+30) if state["mode"] in ("sandbox","editor") else H-30
            p = snap_pos(V2(min(max(pos[0],24),W-24),
                            min(max(pos[1],TOP+30),ymax)))
            obj = state["placing"](p)
            objects.append(obj); state["sel"] = obj; play("place"); dirty()
            if not (pygame.key.get_mods() & pygame.KMOD_SHIFT):
                state["placing"] = None
            return
        for o in reversed(objects):
            if selectable(o) and o.contains(m):
                state["sel"] = o
                if movable(o):
                    state["drag"] = o.pos - m
                    state["pre_scene"] = encode_scene()
                    play("grab", x=o.pos.x)
                else:
                    say("Locked — L to unlock", 1200)
                return
        state["sel"] = None
    elif e.button == 3:
        if state["placing"]: state["placing"] = None; return
        o = state["sel"]
        if o is None or not o.contains(m) or not movable(o):
            o = None
            for cand in reversed(objects):
                if movable(cand) and cand.contains(m): o = cand; break
        if o is not None and not isinstance(o, (Target, Source)):
            state["sel"] = o; state["rotating"] = True
            state["pre_scene"] = encode_scene()
            play("grab", x=o.pos.x)

def on_motion(e):
    m = V2(e.pos)
    if state["rotating"] and state["sel"] is not None:
        o = state["sel"]
        o.angle = math.atan2(m.y-o.pos.y, m.x-o.pos.x); dirty()
        now = pygame.time.get_ticks()
        if now - state["last_tick"] > 90:
            state["last_tick"] = now; play("tick", x=o.pos.x)
    elif state["drag"] is not None and state["sel"] is not None:
        ymax = H-(BOT+20) if state["mode"] in ("sandbox","editor") else H-20
        p = snap_pos(V2(min(max(e.pos[0]+state["drag"].x, 24), W-24),
                        min(max(e.pos[1]+state["drag"].y, TOP+24), ymax)))
        state["sel"].pos = p; dirty()

def on_up(e):
    if (state["drag"] is not None or state["rotating"]) and state["pre_scene"]:
        if encode_scene() != state["pre_scene"]:
            state["undo"].append(state["pre_scene"])
            if len(state["undo"]) > 60: state["undo"].pop(0)
            rec_commit()
    state["pre_scene"] = None
    state["drag"] = None; state["rotating"] = False

def on_wheel(e):
    if state["screen"] == "select":
        state["sel_scroll"] = max(0, min(select_maxscroll(),
                                         state["sel_scroll"] - e.y*56))
        return
    if state["screen"] != "play" or state["paused"] or state["replay"]: return
    o = state["sel"]
    if o is None or isinstance(o, (Target, Source)) or not movable(o): return
    step = 0.25 if e.mod & pygame.KMOD_SHIFT else 2.0
    o.angle += math.radians(step * (1 if e.y > 0 else -1))
    play("tick", x=o.pos.x)
    rec_commit(); dirty()

BACK_BTN = Btn((60, 92, 140, 38), "< BACK", btn_menu)
WIPE_BTN = Btn((70, H-70, 240, 42), "ERASE PROGRESS", btn_wipe,
               dyn=lambda: "SURE? CLICK AGAIN"
               if state["wipe_arm"] and pygame.time.get_ticks()-state["wipe_arm"] < 3500
               else "ERASE PROGRESS")

# --------------------------------------------------------- main loop
def prewarm():
    for fn in SFX.values():
        for _, kw in fn(1.0): S(**kw)
    for f in PENTA:
        S(freq=f, ms=280, vol=.3, atk=.015, sus=.4, curve=2.2, harm=.5)
prewarm()

build_demo()
say("LIGHT LAB 11.0 — 50+ levels plus ENDLESS. Press PLAY!", 3600)

while True:
    dt = clock.tick(60) / 1000.0
    for e in pygame.event.get():
        if e.type == pygame.QUIT: pygame.quit(); sys.exit()
        elif e.type == pygame.KEYDOWN:          handle_keydown(e)
        elif e.type == pygame.TEXTINPUT and \
                state["modal"] in ("load","name","unlock","rival"):
            bufk = {"load":"code_buf","name":"name_buf",
                    "unlock":"unlock_buf","rival":"rival_buf"}[state["modal"]]
            cap = {"load":6000,"name":24,"unlock":24,"rival":6}[state["modal"]]
            if len(state[bufk]) < cap: state[bufk] += e.text
        elif e.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP,
                        pygame.MOUSEMOTION):
            e.pos = to_game(e.pos)
            if   e.type == pygame.MOUSEBUTTONDOWN: on_down(e)
            elif e.type == pygame.MOUSEBUTTONUP:   on_up(e)
            else:                                  on_motion(e)
        elif e.type == pygame.MOUSEWHEEL:         on_wheel(e)
        elif e.type == pygame.WINDOWFOCUSLOST and state["screen"] == "play":
            if not state["complete"] and not state["replay"]:
                state["paused"] = True
                state["paused_at"] = pygame.time.get_ticks()
    nowt = pygame.time.get_ticks()
    state["floats"] = [f for f in state["floats"]
                       if nowt - f["t0"] < f["dur"]]
    if not state["paused"]:
        state["t"] += dt
        state["flash"] = max(0.0, state["flash"] - dt*1.4)
        if state["replay"]:
            apply_replay()
        elif state["screen"] == "menu" and not state["help"] and not state["modal"]:
            for d in state["demo"]:
                d.angle += dt * (0.30 if d is state["demo"][0] else 0.10)
            dirty()
        update_sparks(dt); update_fx(dt); update_dust(dt)
        update_sndq(); update_music()
        if state["dirty"]:
            state["beams"] = trace()
            rebuild_static()
            state["dirty"] = False
            state["trace_count"] += 1
        draw_dynamics(state["t"])
        if state["screen"] == "play": check_win()
    render(state["beams"])