#!/usr/bin/env python3
"""EPISODIO DE NAVIDAD «¡Criamos un DRAGÓN de Navidad!» (10-nov-2026, Luis lo autorizó).
Hereda el montador de la ciudad (pipeline/ciudad.py) y cambia el mundo:
  · 9 zonas (fondos de Flow en assets/navidad/fondos/z1..z9), cada una con su tema de preguntas.
  · Regalos gigantes A (rosado) / B (celeste) en vez de puertas; el que falla queda cubierto de nieve.
  · Público de animales navideños a los costados (assets/navidad/publico), pinos nevados, casas.
  · Túnel infinito de pinos nevados en arco con luces (bosque) y túnel de arcos de luces (avenida).
  · Dragón navideño: huevo-regalo → nace → bebé que vuela → joven → adulto → tira el trineo (zona 9).
  · MAX y NOVA con gorro de Navidad. Nieve cayendo.
Uso: igual que ciudad.py (--contenido, --voces, --out, --cuadros, --tramo/--tramos, --solo-audio).
El guion (meta) puede traer 'zonas': [índice de la 1.ª pregunta de cada zona] (si no, se reparten en 9 partes iguales).
"""
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

sys.path.insert(0, os.path.dirname(__file__))
import ciudad as C
import rapido as R0
from ciudad import Ciudad, SEG, ROADW, BX, DEPTH, PW, PH, HZ, ZP, DRAW, estrella
from rapido import W, H, FPS, RAIZ, font, ORO, BLANCO, TINTA, ROJO, ease_out, ease_back, clamp

D = os.path.join(RAIZ, 'assets', 'navidad')
NIEVE = (236, 242, 252)

# fondo, horizonte (fracción del alto de la foto), lados (casas: textura recortada de un fondo), pinos, público, colores del camino
ZONAS = [
    dict(n='AVENIDA NEVADA', f='z1_avenida', hz=0.68, casas=('z1_avenida', (0, 0, 300, 540)), pinos=0, pub=['ciudad', 'granja'],
         tema='Tradiciones navideñas del mundo', col=(200, 40, 50), cam=((226, 232, 244), (212, 220, 236)), ver=(150, 120, 110), borde='baston'),
    dict(n='TALLER DE PAPÁ NOEL', f='z2_fabrica', hz=0.62, casas=('z2_fabrica', (0, 330, 330, 768)), pinos=0, pub=['dulces', 'ciudad'],
         tema='Juguetes, inventos, ciencia y deportes', col=(176, 30, 40), cam=((150, 96, 60), (136, 86, 54)), ver=(110, 70, 44), borde='baston'),
    dict(n='BOSQUE NEVADO', f='z3_bosque', hz=0.44, casas=None, pinos=2, pub=['bosque'],
         tema='Animales y naturaleza', col=(30, 130, 70), cam=((226, 230, 246), (214, 218, 238)), ver=(190, 196, 224), borde='nieve'),
    dict(n='LAGO CONGELADO', f='z4_lago', hz=0.54, casas=None, pinos=1, pub=['lago'],
         tema='Frío, hielo, agua y mar', col=(40, 120, 200), cam=((150, 205, 240), (136, 192, 232)), ver=(200, 220, 240), borde='hielo'),
    dict(n='CIUDAD DE DULCES', f='z5_dulces', hz=0.52, casas=('z5_dulces', (0, 160, 310, 700)), pinos=0, pub=['dulces'],
         tema='Comida y postres', col=(230, 90, 150), cam=((176, 110, 60), (196, 128, 72)), ver=(246, 240, 236), borde='baston'),
    dict(n='POLO NORTE', f='z6_polo', hz=0.60, casas=None, pinos=0, pub=['polar', 'artico'],
         tema='Animales del frío', col=(30, 170, 150), cam=((230, 238, 250), (216, 228, 246)), ver=(190, 214, 240), borde='baston'),
    dict(n='MONTAÑA DE NIEVE', f='z7_montana', hz=0.47, casas=None, pinos=1, pub=['andes'],
         tema='Montañas, volcanes y geografía', col=(90, 110, 170), cam=((240, 242, 248), (226, 230, 242)), ver=(200, 206, 226), borde='nieve'),
    dict(n='SOBRE LOS TEJADOS', f='z8_tejados', hz=0.36, casas=None, pinos=1, pub=['africa', 'andes', 'selva', 'australia'],
         tema='Países, banderas y lugares', col=(150, 60, 160), cam=((150, 70, 60), (132, 60, 52)), ver=(226, 232, 244), borde='luces'),
    dict(n='CIELO DE NOCHEBUENA', f='z9_cielo', hz=0.36, casas=None, pinos=0, pub=['aves'],
         tema='Planetas y estrellas', col=(220, 170, 40), cam=((255, 220, 120), (250, 204, 96)), ver=(80, 70, 140), borde='luces'),
]
COL_A, COL_B = (240, 80, 160), (70, 190, 240)
# ---- versión 2 (11-nov, crítica de Luis tras ver el episodio 1): paisaje nuevo cada ~45 s, dragón que crece con
# cada acierto (9 niveles con habilidades), pista de montaña rusa con obstáculos, regalos dentro del mundo.
N_MAX = 360            # ~38 min con el ritmo ágil
CADA_ZONA = 5          # preguntas por paisaje (los 9 paisajes se repiten en ciclo)
# nivel del dragón → (imagen, alto al empezar el nivel, alto al terminarlo, vehículo de MAX y NOVA, texto del cartel)
# (Luis: «llegué solo para ver al dragón crecer»: cambia de forma ~cada 3 min, crece con cada acierto y reacciona siempre)
ETAPAS = [None,
    ('bebe_vuela', 190, 225, 'corre', ''),
    ('e02', 225, 255, 'reno', '¡LE CRECIERON LAS ALAS!'),
    ('e03', 250, 280, 'patineta', '¡LE SALIERON CUERNITOS!'),
    ('joven', 285, 320, 'trineo_madera', '¡YA ES UN DRAGÓN JOVEN!'),
    ('e05', 315, 350, 'pinguino', '¡SE ENROLLÓ LUCES DE NAVIDAD!'),
    ('e06', 345, 380, 'patines', '¡AHORA ECHA FUEGO!'),
    ('adulto', 375, 410, 'oso', '¡YA ES ADULTO!'),
    ('e08', 405, 440, 'corre', '¡ARMADURA DORADA!'),
    ('e09', 435, 470, 'snowboard', '¡ALAS DE HIELO!'),
    ('e10', 465, 500, 'tren', '¡HACE PIRUETAS!'),
    ('e11', 495, 530, 'reno', '¡CORONA DE ESTRELLAS!'),
    ('e12', 525, 560, 'montados', '¡NOS LLEVA VOLANDO!'),
    ('e13', 555, 590, 'corre', '¡BRILLA COMO UNA ESTRELLA!'),
    ('trineo', 560, 560, 'trineo', '¡TIRA DEL TRINEO DE PAPÁ NOEL!')]
NMAX_NV = len(ETAPAS) - 1
DRAGON_NV = {k: e[:4] for k, e in enumerate(ETAPAS) if e}
NV_TXT = {k: e[4] for k, e in enumerate(ETAPAS) if e}
NV_FUEGO, NV_PIRUETA, NV_BRILLA = 6, 10, 13
# rasgo de la pista de cada pregunta (se rota): curvas, subidas, caídas en picada, túneles…
PISTA_CICLO = ['curvas', 'colinas', 'zigzag', 'bajada', 'tunel', 'curvas2', 'subida', 'colinas', 'tunel', 'zigzag', 'bajada', 'curvas2']
OBSTACULOS = ['muneco', 'bola', 'tronco', 'rampa', 'volcado', 'regalos', 'baston', 'hielo']
# vehículo de cada zona (se pone en la 2.ª pregunta de la zona, después del cartel)
VEH_ZONA = {0: 'corre', 1: 'patineta', 2: 'trineo_madera', 3: 'patines', 4: 'carrito', 5: 'reno', 6: 'corre', 7: 'pato', 8: 'trineo'}
# vehículo → (alto en pantalla, base y, rebote, frecuencia del rebote)
VEH_NAV = {'trineo': (720, 1110, 16, 2.6), 'reno': (620, 1110, 26, 5.0), 'trineo_madera': (560, 1100, 10, 7.0), 'patines': (470, 1095, 6, 1.6),
           'pinguino': (520, 1100, 8, 3.0), 'oso': (600, 1110, 22, 4.0), 'snowboard': (500, 1095, 10, 2.0), 'tren': (560, 1100, 6, 6.0),
           'montados': (560, 980, 20, 2.2), 'corren': (470, 1100, 0, 1.0)}


# ---------------------------------------------------------------- fondos (se cargan al usarlos: solo 2 en memoria)
_TIRA = {}
def tira(z):
    """Fondo de la zona como tira ancha (espejada para las curvas) con el horizonte de la foto en la fila hy."""
    if z in _TIRA: return _TIRA[z]
    if len(_TIRA) >= 2: _TIRA.pop(next(iter(_TIRA)))
    Z = ZONAS[z]; im = Image.open(os.path.join(D, 'fondos', Z['f'] + '.jpg')).convert('RGB')
    im = im.resize((2304, round(im.height * 2304 / im.width)), Image.LANCZOS)
    hy_im = round(Z['hz'] * im.height)
    top = max(0, HZ + 480 - hy_im) + 40
    alto = top + hy_im + (H - HZ) + 260
    T = Image.new('RGB', (2304, alto))
    # arriba: el color de la primera fila de la foto, oscureciéndose
    c0 = np.asarray(im.crop((0, 0, 2304, 6))).reshape(-1, 3).mean(0)
    g = np.linspace(0.55, 1.0, max(1, top))[:, None, None] * c0
    T.paste(Image.fromarray(np.broadcast_to(g, (max(1, top), 2304, 3)).astype(np.uint8)), (0, 0))
    T.paste(im, (0, top))
    # abajo: reflejo borroso y oscurecido de la parte baja (nieve / suelo)
    resto = alto - (top + im.height)
    if resto > 0:
        refl = ImageOps.flip(im.crop((0, im.height - min(im.height, resto), 2304, im.height)))
        refl = Image.blend(refl.filter(ImageFilter.GaussianBlur(10)), Image.new('RGB', refl.size, (20, 22, 48)), 0.45)
        T.paste(refl, (0, top + im.height))
    t2 = Image.new('RGB', (4608, alto)); t2.paste(T, (0, 0)); t2.paste(ImageOps.mirror(T), (2304, 0))
    banda = np.asarray(im.crop((0, max(0, hy_im - 40), 2304, min(im.height, hy_im + 40)))).reshape(-1, 3).mean(0)
    _TIRA[z] = (t2, top + hy_im, tuple(int(v) for v in banda))
    return _TIRA[z]


