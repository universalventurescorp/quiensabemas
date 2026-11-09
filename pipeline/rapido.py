#!/usr/bin/env python3
"""Montador del formato rápido «¿A o B?» (9-nov-2026): MAX y NOVA corren por un camino en perspectiva.
Cada pregunta: dos carteles con fotos llegan desde el punto de fuga, LA VOZ lee la pregunta, cuenta 3-2-1,
«¡Tiempo!», MAX y NOVA gritan su lado, el cartel correcto se agranda (campanazo + aplausos) y el otro se cae (choque).
TODO SE ACELERA con el avance del video (pedido de Luis): camino, cuenta, voces, pausas y tempo de la música.
Uso:
  python3 pipeline/rapido.py --contenido trabajo/episodio.json --voces voces_ep --out trabajo/video.mp4 [--miniatura trabajo/miniatura.jpg]
Las voces que falten quedan en silencio (para probar sin voces). Escribe también <out>.tiempos.json.
"""
import argparse, json, math, os, random, subprocess, sys, wave, zlib
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

sys.path.insert(0, os.path.dirname(__file__))
from personajes import sprite, voz_sprite
from subtitulos import Subtitulos
import mundos

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
W, H, SR = 1920, 1080, 24000
FPS = int(os.environ.get('QSM_FPS', '30'))
FONT = os.path.join(RAIZ, 'fuentes', 'Poppins-%s.ttf')
BLACK = os.path.join(RAIZ, 'fuentes', 'Poppins-Black.ttf')
_fc = {}


def font(w, s):
    k = (w, s)
    if k not in _fc:
        p = BLACK if w == 'Black' and os.path.exists(BLACK) else FONT % ('Bold' if w == 'Black' else w)
        _fc[k] = ImageFont.truetype(p, s)
    return _fc[k]


ORO, BLANCO, TINTA = (255, 200, 40), (255, 255, 255), (26, 18, 64)
MAXC, NOVAC, VOZC = (255, 200, 40), (90, 215, 255), (140, 235, 110)
VERDE, ROJO = (46, 204, 113), (231, 76, 60)
VP = (960, 430)                       # punto de fuga
CARTEL = [(530, 425), (1390, 425)]    # centro final de cada cartel (izquierda / derecha)
CW, CH = 640, 400                     # tamaño final del cartel (foto)
NIVELES = [('NIVEL 1', 'CALENTANDO', (39, 174, 96)), ('NIVEL 2', '¡SE PONE DIFÍCIL!', (242, 153, 30)),
           ('NIVEL 3', '¡SOLO PARA GENIOS!', (231, 76, 60)), ('NIVEL 4', '¡MODO EXPERTO!', (155, 89, 182)),
           ('NIVEL 5', '¡CASI IMPOSIBLE!', (52, 73, 94)), ('NIVEL 6', '¡LEYENDAS!', (241, 196, 15))]


# ---------------------------------------------------------------- aceleración (pedido de Luis: sin miedo, cada vez más rápido)
class Ritmo:
    """p = avance del video (0 → 1). Todo sale de aquí."""
    def __init__(s): s.p = 0.0
    @property
    def a(s): return 1 + s.p                      # animaciones y pausas: hasta 2 veces más rápidas
    @property
    def cuenta(s): return 3.0 - 2.0 * s.p         # cuenta 3-2-1: de 3 s a 1 s
    @property
    def voz(s): return 1.08 + 0.32 * s.p          # voces: de 1,08x a 1,4x
    @property
    def musica(s): return 1.0 + 0.3 * s.p         # música: de 1x a 1,3x (sin cambiar el tono)
    @property
    def camino(s): return 1.0 + 3.5 * s.p         # velocidad del camino: hasta 4,5x (Luis: «que casi desaparezcan»)
    def pausa(s, x): return x / s.a


# ---------------------------------------------------------------- dibujo base
def ease_out(p): return 1 - (1 - p) ** 3
def ease_back(p):
    c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (p - 1) ** 3 + c1 * (p - 1) ** 2
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))


def cielo():
    """Noche del canal: degradado morado, estrellas, montañas y resplandor dorado en el horizonte."""
    y = np.linspace(0, 1, H)[:, None, None]
    top, mid = np.array([14, 8, 40]), np.array([70, 30, 120])
    g = np.where(y < VP[1] / H, top + (mid - top) * (y / (VP[1] / H)), mid * 0 + np.array([30, 16, 66]))
    img = Image.fromarray(np.broadcast_to(g, (H, W, 3)).astype(np.uint8)).convert('RGBA')
    capa = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(capa)
    r = np.random.default_rng(3)
    for _ in range(160):
        x, yy, rr = r.integers(0, W), r.integers(0, VP[1] - 40), r.uniform(0.8, 2.6)
        d.ellipse((x - rr, yy - rr, x + rr, yy + rr), fill=(255, 255, 255, int(r.integers(60, 220))))
    img = Image.alpha_composite(img, capa)
    glow = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(glow)
    d.ellipse((VP[0] - 900, VP[1] - 120, VP[0] + 900, VP[1] + 120), fill=(255, 140, 90, 120))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(60)))
    m = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(m)   # montañas
    for capa_i, (col, amp, base) in enumerate([((60, 28, 100, 255), 120, VP[1] + 2), ((40, 18, 76, 255), 70, VP[1] + 2)]):
        pts = [(0, base)]
        rr = np.random.default_rng(11 + capa_i)
        for x in range(0, W + 80, 80): pts.append((x, base - abs(np.sin(x / 260 + capa_i)) * amp * rr.uniform(0.5, 1.0)))
        pts += [(W, base)]
        d.polygon(pts, fill=col)
    img = Image.alpha_composite(img, m)
    d = ImageDraw.Draw(img)
    d.rectangle((0, VP[1], W, H), fill=(28, 14, 60))   # suelo
    for k in range(1, 14):   # brillo del suelo hacia el horizonte
        yy = VP[1] + k * k * 4; d.line([(0, yy), (W, yy)], fill=(48, 24, 96), width=1)
    return img.convert('RGB')


def py(z):   # profundidad → y en pantalla
    return VP[1] + 700 / z


