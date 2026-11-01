"""Personajes del canal (MAX, NOVA, LA VOZ) a partir de los PNG recortados de assets/personajes/.
La cara se dibuja por código dentro de la pantalla/visor (recortada por su máscara), con:
  - expresión según la pose (normal, feliz, piensa, sorpresa)
  - boca con 5 niveles (0 cerrada … 4 muy abierta) según el volumen de la voz
  - parpadeo
LA VOZ: esfera dorada que late y emite ondas mientras habla.
Si faltan los PNG, correr antes: python scripts/recortar_personajes.py
"""
import json, os
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops

DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets', 'personajes'))
GEO = json.load(open(os.path.join(DIR, 'geometria.json')))

NOMBRES = {'presentador': 'MAX', 'copresentadora': 'NOVA', 'anunciador': 'LA VOZ'}
PREFIJO = {'presentador': 'max', 'copresentadora': 'nova'}
# ancho en pantalla (px del video) de la pantalla/visor: fija la escala de cada personaje
ANCHO_CARA = {'presentador': 158, 'copresentadora': 130}
ANCHO_MAX = 470  # ancho máximo del personaje en pantalla (columna de 450 px)
EXPRESION = {  # pose -> expresión
    'base': 'normal', 'frente': 'normal', 'senala': 'normal', 'presenta': 'normal',
    'piensa': 'piensa', 'sorpresa': 'sorpresa',
    'saluda': 'feliz', 'celebra': 'feliz', 'celebra2': 'feliz', 'aplaude': 'feliz',
}
# giro de la cabeza de NOVA en cada pose, medido con el MENTÓN: la parte de abajo del visor marca el eje real
# de la cabeza (va con el cuello y el tronco). La cara se centra sobre ese eje y el ojo lejano se achica un poco.
# MAX no lleva giro: su cara siempre se vio bien.
DESPLAZA = 0.09  # desplazamiento máximo de la cara (fracción del ancho del visor) cuando giro = 1


def _giro_por_menton(nombre):
    if not nombre.startswith('nova_'): return 0.0
    m = np.array(Image.open(os.path.join(DIR, nombre + '_cara.png')).convert('L')) > 128
    ys, xs = np.nonzero(m)
    if not len(xs): return 0.0
    y0, y1 = ys.min(), ys.max(); menton = xs[ys >= y0 + 0.9 * (y1 - y0)].mean()
    x0, _, x1, _ = GEO[nombre]['pantalla']
    g = (menton - (x0 + x1) / 2) / (DESPLAZA * (x1 - x0))
    return float(np.clip(round(g, 2), -1, 1)) if abs(g) > 0.1 else 0.0


GIRO = {k: _giro_por_menton(k) for k in GEO if k != 'voz'}


def _centros(nombre):
    """Centro del visor a la altura de los ojos y a la altura de la boca (fracción del ancho, 0 = al medio).
    Cada rasgo va al medio del óvalo a SU altura: así la boca queda centrada sobre el mentón aunque NOVA esté de costado."""
    if not nombre.startswith('nova_'): return (0.0, 0.0)
    m = np.array(Image.open(os.path.join(DIR, nombre + '_cara.png')).convert('L')) > 128
    x0, y0, x1, y1 = GEO[nombre]['pantalla']; w, h, c = x1 - x0, y1 - y0, (x0 + x1) / 2
    out = []
    for f in (0.42, 0.72):
        xs = np.nonzero(m[int(y0 + f * h)])[0]
        # tope: una mano delante del visor (pose sorpresa) no debe empujar el rasgo hasta el borde
        out.append(float(np.clip(round(((xs.min() + xs.max()) / 2 - c) / w, 3), -0.06, 0.06)) if len(xs) else 0.0)
    return tuple(out)


CENTRO = {k: _centros(k) for k in GEO if k != 'voz'}


def _eje(nombre):
    """Eje frente→mentón del visor de NOVA (eje largo del óvalo): ángulo en grados (+ = el mentón va hacia la derecha)
    y su centro (fracción de la caja). La cara se dibuja sobre ese eje y se gira con él."""
    if not nombre.startswith('nova_'): return (0.0, 0.5, 0.5)
    m = np.array(Image.open(os.path.join(DIR, nombre + '_cara.png')).convert('L')) > 128
    ys, xs = np.nonzero(m); cx, cy = xs.mean(), ys.mean()
    ev, evec = np.linalg.eigh(np.cov(np.vstack([xs - cx, ys - cy]))); v = evec[:, 1]
    if v[1] < 0: v = -v
    ang = float(np.clip(np.degrees(np.arctan2(v[0], v[1])), -15, 15))
    x0, y0, x1, y1 = GEO[nombre]['pantalla']
    return (round(ang, 1), (cx - x0) / (x1 - x0), (cy - y0) / (y1 - y0))


EJE = {k: _eje(k) for k in GEO if k != 'voz'}


