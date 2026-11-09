"""Mundos del formato rápido «¿A o B?» (9-nov-2026, idea de Luis: como en un videojuego, cada nivel es un camino nuevo).
Todo dibujado con código (sin créditos ni derechos): cielo, suelo, camino en perspectiva, objetos a los costados
y partículas. Al subir de nivel se cruza un portal. Con la velocidad aparecen líneas de velocidad y sacudida.
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1920, 1080
VP = (960, 430)

# cielo_arriba, cielo_horizonte, resplandor, suelo, camino, durmiente, borde_durmiente, riel, objeto, partículas
MUNDOS = [
    dict(nombre='PISTA', cielo=((14, 8, 40), (70, 30, 120)), brillo=(255, 140, 90), suelo=(28, 14, 60), camino=(52, 30, 96),
         dur=(105, 52, 210), borde=(190, 140, 255), riel=(255, 200, 40), montes=((60, 28, 100), (40, 18, 76)), obj='farol', part=None, estrellas=True),
    dict(nombre='DESIERTO', cielo=((250, 140, 90), (255, 210, 140)), brillo=(255, 240, 200), suelo=(214, 160, 100), camino=(190, 140, 90),
         dur=(120, 78, 44), borde=(80, 50, 26), riel=(150, 150, 160), montes=((190, 110, 90), (160, 90, 80)), obj='cactus', part='polvo', estrellas=False),
    dict(nombre='SELVA', cielo=((20, 60, 40), (90, 160, 90)), brillo=(220, 255, 170), suelo=(24, 70, 34), camino=(80, 60, 40),
         dur=(110, 80, 50), borde=(60, 40, 24), riel=(200, 180, 90), montes=((30, 90, 50), (20, 70, 40)), obj='arbol', part='luciernagas', estrellas=False),
    dict(nombre='HIELO', cielo=((90, 150, 220), (200, 230, 250)), brillo=(255, 255, 255), suelo=(225, 240, 250), camino=(150, 200, 235),
         dur=(190, 225, 250), borde=(110, 170, 220), riel=(80, 120, 170), montes=((170, 200, 230), (140, 175, 215)), obj='pino', part='nieve', estrellas=False),
    dict(nombre='VOLCÁN', cielo=((40, 6, 6), (170, 40, 20)), brillo=(255, 120, 30), suelo=(30, 18, 16), camino=(60, 40, 36),
         dur=(90, 50, 40), borde=(255, 110, 30), riel=(255, 160, 40), montes=((70, 20, 16), (45, 12, 10)), obj='lava', part='chispas', estrellas=False),
    dict(nombre='ESPACIO', cielo=((2, 2, 12), (20, 10, 50)), brillo=(120, 160, 255), suelo=(4, 4, 16), camino=(10, 20, 60),
         dur=(40, 120, 255), borde=(140, 220, 255), riel=(90, 230, 255), montes=None, obj='planeta', part='estrellas', estrellas=True),
]


VARIANTES = [('', None), ('DE NOCHE', ((10, 12, 40), 0.55)), ('DORADO', ((255, 180, 60), 0.32)), ('NEÓN', ((255, 40, 200), 0.3)), ('INFINITO', ((60, 255, 220), 0.3))]


def _tinte(c, tinte):
    if not tinte or not isinstance(c, tuple) or not c or not isinstance(c[0], (int, float)): return c
    col, a = tinte; return tuple(int(v * (1 - a) + w * a) for v, w in zip(c, col))


_MS = {}
def mundo(k):
    """Nivel k (0, 1, 2, … sin límite): los 6 mundos se repiten con otra variante (de noche, dorado, neón, infinito)."""
    if k not in _MS:
        base = MUNDOS[k % 6]; nom, tinte = VARIANTES[(k // 6) % len(VARIANTES)]
        m = dict(base)
        for key in ('cielo', 'montes'):
            if m[key]: m[key] = tuple(_tinte(c, tinte) for c in m[key])
        for key in ('brillo', 'suelo', 'camino', 'dur', 'borde', 'riel'): m[key] = _tinte(m[key], tinte)
        if nom == 'DE NOCHE': m['estrellas'] = True
        m['nombre'] = (base['nombre'] + ' ' + nom).strip()
        _MS[k] = m
    return _MS[k]


def _cielo(m):
    y = np.linspace(0, 1, H)[:, None, None]
    a, b = np.array(m['cielo'][0], float), np.array(m['cielo'][1], float)
    hz = VP[1] / H
    g = np.where(y < hz, a + (b - a) * (y / hz) ** 1.4, np.array(m['suelo'], float))
    img = Image.fromarray(np.broadcast_to(g, (H, W, 3)).astype(np.uint8)).convert('RGBA')
    d = ImageDraw.Draw(img, 'RGBA'); r = np.random.default_rng(3)
    if m['estrellas']:
        for _ in range(260 if m['nombre'] == 'ESPACIO' else 160):
            x, yy, rr = r.integers(0, W), r.integers(0, VP[1] if m['nombre'] != 'ESPACIO' else H), r.uniform(0.8, 2.6)
            d.ellipse((x - rr, yy - rr, x + rr, yy + rr), fill=(255, 255, 255, int(r.integers(60, 230))))
    if m['nombre'] == 'ESPACIO':   # planetas en el cielo
        for cx, cy, rad, col in ((300, 200, 110, (230, 140, 80)), (1620, 160, 70, (120, 200, 255)), (1250, 300, 34, (240, 220, 160))):
            d.ellipse((cx - rad, cy - rad, cx + rad, cy + rad), fill=col + (255,))
            d.ellipse((cx - rad * 0.2, cy - rad, cx + rad * 1.1, cy + rad * 0.9), fill=(0, 0, 0, 90))
        d.ellipse((300 - 190, 200 - 26, 300 + 190, 200 + 26), outline=(240, 200, 150, 200), width=6)
    if m['nombre'] == 'DESIERTO':
        d.ellipse((VP[0] - 120, VP[1] - 190, VP[0] + 120, VP[1] + 50), fill=(255, 245, 210, 255))   # sol
    glow = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dg = ImageDraw.Draw(glow)
    dg.ellipse((VP[0] - 900, VP[1] - 120, VP[0] + 900, VP[1] + 120), fill=m['brillo'] + (120,))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(60)))
    if m['montes']:
        mm = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(mm)
        for i, (col, amp) in enumerate(zip(m['montes'], (130, 75))):
            pts = [(0, VP[1] + 2)]; rr = np.random.default_rng(11 + i)
            for x in range(0, W + 80, 80): pts.append((x, VP[1] + 2 - abs(np.sin(x / 260 + i)) * amp * rr.uniform(0.5, 1.0)))
            pts.append((W, VP[1] + 2)); d.polygon(pts, fill=col + (255,))
            if m['nombre'] in ('HIELO',):   # cumbres nevadas
                for (x, y) in pts[1:-1]:
                    if y < VP[1] - amp * 0.6: d.polygon([(x - 18, y + 22), (x, y), (x + 18, y + 22)], fill=(255, 255, 255, 255))
        img = Image.alpha_composite(img, mm)
    d = ImageDraw.Draw(img)
    for k in range(1, 14):
        yy = VP[1] + k * k * 4; c = tuple(min(255, int(v * 1.15) + 8) for v in m['suelo'])
        d.line([(0, yy), (W, yy)], fill=c, width=1)
    return img.convert('RGB')


_CIELOS = {}
def cielo(i):
    if i not in _CIELOS:
        if len(_CIELOS) > 4: _CIELOS.clear()
        _CIELOS[i] = _cielo(mundo(i))
    return _CIELOS[i]


def _objeto(d, tipo, x, y, f, lado, t):
    """Objeto a un costado del camino, en el suelo (x, y) con escala f."""
    if tipo == 'farol':
        alto = 900 * f; w = max(1, int(14 * f)); r = max(2, 16 * f)
        d.line([(x, y), (x, y - alto)], fill=(20, 10, 40, 255), width=w)
        d.ellipse((x - r, y - alto - r, x + r, y - alto + r), fill=(255, 220, 120, 255))
        d.ellipse((x - 3 * r, y - alto - 3 * r, x + 3 * r, y - alto + 3 * r), fill=(255, 200, 80, 40))
    elif tipo == 'cactus':
        a = 520 * f; w = max(2, 60 * f); c = (60, 130, 70, 255)
        d.rounded_rectangle((x - w / 2, y - a, x + w / 2, y), int(w / 2), fill=c)
        d.rounded_rectangle((x - w * 1.6, y - a * 0.62, x - w * 1.0, y - a * 0.32), int(w / 3), fill=c)
        d.rounded_rectangle((x - w * 1.6, y - a * 0.4, x - w / 2, y - a * 0.3), int(w / 4), fill=c)
        d.rounded_rectangle((x + w, y - a * 0.8, x + w * 1.6, y - a * 0.5), int(w / 3), fill=c)
        d.rounded_rectangle((x + w / 2, y - a * 0.58, x + w * 1.6, y - a * 0.48), int(w / 4), fill=c)
        d.line([(x - 2.5 * w, y - a * 0.75), (x - 2.5 * w, y)], fill=(90, 60, 30, 255), width=max(1, int(8 * f)))   # poste de madera
    elif tipo == 'arbol':
        a = 760 * f; w = max(2, 40 * f)
        d.rectangle((x - w / 2, y - a * 0.55, x + w / 2, y), fill=(70, 45, 25, 255))
        for k, (dx, dy, rr, col) in enumerate(((0, 0.62, 0.32, (30, 110, 50)), (-0.22, 0.5, 0.24, (40, 130, 60)), (0.22, 0.52, 0.24, (25, 100, 45)), (0, 0.8, 0.22, (50, 150, 70)))):
            R = rr * a; cx, cy = x + dx * a, y - dy * a
            d.ellipse((cx - R, cy - R, cx + R, cy + R), fill=col + (255,))
    elif tipo == 'pino':
        a = 700 * f; w = 230 * f
        d.rectangle((x - 14 * f, y - a * 0.2, x + 14 * f, y), fill=(80, 55, 40, 255))
        for k in range(3):
            yb = y - a * (0.15 + 0.27 * k); ww = w * (1 - 0.25 * k)
            d.polygon([(x - ww / 2, yb), (x + ww / 2, yb), (x, yb - a * 0.42)], fill=(30, 90, 70, 255))
            d.polygon([(x - ww / 4, yb - a * 0.21), (x + ww / 4, yb - a * 0.21), (x, yb - a * 0.42)], fill=(250, 252, 255, 255))
    elif tipo == 'lava':
        a = 420 * f; w = 160 * f   # roca volcánica con brillo
        d.polygon([(x - w, y), (x - w * 0.5, y - a), (x + w * 0.3, y - a * 0.8), (x + w, y)], fill=(40, 22, 18, 255))
        fl = 0.6 + 0.4 * math.sin(t * 9 + x * 0.01)
        d.line([(x - w * 0.4, y - a * 0.8), (x - w * 0.1, y - a * 0.3), (x + w * 0.2, y)], fill=(255, int(120 * fl), 20, 255), width=max(1, int(10 * f)))
    elif tipo == 'planeta':
        R = 120 * f; cy = y - 500 * f
        d.ellipse((x - R, cy - R, x + R, cy + R), fill=((140, 90, 220) if lado < 0 else (90, 200, 240)) + (255,))
        d.ellipse((x - R * 1.8, cy - R * 0.25, x + R * 1.8, cy + R * 0.25), outline=(255, 230, 160, 220), width=max(1, int(6 * f)))


def camino(img, dist, i, t=0.0, vel=1.0):
    """Carretera en perspectiva del mundo i con durmientes, rieles y objetos que pasan según la distancia recorrida."""
    m = mundo(i); d = ImageDraw.Draw(img, 'RGBA')
    ab, ar = 760, 8
    if m['obj'] == 'lava':   # ríos de lava a los costados
        fl = int(30 * math.sin(t * 5))
        for s in (-1, 1):
            d.polygon([(VP[0] + s * ar, VP[1]), (VP[0] + s * 30, VP[1]), (VP[0] + s * ab * 1.9, H), (VP[0] + s * ab * 1.05, H)], fill=(255, 90 + fl, 20, 255))
    if m['nombre'] == 'HIELO':
        for s in (-1, 1):
            d.polygon([(VP[0] + s * ar, VP[1]), (VP[0] + s * 20, VP[1]), (VP[0] + s * ab * 1.4, H), (VP[0] + s * ab * 1.02, H)], fill=(255, 255, 255, 255))
    d.polygon([(VP[0] - ar, VP[1]), (VP[0] + ar, VP[1]), (VP[0] + ab, H), (VP[0] - ab, H)], fill=m['camino'] + (255,))
    off = dist % 0.5
    for k in range(0, 120):
        z0 = 0.62 + k * 0.5 - off; z1 = z0 + 0.16
        if z0 <= 0.62: continue
        y0, y1 = VP[1] + 700 / z1, VP[1] + 700 / z0
        if y1 > H + 40 or y0 - VP[1] < 1: continue
        f0, f1 = (y0 - VP[1]) / (H - VP[1]), (y1 - VP[1]) / (H - VP[1])
        w0, w1 = ar + (ab - ar) * f0 * 0.82, ar + (ab - ar) * f1 * 0.82
        q = 0.55 + 0.45 * min(1, f1 * 1.4); c = tuple(int(v * q) for v in m['dur'])
        if vel > 3.2:   # a mucha velocidad las tablas se estiran (desenfoque de movimiento)
            y0 -= (y1 - y0) * min(3, vel - 3.2); w0 = ar + (ab - ar) * max(0, (y0 - VP[1]) / (H - VP[1])) * 0.82
        d.polygon([(VP[0] - w0, y0), (VP[0] + w0, y0), (VP[0] + w1, y1), (VP[0] - w1, y1)], fill=c + (255,))
        d.line([(VP[0] - w1, y1), (VP[0] + w1, y1)], fill=m['borde'] + (int(140 * min(1, f1 * 2)),), width=max(1, int(3 * f1)))
    for s in (-1, 1):
        for g, a in ((10, 70), (4, 255)):
            d.line([(VP[0] + s * 4, VP[1]), (VP[0] + s * ab * 0.55, H)], fill=m['riel'] + (a,), width=g)
    off3 = dist % 3.0
    objs = []
    for k in range(0, 14):
        z = 0.7 + 3 * k - off3
        if z <= 0.7: continue
        f = 700 / z / (H - VP[1]); y = VP[1] + 700 / z
        if f > 1.6: continue
        for s in (-1, 1): objs.append((f, VP[0] + s * (ab * (1.25 if m['obj'] != 'lava' else 2.0)) * f, y, s))
    for f, x, y, s in sorted(objs):   # de lejos a cerca
        _objeto(d, m['obj'], x, y, f, s, t)


def particulas(img, i, t, vel):
    """Polvo, luciérnagas, nieve, chispas o estrellas que pasan volando (más rápido con la velocidad)."""
    tipo = mundo(i)['part']
    if not tipo: return
    d = ImageDraw.Draw(img, 'RGBA'); r = np.random.default_rng(42 + i)
    n = 70
    base = r.uniform(0, 1, (n, 3))
    for k in range(n):
        ang, ph, sz = base[k]
        if tipo in ('nieve', 'estrellas', 'polvo'):   # salen del punto de fuga hacia la cámara
            u = (ph + t * 0.35 * vel) % 1.0; e = u ** 2.2
            a = ang * 2 * math.pi
            x = VP[0] + math.cos(a) * 1300 * e; y = VP[1] + math.sin(a) * 900 * e + (60 * e if tipo == 'nieve' else 0)
            rr = (1 + 9 * e) * (0.6 + sz)
            col = {'nieve': (255, 255, 255, 230), 'estrellas': (200, 230, 255, 255), 'polvo': (255, 230, 190, 150)}[tipo]
            if tipo == 'estrellas' and vel > 1.6:   # estelas
                x0 = VP[0] + math.cos(a) * 1300 * e * 0.8; y0 = VP[1] + math.sin(a) * 900 * e * 0.8
                d.line([(x0, y0), (x, y)], fill=col, width=max(1, int(rr / 2)))
            else:
                d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=col)
        elif tipo == 'luciernagas':
            x = (ang * W + 40 * math.sin(t * 1.3 + ph * 9)) % W; y = 200 + ph * 700 + 30 * math.sin(t * 2 + ang * 7)
            br = 0.5 + 0.5 * math.sin(t * 4 + ph * 20); rr = 3 + 3 * sz
            d.ellipse((x - rr * 3, y - rr * 3, x + rr * 3, y + rr * 3), fill=(220, 255, 120, int(50 * br)))
            d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=(240, 255, 160, int(230 * br)))
        elif tipo == 'chispas':
            u = (ph + t * 0.25 * vel) % 1.0
            x = ang * W + 30 * math.sin(t * 3 + ph * 10); y = H - u * (H - 100)
            rr = 2 + 4 * sz
            d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=(255, int(140 + 100 * (1 - u)), 40, int(255 * (1 - u))))


def lineas_velocidad(img, t, fuerza):
    """Líneas radiales desde el punto de fuga (estilo anime) cuando se va muy rápido. fuerza 0..1."""
    if fuerza <= 0.02: return
    d = ImageDraw.Draw(img, 'RGBA'); r = np.random.default_rng(int(t * 30) % 1000)
    for _ in range(int(14 + 46 * fuerza)):
        a = r.uniform(0, 2 * math.pi); r0 = r.uniform(380, 700); r1 = r0 + r.uniform(150, 500) * (0.5 + fuerza)
        x0, y0 = VP[0] + math.cos(a) * r0 * 1.4, VP[1] + math.sin(a) * r0
        x1, y1 = VP[0] + math.cos(a) * r1 * 1.4, VP[1] + math.sin(a) * r1
        d.line([(x0, y0), (x1, y1)], fill=(255, 255, 255, int(40 + 110 * fuerza)), width=int(r.integers(2, 5)))


def portal(img, u, nuevo):
    """Portal que crece desde el punto de fuga (u 0→1). Al final, destello blanco."""
    d = ImageDraw.Draw(img, 'RGBA')
    R = 30 + 1500 * u ** 2.2
    cols = [(255, 200, 40), (255, 90, 200), (90, 215, 255), (140, 235, 110)]
    for k in range(6):
        rr = R * (1 - k * 0.09)
        if rr < 4: continue
        c = cols[(k + int(u * 20)) % 4]
        d.ellipse((VP[0] - rr * 0.8, VP[1] - 20 - rr, VP[0] + rr * 0.8, VP[1] - 20 + rr), outline=c + (230,), width=max(3, int(rr * 0.05)))
    if u > 0.12:
        mini = cielo(nuevo).resize((W // 8, H // 8))
        rr = R * 0.45
        m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).ellipse((VP[0] - rr * 0.8, VP[1] - 20 - rr, VP[0] + rr * 0.8, VP[1] - 20 + rr), fill=255)
        img.paste(mini.resize((W, H), Image.BILINEAR), (0, 0), m)
    if u > 0.85:
        img.paste(Image.new('RGB', (W, H), (255, 255, 255)), (0, 0), Image.new('L', (W, H), int(255 * (u - 0.85) / 0.15)))


def tunel(img, t, fuerza):
    """Túnel de luz del teletransporte (nivel dios): anillos que salen del punto de fuga."""
    d = ImageDraw.Draw(img, 'RGBA'); cols = [(90, 215, 255), (255, 90, 200), (255, 200, 40), (140, 235, 110)]
    for k in range(12):
        u = ((t * (0.8 + 1.5 * fuerza)) + k / 12) % 1.0; e = u ** 2.4; R = 20 + 1800 * e
        d.ellipse((VP[0] - R * 1.3, VP[1] - R, VP[0] + R * 1.3, VP[1] + R), outline=cols[k % 4] + (int(200 * (1 - u)),), width=max(2, int(10 * e)))