def camino(img, dist):
    """Carretera en perspectiva con durmientes y postes que pasan según la distancia recorrida."""
    d = ImageDraw.Draw(img, 'RGBA')
    ab, ar = 760, 8      # semiancho abajo / arriba
    d.polygon([(VP[0] - ar, VP[1]), (VP[0] + ar, VP[1]), (VP[0] + ab, H), (VP[0] - ab, H)], fill=(52, 30, 96))
    # durmientes (tablas): cada 1 unidad de profundidad
    off = dist % 0.5
    for k in range(0, 120):
        z0 = 0.62 + k * 0.5 - off; z1 = z0 + 0.16
        if z0 <= 0.62: continue
        y0, y1 = py(z1), py(z0)
        if y1 > H + 40 or y0 - VP[1] < 1: continue
        f0, f1 = (y0 - VP[1]) / (H - VP[1]), (y1 - VP[1]) / (H - VP[1])
        w0, w1 = ar + (ab - ar) * f0 * 0.82, ar + (ab - ar) * f1 * 0.82
        luz = int(90 + 120 * min(1, f1 * 1.4))
        d.polygon([(VP[0] - w0, y0), (VP[0] + w0, y0), (VP[0] + w1, y1), (VP[0] - w1, y1)], fill=(luz // 2, luz // 4, luz, 255))
        d.line([(VP[0] - w1, y1), (VP[0] + w1, y1)], fill=(190, 140, 255, int(120 * min(1, f1 * 2))), width=max(1, int(3 * f1)))
    # rieles dorados
    for s in (-1, 1):
        for g, a in ((10, 70), (4, 255)):
            d.line([(VP[0] + s * 4, VP[1]), (VP[0] + s * ab * 0.55, H)], fill=(255, 200, 40, a), width=g)
    # postes con luz a los costados (como en el dibujo): cada 3 unidades
    off3 = dist % 3.0
    for k in range(0, 14):
        z = 0.7 + 3 * k - off3
        if z <= 0.7: continue
        f = 700 / z / (H - VP[1]); y = VP[1] + 700 / z
        if f > 1.6: continue
        alto = 900 * f
        for s in (-1, 1):
            x = VP[0] + s * (ab * 1.25) * f
            ancho = max(1, int(14 * f))
            d.line([(x, y), (x, y - alto)], fill=(20, 10, 40, 255), width=ancho)
            r = max(2, 16 * f)
            d.ellipse((x - r, y - alto - r, x + r, y - alto + r), fill=(255, 220, 120, 255))
            d.ellipse((x - 3 * r, y - alto - 3 * r, x + 3 * r, y - alto + 3 * r), fill=(255, 200, 80, 40))


# ---------------------------------------------------------------- carteles con foto
class Foto:
    def __init__(s, path, nombre, es_bandera):
        im = Image.open(path).convert('RGB'); s.bandera = es_bandera
        if es_bandera:   # bandera entera sobre blanco
            im.thumbnail((CW - 80, CH - 80), Image.LANCZOS); c = Image.new('RGB', (CW, CH), (255, 255, 255))
            c.paste(im, ((CW - im.width) // 2, (CH - im.height) // 2)); im = c
        else:
            im.thumbnail((1700, 1700), Image.LANCZOS)
            if im.height > im.width * 0.85:   # foto vertical: entera, sobre la misma foto difuminada (no cortar la torre ni las pirámides)
                fondo = ImageOps.fit(im, (1600, 1000), Image.BILINEAR).filter(ImageFilter.GaussianBlur(30))
                fondo = Image.blend(fondo, Image.new('RGB', fondo.size, (10, 6, 30)), 0.35)
                im2 = im.copy(); im2.thumbnail((1600, 1000), Image.LANCZOS)
                fondo.paste(im2, ((1600 - im2.width) // 2, (1000 - im2.height) // 2)); im = fondo
        s.src = im; s.nombre = nombre
        f = font('Black', 64); tw = ImageDraw.Draw(im).textlength(nombre, font=f)
        while tw > CW - 60 and f.size > 34: f = font('Black', f.size - 4); tw = ImageDraw.Draw(im).textlength(nombre, font=f)
        s.f, s.tw = f, tw

    def cuadro(s, w, h, zoom=1.0):
        """Foto recortada al tamaño w×h con zoom (movimiento lento)."""
        iw, ih = s.src.size; ar = w / h
        if iw / ih > ar: ch_ = ih; cw_ = ih * ar
        else: cw_ = iw; ch_ = iw / ar
        cw_ /= zoom; ch_ /= zoom
        cx, cy = iw / 2, ih * (0.5 if s.bandera else 0.44)
        x0 = clamp(cx - cw_ / 2, 0, iw - cw_); y0 = clamp(cy - ch_ / 2, 0, ih - ch_)
        return s.src.resize((max(1, int(w)), max(1, int(h))), Image.BILINEAR, box=(x0, y0, x0 + cw_, y0 + ch_))

    def tarjeta(s, w, h, zoom=1.0, borde=BLANCO, grosor=10, check=False, fichas=()):
        """Cartel completo (RGBA): marco, foto, nombre abajo, fichas MAX/NOVA y visto bueno."""
        w, h = int(w), int(h); b = grosor
        t = Image.new('RGBA', (w + 2 * b, h + 2 * b + 0), (0, 0, 0, 0)); d = ImageDraw.Draw(t)
        d.rounded_rectangle((0, 0, w + 2 * b - 1, h + 2 * b - 1), 30, fill=borde + (255,))
        ph = s.cuadro(w, h, zoom); m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), 24, fill=255)
        t.paste(ph, (b, b), m)
        esc = w / CW
        if esc > 0.25:   # nombre en franja oscura abajo
            f = font('Black', max(14, int(s.f.size * esc))); fh = int(f.size * 1.5)
            g = Image.new('RGBA', (w, fh + 30), (0, 0, 0, 0)); dg = ImageDraw.Draw(g)
            for k in range(fh + 30): dg.line([(0, k), (w, k)], fill=(10, 6, 30, int(210 * k / (fh + 30))))
            mm = Image.new('L', (w, fh + 30), 0); ImageDraw.Draw(mm).rounded_rectangle((0, -40, w - 1, fh + 29), 24, fill=255)
            g.putalpha(Image.fromarray(np.minimum(np.array(g.getchannel('A')), np.array(mm))))
            t.alpha_composite(g, (b, b + h - fh - 30))
            d = ImageDraw.Draw(t)
            d.text((b + w / 2, b + h - fh / 2 - 6), s.nombre, font=f, fill=BLANCO, anchor='mm', stroke_width=max(2, int(5 * esc)), stroke_fill=TINTA)
            x = b + w - 20 * esc
            for nom, col, sc in fichas:   # fichas MAX / NOVA (sc = escala del «pop»)
                ff = font('Black', max(12, int(46 * esc * sc))); tw = d.textlength(nom, font=ff); hh = ff.size * 1.25
                d.rounded_rectangle((x - tw - 36 * esc, b + 20 * esc, x, b + 20 * esc + hh), int(hh / 2), fill=col, outline=BLANCO, width=max(2, int(5 * esc)))
                d.text((x - tw / 2 - 18 * esc, b + 20 * esc + hh / 2), nom, font=ff, fill=TINTA, anchor='mm')
                x -= tw + 52 * esc
            if check:
                r = 56 * esc; cx, cy = b + 26 * esc + r, b + 26 * esc + r
                d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=VERDE, outline=BLANCO, width=max(2, int(6 * esc)))
                d.line([(cx - r * .45, cy + r * .02), (cx - r * .12, cy + r * .36), (cx + r * .5, cy - r * .36)], fill=BLANCO, width=max(3, int(14 * esc)), joint='curve')
        return t


def pegar_centro(fr, im, cx, cy):
    fr.paste(im, (int(cx - im.width / 2), int(cy - im.height / 2)), im)


# ---------------------------------------------------------------- corredores y retratos
class Corredores:
    ALTO = 440

    def __init__(s):
        D = os.path.join(RAIZ, 'assets', 'corredores')
        def carga(n, espejo=False):
            im = Image.open(os.path.join(D, n + '.png')).convert('RGBA')
            im = im.resize((round(im.width * s.ALTO / im.height), s.ALTO), Image.LANCZOS)
            return ImageOps.mirror(im) if espejo else im
        # MAX: una sola imagen de carrera → la otra pierna es su espejo; al hablar mira a NOVA (espejo de la de perfil)
        s.max = [carga('max'), carga('max', True)]; s.max_mira = carga('max_mira', True)
        s.nova = [carga('nova1'), carga('nova2')]; s.nova_mira = carga('nova_mira')
        s._esc = {}

    def esc(s, im, f):
        k = (id(im), round(f, 2))
        if k not in s._esc:
            if len(s._esc) > 200: s._esc.clear()
            s._esc[k] = im.resize((max(1, int(im.width * f)), max(1, int(im.height * f))), Image.BILINEAR) if abs(f - 1) > 0.005 else im
        return s._esc[k]

    def fantasma(s, im, f, a):
        k = (id(im), round(f, 2), a)
        if k not in s._esc:
            e = s.esc(im, f).copy(); al = e.getchannel('A').point(lambda v: int(v * a / 100)); e.putalpha(al); s._esc[k] = e
        return s._esc[k]

    def dibujar(s, fr, fase, xm, xn, habla_m, habla_n, fm=1.0, fn=1.0, estela=0.0):
        """fase: avance del paso (sube con la velocidad). x: centro de cada uno; f: escala (más chico = más adelante)."""
        k = int(fase) % 2
        for im, x, f, ph in ((s.nova_mira if habla_n else s.nova[k], xn, fn, 0.5), (s.max_mira if habla_m else s.max[k], xm, fm, 0.0)):
            bob = abs(math.sin(math.pi * (fase + ph))) * 14
            for j in range(3, 0, -1):   # estela: copias transparentes detrás, más grandes y más abajo (vienen de la cámara)
                if estela <= 0.05: break
                g = s.fantasma(im, f * (1 + 0.05 * j * estela), int(45 * estela / j))
                fr.paste(g, (int(x - g.width / 2), int(H + 30 - g.height - bob * f + 40 * j * estela)), g)
            e = s.esc(im, f)
            fr.paste(e, (int(x - e.width / 2), int(H + 30 - e.height - bob * f)), e)


@__import__('functools').lru_cache(maxsize=512)
def retrato(quien, pose, boca, parp):
    """Cara del personaje (de frente, con la boca animada) para la ventanita de la esquina."""
    sp, (cx, cy) = sprite(quien, pose, boca, parp)
    box = (int(cx - 165), int(cy - 150), int(cx + 165), int(cy + 180))
    c = Image.new('RGBA', (box[2] - box[0], box[3] - box[1]), (0, 0, 0, 0))
    c.paste(sp, (-box[0], -box[1]), sp)
    c = c.resize((200, 200), Image.LANCZOS)
    return ImageOps.mirror(c) if quien == 'copresentadora' else c   # se miran entre ellos


# ---------------------------------------------------------------- sonidos (todos sintetizados: sin derechos)
def tono(f, dur, vol=0.25, dec=30):
    t = np.arange(int(SR * dur)) / SR; return (vol * np.sin(2 * np.pi * f * t) * np.exp(-dec * t)).astype(np.float32)


def ruido(n, sem=1): return np.random.default_rng(sem).standard_normal(n).astype(np.float32)


def lp(x, fc):
    from scipy.signal import lfilter
    a = math.exp(-2 * math.pi * fc / SR); return lfilter([1 - a], [1, -a], x).astype(np.float32)


def sonidos():
    S = {}
    S['tick'] = tono(1500, 0.05, 0.22, 70); S['tick_hi'] = tono(2100, 0.07, 0.3, 50)
    t = np.arange(int(SR * 0.4)) / SR; n = ruido(len(t), 2)
    S['whoosh'] = (lp(n, 2500) * np.sin(np.pi * t / t[-1]) ** 2 * 0.9).astype(np.float32)
    camp = np.zeros(int(SR * 1.6), np.float32)
    for k, f in enumerate([1046.5, 1318.5, 1568.0, 2093.0]):
        st = int(k * 0.06 * SR); seg = tono(f, 1.6 - k * 0.06, 0.2, 3.2); camp[st:st + len(seg)] += seg
    S['campana'] = camp
    ap = np.zeros(int(SR * 1.6), np.float32); r = np.random.default_rng(5)
    for _ in range(140):   # aplausos: muchas palmadas cortas
        st = int(r.uniform(0, 1.2) ** 1.6 * SR); L = int(SR * r.uniform(0.008, 0.02))
        c = ruido(L, int(r.integers(1e6))) * np.exp(-np.arange(L) / (L / 4)); c = c - lp(c, 900)
        ap[st:st + L] += c * r.uniform(0.15, 0.35)
    S['aplausos'] = (ap * np.linspace(1, 0.2, len(ap))).astype(np.float32)
    t = np.arange(int(SR * 0.45)) / SR   # caída: silbido que baja
    S['cae'] = (0.18 * np.sin(2 * np.pi * np.cumsum(np.linspace(1100, 250, len(t))) / SR) * np.linspace(1, 0.4, len(t))).astype(np.float32)
    L = int(SR * 0.7); t = np.arange(L) / SR   # choque: golpe grave + ruido
    S['choque'] = (0.6 * np.sin(2 * np.pi * (70 - 30 * t) * t) * np.exp(-6 * t) + lp(ruido(L, 9), 1800) * 0.5 * np.exp(-9 * t)).astype(np.float32)
    S['tiempo'] = (tono(220, 0.55, 0.22, 4) + tono(233, 0.55, 0.22, 4)).astype(np.float32)
    S['pop'] = (0.3 * np.sin(2 * np.pi * np.cumsum(np.linspace(500, 1300, int(SR * 0.07))) / SR) * np.linspace(1, 0, int(SR * 0.07))).astype(np.float32)
    L = int(SR * 1.2); t = np.arange(L) / SR   # golpe de nivel
    S['golpe'] = (0.9 * np.sin(2 * np.pi * (55 - 15 * t) * t) * np.exp(-3 * t) + lp(ruido(L, 4), 3000) * 0.4 * np.exp(-12 * t)).astype(np.float32)
    fan = np.zeros(int(SR * 2.0), np.float32)
    for k, f in enumerate([523.25, 659.25, 783.99, 1046.5]):
        st = int(k * 0.12 * SR); seg = tono(f, 2.0 - k * 0.12, 0.2, 2.5); fan[st:st + len(seg)] += seg
    S['fanfarria'] = fan
    return S


def riser(dur):
    """Subida de tensión durante la cuenta: ruido filtrado que se abre + tono que sube."""
    L = int(SR * dur); t = np.arange(L) / SR; u = t / max(dur, 1e-3)
    n = ruido(L, 7); out = np.zeros(L, np.float32); B = 2400
    for a in range(0, L, B):   # filtro que se abre por bloques
        out[a:a + B] = lp(n[a:a + B], 400 + 5000 * u[a] ** 2)
    sw = np.sin(2 * np.pi * np.cumsum(300 + 900 * u ** 2) / SR)
    return ((out * 0.35 + sw * 0.06) * u ** 1.5).astype(np.float32)


# ---------------------------------------------------------------- audio de voces
def leer(path, tempo=1.0):
    af = ['-af', f'atempo={tempo:.3f}'] if abs(tempo - 1) > 0.005 else []
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, *af, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def niveles_boca(arr):
    hop = SR // FPS; n = max(1, len(arr) // hop)
    env = np.array([np.sqrt(np.mean(arr[i * hop:(i + 1) * hop] ** 2) + 1e-9) for i in range(n)])
    ref = max(np.percentile(env, 92), 1e-4)
    lv = np.clip(np.round(env / ref * 4), 0, 4).astype(int); lv[env < 0.012] = 0
    return lv


# ---------------------------------------------------------------- programa
class Show:
    def __init__(s, meta, voces, raiz=RAIZ):
        s.m = meta; s.Q = meta['preguntas']; s.N = len(s.Q); s.voces = voces
        s.sem = sum(map(ord, meta.get('id', 'rapido')))
        s.R = Ritmo(); s.S = sonidos(); s.t = 0.0
        s.audio, s.habla, s.esc = [], [], []        # (t, arr) · (t0, t1, quien, lv) · (t0, t1, fn)
        s.cuentas, s.drops = [], []                 # tramos con música apagada (filtro) y cortes de nivel
        s.tempos = []                               # (t, tempo de música)
        s.faltan = []
        s.vel = []                                  # (t, velocidad del camino) para integrar la distancia
        s.cambios = []                              # (inicio del portal, cambio de mundo, mundo nuevo)
        s.banco = os.path.join(raiz, 'banco', 'rapido'); s.TXT = {}
        for f in (os.path.join(s.banco, 'indice.json'), os.path.join(voces, 'indice.json') if voces else ''):
            if f and os.path.exists(f): s.TXT.update({k: v.get('texto', '') for k, v in json.load(open(f, encoding='utf-8')).items()})
        s.uso = {}; s.rr = random.Random(s.sem * 31 + 7); s.rc = random.Random(s.sem * 13 + 5)
        s.subs = Subtitulos(W, H, FPS, BLACK, FONT % 'Bold', 330, W - 330, 1000)

    # ---- voces
    def clip(s, clave, est=''):
        """Devuelve (audio, texto, quien) de una clave del episodio o del banco (las variantes rotan)."""
        quien = {'pr': 'presentador', 'co': 'copresentadora'}.get(clave[:2], 'anunciador')
        vs = sorted(f for f in os.listdir(s.banco) if f.startswith(clave + '__') and f.endswith('.wav')) if os.path.isdir(s.banco) else []
        if vs:
            k = (s.sem + s.uso.get(clave, 0) * 7) % len(vs); s.uso[clave] = s.uso.get(clave, 0) + 1
            p = os.path.join(s.banco, vs[k]); return leer(p, s.R.voz), s.TXT.get(vs[k][:-4], est), quien
        txt = (s.m.get('extra_tts', {}).get(clave) or [None, ''])[1] or est or s.TXT.get(clave, '')
        p = os.path.join(s.voces, clave + '.wav') if s.voces else ''
        if p and os.path.exists(p): return leer(p, s.R.voz), txt, quien
        s.faltan.append(clave); return np.zeros(int(SR * max(0.6, len(txt) / 16 / s.R.voz)), np.float32), txt, quien

    def decir(s, clave, at, est=''):
        arr, txt, quien = s.clip(clave, est)
        s.audio.append((at, arr)); lv = niveles_boca(arr)
        s.habla.append((at, at + len(arr) / SR, quien, lv))
        if txt: s.subs.agregar(at, lv, quien, txt, '')   # Luis: subtítulos de TODO lo que dicen
        return at + len(arr) / SR

    def son(s, k, at, g=1.0): s.audio.append((at, s.S[k] * g))

    def boca(s, t, quien):
        for t0, t1, q, lv in s.habla:
            if q == quien and t0 <= t < t1: return int(lv[min(len(lv) - 1, int((t - t0) * FPS))])
        return 0

    def hablando(s, t, quien):
        return any(q == quien and t0 - 0.1 <= t < t1 + 0.25 for t0, t1, q, lv in s.habla)

    def variante_pick(s, quien, lado): return f"{'pr' if quien == 'presentador' else 'co'}_{'izq' if lado == 0 else 'der'}"

    # ---- guion
    def armar(s):
        Q, N, R = s.Q, s.N, s.R
        cada = int(s.m.get('niveles_cada', 25)); sus_en = s.m.get('suscripcion_en', 50)
        pts = [0, 0]; s.pts_t = []      # (t, max, nova)
        s.tiempos, s.capitulos, s.apuestas = [], [], {}
        s.fotos = {}
        for q in Q:
            s.fotos[q['n']] = [Foto(os.path.join(RAIZ, q["o_img"][i]), q['o'][i], q['o_img'][i].endswith('.png')) for i in range(2)]
        s.son('whoosh', 0.0, 0.8)
        sin_chacota = 0
        for idx, q in enumerate(Q):
            R.p = idx / max(1, N - 1); n = q['n']; nivel = idx // cada
            s.tempos.append((s.t, R.musica)); s.vel.append((s.t, R.camino))
            if idx % cada == 0:
                s.capitulos.append((s.t, f"{NIVELES[min(nivel, 5)][0].title()}: {NIVELES[min(nivel, 5)][1].strip('¡!').capitalize()}"))
                if idx:   # portal al mundo nuevo, golpe y «drop» de la música, cartel del nivel
                    t0 = s.t; tp = t0 + 0.9; s.cambios.append((t0, tp, min(nivel, 5)))
                    s.son('whoosh', t0, 1.0); s.son('whoosh', t0 + 0.45, 1.0)
                    s.drops.append(tp); s.son('golpe', tp, 1.0)
                    fin = s.decir(f'an_nivel_{min(nivel, 5) + 1}', tp + 0.15)
                    s.esc.append((t0, fin + R.pausa(0.5), ('nivel', nivel)))
                    s.t = fin + R.pausa(0.5)
            if n == sus_en and idx:   # MAX en broma: suscríbanse (mira a NOVA y al público)
                t0 = s.t; fin = s.decir('pr_suscribe', t0 + 0.1)
                s.esc.append((t0, fin + 0.3, ('suscribe',))); s.son('pop', t0 + 0.1); s.t = fin + 0.3
            # 1) llegan los carteles
            t_abre = s.t; lleg = R.pausa(0.7)
            s.son('whoosh', t_abre, 0.9)
            ini = t_abre + R.pausa(0.25)
            if idx == 0: ini = s.decir('an_arranque', t_abre + 0.2) + 0.1   # «¡Diez preguntas! ¿Cuántas aciertas? ¡Vamos!»
            fin_p = s.decir(f'q{n:02d}_pregunta', max(ini, t_abre + lleg * 0.6), q['tp'])
            # 2) cuenta 3-2-1 (cada vez más corta)
            tc = fin_p + R.pausa(0.12); dc = R.cuenta
            for k in range(3): s.son('tick_hi' if k == 2 else 'tick', tc + k * dc / 3, 0.9)
            s.audio.append((tc, riser(dc))); s.cuentas.append((tc, tc + dc))
            tt = tc + dc
            s.son('tiempo', tt, 0.8)
            fin_t = s.decir('an_tiempo', tt + 0.05)
            # 3) MAX y NOVA eligen
            dif = min(5, nivel)
            ap = {}
            for k, pr in (('presentador', [0.72, 0.66, 0.62, 0.58, 0.55, 0.52][dif]), ('copresentadora', [0.70, 0.66, 0.6, 0.57, 0.55, 0.52][dif])):
                ap[k] = q['c'] if s.rr.random() < pr else 1 - q['c']
            s.apuestas[str(n)] = [ap['presentador'], ap['copresentadora']]
            t_m = fin_t + R.pausa(0.05); s.son('pop', t_m)
            fin_m = s.decir(s.variante_pick('presentador', ap['presentador']), t_m)
            t_n = fin_m + R.pausa(0.05) - (0.25 if R.p > 0.5 else 0); s.son('pop', t_n)   # al final casi se pisan
            fin_n = s.decir(s.variante_pick('copresentadora', ap['copresentadora']), t_n)
            # 4) revelación
            tr = max(fin_m, fin_n) + R.pausa(0.15)
            s.son('campana', tr, 0.9); s.son('aplausos', tr + 0.05, 0.8); s.son('cae', tr + 0.05, 0.9); s.son('choque', tr + R.pausa(0.5), 0.9)
            pts[0] += ap['presentador'] == q['c']; pts[1] += ap['copresentadora'] == q['c']
            s.pts_t.append((tr + 0.2, pts[0], pts[1]))
            fin_r = s.decir(f'q{n:02d}_respuesta', tr + R.pausa(0.3), q['tr'])
            fin = fin_r + R.pausa(0.35)
            # 5) chacota (1 de cada 3-4)
            sin_chacota += 1
            m_ok, n_ok = ap['presentador'] == q['c'], ap['copresentadora'] == q['c']
            if sin_chacota >= 3 and (s.rc.random() < 0.55 or sin_chacota >= 4) and idx < N - 1:
                sin_chacota = 0
                if m_ok and not n_ok: cl = 'pr_chacota'
                elif n_ok and not m_ok: cl = 'co_chacota'
                elif m_ok: cl = s.rc.choice(['pr_ambos_bien', 'co_ambos_bien'])
                else: cl = s.rc.choice(['pr_ambos_mal', 'co_ambos_mal'])
                fin = s.decir(cl, fin_r + R.pausa(0.15)) + R.pausa(0.2)
            s.esc.append((t_abre, fin, ('pregunta', idx, dict(lleg=lleg, tc=tc, dc=dc, tt=tt, t_m=t_m, t_n=t_n, tr=tr, ap=ap))))
            s.tiempos.append({'n': n, 'abre': round(t_abre, 2), 'reloj': round(tc, 2), 'cierra': round(tt, 2)})
            s.t = fin
        # final
        R.p = 1.0
        t0 = s.t; s.son('fanfarria', t0, 0.9); s.capitulos.append((t0, 'Resultado: MAX contra NOVA'))
        if pts[0] == pts[1]: pts[1] += 1   # sin empates
        s.pts_t.append((t0, pts[0], pts[1]))
        fin = s.decir('an_final', t0 + 0.3)
        fin = s.decir('pr_gana' if pts[0] > pts[1] else 'co_gana', fin + 0.15)
        s.esc.append((t0, fin + 1.6, ('final', pts[0] > pts[1])))
        s.t = fin + 1.6; s.vel.append((t0, 0.6)); s.tempos.append((t0, 1.3))
        s.final_pts = tuple(pts)
        # distancia recorrida del camino (integral de la velocidad)
        n_fr = int(s.t * FPS) + 2; v = np.zeros(n_fr)
        for i, (t, vv) in enumerate(s.vel):
            a = int(t * FPS); b = int(s.vel[i + 1][0] * FPS) if i + 1 < len(s.vel) else n_fr
            v[a:b] = vv
        s.velk = v
        s.dist = np.cumsum(v * 2.5 / FPS)   # 6 durmientes por segundo al inicio
        s.paso = np.cumsum(v * 3.2 / FPS)   # pasos por segundo de los corredores

    # ---- pantallas
    def marcador_en(s, t):
        m = (0, 0); pop = [0, 0]
        for k, (tt, a, b) in enumerate(s.pts_t):
            if t >= tt:
                prev = s.pts_t[k - 1][1:] if k else (0, 0)
                if t - tt < 0.35: pop = [a > prev[0], b > prev[1]]
                m = (a, b)
        return m, pop

    def hud(s, fr, t, n_actual, nivel, pregunta=None):
        d = ImageDraw.Draw(fr)
        if pregunta:   # banda de la pregunta
            f = font('Black', 64); tw = d.textlength(pregunta, font=f)
            while tw > 1180 and f.size > 36: f = font('Black', f.size - 4); tw = d.textlength(pregunta, font=f)
            d.rounded_rectangle((W / 2 - tw / 2 - 40, 26, W / 2 + tw / 2 + 40, 126), 50, fill=(18, 10, 46), outline=ORO, width=4)
            d.text((W / 2, 76), pregunta, font=f, fill=BLANCO, anchor='mm')
        # contador · nivel · racha
        nv = NIVELES[min(nivel, 5)]
        piezas = [(f'{n_actual}/{s.N}', ORO, TINTA), (f"{nv[0]} · {mundos.MUNDOS[min(nivel, 5)]['nombre']}", nv[2], BLANCO), ('¿Cuántas llevas seguidas?', (18, 10, 46), BLANCO)]
        f = font('Bold', 30); anchos = [d.textlength(p, font=f) + 44 for p, _, _ in piezas]; anchos[2] += 40
        x = W / 2 - (sum(anchos) + 20 * 2) / 2
        for (txt, bg, fg), w in zip(piezas, anchos):
            d.rounded_rectangle((x, 146, x + w, 194), 24, fill=bg, outline=(255, 255, 255) if bg == (18, 10, 46) else None, width=2)
            tx = x + 22
            if txt.startswith('¿'):   # llamita
                fx, fy = x + 30, 170
                d.polygon([(fx, fy - 18), (fx + 11, fy - 2), (fx + 8, fy + 14), (fx - 8, fy + 14), (fx - 11, fy - 2)], fill=(255, 120, 30))
                d.polygon([(fx, fy - 6), (fx + 5, fy + 4), (fx, fy + 13), (fx - 5, fy + 4)], fill=(255, 220, 80)); tx += 30
            d.text((tx, 170), txt, font=f, fill=fg, anchor='lm'); x += w + 20
        # ventanitas de MAX y NOVA (cara de frente + marcador)
        (pm, pn), pop = s.marcador_en(t)
        for quien, nom, col, pts_, x0, pp in (('presentador', 'MAX', MAXC, pm, 24, pop[0]), ('copresentadora', 'NOVA', NOVAC, pn, W - 24 - 230, pop[1])):
            hab = s.hablando(t, quien)
            d.rounded_rectangle((x0, 20, x0 + 230, 290), 26, fill=(18, 10, 46), outline=col, width=6 if hab else 3)
            b = s.boca(t, quien); k = int(t * FPS) + (17 if quien == 'copresentadora' else 0)
            pose = s.pose.get(quien, 'base')
            fr.paste(*(lambda r: (r, (x0 + 15, 30), r))(retrato(quien, pose, b, (k % 61) in (0, 1))))
            sc = 1.35 if pp else 1.0
            f2 = font('Black', int(40 * sc)); d = ImageDraw.Draw(fr)
            d.rounded_rectangle((x0 + 10, 232, x0 + 220, 282), 25, fill=col)
            d.text((x0 + 115, 257), f'{nom} {pts_}', font=f2, fill=TINTA, anchor='mm')

    def centro(s, fr, t, cont):
        """Círculo en el punto de fuga: LA VOZ (cuando habla), la cuenta 3-2-1 o «¡TIEMPO!»."""
        d = ImageDraw.Draw(fr); cx, cy = VP[0], VP[1] - 20
        if cont is not None:
            txt, col, sc = cont
            r = 92 * sc
            d.ellipse((cx - r - 8, cy - r - 8, cx + r + 8, cy + r + 8), fill=BLANCO)
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)
            d.text((cx, cy + 4), txt, font=font('Black', int((110 if len(txt) < 3 else 34) * sc)), fill=BLANCO, anchor='mm')
            return
        b = s.boca(t, 'anunciador')
        if s.hablando(t, 'anunciador'):
            sp = voz_sprite(b, int(t * 12) % 12 if b else 0).resize((240, 240), Image.BILINEAR)
            pegar_centro(fr, sp, cx, cy)

    def frame(s, k):
        t = k / FPS
        kk = min(k, len(s.dist) - 1); vel = float(s.velk[kk])
        mi = 0; por = None
        for a0, a1, nuevo in s.cambios:
            if t >= a1: mi = nuevo
            elif t >= a0: por = ((t - a0) / (a1 - a0), nuevo)
        fr = mundos.cielo(mi).copy(); mundos.camino(fr, s.dist[kk], mi, t, vel)
        mundos.particulas(fr, mi, t, vel)
        fuerza = clamp((vel - 1.8) / 2.4)
        mundos.lineas_velocidad(fr, t, fuerza)
        if por: mundos.portal(fr, min(por[0], 0.85), por[1])
        esc = None
        for e in s.esc:
            if e[0] <= t < e[1]: esc = e; break
        s.pose = {'presentador': 'base', 'copresentadora': 'base'}
        xm, xn, fm, fn = 690.0, 1230.0, 1.0, 1.0
        n_actual, nivel, preg, cont = 1, 0, None, None
        if esc and esc[2][0] == 'pregunta':
            idx, P = esc[2][1], esc[2][2]; q = s.Q[idx]; n_actual = idx + 1; nivel = idx // int(s.m.get('niveles_cada', 25))
            lt = t - esc[0]; a = 1 + idx / max(1, s.N - 1); preg = q['p']; fotos = s.fotos[q['n']]
            pl = clamp(lt / P['lleg']); e = ease_back(pl)
            zoom = 1.0 + 0.12 * clamp((t - esc[0]) / max(0.1, P['tt'] - esc[0]))
            ap = P['ap']; tr = P['tr']
            if t < P['tc']: s.pose = {'presentador': 'senala', 'copresentadora': 'presenta'}
            elif t < P['tt']: s.pose = {'presentador': 'piensa', 'copresentadora': 'base'}
            elif t < tr: s.pose = {'presentador': 'frente', 'copresentadora': 'presenta'}
            else:
                m_ok, n_ok = ap['presentador'] == q['c'], ap['copresentadora'] == q['c']
                s.pose = {'presentador': 'celebra' if m_ok else 'piensa', 'copresentadora': 'celebra' if n_ok else 'sorpresa'}
            # corredores se cambian de carril hacia el lado que eligieron
            for quien, t0 in (('presentador', P['t_m']), ('copresentadora', P['t_n'])):
                u = ease_out(clamp((t - t0) / (0.35 / a)))
                lado = ap[quien]; dx = (-190 if lado == 0 else 190) * u
                if quien == 'presentador': xm = 690 + dx - (60 * u if lado == 1 else 0)
                else: xn = 1230 + dx + (60 * u if lado == 0 else 0)
            for i in (0, 1):
                fx, fy = CARTEL[i]
                cx = VP[0] + (fx - VP[0]) * e; cy = VP[1] + (fy - VP[1]) * e; sc = max(0.04, e)
                fichas = []
                for quien, nom, col, t0 in (('presentador', 'MAX', MAXC, P['t_m']), ('copresentadora', 'NOVA', NOVAC, P['t_n'])):
                    if t >= t0 and ap[quien] == i:
                        u = clamp((t - t0) / 0.18); fichas.append((nom, col, 1 + 0.6 * math.sin(math.pi * u) if u < 1 else 1.0))
                ok = i == q['c']; ang = 0; borde = BLANCO; check = False
                if t >= tr:
                    u = ease_out(clamp((t - tr) / (0.45 / a)))
                    if ok:   # el correcto se agranda hasta casi llenar la pantalla
                        sc = 1 + 0.5 * u; cx = cx + (W / 2 - cx) * u; cy = cy + (525 - cy) * u
                        borde = VERDE; check = True
                    else:    # el otro se cae
                        g = clamp((t - tr) / (0.7 / a)); cy += 1100 * g * g; ang = (-1 if i == 0 else 1) * 35 * g; sc *= (1 - 0.2 * g)
                if cy - CH * sc / 2 > H: continue
                card = fotos[i].tarjeta(CW * sc, CH * sc, zoom, borde, max(2, int(12 * sc)), check, fichas)
                if ang: card = card.rotate(ang, Image.BILINEAR, expand=True)
                if sc > 0.3 and not ang:   # sombra suave
                    sh = Image.new('RGBA', card.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((10, 18, card.width - 10, card.height), 30, fill=(0, 0, 0, 110))
                    pegar_centro(fr, sh.filter(ImageFilter.GaussianBlur(14)), cx, cy + 10)
                pegar_centro(fr, card, cx, cy)
            if P['tc'] <= t < P['tt']:
                k3 = min(2, int((t - P['tc']) / (P['dc'] / 3))); u = ((t - P['tc']) / (P['dc'] / 3)) % 1
                cont = (str(3 - k3), ORO if k3 < 2 else ROJO, 1 + 0.35 * max(0, 1 - u * 4))
            elif P['tt'] <= t < P['t_m'] + 0.2:
                cont = ('¡TIEMPO!', ROJO, 1.0 + 0.2 * max(0, 1 - (t - P['tt']) * 5))
        elif esc and esc[2][0] == 'nivel':
            nivel = esc[2][1] if t >= esc[0] + 0.9 else esc[2][1] - 1; n_actual = esc[2][1] * int(s.m.get('niveles_cada', 25)) + 1
        elif esc and esc[2][0] == 'final':
            n_actual = s.N; nivel = (s.N - 1) // int(s.m.get('niveles_cada', 25))
            gana_max = esc[2][1]
            s.pose = {'presentador': 'celebra2' if gana_max else 'piensa', 'copresentadora': 'sorpresa' if gana_max else 'celebra'}
        elif esc and esc[2][0] == 'suscribe':
            for i, e in enumerate(s.esc):
                if e is esc: nxt = next((x for x in s.esc[i + 1:] if x[2][0] == 'pregunta'), None)
            n_actual = nxt[2][1] + 1 if nxt else 1; s.pose = {'presentador': 'saluda', 'copresentadora': 'aplaude'}
        # corredores (de espaldas; al hablar giran la cabeza)
        s.corr.dibujar(fr, s.paso[min(k, len(s.paso) - 1)], xm, xn, s.hablando(t, 'presentador'), s.hablando(t, 'copresentadora'), fm, fn, fuerza)
        s.centro(fr, t, cont)
        if esc and esc[2][0] == 'nivel':
            nv = NIVELES[min(esc[2][1], 5)]; u = clamp((t - esc[0] - 0.9) / 0.25); sc = max(0.01, ease_back(u)) if u > 0 else 0
            if sc > 0.02:
                d = ImageDraw.Draw(fr); f = font('Black', max(10, int(170 * sc))); f2 = font('Black', max(10, int(80 * sc)))
                d.text((W / 2, 400), nv[0], font=f, fill=nv[2], anchor='mm', stroke_width=12, stroke_fill=BLANCO)
                d.text((W / 2, 545), mundos.MUNDOS[min(esc[2][1], 5)]['nombre'], font=f2, fill=ORO, anchor='mm', stroke_width=8, stroke_fill=TINTA)
                d.text((W / 2, 650), nv[1], font=f2, fill=BLANCO, anchor='mm', stroke_width=8, stroke_fill=TINTA)
        if esc and esc[2][0] == 'suscribe':
            u = clamp((t - esc[0]) / 0.25); sc = max(0.05, ease_back(u)); d = ImageDraw.Draw(fr)
            w, h = 560 * sc, 130 * sc
            d.rounded_rectangle((W / 2 - w / 2, 420 - h / 2, W / 2 + w / 2, 420 + h / 2), int(h / 2), fill=(230, 33, 23), outline=BLANCO, width=6)
            d.text((W / 2, 420), 'SUSCRÍBETE', font=font('Black', max(10, int(72 * sc))), fill=BLANCO, anchor='mm')
        if esc and esc[2][0] == 'final':
            u = clamp((t - esc[0]) / 0.3); sc = max(0.05, ease_back(u)); d = ImageDraw.Draw(fr)
            pm, pn = s.final_pts
            d.text((W / 2, 400), '¡SE ACABÓ!', font=font('Black', max(10, int(150 * sc))), fill=ORO, anchor='mm', stroke_width=10, stroke_fill=TINTA)
            d.text((W / 2, 545), f'MAX {pm}  ·  NOVA {pn}', font=font('Black', max(10, int(80 * sc))), fill=BLANCO, anchor='mm', stroke_width=8, stroke_fill=TINTA)
            d.text((W / 2, 660), '¿Cuántas sacaste? Escríbelo abajo', font=font('Black', max(10, int(56 * sc))), fill=BLANCO, anchor='mm', stroke_width=6, stroke_fill=TINTA)
            ax = W / 2; ay = 730   # flecha hacia abajo
            d.polygon([(ax - 40, ay), (ax + 40, ay), (ax + 40, ay + 40), (ax + 75, ay + 40), (ax, ay + 110), (ax - 75, ay + 40), (ax - 40, ay + 40)], fill=ORO)
        s.hud(fr, t, n_actual, nivel, preg)
        st = s.subs.estado(t)
        if st: s.subs.dibujar(fr, st)
        if por and por[0] > 0.8:   # destello del portal
            fr.paste(Image.new('RGB', (W, H), (255, 255, 255)), (0, 0), Image.new('L', (W, H), int(255 * min(1, (por[0] - 0.8) / 0.2))))
        for a0, a1, nuevo in s.cambios:
            if a1 <= t < a1 + 0.3: fr.paste(Image.new('RGB', (W, H), (255, 255, 255)), (0, 0), Image.new('L', (W, H), int(255 * (1 - (t - a1) / 0.3))))
        if fuerza > 0.25:   # sacudida de cámara a toda velocidad
            r = random.Random(k); dx, dy = int(r.uniform(-1, 1) * 7 * fuerza), int(r.uniform(-1, 1) * 5 * fuerza)
            fr = fr.transform(fr.size, Image.AFFINE, (1, 0, dx, 0, 1, dy), Image.BILINEAR)
        return fr

    # ---- audio
    def musica(s, mix):
        """Música alta todo el video, cada vez más rápida (atempo por tramos, sin cambiar el tono), apagada
        (filtro) durante la cuenta y con «drop» antes de cada nivel. Sin la carpeta de música: sin música."""
        from musica import carpeta_musica, MusicaArchivos
        cm = carpeta_musica(RAIZ)
        if not cm or os.environ.get('QSM_SIN_MUSICA'): print('Sin música (falta assets/musica)'); return mix
        M = MusicaArchivos(cm, s.sem); L = len(M.lista); n = len(mix)
        out = np.zeros(n, np.float32); pos = float(M.ini); X = int(0.04 * SR)
        tramos = s.tempos + [(s.t, 1.0)]
        tmp = '/tmp/qsm_mus.f32'
        for i in range(len(tramos) - 1):
            t0, tempo = tramos[i]; t1 = tramos[i + 1][0]
            a, b = int(t0 * SR), min(n, int(t1 * SR) + X)
            if b <= a: continue
            pre = int(0.25 * SR); need = int((b - a + pre) * tempo) + SR
            idx = (np.arange(need) + int(pos) - int(pre * tempo)) % L
            M.lista[idx].astype(np.float32).tofile(tmp)
            raw = subprocess.run(['ffmpeg', '-v', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', tmp, '-af', f'atempo={tempo:.3f}',
                                  '-f', 'f32le', '-'], check=True, capture_output=True).stdout
            y = np.frombuffer(raw, np.float32)[pre:pre + (b - a)]
            if len(y) < b - a: y = np.pad(y, (0, b - a - len(y)))
            if a > 0:   # fundido cruzado corto con el tramo anterior
                f = np.linspace(0, 1, min(X, len(y)), dtype=np.float32); y = y.copy(); y[:len(f)] *= f
                out[a:a + len(f)] *= (1 - f)
            out[a:b] += y
            pos += (t1 - t0) * SR * tempo
        # nivel respecto a la voz
        voz = np.zeros(n, bool)
        for t0, t1, q, lv in s.habla: voz[int(t0 * SR):int(t1 * SR)] = True
        ref = max(float(np.sqrt(np.mean(mix[voz][::50] ** 2))) if voz.any() else 0.1, 0.02)
        g = 10 ** (float(os.environ.get('QSM_RAPIDO_MUSICA_DB', '-1')) / 20) * ref
        env = np.ones(n, np.float32)
        for a_, b_ in s.cuentas:   # durante la cuenta: música «ahogada» que se libera en la revelación
            A, B = int(a_ * SR), min(n, int(b_ * SR)); seg = out[A:B]
            if len(seg) > 10: out[A:B] = lp(seg, 650) * 1.25
        for td in s.drops:          # «drop»: silencio corto antes del golpe del nivel
            A = int((td - 0.35) * SR); B = int(td * SR)
            if A > 0: env[A:B] = np.linspace(1, 0, B - A) ** 2
        fd = int(0.3 * SR); env[:fd] *= np.linspace(0, 1, fd); fo = int(2.0 * SR); env[n - fo:] *= np.linspace(1, 0, fo)
        mix += out * env * g
        return mix

    def render(s, out, tmp):
        os.makedirs(tmp, exist_ok=True)
        s.corr = Corredores(); s.subs.cerrar()
        nfr = int(s.t * FPS); vid = os.path.join(tmp, 'video.mp4')
        ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                               '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', vid], stdin=subprocess.PIPE)
        import time; t0 = time.time()
        for k in range(nfr):
            ff.stdin.write(s.frame(k).convert('RGB').tobytes())
            if k % (FPS * 30) == 0: print(f'  {k / FPS / 60:.1f}/{s.t / 60:.1f} min · {(time.time() - t0) / 60:.1f} min de render', flush=True)
        ff.stdin.close(); ff.wait()
        mix = np.zeros(int(SR * (s.t + 0.5)), np.float32)
        for at, a in s.audio:
            st = int(at * SR); e = min(len(mix), st + len(a))
            if e > st: mix[st:e] += a[:e - st]
        mix = s.musica(mix)
        pk = np.abs(mix).max()
        if pk > 0.98: mix *= 0.98 / pk
        wav = os.path.join(tmp, 'audio.wav')
        with wave.open(wav, 'w') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype(np.int16).tobytes())
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', vid, '-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                        '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', '48000', '-ac', '2', '-c:a', 'aac', '-b:a', '192k',
                        '-shortest', '-movflags', '+faststart', out], check=True)