def _corte_cintura(nombre):
    """Fila (en px del PNG original) donde empiezan a verse las piernas bajo el saco de NOVA.
    Desde ahí hacia abajo el personaje se desvanece: en un canal familiar no deben verse."""
    if not nombre.startswith('nova_'): return None
    a = np.array(Image.open(os.path.join(DIR, nombre + '.png')).convert('RGBA')).astype(int)
    A = a[:, :, 3] > 128; r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    piel = A & (r > 140) & (r >= b - 30) & (g < r)
    x0, y0, x1, y1 = GEO[nombre]['pantalla']; cx = (x0 + x1) // 2
    for y in range(y1 + 250, a.shape[0]):
        if piel[y, max(0, cx - 90):cx + 150].sum() > 6: return y - 45
    return None


CORTE = {k: _corte_cintura(k) for k in GEO if k != 'voz'}
FUNDIDO = 60  # px del PNG original en que se desvanece
LUZ = {'presentador': (120, 235, 255), 'copresentadora': (150, 205, 255)}


def poses(quien):
    p = PREFIJO[quien] + '_'
    return sorted(k[len(p):] for k in GEO if k.startswith(p))


@lru_cache(maxsize=32)
def _base(nombre, esc):
    im = Image.open(os.path.join(DIR, nombre + '.png')).convert('RGBA')
    m = Image.open(os.path.join(DIR, nombre + '_cara.png')).convert('L')
    pb = os.path.join(DIR, nombre + '_brillo.png')
    br = Image.open(pb).convert('L') if os.path.exists(pb) else Image.new('L', im.size, 0)
    w, h = round(im.width * esc), round(im.height * esc)
    return im.resize((w, h), Image.LANCZOS), m.resize((w, h), Image.LANCZOS), br.resize((w, h), Image.LANCZOS)


def escala(quien, pose):
    n = f'{PREFIJO[quien]}_{pose}'; g = GEO[n]['pantalla']
    e = ANCHO_CARA[quien] / (g[2] - g[0])
    return min(e, ANCHO_MAX / GEO[n]['tam'][0])  # poses muy abiertas (brazos arriba) no invaden el contenido


def _cara(quien, expr, boca, parp, w, h, giro=0.0, eje=(0.0, 0.5, 0.5)):
    """Dibuja la cara en un lienzo w×h (coordenadas 0..1 dentro de la caja de la pantalla). Devuelve RGBA."""
    S = 3; W, H = w * S, h * S
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    col = LUZ[quien] + (255,)
    max_ = quien == 'presentador'
    # ojos
    ey = H * (0.40 if max_ else 0.42); ex = W * (0.26 if max_ else 0.24)
    ew0, eh = W * (0.085 if max_ else 0.075), H * (0.15 if max_ else 0.11)
    lw = int(W * 0.035)
    cx0 = eje[1] * W                           # ojos y boca sobre el eje frente→mentón
    ex *= 1 - 0.12 * abs(giro)             # en perspectiva los ojos quedan más juntos
    for sx in (-1, 1):
        lejos = sx * giro > 0              # el ojo del lado al que gira queda más lejos: más angosto
        ew = ew0 * ((1 - 0.28 * abs(giro)) if lejos else (1 + 0.04 * abs(giro)))
        cx = cx0 + sx * ex
        if parp:
            d.line((cx - ew, ey, cx + ew, ey), fill=col, width=lw)
        elif expr == 'feliz':
            d.arc((cx - ew * 1.25, ey - eh * 0.55, cx + ew * 1.25, ey + eh * 0.9), 195, 345, fill=col, width=lw)
        elif expr == 'sorpresa':
            r = ew * 1.25; d.ellipse((cx - r, ey - r * 1.15, cx + r, ey + r * 1.15), outline=col, width=lw)
            d.ellipse((cx - r * 0.35, ey - r * 0.35, cx + r * 0.35, ey + r * 0.35), fill=col)
        elif expr == 'piensa':
            if sx < 0:  # un ojo entrecerrado, el otro mirando arriba
                d.line((cx - ew, ey + eh * 0.1, cx + ew, ey - eh * 0.15), fill=col, width=lw)
            else:
                d.rounded_rectangle((cx - ew + ew * 0.3, ey - eh * 1.05, cx + ew + ew * 0.3, ey + eh * 0.55), ew, fill=col)
        else:
            d.rounded_rectangle((cx - ew, ey - eh, cx + ew, ey + eh), ew, fill=col)
            d.ellipse((cx - ew * 0.15, ey - eh * 0.75, cx + ew * 0.55, ey - eh * 0.2), fill=(255, 255, 255, 200))
    # mejillas (feliz)
    if expr == 'feliz' and not parp:
        for sx in (-1, 1):
            cx = cx0 + sx * ex * 1.25; ew = ew0 * ((1 - 0.35 * abs(giro)) if sx * giro > 0 else 1)
            d.ellipse((cx - ew, ey + eh * 1.1, cx + ew, ey + eh * 1.6), fill=(255, 130, 200, 110))
    # boca
    my = H * (0.70 if max_ else 0.72); mw = W * (0.16 if max_ else 0.12) * (1 - 0.12 * abs(giro)); X = cx0
    if boca == 0:
        if expr == 'sorpresa':
            r = mw * 0.35; d.ellipse((X - r, my - r, X + r, my + r * 1.3), outline=col, width=lw)
        elif expr == 'piensa':
            pts = [(X - mw * 0.7 + i * mw * 0.35, my + (6 if i % 2 else -6) * S) for i in range(5)]
            d.line(pts, fill=col, width=lw, joint='curve')
        else:
            d.arc((X - mw, my - mw * 0.75, X + mw, my + mw * 0.45), 25, 155, fill=col, width=lw)
    else:
        ab = H * (0.035 + 0.045 * boca)  # apertura según nivel
        bw = mw * (0.95 - 0.06 * boca)
        d.rounded_rectangle((X - bw, my - ab * 0.35, X + bw, my + ab), min(bw, ab), fill=col)
        if boca >= 2:
            d.rounded_rectangle((X - bw * 0.55, my + ab * 0.35, X + bw * 0.55, my + ab * 0.85), ab * 0.3,
                                fill=(255, 120, 170, 210))
    # brillo (glow) y líneas de TV en MAX
    if eje[0]:  # girar la cara con la inclinación de la cabeza, alrededor del centro del visor
        lay = lay.rotate(eje[0], resample=Image.BICUBIC, center=(cx0, eje[2] * H))
    glow = lay.filter(ImageFilter.GaussianBlur(S * 5))
    out = Image.alpha_composite(glow, lay)
    if max_:
        sl = Image.new('L', (W, H), 255); ds = ImageDraw.Draw(sl)
        for y in range(0, H, S * 4): ds.line((0, y, W, y), fill=170, width=S)
        a = ImageChops.multiply(out.getchannel('A'), sl); out.putalpha(a)
    return out.resize((w, h), Image.LANCZOS)