_FACH = {}
def fachada(z):
    """Textura de casas/estantes de la zona: un recorte del propio fondo de Flow, repetido en mosaico."""
    if z not in _FACH:
        f, caja = ZONAS[z]['casas']
        im = Image.open(os.path.join(D, 'fondos', f + '.jpg')).convert('RGB').crop(caja)
        im = im.resize((512, round(512 * im.height / im.width)), Image.LANCZOS)
        at = Image.new('RGB', (im.width * 3, im.height * 6))
        for i in range(3):
            for j in range(6): at.paste(im if (i + j) % 2 == 0 else ImageOps.mirror(im), (i * im.width, j * im.height))
        _FACH[z] = at.resize((1024 * 3, round(1024 * 3 * at.height / at.width)), Image.LANCZOS)
    return _FACH[z]


# ---------------------------------------------------------------- pino nevado con luces (dibujado por código)
def _pino_base():
    w, h = 600, 1000; im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im); r = np.random.default_rng(5)
    d.rectangle((w / 2 - 34, h - 140, w / 2 + 34, h), fill=(92, 58, 36, 255))
    pisos = 5
    for i in range(pisos):
        y0 = 40 + i * 150; y1 = y0 + 330; hw = 90 + i * 52
        d.polygon([(w / 2, y0), (w / 2 + hw, y1), (w / 2 - hw, y1)], fill=(20, 84, 58, 255))
        d.polygon([(w / 2, y0), (w / 2 + hw, y1), (w / 2 + hw * 0.2, y1)], fill=(14, 66, 46, 255))   # lado en sombra
        # nieve en el borde de cada piso
        d.polygon([(w / 2, y0), (w / 2 + hw * 0.55, y0 + 200), (w / 2 + hw, y1), (w / 2 + hw * 0.85, y1 - 40),
                   (w / 2 + hw * 0.4, y0 + 230), (w / 2, y0 + 70), (w / 2 - hw * 0.4, y0 + 230), (w / 2 - hw * 0.85, y1 - 40),
                   (w / 2 - hw, y1), (w / 2 - hw * 0.55, y0 + 200)], fill=NIEVE + (255,))
        for _ in range(4 + i * 2):   # foquitos
            x = w / 2 + r.uniform(-0.8, 0.8) * hw; y = y1 - r.uniform(30, 120)
            c = [(255, 70, 70), (255, 214, 90), (90, 170, 255), (255, 255, 255)][int(r.integers(0, 4))]
            d.ellipse((x - 11, y - 11, x + 11, y + 11), fill=c + (255,))
    estrella(d, w / 2, 40, 46, ORO)
    return im


_PINO = {}
def pino(alto):
    k = max(4, int(round(alto / 4)) * 4)
    if k not in _PINO:
        if not _PINO: _PINO['base'] = _pino_base()
        if len(_PINO) > 400: b = _PINO['base']; _PINO.clear(); _PINO['base'] = b
        b = _PINO['base']; _PINO[k] = b.resize((max(2, int(b.width * k / b.height)), k), Image.BILINEAR)
    return _PINO[k]


# ---------------------------------------------------------------- público (animales navideños que saludan)
_PUB_LISTA = {}
def publico_de(z):
    if z not in _PUB_LISTA:
        fs = sorted(os.listdir(os.path.join(D, 'publico')))
        _PUB_LISTA[z] = [f for f in fs if any(f.startswith(p) and f[len(p):len(p) + 1].isdigit() for p in ZONAS[z]['pub'])]
    return _PUB_LISTA[z]


_PUB = {}
def animal(nombre, alto, ang):
    k = (nombre, max(4, int(round(alto / 6)) * 6), int(round(ang / 3)) * 3)
    if k not in _PUB:
        if len(_PUB) > 700: _PUB.clear()
        if nombre not in _PUB: _PUB[nombre] = Image.open(os.path.join(D, 'publico', nombre)).convert('RGBA')
        b = _PUB[nombre]; im = b.resize((max(2, int(b.width * k[1] / b.height)), k[1]), Image.BILINEAR)
        if k[2] and k[1] > 60: im = im.rotate(k[2], Image.BILINEAR, expand=True, center=(im.width / 2, im.height))
        _PUB[k] = im
    return _PUB[k]


# ---------------------------------------------------------------- imágenes navideñas (dragón, regalos, corredores)
_NAV = {}
def nav_img(n, alto):
    k = (n, alto)
    if k not in _NAV:
        if len(_NAV) > 120: _NAV.clear()
        im = Image.open(os.path.join(D, n + '.png')).convert('RGBA')
        _NAV[k] = im.resize((max(1, round(im.width * alto / im.height)), alto), Image.LANCZOS)
    return _NAV[k]


# ---------------------------------------------------------------- animaciones de verdad (clips de Flow/Veo en verde
# recortados a cuadros PNG: assets/navidad/anim/<nombre>/000.png…; el bucle se repite a ANIM_FPS)
ANIM_FPS = 24
_ANIM_N = {}
def anim_n(nombre):
    if nombre not in _ANIM_N:
        dd = os.path.join(D, 'anim', nombre)
        _ANIM_N[nombre] = len([f for f in os.listdir(dd) if f.endswith('.png')]) if os.path.isdir(dd) else 0
    return _ANIM_N[nombre]