def miniatura(meta, out):
    """Dos fotos partidas + «¿A o B?» al centro + cantidad de preguntas (provisional: la buena la hace Luis en Flow)."""
    q = next((x for x in meta['preguntas'] if x.get('o_img')), None)
    img = Image.new('RGB', (1280, 720), (18, 10, 46))
    if q:
        for i in (0, 1):
            f = Foto(os.path.join(RAIZ, q["o_img"][i]), q['o'][i], q['o_img'][i].endswith('.png'))
            img.paste(f.cuadro(640, 720, 1.0), (i * 640, 0))
    d = ImageDraw.Draw(img); d.rectangle((632, 0, 648, 720), fill=BLANCO)
    d.ellipse((640 - 190, 360 - 190, 640 + 190, 360 + 190), fill=ROJO, outline=BLANCO, width=12)
    d.text((640, 350), '¿A o B?', font=font('Black', 110), fill=BLANCO, anchor='mm', stroke_width=6, stroke_fill=TINTA)
    d.text((640, 640), f"{len(meta['preguntas'])} PREGUNTAS", font=font('Black', 80), fill=ORO, anchor='mm', stroke_width=8, stroke_fill=TINTA)
    img.save(out, quality=92)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--contenido', required=True); ap.add_argument('--voces', default='')
    ap.add_argument('--out', required=True); ap.add_argument('--tmp', default='tmp'); ap.add_argument('--miniatura')
    ap.add_argument('--cuadros', help='solo guardar estos segundos como JPG (prueba), p. ej. 1,5,9')
    a = ap.parse_args()
    meta = json.load(open(a.contenido, encoding='utf-8'))
    meta['preguntas'] = [q for q in meta['preguntas'] if q.get('o_img')]
    S = Show(meta, a.voces); S.armar()
    print(f'Duración: {S.t / 60:.2f} min · {S.N} preguntas · MAX {S.final_pts[0]} - NOVA {S.final_pts[1]}')
    sync = {'formato': 'rapido', 'ya': 0, 'total': S.N, 'duracion': round(S.t, 2), 'tiempos': S.tiempos, 'apuestas': S.apuestas,
            'capitulos': [[round(t, 1), c] for t, c in S.capitulos], 'faltan': sorted(set(S.faltan))}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(sync, open(os.path.splitext(a.out)[0] + '.tiempos.json', 'w'), ensure_ascii=False, indent=1)
    if S.faltan: print('Voces faltantes (silencio):', sorted(set(S.faltan)))
    if a.miniatura: miniatura(meta, a.miniatura)
    if a.cuadros:
        S.corr = Corredores(); S.subs.cerrar()
        for sec in a.cuadros.split(','):
            S.frame(int(float(sec) * FPS)).save(os.path.join(a.tmp, f'cuadro_{sec}.jpg'), quality=85)
        return
    S.render(a.out, a.tmp); print('OK', a.out)


if __name__ == '__main__':
    main()