@lru_cache(maxsize=256)
def sprite(quien, pose='base', boca=0, parp=False):
    """Devuelve (imagen RGBA, (cx, cy) centro de la pantalla en la imagen)."""
    nombre = f'{PREFIJO[quien]}_{pose}'
    esc = escala(quien, pose)
    im, mask, brillo = _base(nombre, esc)
    x0, y0, x1, y1 = [round(v * esc) for v in GEO[nombre]['pantalla']]
    w, h = x1 - x0, y1 - y0
    cara = _cara(quien, EXPRESION.get(pose, 'normal'), boca, parp, w, h, GIRO.get(nombre, 0.0), EJE.get(nombre, (0.0, 0.5, 0.5)))
    # tono de pantalla encendida + cara, recortado por la máscara del visor
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0))
    tinte = Image.new('RGBA', (w, h), LUZ[quien][:3] + (26,))
    lay.paste(tinte, (x0, y0)); lay.alpha_composite(cara, (x0, y0))
    a = ImageChops.multiply(lay.getchannel('A'), mask); lay.putalpha(a)
    out = Image.alpha_composite(im, lay)
    # el reflejo del vidrio vuelve encima de la cara (se ve detrás del visor)
    refl = im.copy(); refl.putalpha(brillo.point(lambda v: int(v * 0.6)))
    out.alpha_composite(refl)
    c = CORTE.get(nombre)
    if c:  # desvanecer desde la cintura hacia abajo
        y0c, y1c = round((c - FUNDIDO) * esc), round(c * esc)
        col = np.ones(out.height, np.float32)
        col[y0c:y1c] = np.linspace(1, 0, max(1, y1c - y0c)); col[y1c:] = 0
        al = (np.array(out.getchannel('A')).astype(np.float32) * col[:, None]).astype(np.uint8)
        out.putalpha(Image.fromarray(al))
    return out, ((x0 + x1) / 2, (y0 + y1) / 2)


# ------------------------------------------------------------------ LA VOZ
@lru_cache(maxsize=1)
def _voz_base(alto=360):
    im = Image.open(os.path.join(DIR, 'voz.png')).convert('RGBA')
    return im.resize((round(im.width * alto / im.height), alto), Image.LANCZOS)


@lru_cache(maxsize=128)
def voz_sprite(nivel=0, fase=0, lienzo=520):
    """nivel 0..4 (volumen), fase 0..11 (avance de las ondas). Devuelve RGBA lienzo×lienzo."""
    out = Image.new('RGBA', (lienzo, lienzo), (0, 0, 0, 0)); c = lienzo / 2
    if nivel:
        g = Image.new('RGBA', (lienzo, lienzo), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
        r = 120 + 18 * nivel; d.ellipse((c - r, c - r, c + r, c + r), fill=(255, 190, 60, 60 + 25 * nivel))
        out = Image.alpha_composite(out, g.filter(ImageFilter.GaussianBlur(40)))
        d = ImageDraw.Draw(out)
        for k in range(3):  # ondas que se expanden
            p = ((fase / 12) + k / 3) % 1
            r = 150 + p * 105; al = int((1 - p) * (90 + 35 * nivel))
            d.ellipse((c - r, c - r, c + r, c + r), outline=(255, 215, 110, al), width=5)
    s = 1 + 0.035 * nivel
    b = _voz_base(); b = b.resize((round(b.width * s), round(b.height * s)), Image.LANCZOS)
    out.alpha_composite(b, (round(c - b.width / 2), round(c - b.height / 2)))
    return out