_ANIM = {}
def anim_img(nombre, alto, t, vel=1.0):
    """Cuadro de la animación 'nombre' en el instante t (o None si no hay animación)."""
    n = anim_n(nombre)
    if not n: return None
    i = int(t * ANIM_FPS * vel) % n; k = (nombre, i, int(alto) // 4 * 4)
    if k not in _ANIM:
        if len(_ANIM) > 500: _ANIM.clear()
        im = Image.open(os.path.join(D, 'anim', nombre, f'{i:03d}.png')).convert('RGBA')
        _ANIM[k] = im.resize((max(1, round(im.width * k[2] / im.height)), max(1, k[2])), Image.BILINEAR)
    return _ANIM[k]


DE_LADO = {'oso', 'pinguino', 'reno'}   # animaciones de perfil o lado a lado
def veh_ok(v):
    """¿Hay imagen o animación para este vehículo? (los nuevos de Flow pueden faltar todavía)"""
    if v in DE_LADO: return False     # Luis: nada corre de costado; vuelven cuando haya clip visto desde atrás
    return v in ('corre', 'patineta') or os.path.exists(os.path.join(D, v + '.png')) or anim_n(v) > 0


_ETAPA_RESPALDO = {'e02': 'bebe_vuela', 'e03': 'bebe_vuela', 'e05': 'joven', 'e06': 'joven', 'e08': 'adulto', 'e09': 'adulto',
                   'e10': 'adulto', 'e11': 'adulto', 'e12': 'adulto', 'e13': 'adulto'}
def etapa_img(n, alto, t=None):
    """Dragón de la etapa n: animación si la hay, si no la imagen fija (y si aún no existe, la etapa anterior)."""
    if t is not None:
        im = anim_img('dragon_' + n, alto, t)
        if im is not None: return im
    if not os.path.exists(os.path.join(D, n + '.png')): n = _ETAPA_RESPALDO.get(n, n)
    return nav_img(n, alto)


_DRAG_NOMBRE = {'huevo': 'huevo', 'bebe_nace': 'nace', 'bebe_vuela': 'bebe_vuela', 'joven': 'joven', 'adulto': 'adulto', 'gigante': 'adulto'}
def dragon_nav(n, alto):
    return nav_img(_DRAG_NOMBRE.get(n, n), alto)


C.dragon_img = dragon_nav    # ciudad.py busca el dragón por este nombre


def tono(im, grados, sat=1.0):
    """Gira el tono de una imagen RGBA (cambia el color del papel de regalo sin perder brillos ni sombras)."""
    a = np.asarray(im.convert('RGBA')); hsv = np.asarray(im.convert('RGB').convert('HSV')).astype(np.int16)
    hsv[..., 0] = (hsv[..., 0] + int(grados * 256 / 360)) % 256; hsv[..., 1] = np.clip(hsv[..., 1] * sat, 0, 255)
    rgb = np.asarray(Image.fromarray(hsv.astype(np.uint8), 'HSV').convert('RGB'))
    return Image.fromarray(np.dstack([rgb, a[..., 3]]), 'RGBA')


# variantes de regalo: (giro de tono, saturación, alto relativo)
REG_VAR = [(0, 1.0, 1.0), (120, 1.1, 1.25), (200, 1.0, 0.82), (60, 1.2, 1.1), (280, 1.0, 0.9), (330, 1.1, 1.3), (160, 0.9, 1.0), (30, 1.2, 0.85)]


# ---------------------------------------------------------------- obstáculos que MAX y NOVA saltan (dibujados por código)
def _obst_base(kind):
    w, h = 1400, 800; im = Image.new('RGBA', (w * 2, h * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(im); S = 2
    def E(x0, y0, x1, y1, **k): d.ellipse((x0 * S, y0 * S, x1 * S, y1 * S), **k)
    def R(x0, y0, x1, y1, r=0, **k): d.rounded_rectangle((x0 * S, y0 * S, x1 * S, y1 * S), r * S, **k)
    if kind == 'muneco':   # muñeco de nieve con bufanda y sombrero
        cx = w / 2
        E(cx - 260, 420, cx + 260, 800, fill=(244, 248, 255), outline=(170, 190, 225), width=10)
        E(cx - 190, 220, cx + 190, 520, fill=(248, 250, 255), outline=(170, 190, 225), width=10)
        E(cx - 140, 60, cx + 140, 300, fill=(250, 252, 255), outline=(170, 190, 225), width=10)
        R(cx - 200, 270, cx + 200, 330, 25, fill=(220, 40, 50)); R(cx + 60, 300, cx + 140, 470, 20, fill=(220, 40, 50))
        R(cx - 120, 40, cx + 120, 80, 10, fill=(30, 30, 40)); R(cx - 80, -60 + 60, cx + 80, 60, 10, fill=(30, 30, 40))
        E(cx - 70, 140, cx - 30, 180, fill=(30, 30, 40)); E(cx + 30, 140, cx + 70, 180, fill=(30, 30, 40))
        d.polygon([(cx * S, 190 * S), ((cx + 130) * S, 215 * S), (cx * S, 235 * S)], fill=(255, 140, 30))
        for yy in (370, 440, 560, 650): E(cx - 18, yy, cx + 18, yy + 36, fill=(30, 30, 40))
    elif kind == 'tronco':   # tronco atravesado con nieve encima
        R(80, 430, w - 80, 760, 160, fill=(120, 74, 40), outline=(80, 48, 26), width=12)
        for x in range(200, w - 200, 120): d.line(((x) * S, 470 * S, (x + 60) * S, 720 * S), fill=(96, 58, 30), width=10 * S)
        E(w - 300, 430, w - 60, 760, fill=(196, 150, 96), outline=(80, 48, 26), width=12)
        E(w - 240, 500, w - 120, 690, outline=(150, 104, 60), width=10)
        R(140, 380, w - 260, 480, 50, fill=(244, 248, 255))
    elif kind == 'regalos':   # montón de regalos caídos
        for x0, y0, x1, y1, c, cr in ((120, 420, 600, 800, (220, 40, 60), ORO), (560, 300, 1000, 800, (40, 150, 90), (250, 250, 250)),
                                      (960, 480, 1300, 800, (60, 120, 220), ORO), (380, 160, 760, 420, (240, 190, 40), (220, 40, 60))):
            R(x0, y0, x1, y1, 24, fill=c, outline=(30, 20, 40), width=8)
            m = (x0 + x1) / 2; R(m - 30, y0, m + 30, y1, 0, fill=cr); R(x0, (y0 + y1) / 2 - 30, x1, (y0 + y1) / 2 + 30, 0, fill=cr)
    elif kind == 'bola':   # bola de nieve gigante
        E(w / 2 - 380, 40, w / 2 + 380, 800, fill=(236, 242, 252), outline=(170, 190, 225), width=12)
        E(w / 2 - 330, 90, w / 2 + 120, 520, fill=(250, 252, 255))
        for k in range(14):
            a = k * 2.3; x = w / 2 + 300 * math.cos(a) * (0.3 + (k % 3) * 0.3); y = 420 + 300 * math.sin(a) * (0.3 + (k % 3) * 0.3)
            E(x - 22, y - 16, x + 22, y + 16, fill=(205, 220, 240))
    elif kind == 'volcado':   # trineo volcado con regalos desparramados
        d.polygon([(200 * S, 700 * S), (1150 * S, 420 * S), (1230 * S, 560 * S), (300 * S, 800 * S)], fill=(200, 30, 40), outline=(90, 10, 20), width=10 * S)
        d.polygon([(250 * S, 640 * S), (1100 * S, 380 * S), (1120 * S, 430 * S), (270 * S, 690 * S)], fill=(240, 190, 60))
        d.line((180 * S, 760 * S, 1180 * S, 470 * S), fill=(60, 40, 30), width=26 * S)
        for x0, c in ((120, (40, 150, 90)), (980, (60, 120, 220)), (1180, (240, 190, 40))):
            R(x0, 600, x0 + 200, 790, 18, fill=c, outline=(30, 20, 40), width=8); R(x0 + 85, 600, x0 + 115, 790, 0, fill=ORO)
    elif kind == 'hielo':   # muro de hielo (el dragón lo derrite desde el nivel del fuego)
        R(60, 120, w - 60, 800, 40, fill=(170, 220, 250, 215), outline=(235, 248, 255), width=14)
        for k in range(6):
            x = 160 + k * 200; d.line((x * S, 160 * S, (x + 120) * S, 760 * S), fill=(240, 250, 255), width=10 * S)
        for k in range(9):
            x = 110 + k * 145; d.polygon([(x * S, 120 * S), ((x + 60) * S, 120 * S), ((x + 30) * S, 40 * S)], fill=(225, 245, 255))
    elif kind == 'rampa':   # rampa de nieve para el gran salto
        d.polygon([(80 * S, 800 * S), (w * S - 80 * S, 800 * S), (w * S - 200 * S, 330 * S), (200 * S, 330 * S)], fill=(240, 246, 255), outline=(170, 190, 225), width=10 * S)
        d.polygon([(200 * S, 330 * S), (w * S - 200 * S, 330 * S), (w * S - 230 * S, 290 * S), (230 * S, 290 * S)], fill=(255, 255, 255))
        for k in range(5):
            x = 300 + k * 200; d.polygon([(x * S, 770 * S), ((x + 60) * S, 770 * S), ((x + 40) * S, 360 * S), ((x + 20) * S, 360 * S)], fill=(255, 210, 60) if k % 2 else (230, 40, 50))
    else:   # barrera de bastones de caramelo
        R(160, 160, 260, 800, 40, fill=(250, 250, 250)); R(w - 260, 160, w - 160, 800, 40, fill=(250, 250, 250))
        for k in range(0, 1100, 110):
            d.polygon([((140 + k) * S, 330 * S), ((200 + k) * S, 330 * S), ((140 + k + 120) * S, 500 * S), ((80 + k + 120) * S, 500 * S)], fill=(220, 30, 40))
        R(120, 320, w - 120, 510, 60, outline=(250, 250, 250), width=14)
        for k in range(160, 800, 120): R(160, k, 260, k + 50, 0, fill=(220, 30, 40)); R(w - 260, k, w - 160, k + 50, 0, fill=(220, 30, 40))
    return im.resize((w, h), Image.LANCZOS)


_OBST = {}
def obst_img(kind, ancho):
    k = (kind, max(8, int(round(ancho / 8)) * 8))
    if k not in _OBST:
        if len(_OBST) > 300: _OBST.clear()
        if kind not in _OBST: _OBST[kind] = _obst_base(kind)
        b = _OBST[kind]; _OBST[k] = b.resize((k[1], max(1, int(b.height * k[1] / b.width))), Image.BILINEAR)
    return _OBST[k]


class Regalo(C.Puerta):
    """Regalo (Flow) con la foto pegada al frente, la letra en un círculo y el nombre abajo. Cambia de color y forma."""
    def __init__(s, foto, letra, col, var=0):
        s.foto, s.letra, s.col = foto, letra, col
        g = Image.open(os.path.join(D, 'regalo_a.png' if letra == 'A' else 'regalo_b.png')).convert('RGBA')
        gr, sat, alto = REG_VAR[var % len(REG_VAR)]
        if gr or sat != 1.0: g = tono(g, gr, sat)
        w = 900; g = g.resize((w, round(g.height * w / g.width * alto)), Image.LANCZOS); h = g.height
        im = Image.new('RGBA', (w, h + 40), (0, 0, 0, 0)); im.paste(g, (0, 40), g); d = ImageDraw.Draw(im)
        # foto con marco blanco sobre el frente de la caja
        fw, fh = 640, 470; fx, fy = (w - fw) // 2, 40 + max(int(h * 0.36), (h - fh) // 2 + 30) if h > 700 else 40 + int(h * 0.3)
        d.rounded_rectangle((fx - 18, fy - 18, fx + fw + 18, fy + fh + 18), 40, fill=BLANCO, outline=col, width=10)
        ph = foto.cuadro(fw, fh, 1.0); m = Image.new('L', ph.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, fw - 1, fh - 1), 30, fill=255)
        im.paste(ph, (fx, fy), m)
        # el nombre lo dibuja etiquetas() encima de todo
        d.ellipse((30, 60, 210, 240), fill=col, outline=BLANCO, width=12)
        d.text((120, 154), letra, font=font('Black', 120), fill=BLANCO, anchor='mm', stroke_width=6, stroke_fill=TINTA)
        s.img = im; s._c = {}
        c = foto.cuadro(300, 300, 1.0); m = Image.new('L', (300, 300), 0); ImageDraw.Draw(m).ellipse((0, 0, 299, 299), fill=255)
        bub = Image.new('RGBA', (330, 330), (0, 0, 0, 0)); ImageDraw.Draw(bub).ellipse((0, 0, 329, 329), fill=ORO + (255,)); bub.paste(c, (15, 15), m)
        s.burbuja = bub


# ---------------------------------------------------------------- el episodio
class Navidad(Ciudad):
    def __init__(s, meta, voces):
        # temas mezclados (una de cada tema, en rueda) y de fácil a difícil; máximo N_MAX preguntas
        Q = meta['preguntas']; nmax = int(os.environ.get('QSM_NAV_MAX', N_MAX))
        if Q and all('zona' in q for q in Q):
            grupos = {}
            for q in Q: grupos.setdefault(q['zona'], []).append(q)
            tot = len(Q)
            if tot > nmax:   # recorte parejo dentro de cada tema
                for z, l in grupos.items():
                    k = max(1, round(len(l) * nmax / tot)); grupos[z] = [l[int(i)] for i in np.linspace(0, len(l) - 1, k)]
            rueda = []; colas = [list(l) for _, l in sorted(grupos.items())]
            while any(colas):
                for c in colas:
                    if c: rueda.append(c.pop(0))
            Q = sorted(rueda[:nmax], key=lambda q: q.get('nivel', 1))   # sorted es estable: la rueda se mantiene
            meta['preguntas'] = Q
        N = len(Q)
        # el dragón sube de nivel cada ~4-5 min (Luis: «llegué solo para ver al dragón crecer»); el avance en
        # preguntas va más rápido al final (fracción del tiempo ≈ fracción de preguntas ** 0.75)
        # fracción de preguntas medida para que suba de nivel cada ~3 min (2.5, 5.3, 8.2 … 38.5 min de 44)
        QF = [0.033, 0.077, 0.123, 0.173, 0.223, 0.277, 0.33, 0.383, 0.44, 0.5, 0.553, 0.62, 0.75]
        s.nv_idx = {k: min(N - 2, max(6, int(N * QF[k - 2]))) for k in range(2, NMAX_NV + 1)}
        meta['vehiculos'] = {str(i + 1): DRAGON_NV[k][3] for k, i in s.nv_idx.items() if veh_ok(DRAGON_NV[k][3])}
        meta['dragon'] = {'meta_huevo': 3, 'antes_3': 'nace'}
        meta['zonas'] = None
        super().__init__(meta, voces)
        # rasgo de pista para cada pregunta (rota; sin repetir el anterior)
        rr = np.random.default_rng(int(s.sem) + 404); s.ev = dict(s.ev)
        for i in range(2, N):
            s.ev[str(i)] = PISTA_CICLO[(i + int(rr.integers(0, 3))) % len(PISTA_CICLO)]
        for i in range(17, N - 5, 23): s.ev[f'antes_{i}'] = 'vuelta'   # vuelta de cabeza de vez en cuando
        s.obst = []                       # (t en que los corredores saltan, tipo)
        s.estrellas = []                  # (t en que la recogen, X en el camino)
        s._drag_xy = (960, 330)
        s.nv_t = [(0.0, 0)]               # (t, nivel del dragón); 0 = huevo
        s.bancon = os.path.join(RAIZ, 'banco', 'navidad')
        f = os.path.join(s.bancon, 'indice.json')
        if os.path.exists(f): s.TXT.update({k: v.get('texto', '') for k, v in json.load(open(f, encoding='utf-8')).items()})
        fv = os.path.join(RAIZ, 'contenido', 'navidad_voces.json')
        if os.path.exists(fv): s.EST.update({k: v[1][0] for k, v in json.load(open(fv, encoding='utf-8'))['variantes'].items()})
        s.zona_t = [(0.0, 0)]
        s.drag = [(0.0, 'huevo')]

    # voces: primero las navideñas, luego las de la ciudad y las del formato rápido
    REMAP = {'an_ciudad_intro': 'an_nav_intro2', 'an_huevo': 'an_nav_huevo', 'an_final_equipo': 'an_nav_final'}
    def clip(s, clave, est=''):
        clave = s.REMAP.get(clave, clave)
        if os.path.isdir(s.bancon) and any(f.startswith(clave + '__') for f in os.listdir(s.bancon)):
            b = s.banco; s.banco = s.bancon
            try: return R0.Show.clip(s, clave, est)
            finally: s.banco = b
        return super().clip(clave, est)

    def antes_pregunta(s, idx):
        # nuevo paisaje cada CADA_ZONA preguntas: destello + nombre, sin voz (Luis: «cada 30-40 s»)
        if idx > 0 and idx % CADA_ZONA == 0:
            k = (idx // CADA_ZONA) % 9; t0 = s.t
            s.son('whoosh', t0, 1.0); s.son('campana', t0 + 0.12, 0.7)
            s.esc.append((t0, t0 + 0.9, ('nivel', k))); s.zona_t.append((t0 + 0.1, k)); s.t = t0 + 0.9
        # el dragón sube de nivel
        for k, i in s.nv_idx.items():
            if i != idx: continue
            t0 = s.t; s.son('tiempo', t0, 0.5); s.audio.append((t0, R0.riser(1.0)))
            s.son('golpe', t0 + 1.0, 1.0); s.son('fanfarria', t0 + 1.05, 0.9); s.son('aplausos', t0 + 1.1, 0.8)
            f = s.decir(f'an_drag_{k}', t0 + 1.15)
            et = DRAGON_NV[k][0]; s.drag.append((t0 + 1.0, et)); s.nv_t.append((t0 + 1.0, k))
            s.esc.append((t0, f + 0.3, ('crece', t0 + 1.0, et, k))); s.drops.append(t0 + 1.0)
            if k % 2 == 0 or k == NMAX_NV: s.capitulos.append((t0, f'Nivel {k} del dragón: {NV_TXT[k].strip("¡!").capitalize()}'))
            s.t = f + 0.3
        if idx == 3: s.nv_t.append((s.t + 1.6, 1)); s.capitulos.append((s.t, '¡Nace el dragón!'))

    def habla_ev(s, idx):
        return idx % 19 == 3     # el anunciador presenta túnel / curvas / bajada solo de vez en cuando

    def despues_pregunta(s, idx, t_abre, fin, tc):
        """Obstáculo en el camino mientras se lee la pregunta: MAX y NOVA lo saltan."""
        Pq = s.esc[-1][2][2]
        a, b = t_abre + Pq['lleg'] + 0.5, tc - 0.4
        s.estrellas_pregunta(t_abre, tc)
        if b - a < 0.6 or idx < 3 or idx % 3 == 1: return
        tj = (a + b) / 2; kind = OBSTACULOS[(idx * 7 // 3) % len(OBSTACULOS)]
        nv = s.nv_t[-1][1]
        if kind == 'hielo' and nv < NV_FUEGO: kind = 'muneco'
        s.obst.append((tj, kind))
        if kind == 'hielo':   # el dragón lo derrite con fuego: pasan sin saltar
            s.son('whoosh', tj - 0.5, 0.9); s.son('vidrio', tj - 0.2, 0.8)
        elif kind == 'rampa':
            s.son('whoosh', tj - 0.2, 1.0); s.son('viento', tj, 0.6); s.son('golpe', tj + 1.15, 0.8)
        else:
            s.son('boing', tj - 0.15, 0.7); s.son('whoosh', tj - 0.3, 0.5)

    def estrellas_pregunta(s, t_abre, tc):
        """Estrellas doradas en el camino que MAX y NOVA recogen (alimentan al dragón)."""
        a, b = t_abre + 0.6, tc - 0.3
        if b - a < 0.8: return
        n = 3 if b - a < 2.5 else 5
        for k in range(n):
            tk = a + (b - a) * (k + 0.5) / n
            if any(abs(tk - o[0]) < 0.5 for o in s.obst): continue
            s.estrellas.append((tk, (-260, 0, 260)[(k + len(s.estrellas)) % 3])); s.son('campana', tk, 0.35)

    def nivel_en(s, t):
        n = 0; t0 = 0.0
        for tt, k in s.nv_t:
            if t >= tt: n, t0 = k, tt
        return n, t0

    def armar(s):
        super().armar()
        s.capitulos[0] = (0.0, 'El huevo de dragón')
        s.capitulos.sort(key=lambda c: c[0])
        s.tr_preg = {e[2][1]: e[2][2] for e in s.esc if e[2][0] == 'pregunta'}

    def zona_en(s, t):
        z = 0
        for t0, k in s.zona_t:
            if t >= t0: z = k
        return z

    def zona_desde(s, t):
        d = (0.0, 0)
        for t0, k in s.zona_t:
            if t >= t0: d = (t0, k)
        return d

    def construir_pista(s):
        super().construir_pista()
        P = s.P
        # zona de cada tramo: cambia donde están los corredores al empezar la zona
        s.zseg = np.zeros(P.n + 2, int)
        lim = [(int((s.d_en(t0) + ZP) / SEG), k) for t0, k in s.zona_t]
        for a, k in lim: s.zseg[min(P.n + 1, max(0, a)):] = k
        # túneles: arcos según el paisaje (pinos en el bosque, bastones en dulces, hielo en lago/polo, luces en el resto)
        s.arco = np.zeros(P.n + 2, np.int8)
        TIPO_Z = {2: 1, 4: 3, 3: 4, 5: 4, 6: 1}
        for j in np.nonzero(P.tunel)[0]:
            if j % 3 == 0: s.arco[j] = TIPO_Z.get(int(s.zseg[min(j, len(s.zseg) - 1)]), 2)
        for lado in (-1, 1):
            for e in P.edif[lado]: e['letrero'] = False

    # ---- dibujo del mundo
    def mundo(s, fr, t, k):
        P = s.P; fila = s.proyectar(k); s._skyx = s.skyx_de(k); dz = int(s.hz - HZ)
        t0z, z = s.zona_desde(t)
        def fondo_de(zz):
            T, hy, _ = tira(zz); ox = int(s._skyx * 0.5) % (T.width // 2); oy = max(0, min(T.height - H, hy - HZ - dz))
            return T.crop((ox, oy, ox + W, oy + H))
        fr.paste(fondo_de(z))
        if z > 0 and t - t0z < 0.5:   # cambio de zona: fundido corto (lo tapa el destello del cartel)
            fr.paste(Image.blend(fondo_de(s.zona_t[[k_ for _, k_ in s.zona_t].index(z) - 1][1]), fr, clamp((t - t0z) / 0.5)))
        s._fr = fr; d = ImageDraw.Draw(fr, 'RGBA')
        pr = []
        for j_i, (j, zz, xoff) in enumerate(fila):
            if zz <= 40: pr.append(None); continue
            sc = DEPTH / zz; pr.append((PW + sc * xoff * PW, s.hz - sc * (P.y[j] - s._camY) * PH, sc, zz))
        vis = [False] * len(pr); maxy = H + 400
        for i in range(len(pr) - 1):
            a, b = pr[i], pr[i + 1]
            if a is None or b is None: continue
            if b[1] < maxy: vis[i] = True; maxy = min(maxy, b[1])
        lejos = DRAW * SEG * 0.95
        def fog(c, zz, zona):
            fc = tira(zona)[2] if zona in _TIRA else (70, 70, 110); u = min(1, zz / lejos) ** 1.4
            return tuple(int(c[q] + (fc[q] - c[q]) * u) for q in range(3))
        base = fila[0][0]; porTramo = {}
        for lado in (-1, 1):
            for e in P.edif[lado]:
                if e['s1'] < base or e['s0'] > base + len(pr) - 2: continue
                porTramo.setdefault(max(e['s0'], base + 1), []).append((lado, e))
        for i in range(len(pr) - 2, -1, -1):
            a, b = pr[i], pr[i + 1]; j = fila[i][0]; zj = int(s.zseg[min(j, len(s.zseg) - 1)]); Z = ZONAS[zj]
            if a is not None and b is not None and vis[i] and not P.vacio[j]:
                (x1, y1, s1, z1), (x2, y2, s2, z2) = a, b
                w1, w2 = s1 * ROADW * PW, s2 * ROADW * PW; v1, v2 = s1 * BX * PW, s2 * BX * PW
                par = (j // 3) % 2
                d.polygon([(x1 - v1, y1), (x1 + v1, y1), (x2 + v2, y2), (x2 - v2, y2)], fill=fog(Z['ver'], z1, zj))
                d.polygon([(x1 - w1, y1), (x1 + w1, y1), (x2 + w2, y2), (x2 - w2, y2)], fill=fog(Z['cam'][par], z1, zj))
                r1, r2 = w1 * 0.07, w2 * 0.07
                for sg_ in (-1, 1):
                    if Z['borde'] == 'baston': cb = (220, 30, 40) if (j // 2 + (sg_ > 0)) % 2 else (250, 250, 250)
                    elif Z['borde'] == 'hielo': cb = (210, 240, 255)
                    elif Z['borde'] == 'luces': cb = [(255, 70, 70), ORO, (90, 200, 255), (120, 230, 120)][(j + int(t * 4)) % 4]
                    else: cb = (255, 255, 255)
                    d.polygon([(x1 + sg_ * w1, y1), (x1 + sg_ * (w1 - r1), y1), (x2 + sg_ * (w2 - r2), y2), (x2 + sg_ * w2, y2)], fill=fog(cb, z1 * 0.6, zj))
                if j % 4 < 2:
                    l1, l2 = w1 * 0.025, w2 * 0.025
                    d.polygon([(x1 - l1, y1), (x1 + l1, y1), (x2 + l2, y2), (x2 - l2, y2)], fill=fog(ORO, z1 * 0.7, zj))
            if Z['casas']:
                C.FACHADAS[:] = [fachada(zj)]
                for lado, e in porTramo.get(j, []): s.edificio(d, e, lado, base, pr)
            if a is None: continue
            cx, sy, sc, zz = a
            if zz > 200 and Z['pinos'] and j % 2 == 0:
                for lado in (-1, 1):
                    for fila_ in range(Z['pinos']):
                        X = lado * (BX + 420 + 900 * fila_ + (j * 37 + fila_ * 11) % 5 * 160)
                        alto = sc * (2600 + (j * 53 % 7) * 260) * PH
                        if alto < 3: continue
                        im = pino(alto); fr.paste(im, (int(cx + sc * X * PW - im.width / 2), int(sy - im.height + 2)), im)
            if zz > 120 and Z['pub'] and j % 5 == 0 and s.arco[j] != 1:
                lista = publico_de(zj)
                for lado in (-1, 1):
                    nom = lista[(j // 5 * 2 + (lado > 0)) % len(lista)]
                    alto = sc * 640 * PH
                    if alto < 4: continue
                    ang = 8 * math.sin(t * 5 + j * 0.7 + lado) if alto > 60 else 0
                    hop = abs(math.sin(t * 4 + j)) * 60 * sc * PH
                    im = animal(nom, alto, ang); X = lado * (ROADW * 1.14)
                    fr.paste(im, (int(cx + sc * X * PW - im.width / 2), int(sy - im.height - hop)), im)
            if s.arco[j]: s.arco_dibujar(d, cx, sy, sc, zz, j, t, s.arco[j], zj)
        s.nieve(fr, t, z)
        if z in (2, 3, 5): s.luciernagas(fr, t, z)

    def arco_dibujar(s, d, cx, sy, sc, zz, j, t, tipo, zj):
        """Arco sobre la carretera. tipo 1: pinos nevados con luces (se repite hasta el horizonte); 2: arco de luces."""
        n = 26; fogc = tira(zj)[2]; u = min(1, zz / (DRAW * SEG * 0.95)) ** 1.2
        F = lambda c: tuple(int(c[q] + (fogc[q] - c[q]) * u) for q in range(3))
        def arc(X, Y):
            return [(cx + math.cos(math.pi * i / n) * sc * X * PW, sy - math.sin(math.pi * i / n) * sc * Y * PH) for i in range(n + 1)]
        if tipo == 1:
            Xo, Yo, Xi, Yi = BX * 1.35, 4300, BX * 0.98, 3300
            ext, inn = arc(Xo, Yo), arc(Xi, Yi)
            d.polygon(ext + inn[::-1], fill=F((18, 78, 54) if (j // 3) % 2 else (22, 90, 62)))
            if sc * Yo * PH > 30:
                ra = max(1, sc * 300 * PH)   # copas abultadas en el borde de afuera
                for i in range(1, n, 2):
                    x, y = ext[i]; d.ellipse((x - ra, y - ra, x + ra, y + ra), fill=F((24, 96, 66)))
                for i in range(2, n - 1, 2):
                    x, y = ext[i]; r2 = ra * 0.9; d.ellipse((x - r2, y - r2 * 0.75, x + r2, y + r2 * 0.35), fill=F(NIEVE))
            d.line(ext[3:-3], fill=F(NIEVE) + (255,), width=max(1, int(sc * 220 * PH)), joint='curve')
            mid = arc((Xo + Xi) / 2, (Yo + Yi) / 2)
            rl = max(1.0, sc * 90 * PH)
            for i in range(1, n):
                c = [(255, 70, 70), (255, 214, 90), (90, 170, 255), (255, 255, 255)][(i + j) % 4]
                if (i + j + int(t * 3)) % 5 == 0: c = tuple(min(255, v + 60) for v in c)
                x, y = mid[i]
                if rl > 2.5: d.ellipse((x - rl * 2, y - rl * 2, x + rl * 2, y + rl * 2), fill=c + (60,))
                d.ellipse((x - rl, y - rl, x + rl, y + rl), fill=F(c) + (255,))
        elif tipo == 3:   # bastón de caramelo gigante
            ln = arc(BX * 1.05, 3800); wd = max(1, int(sc * 260 * PH))
            for i in range(n):
                c = (230, 30, 40) if (i + j // 3) % 2 else (250, 250, 250)
                d.line([ln[i], ln[i + 1]], fill=F(c) + (255,), width=wd)
        elif tipo == 4:   # arco de hielo con carámbanos
            ext, inn = arc(BX * 1.25, 4100), arc(BX * 1.0, 3500)
            d.polygon(ext + inn[::-1], fill=F((170, 220, 250)) + (235,))
            d.line(ext[1:-1], fill=F((240, 250, 255)) + (255,), width=max(1, int(sc * 90 * PH)))
            for i in range(2, n - 1, 2):
                x, y = inn[i]; L = sc * (380 + 160 * ((i + j) % 3)) * PH; w_ = sc * 70 * PW
                if L > 2: d.polygon([(x - w_, y), (x + w_, y), (x, y + L)], fill=F((215, 240, 255)) + (240,))
        else:
            ln = arc(BX * 1.05, 3600); d.line(ln, fill=F((40, 30, 30)) + (255,), width=max(1, int(sc * 40 * PH)), joint='curve')
            rl = max(1.0, sc * 80 * PH)
            for i in range(0, n + 1):
                c = [(255, 70, 70), ORO, (90, 200, 255), (120, 230, 120)][(i + j // 4 + int(t * 4)) % 4]
                x, y = ln[i]
                if rl > 2.5: d.ellipse((x - rl * 2.4, y - rl * 2.4, x + rl * 2.4, y + rl * 2.4), fill=c + (70,))
                d.ellipse((x - rl, y - rl, x + rl, y + rl), fill=c + (255,))

    def luciernagas(s, fr, t, z):
        """Lucecitas flotantes (idea del video del ciervo de Luis): bosque dorado, lago y Polo Norte turquesa."""
        capa = Image.new('RGBA', (W // 2, H // 2), (0, 0, 0, 0)); d = ImageDraw.Draw(capa)
        r = np.random.default_rng(31 + z); col = (255, 214, 120) if z == 2 else (140, 240, 255)
        for i in range(60):
            x0, y0, sp, ph = r.uniform(0, W / 2), r.uniform(H * 0.12, H * 0.48), r.uniform(0.3, 1.0), r.uniform(0, 6.3)
            x = (x0 + 30 * math.sin(t * 0.6 * sp + ph) - t * 25 * sp) % (W / 2); y = y0 + 18 * math.sin(t * 0.9 * sp + ph * 2)
            br = 0.5 + 0.5 * math.sin(t * 2.5 * sp + ph * 3)
            R = 7 + 6 * sp; d.ellipse((x - R, y - R, x + R, y + R), fill=col + (int(70 * br),))
            r2 = 1.6 + 1.2 * sp; d.ellipse((x - r2, y - r2, x + r2, y + r2), fill=(255, 255, 240, int(150 + 105 * br)))
        capa = capa.filter(ImageFilter.GaussianBlur(1.5)).resize((W, H), Image.BILINEAR)
        fr.paste(capa, (0, 0), capa)

    def nieve(s, fr, t, z):
        """Copos cayendo (en el cielo de Nochebuena: destellos dorados)."""
        d = ImageDraw.Draw(fr, 'RGBA'); r = np.random.default_rng(9); vel = 1 + float(s.velk[min(int(t * FPS), len(s.velk) - 1)]) / 6000
        dorado = z == 8
        for i in range(110):
            x0, ph, sz, sp = r.uniform(0, W), r.uniform(0, 1), r.uniform(2, 7), r.uniform(0.6, 1.4)
            y = ((ph + t * 0.12 * sp * vel) % 1.0) * (H + 40) - 20
            x = (x0 + 40 * math.sin(t * sp + i) - (y - H / 2) * 0.15 * (vel - 1)) % W
            c = (255, 220, 120) if dorado else (255, 255, 255)
            d.ellipse((x - sz, y - sz, x + sz, y + sz), fill=c + (int(150 + 80 * sp / 1.4),))

    # ---- regalos DENTRO del mundo (Luis: que no tapen la carretera): vienen desde lejos por el camino, a los costados,
    # sobre la nieve, con globos o colgando del túnel; al responder bajan y se cruzan en el camino de MAX y NOVA.
    puerta_limita = False
    agil = True
    puerta_techo = 215
    ZH = 2400.0

    def puerta_z(s, t, esc, Pq, a):
        t0, tt, tr, tch = esc[0], Pq['tt'], Pq['tr'], Pq['tch']; ZH = s.ZH
        tc = Pq['tc']
        if t < tc:   # llegan por el camino mientras se lee la pregunta (visibles durante toda la cuenta)
            u = clamp((t - t0) / max(0.4, tc - t0)); return ZH + (26000 - ZH) * (1 - u) ** 1.35
        if t < tr: return ZH - 300 * clamp((t - tc) / max(0.1, tr - tc))
        return (ZH - 300) - (ZH - 300 - C.ZRUN) * clamp((t - tr) / Pq['vuelo']) ** 1.6 - max(0, t - tch) * 3600 * a

    def estilo_regalo(s, idx):
        Pq = s.tr_preg.get(idx) if hasattr(s, 'tr_preg') else None
        if Pq is not None:
            dd = s.d_en(Pq['tt']) + s.ZH; j = int(dd // SEG)
            if 0 <= j < s.P.n and s.P.tunel[j]: return 'colgado'
        return ('suelo', 'nieve')[idx % 2]

    def puerta_tam(s, idx, i):
        return (0.92, 1.0, 1.08, 0.86, 1.12)[(idx * 2 + i) % 5]

    def puerta_xy(s, z, i, idx, t, Pq):
        est = s.estilo_regalo(idx); lado = -1 if i == 0 else 1
        u = ease_out(clamp((t - Pq['tr']) / Pq['vuelo']))       # 0 mientras se lee; 1 al chocar
        X = lado * (C.ROADW * 0.9 + (C.PX - C.ROADW * 0.9) * u)
        Y = {'suelo': 0, 'nieve': 0, 'globo': 160 + 50 * math.sin(t * 2.1 + i * 2), 'colgado': 300}[est] * (1 - u)
        if est == 'colgado': X += 110 * math.sin(t * 2.2 + i * 1.3) * (1 - u)
        if est == 'globo': X += 40 * math.sin(t * 1.3 + i) * (1 - u)
        s._pinfo[(idx, i)] = (est, Y)
        return s.en_s(z, X, Y)

    _pinfo = {}

    def adorno_regalo(s, d, cx, y, im, i, idx, sc):
        """Globos, cuerda del túnel o montoncito de nieve, según el estilo del regalo."""
        est, Y = s._pinfo.get((idx, i), ('suelo', 0)); w = im.width
        if est == 'globo' and Y > 30:
            cols = [(255, 80, 90), (255, 214, 70), (90, 200, 255), (140, 230, 120), (220, 120, 255)]
            for k, dx in enumerate((-0.28, 0.0, 0.3)):
                bx = cx + dx * w + 10 * math.sin(s._t * 2 + k); by = y - w * (0.42 + 0.1 * (k == 1)); r = w * 0.15
                d.line([(cx + dx * w * 0.3, y + w * 0.05), (bx, by + r)], fill=(250, 250, 250, 220), width=max(1, int(w / 220)))
                c = cols[(idx + k + i) % len(cols)]
                d.ellipse((bx - r * 0.85, by - r, bx + r * 0.85, by + r), fill=c + (255,))
                d.ellipse((bx - r * 0.45, by - r * 0.7, bx - r * 0.1, by - r * 0.25), fill=(255, 255, 255, 120))
        elif est == 'colgado' and Y > 30:
            top = y + w * 0.06 - sc * 3000 * PH
            for dx_ in (-0.18, 0.18):   # dos cintas doradas que bajan del arco del túnel
                d.line([(cx + dx_ * w, y + w * 0.12), (cx + dx_ * w * 0.4, top)], fill=(255, 205, 70, 255), width=max(3, int(w / 45)))
        elif est == 'nieve':
            h = im.height; d.ellipse((cx - w * 0.62, y + h - w * 0.12, cx + w * 0.62, y + h + w * 0.1), fill=NIEVE + (255,))

    # ---- puertas = regalos
    def puertas_de(s, idx, q):
        if idx not in s.puertas:
            if len(s.puertas) > 4: s.puertas.pop(next(iter(s.puertas)))
            f = s.fotos(q); v = (idx * 3) % len(REG_VAR)
            s.puertas[idx] = [Regalo(f[0], 'A', COL_A, v), Regalo(f[1], 'B', COL_B, v + 1 + idx % 3)]
        return s.puertas[idx]

    def dibujar_puertas(s, fr, lista, t, adelante=False):
        """Como en la ciudad, pero el regalo equivocado queda cubierto de nieve (en vez de ladrillos)."""
        if not lista: return
        c = s._ctx; q, Pq = c['q'], c['Pq']; d = ImageDraw.Draw(fr, 'RGBA')
        idx = C.c_idx(s, q); s._t = t
        for cx, cy, im, i, ok, sc in sorted(lista, key=lambda x: x[5]):
            y = cy - im.height
            if t < Pq['tch']: s.adorno_regalo(d, cx, y, im, i, idx, sc)
            fr.paste(im, (int(cx - im.width / 2), int(y)), im); esc_ = im.width / 900
            if esc_ > 0.25 and t < Pq['tch']: s._etq.append((cx, y + im.height * 0.86, esc_, s.puertas_de(C.c_idx(s, q), q)[i].foto.nombre.upper(), (COL_A, COL_B)[i]))
            fichas = [(nom, col) for quien, nom, col, t0 in (('presentador', 'MAX', R0.MAXC, Pq['t_m']), ('copresentadora', 'NOVA', R0.NOVAC, Pq['t_n']))
                      if t >= t0 and Pq['ap'][quien] == i]
            if fichas and esc_ > 0.2:
                ff = font('Black', max(10, int(54 * esc_))); x = cx - (len(fichas) - 1) * 130 * esc_
                for nom, col in fichas:
                    tw = d.textlength(nom, font=ff); hh = ff.size * 1.3; yy = y + 290 * esc_
                    d.rounded_rectangle((x - tw / 2 - 20 * esc_, yy - hh / 2, x + tw / 2 + 20 * esc_, yy + hh / 2), int(hh / 2), fill=col, outline=BLANCO, width=max(2, int(5 * esc_)))
                    d.text((x, yy), nom, font=ff, fill=TINTA, anchor='mm'); x += 260 * esc_
            if t >= Pq['tch'] - 0.02 and not ok:
                h, w = im.height, im.width; u = clamp((t - Pq['tch']) / 0.25); rr = np.random.default_rng(i * 7 + 3)
                for _ in range(26):   # plasta de nieve
                    px, py, pr_ = cx + rr.uniform(-0.42, 0.42) * w, y + h * rr.uniform(0.3, 0.92), w * rr.uniform(0.07, 0.16) * ease_back(u)
                    d.ellipse((px - pr_, py - pr_, px + pr_, py + pr_), fill=NIEVE + (245,))
                if not c['en_nave']:
                    for quien in ('presentador', 'copresentadora'):
                        if Pq['ap'][quien] == i and t - Pq['tch'] <= 0.45:
                            ims = C.poses_flow(s.corr)['max_estrella' if quien == 'presentador' else 'nova_estrella']
                            ww, hh = int(ims.width * esc_ * 1.45), int(ims.height * esc_ * 0.82)
                            if ww > 4 and hh > 4:
                                aa = ims.resize((ww, hh), Image.BILINEAR); fr.paste(aa, (int(cx - ww / 2 + (60 if quien == 'copresentadora' else -60) * esc_), int(y + h * 0.6 - hh / 2)), aa)
                    ff = font('Black', max(10, int(150 * esc_)))
                    d.text((cx, y + 80 * esc_), '¡PLAF!', font=ff, fill=ORO, anchor='mm', stroke_width=max(2, int(10 * esc_)), stroke_fill=TINTA)

    # ---- corredores con gorro y el trineo
    def obstaculos(s, fr, t, cerca):
        """Dibuja los obstáculos: los lejanos antes de los corredores, los que ya pasaron (cerca) después."""
        cam = s._cam
        for tj, kind in s.obst:
            if not (tj - 4.0 < t < tj + 0.6): continue
            srel = s.d_en(tj) + C.ZP - cam
            if srel < 120 or srel > DRAW * SEG * 0.9: continue
            if (srel < C.ZP) != cerca: continue
            cx, cy, sc = s.en_s(srel, 0, 0); ancho = sc * 1500 * PW
            if ancho < 6: continue
            im = obst_img(kind, ancho)
            if kind == 'hielo':   # el dragón le echa fuego y se derrite
                u = clamp((t - (tj - 0.45)) / 0.35)
                if u >= 1: continue
                if u > 0:
                    im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v, f=1 - u: int(v * f)))
                    dx, dy = s._drag_xy
                    s.fuego(ImageDraw.Draw(fr, 'RGBA'), dx, dy, cx, cy - im.height / 2, u, int(t * 10))
            fr.paste(im, (int(cx - im.width / 2), int(cy - im.height)), im)
        if cerca: return
        d = ImageDraw.Draw(fr, 'RGBA')
        for tk, X in s.estrellas:
            if not (tk - 3.0 < t < tk + 0.35): continue
            if t >= tk:   # recogida: destello que sube
                u = (t - tk) / 0.35; x_, y_ = 960 + X * 0.9, 760 - 200 * u
                for k_ in range(6):
                    a_ = k_ * math.pi / 3 + t * 4; estrella(d, x_ + math.cos(a_) * 60 * u, y_ + math.sin(a_) * 60 * u, 14 * (1 - u) + 3, ORO)
                continue
            srel = s.d_en(tk) + C.ZP - cam
            if srel < 150: continue
            cx, cy, sc = s.en_s(srel, X, 260 + 40 * math.sin(t * 5 + tk))
            r = min(70, sc * 230 * PW)
            if r < 2: continue
            d.ellipse((cx - r * 1.8, cy - r * 1.8, cx + r * 1.8, cy + r * 1.8), fill=(255, 220, 110, 60))
            estrella(d, cx, cy, r, ORO)

    def corredores(s, fr, t, xm, xn, extra):
        for tj, kind in s.obst:   # salto sobre el obstáculo (rampa: gran salto; hielo: lo derrite el dragón)
            if kind == 'hielo': continue
            if kind == 'rampa':
                if -0.1 < t - tj < 1.2: extra['salto'] = (t - tj + 0.1) / 1.3; extra['alto'] = 2.3
            elif abs(t - tj) < 0.38: extra['salto'] = (t - tj + 0.38) / 0.76
        s.obstaculos(fr, t, False)
        s._corredores(fr, t, xm, xn, extra)
        s.obstaculos(fr, t, True)

    def _corredores(s, fr, t, xm, xn, extra):
        c = s.corr
        v0 = s.vehiculo_en(t)
        libres = not any(k in extra for k in ('salto', 'cae', 'ocultar', 'dy')) and not extra.get('flota') and \
                 not any(extra.get(k) is not None for k in ('plaf_presentador', 'plaf_copresentadora'))
        if v0 == 'corre' and libres and abs(xm - 690) < 3 and abs(xn - 1230) < 3 and not (s.hablando(t, 'presentador') or s.hablando(t, 'copresentadora')):
            im = anim_img('corren', 600, t)    # MAX y NOVA corriendo de verdad (clip de Flow)
            if im is not None:
                fr.paste(im, (int(960 - im.width / 2), int(H + 30 - im.height)), im); return
        if not hasattr(c, '_nav'):
            A = R0.Corredores.ALTO
            m = nav_img('max_gorro', A); n = nav_img('nova_gorro', A)
            c.max = [m, ImageOps.mirror(m)]; c.max_mira = m; c.nova = [n, ImageOps.mirror(n)]; c.nova_mira = n; c._nav = True
        v = s.vehiculo_en(t)
        if v in VEH_NAV:   # vehículos navideños de Flow (dragón con trineo, reno gigante, trineo de madera, patines)
            alto, base, bote, fq = VEH_NAV[v]
            u = clamp((t - s.veh_desde(t)) / 0.6); x = (xm + xn) / 2
            if v == 'patines': x += 60 * math.sin(t * 1.3)          # se deslizan de lado a lado
            y = base + bote * abs(math.sin(t * fq)) + extra.get('dy', 0) + 600 * (1 - ease_back(u)) - 230 * extra.get('alto', 1) * math.sin(math.pi * clamp(extra.get('salto', 0)))
            im = anim_img(v, alto, t); animado = im is not None
            if not animado: im = nav_img(v, alto)
            if animado: bote = bote * 0.15     # el clip ya trae su propio galope
            y = base + bote * abs(math.sin(t * fq)) + extra.get('dy', 0) + 600 * (1 - ease_back(u)) - 230 * extra.get('alto', 1) * math.sin(math.pi * clamp(extra.get('salto', 0)))
            a = math.sin(t * 4.5)
            if v == 'trineo': im = im.resize((int(im.width * (1 + 0.04 * a)), int(im.height * (1 - 0.02 * a))), Image.BILINEAR)
            im = im.rotate(-(xm + xn - 1920) / 1920 * 10 + (4 * math.sin(t * 1.3) if v == 'patines' else 0), Image.BILINEAR, expand=True)
            fr.paste(im, (int(x - im.width / 2), int(y - im.height)), im); return
        super().corredores(fr, t, xm, xn, extra)

    # ---- el dragón: vuela delante de ellos (lo vemos de espaldas), crece con cada pregunta y sube de nivel
    def prog_nivel(s, t):
        nv, t0 = s.nivel_en(t)
        t1 = next((tt for tt, k in s.nv_t if k == nv + 1), s.t)
        return nv, clamp((t - t0) / max(1.0, t1 - t0))

    def fuego(s, d, x0, y0, x1, y1, u, seed):
        r = np.random.default_rng(seed)
        for k in range(36):
            f = (k / 36 + u * 1.5) % 1.0
            x = x0 + (x1 - x0) * f + r.uniform(-1, 1) * 40 * f; y = y0 + (y1 - y0) * f + r.uniform(-1, 1) * 40 * f
            R = 14 + 70 * f; c = [(255, 250, 180), (255, 210, 60), (255, 140, 30), (240, 60, 30)][min(3, int(f * 4))]
            d.ellipse((x - R, y - R, x + R, y + R), fill=c + (int(220 * (1 - f * 0.6)),))

    def mascota(s, fr, t, esc):
        tipo = esc[2][0] if esc else ''
        d = ImageDraw.Draw(fr, 'RGBA')
        if tipo == 'intro':   # gancho: así de grande puede llegar a ser
            u = clamp((t - esc[0]) / 0.45); sc = max(0.05, ease_back(u)) if u < 1 else 1.0
            im = anim_img('trineo', max(20, int(640 * sc)), t) or nav_img('trineo', max(20, int(640 * sc))); y = 410 + 16 * math.sin(t * 3)
            for r_ in range(3):
                R = (260 + 110 * r_) * sc; d.ellipse((W / 2 - R, y + 300 - R, W / 2 + R, y + 300 + R), fill=(255, 200, 80, 34))
            fr.paste(im, (int(W / 2 - im.width / 2), int(y)), im)
            d.text((W / 2, 270), '¿LLEGARÁS A CRIAR', font=font('Black', max(10, int(96 * sc))), fill=BLANCO, anchor='mm', stroke_width=10, stroke_fill=TINTA)
            d.text((W / 2, 375), '¡ESTE DRAGÓN?', font=font('Black', max(10, int(110 * sc))), fill=ORO, anchor='mm', stroke_width=10, stroke_fill=TINTA)
            return
        if tipo == 'crece':
            tc, et_, k = esc[2][1], esc[2][2], esc[2][3]
            if t < tc:   # brilla, tiembla y se agranda
                u = clamp((t - esc[0]) / max(0.1, tc - esc[0])); prev = DRAGON_NV[k - 1]
                alto = int(prev[2] * (1.2 + 0.5 * u)); x = W / 2 + 14 * u * math.sin(t * 55); y = 600
                for r_ in range(4):
                    R = (200 + 90 * r_) * (0.7 + u); d.ellipse((x - R, y - R, x + R, y + R), fill=(255, 200, 70, int(30 + 40 * u)))
                im = etapa_img(prev[0], alto, t); fr.paste(im, (int(x - im.width / 2), int(y - im.height / 2)), im)
                d.text((W / 2, 300), '¡ESTÁ CRECIENDO!', font=font('Black', 110), fill=ORO, anchor='mm', stroke_width=10, stroke_fill=TINTA)
            else:
                u = clamp((t - tc) / 0.5); sc = max(0.05, ease_back(u)) if u < 1 else 1.0
                im = etapa_img('trineo' if k == NMAX_NV else et_, max(20, int(760 * sc)), t)
                y = 640 + 18 * math.sin(t * 2.5)
                for k_ in range(16):
                    a_ = k_ * 2 * math.pi / 16 + t * 1.5; R = 430 + 30 * math.sin(t * 6 + k_)
                    estrella(d, W / 2 + math.cos(a_) * R * 1.35, y + math.sin(a_) * R * 0.7, 24, ORO)
                fr.paste(im, (int(W / 2 - im.width / 2), int(y - im.height / 2)), im)
                d.text((W / 2, 300), f'¡NIVEL {k}!', font=font('Black', max(10, int(150 * sc))), fill=ORO, anchor='mm', stroke_width=12, stroke_fill=TINTA)
                d.text((W / 2, 420), NV_TXT[k], font=font('Black', max(10, int(84 * sc))), fill=BLANCO, anchor='mm', stroke_width=9, stroke_fill=TINTA)
                if t - tc < 0.25: fr.paste(Image.new('RGB', (W, H), (255, 255, 255)), (0, 0), Image.new('L', (W, H), int(255 * (1 - (t - tc) / 0.25))))
            return
        if tipo == 'huevo':
            u = clamp((t - esc[0]) / 0.5); sc = max(0.05, ease_back(u)) if u < 1 else 1.0
            im = dragon_nav('huevo', max(20, int(560 * sc))); y = 620 + 14 * math.sin(t * 3)
            R = 340; d.ellipse((W / 2 - R, y - R, W / 2 + R, y + R), fill=(255, 190, 60, 45))
            fr.paste(im, (int(W / 2 - im.width / 2), int(y - im.height / 2)), im)
            d.text((W / 2, 270), '¡UN HUEVO DE DRAGÓN!', font=font('Black', max(10, int(110 * sc))), fill=ORO, anchor='mm', stroke_width=10, stroke_fill=TINTA)
            return
        nv, prog = s.prog_nivel(t)
        if tipo == 'nace' or nv == 0: return super().mascota(fr, t, esc)
        if s.vehiculo_en(t) in ('trineo', 'montados'): s.barra_dragon(fr, t); return
        img, a0, a1, _ = DRAGON_NV[nv]; alto = a0 + (a1 - a0) * prog
        x = 960 + 330 * math.sin(t * 0.42) + 90 * math.sin(t * 1.17); y = 400 + 30 * math.sin(t * 1.6) + alto * 0.12
        ang = -9 * math.cos(t * 0.42); rot = 0.0; fuego_a = None; ancho_max = None
        if tipo == 'pregunta':
            q = s.Q[esc[2][1]]; Pq = esc[2][2]; dt = t - Pq['tch']
            if t < Pq['tch'] + 0.05:   # mientras se responde: en el carril del medio, sin tapar los regalos
                u_ = clamp((t - esc[0]) / 0.4); x = x + (960 + 40 * math.sin(t * 0.8) - x) * ease_out(u_)
                y = y + (300 + 20 * math.sin(t * 1.6) - y) * ease_out(u_); ancho_max = 380 + (900 - 380) * (1 - ease_out(u_))
            if 0 <= dt < 1.4:
                u = dt / 1.4
                if nv >= NV_PIRUETA:   # pirueta: da una vuelta completa en el aire
                    rot = 360 * ease_out(u); x += 170 * math.sin(2 * math.pi * u); y -= 170 * (1 - math.cos(2 * math.pi * u))
                else: y -= 140 * math.sin(math.pi * u); alto *= 1 + 0.15 * math.sin(math.pi * u)
                malo = [quien for quien in ('presentador', 'copresentadora') if Pq['ap'][quien] != q['c']]
                if nv >= NV_FUEGO and malo and 0.1 < dt < 1.2:
                    lado = -1 if q['c'] == 1 else 1; fuego_a = (960 + lado * 430, 470, dt)
        elif tipo == 'nivel':   # cambio de paisaje: pasa volando de lado a lado
            u = clamp((t - esc[0]) / max(0.1, esc[1] - esc[0])); x = 1800 - 1680 * ease_out(u); y = 380; ang = 12
        if nv >= NV_BRILLA:
            for r_ in range(3):
                R = alto * (0.55 + 0.18 * r_) * (1 + 0.05 * math.sin(t * 4)); d.ellipse((x - R, y - R, x + R, y + R), fill=(255, 220, 110, 26))
        if nv >= 2:   # estela de chispitas
            for k_ in range(7):
                tt = t - k_ * 0.07; xx = 960 + 330 * math.sin(tt * 0.42) + 90 * math.sin(tt * 1.17) if tipo != 'nivel' else x + k_ * 40
                estrella(d, xx + 30 * math.sin(k_ * 2.1), y + alto * 0.42 + k_ * 9, max(3, 11 - k_), ORO)
        w0 = etapa_img(img, 100).width / 100
        alto = min(alto, (ancho_max or 760) / max(0.3, w0))   # que quepa entre los regalos / no tape todo
        im = anim_img('dragon_' + img, max(20, int(alto)), t); a_ = math.sin(t * 6.5)
        if im is None:
            im = etapa_img(img, max(20, int(alto)))
            im = im.resize((max(1, int(im.width * (1 + 0.08 * a_))), max(1, int(im.height * (1 - 0.03 * a_)))), Image.BILINEAR)
        im = im.rotate(ang + rot, Image.BILINEAR, expand=True)
        fr.paste(im, (int(x - im.width / 2), int(y - im.height / 2)), im); s._drag_xy = (x, y - alto * 0.38)
        if tipo == 'pregunta':   # el acierto alimenta al dragón: una estrella «+1» vuela del regalo correcto hasta él
            q = s.Q[esc[2][1]]; Pq = esc[2][2]; dt = t - Pq['tch'] - 0.1
            if 0 <= dt < 1.1:
                gx, gy = 960 + (-430 if q['c'] == 0 else 430), 520
                if dt < 0.7:
                    p_ = ease_out(dt / 0.7); sx = gx + (x - gx) * p_; sy = gy + (y - gy) * p_ - 160 * math.sin(math.pi * p_)
                    estrella(d, sx, sy, 34, ORO)
                    d.text((sx + 46, sy - 10), '+1', font=font('Black', 52), fill=ORO, anchor='mm', stroke_width=6, stroke_fill=TINTA)
                else:
                    u = (dt - 0.7) / 0.4; R = alto * (0.4 + 0.5 * u)
                    d.ellipse((x - R, y - R, x + R, y + R), outline=(255, 220, 110, int(230 * (1 - u))), width=max(2, int(14 * (1 - u))))
                    for k_ in range(8):
                        a2 = k_ * math.pi / 4 + t; estrella(d, x + math.cos(a2) * R, y + math.sin(a2) * R, 14 * (1 - u) + 2, ORO)
        if fuego_a:
            fx, fy, dt = fuego_a; self_mouth = (x, y - alto * 0.38)
            s.fuego(d, self_mouth[0], self_mouth[1], fx, fy, dt, int(t * 10))

    def barra_dragon(s, fr, t):
        nv, prog = s.prog_nivel(t)
        if nv == 0: return
        d = ImageDraw.Draw(fr, 'RGBA'); x0, y0, w = 24, H - 116, 230
        d.rounded_rectangle((x0, y0, x0 + w, y0 + 92), 22, fill=(18, 10, 46, 235), outline=ORO, width=4)
        d.text((x0 + w / 2, y0 + 26), f'DRAGÓN NV {nv}', font=font('Black', 30), fill=ORO, anchor='mm')
        if nv < NMAX_NV:
            d.rounded_rectangle((x0 + 14, y0 + 52, x0 + w - 14, y0 + 78), 13, fill=(50, 36, 90))
            d.rounded_rectangle((x0 + 14, y0 + 52, x0 + 14 + max(26, (w - 28) * prog), y0 + 78), 13, fill=ORO)
            d.text((x0 + w / 2, y0 + 65), f'{int(prog * 100)}%', font=font('Black', 20), fill=TINTA if prog > 0.5 else BLANCO, anchor='mm')
        else: d.text((x0 + w / 2, y0 + 65), '¡MÁXIMO!', font=font('Black', 26), fill=BLANCO, anchor='mm')

    # ---- carteles y HUD con las 9 zonas
    def carteles(s, fr, t, esc):
        if esc and esc[2][0] == 'nivel':
            k = esc[2][1]; Z = ZONAS[k]; d = ImageDraw.Draw(fr)
            u = clamp((t - esc[0]) / 0.25); sc = max(0.01, ease_back(u))
            if sc > 0.02:
                d.text((W / 2, 420), Z['n'], font=font('Black', max(10, int(120 * sc))), fill=ORO, anchor='mm', stroke_width=10, stroke_fill=TINTA)
            return
        super().carteles(fr, t, esc)

    def centro(s, fr, t, cont):
        if cont is not None: return super().centro(fr, t, cont)
        if s.hablando(t, 'anunciador'):
            b = s.boca(t, 'anunciador'); sp = C.voz_sprite(b, int(t * 12) % 12 if b else 0).resize((170, 170), Image.BILINEAR)
            C.pegar_centro(fr, sp, 125, 855)

    def hud_c(s, fr, t, n_actual, zona, pregunta):
        zona = s.zona_en(t); Z = ZONAS[zona]
        d = ImageDraw.Draw(fr)
        if pregunta:
            f = font('Black', 64); tw = d.textlength(pregunta, font=f)
            while tw > 1180 and f.size > 36: f = font('Black', f.size - 4); tw = d.textlength(pregunta, font=f)
            d.rounded_rectangle((W / 2 - tw / 2 - 40, 26, W / 2 + tw / 2 + 40, 126), 50, fill=(18, 10, 46), outline=ORO, width=4)
            d.text((W / 2, 76), pregunta, font=f, fill=BLANCO, anchor='mm')
        s.barra_dragon(fr, t); d = ImageDraw.Draw(fr)
        piezas = [(f'{n_actual}/{s.N}', ORO, TINTA), (Z['n'], Z['col'], BLANCO)]
        f = font('Bold', 30); anchos = [d.textlength(p, font=f) + 44 for p, _, _ in piezas]
        neq = len([1 for t0, _ in s.equipo if t >= t0]); extra_w = (170 + 48 * min(8, neq)) if neq else 0
        x = W / 2 - (sum(anchos) + 20 + extra_w) / 2
        for (txt, bg, fg), w in zip(piezas, anchos):
            d.rounded_rectangle((x, 146, x + w, 194), 24, fill=bg); d.text((x + w / 2, 170), txt, font=f, fill=fg, anchor='mm'); x += w + 20
        s._pill_fin = x - 20
        (pm, pn), pop = s.marcador_en(t)
        for quien, nom, col, pts_, x0, pp in (('presentador', 'MAX', R0.MAXC, pm, 24, pop[0]), ('copresentadora', 'NOVA', R0.NOVAC, pn, W - 24 - 230, pop[1])):
            hab = s.hablando(t, quien)
            d.rounded_rectangle((x0, 20, x0 + 230, 290), 26, fill=(18, 10, 46), outline=col, width=6 if hab else 3)
            b = s.boca(t, quien); k = int(t * FPS) + (17 if quien == 'copresentadora' else 0)
            r = R0.retrato(quien, s.pose.get(quien, 'base'), b, (k % 61) in (0, 1)); fr.paste(r, (x0 + 15, 30), r)
            sc = 1.35 if pp else 1.0; d = ImageDraw.Draw(fr)
            d.rounded_rectangle((x0 + 10, 232, x0 + 220, 282), 25, fill=col)
            d.text((x0 + 115, 257), f'{nom} {pts_}', font=font('Black', int(40 * sc)), fill=TINTA, anchor='mm')


def miniatura_navidad(meta, out, base='base1.jpg'):
    """Miniatura 1280x720: base de Flow (dragón bebé saliendo del regalo + MAX y NOVA asombrados) + texto grande."""
    im = Image.open(os.path.join(D, 'miniaturas', base)).convert('RGB')
    im = ImageOps.fit(im, (1280, 720), Image.LANCZOS)
    g = Image.new('L', (1, 720)); [g.putpixel((0, y), int(200 * max(0, 1 - y / 260))) for y in range(720)]
    im.paste(Image.new('RGB', im.size, (10, 8, 40)), (0, 0), g.resize(im.size))      # sombra arriba para el título
    d = ImageDraw.Draw(im)
    t1 = '¡CRIAMOS UN DRAGÓN'; t2 = 'DE NAVIDAD!'
    f = font('Black', 92)
    d.text((640, 70), t1, font=f, fill=BLANCO, anchor='mm', stroke_width=10, stroke_fill=TINTA)
    d.text((640, 165), t2, font=font('Black', 104), fill=ORO, anchor='mm', stroke_width=10, stroke_fill=TINTA)
    for txt, x, col in (('A', 120, COL_A), ('B', 1160, COL_B)):   # fichas A / B en las esquinas de abajo
        d.ellipse((x - 85, 545, x + 85, 715), fill=col, outline=BLANCO, width=10)
        d.text((x, 632), txt, font=font('Black', 120), fill=BLANCO, anchor='mm', stroke_width=6, stroke_fill=TINTA)
    im.save(out, quality=92)


def main():
    R0.miniatura = miniatura_navidad
    C.Ciudad = Navidad   # main() de ciudad.py arma con esta clase
    C.main()


if __name__ == '__main__':
    main()
