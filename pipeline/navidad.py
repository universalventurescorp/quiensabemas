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
         tema='Juguetes, inventos y ciencia', col=(176, 30, 40), cam=((150, 96, 60), (136, 86, 54)), ver=(110, 70, 44), borde='baston'),
    dict(n='BOSQUE NEVADO', f='z3_bosque', hz=0.44, casas=None, pinos=2, pub=['bosque'],
         tema='Animales del bosque y árboles', col=(30, 130, 70), cam=((226, 230, 246), (214, 218, 238)), ver=(190, 196, 224), borde='nieve'),
    dict(n='LAGO CONGELADO', f='z4_lago', hz=0.54, casas=None, pinos=1, pub=['lago'],
         tema='Frío, hielo y agua', col=(40, 120, 200), cam=((150, 205, 240), (136, 192, 232)), ver=(200, 220, 240), borde='hielo'),
    dict(n='CIUDAD DE DULCES', f='z5_dulces', hz=0.52, casas=('z5_dulces', (0, 160, 310, 700)), pinos=0, pub=['dulces'],
         tema='Comida y postres', col=(230, 90, 150), cam=((176, 110, 60), (196, 128, 72)), ver=(246, 240, 236), borde='baston'),
    dict(n='POLO NORTE', f='z6_polo', hz=0.60, casas=None, pinos=0, pub=['polar', 'artico'],
         tema='Animales del frío', col=(30, 170, 150), cam=((230, 238, 250), (216, 228, 246)), ver=(190, 214, 240), borde='baston'),
    dict(n='MONTAÑA DE NIEVE', f='z7_montana', hz=0.47, casas=None, pinos=1, pub=['andes'],
         tema='Montañas, volcanes y geografía', col=(90, 110, 170), cam=((240, 242, 248), (226, 230, 242)), ver=(200, 206, 226), borde='nieve'),
    dict(n='SOBRE LOS TEJADOS', f='z8_tejados', hz=0.36, casas=None, pinos=1, pub=['africa', 'andes', 'selva', 'australia'],
         tema='Papá Noel visita este país', col=(150, 60, 160), cam=((150, 70, 60), (132, 60, 52)), ver=(226, 232, 244), borde='luces'),
    dict(n='CIELO DE NOCHEBUENA', f='z9_cielo', hz=0.36, casas=None, pinos=0, pub=['aves'],
         tema='Planetas y estrellas', col=(220, 170, 40), cam=((255, 220, 120), (250, 204, 96)), ver=(80, 70, 140), borde='luces'),
]
COL_A, COL_B = (240, 80, 160), (70, 190, 240)
# vehículo → (alto en pantalla, base y, rebote, frecuencia del rebote)
VEH_NAV = {'trineo': (540, 1090, 16, 2.6), 'reno': (620, 1110, 26, 5.0), 'trineo_madera': (560, 1100, 10, 7.0), 'patines': (470, 1095, 6, 1.6)}


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


_DRAG_NOMBRE = {'huevo': 'huevo', 'bebe_nace': 'nace', 'bebe_vuela': 'bebe_vuela', 'joven': 'joven', 'adulto': 'adulto', 'gigante': 'adulto'}
def dragon_nav(n, alto):
    return nav_img(_DRAG_NOMBRE.get(n, n), alto)


C.dragon_img = dragon_nav    # ciudad.py busca el dragón por este nombre


class Regalo(C.Puerta):
    """Regalo gigante (Flow) con la foto pegada al frente, la letra en un círculo y el nombre abajo."""
    def __init__(s, foto, letra, col):
        s.foto, s.letra, s.col = foto, letra, col
        g = Image.open(os.path.join(D, 'regalo_a.png' if letra == 'A' else 'regalo_b.png')).convert('RGBA')
        w = 900; g = g.resize((w, round(g.height * w / g.width)), Image.LANCZOS); h = g.height
        im = Image.new('RGBA', (w, h + 40), (0, 0, 0, 0)); im.paste(g, (0, 40), g); d = ImageDraw.Draw(im)
        # foto con marco blanco sobre el frente de la caja
        fw, fh = 640, 470; fx, fy = (w - fw) // 2, 40 + int(h * 0.36)
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
        super().__init__(meta, voces)
        s.bancon = os.path.join(RAIZ, 'banco', 'navidad')
        f = os.path.join(s.bancon, 'indice.json')
        if os.path.exists(f): s.TXT.update({k: v.get('texto', '') for k, v in json.load(open(f, encoding='utf-8')).items()})
        fv = os.path.join(RAIZ, 'contenido', 'navidad_voces.json')
        if os.path.exists(fv): s.EST.update({k: v[1][0] for k, v in json.load(open(fv, encoding='utf-8'))['variantes'].items()})
        ini = meta.get('zonas') or [round(k * s.N / 9) for k in range(9)]
        s.zona_ini = {int(i): k for k, i in enumerate(ini) if k > 0}
        s.zona_t = [(0.0, 0)]
        s.drag = [(0.0, 'huevo')]

    # voces: primero las navideñas, luego las de la ciudad y las del formato rápido
    REMAP = {'an_ciudad_intro': 'an_nav_intro', 'an_huevo': 'an_nav_huevo', 'an_final_equipo': 'an_nav_final'}
    def clip(s, clave, est=''):
        clave = s.REMAP.get(clave, clave)
        if os.path.isdir(s.bancon) and any(f.startswith(clave + '__') for f in os.listdir(s.bancon)):
            b = s.banco; s.banco = s.bancon
            try: return R0.Show.clip(s, clave, est)
            finally: s.banco = b
        return super().clip(clave, est)

    def antes_pregunta(s, idx):
        k = s.zona_ini.get(idx)
        if not k: return
        t0 = s.t; s.son('whoosh', t0, 1.0); s.son('golpe', t0 + 0.15, 1.0); s.son('fanfarria', t0 + 0.2, 0.7)
        f = s.decir(f'an_zona_{k + 1}', t0 + 0.3)
        s.esc.append((t0, f + 0.35, ('nivel', k))); s.zona_t.append((t0 + 0.15, k))
        s.capitulos.append((t0, f'Zona {k + 1}: {ZONAS[k]["n"].title()}')); s.drops.append(t0)
        s.t = f + 0.35

    def armar(s):
        super().armar()
        s.capitulos[0] = (0.0, f'Zona 1: {ZONAS[0]["n"].title()}')

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
        # arcos: túnel de pinos en TODO el bosque (zona 3) y arcos de luces en la segunda mitad de la avenida
        s.arco = np.zeros(P.n + 2, np.int8)
        for z, tipo in ((2, 1), (0, 2)):
            js = np.nonzero(s.zseg == z)[0]
            if len(js) < 30: continue
            a, b = js[0] + 12, js[-1] - 12
            if z == 0: a = (js[0] + js[-1]) // 2
            for j in range(a, b, 3): s.arco[j] = tipo
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

    # ---- puertas = regalos
    def puertas_de(s, idx, q):
        if idx not in s.puertas:
            if len(s.puertas) > 4: s.puertas.pop(next(iter(s.puertas)))
            f = s.fotos(q); s.puertas[idx] = [Regalo(f[0], 'A', COL_A), Regalo(f[1], 'B', COL_B)]
        return s.puertas[idx]

    def dibujar_puertas(s, fr, lista, t, adelante=False):
        """Como en la ciudad, pero el regalo equivocado queda cubierto de nieve (en vez de ladrillos)."""
        if not lista: return
        c = s._ctx; q, Pq = c['q'], c['Pq']; d = ImageDraw.Draw(fr, 'RGBA')
        for cx, cy, im, i, ok, sc in sorted(lista, key=lambda x: x[5]):
            y = cy - im.height; fr.paste(im, (int(cx - im.width / 2), int(y)), im); esc_ = im.width / 900
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
    def corredores(s, fr, t, xm, xn, extra):
        c = s.corr
        if not hasattr(c, '_nav'):
            A = R0.Corredores.ALTO
            m = nav_img('max_gorro', A); n = nav_img('nova_gorro', A)
            c.max = [m, ImageOps.mirror(m)]; c.max_mira = m; c.nova = [n, ImageOps.mirror(n)]; c.nova_mira = n; c._nav = True
        v = s.vehiculo_en(t)
        if v in VEH_NAV:   # vehículos navideños de Flow (dragón con trineo, reno gigante, trineo de madera, patines)
            alto, base, bote, fq = VEH_NAV[v]
            u = clamp((t - s.veh_desde(t)) / 0.6); x = (xm + xn) / 2
            if v == 'patines': x += 60 * math.sin(t * 1.3)          # se deslizan de lado a lado
            y = base + bote * abs(math.sin(t * fq)) + extra.get('dy', 0) + 600 * (1 - ease_back(u))
            im = nav_img(v, alto); a = math.sin(t * 4.5)
            if v == 'trineo': im = im.resize((int(im.width * (1 + 0.04 * a)), int(im.height * (1 - 0.02 * a))), Image.BILINEAR)
            im = im.rotate(-(xm + xn - 1920) / 1920 * 10 + (4 * math.sin(t * 1.3) if v == 'patines' else 0), Image.BILINEAR, expand=True)
            fr.paste(im, (int(x - im.width / 2), int(y - im.height)), im); return
        super().corredores(fr, t, xm, xn, extra)

    # ---- el dragón que acompaña
    def mascota(s, fr, t, esc):
        if s.vehiculo_en(t) in ('trineo', 'reno'): return
        tipo = esc[2][0] if esc else ''
        d = ImageDraw.Draw(fr, 'RGBA')
        if tipo == 'crece':
            tc, et_ = esc[2][1], (esc[2][2] if len(esc[2]) > 2 else 'joven')
            if t >= tc:
                u = clamp((t - tc) / 0.5); sc = max(0.05, ease_back(u)) if u < 1 else 1.0
                im = dragon_nav(et_, max(20, int(860 * sc))); fr.paste(im, (int(W / 2 - im.width / 2), int(600 - im.height / 2)), im)
                d.text((W / 2, 200), '¡CRECIÓ!', font=font('Black', max(10, int(150 * sc))), fill=ORO, anchor='mm', stroke_width=12, stroke_fill=TINTA)
                if t - tc < 0.25: fr.paste(Image.new('RGB', (W, H), (255, 255, 255)), (0, 0), Image.new('L', (W, H), int(255 * (1 - (t - tc) / 0.25))))
                return
        if tipo == 'huevo':
            u = clamp((t - esc[0]) / 0.5); sc = max(0.05, ease_back(u)) if u < 1 else 1.0
            im = dragon_nav('huevo', max(20, int(560 * sc))); y = 620 + 14 * math.sin(t * 3)
            R = 340; d.ellipse((W / 2 - R, y - R, W / 2 + R, y + R), fill=(255, 190, 60, 45))
            fr.paste(im, (int(W / 2 - im.width / 2), int(y - im.height / 2)), im)
            d.text((W / 2, 230), '¡UN REGALO… CON UN HUEVO DE DRAGÓN!', font=font('Black', max(10, int(84 * sc))), fill=ORO, anchor='mm', stroke_width=10, stroke_fill=TINTA)
            return
        if s.dragon_en(t) == 'adulto' and tipo not in ('nace',):
            x = 1600 + 70 * math.sin(t * 0.9); y = 560 + 40 * math.sin(t * 1.8)
            im = dragon_nav('adulto', 520); a_ = math.sin(t * 5)
            im = im.resize((int(im.width * (1 + 0.06 * a_)), int(im.height * (1 - 0.03 * a_))), Image.BILINEAR)
            fr.paste(im, (int(x - im.width / 2), int(y - im.height / 2)), im); return
        super().mascota(fr, t, esc)

    # ---- carteles y HUD con las 9 zonas
    def carteles(s, fr, t, esc):
        if esc and esc[2][0] == 'nivel':
            k = esc[2][1]; Z = ZONAS[k]; d = ImageDraw.Draw(fr)
            u = clamp((t - esc[0]) / 0.25); sc = max(0.01, ease_back(u))
            if sc > 0.02:
                d.text((W / 2, 380), f'ZONA {k + 1}', font=font('Black', max(10, int(170 * sc))), fill=Z['col'], anchor='mm', stroke_width=12, stroke_fill=BLANCO)
                d.text((W / 2, 525), Z['n'], font=font('Black', max(10, int(96 * sc))), fill=ORO, anchor='mm', stroke_width=8, stroke_fill=TINTA)
                d.text((W / 2, 630), Z['tema'], font=font('Black', max(10, int(58 * sc))), fill=BLANCO, anchor='mm', stroke_width=6, stroke_fill=TINTA)
            return
        super().carteles(fr, t, esc)

    def hud_c(s, fr, t, n_actual, zona, pregunta):
        zona = s.zona_en(t); Z = ZONAS[zona]
        d = ImageDraw.Draw(fr)
        if pregunta:
            f = font('Black', 64); tw = d.textlength(pregunta, font=f)
            while tw > 1180 and f.size > 36: f = font('Black', f.size - 4); tw = d.textlength(pregunta, font=f)
            d.rounded_rectangle((W / 2 - tw / 2 - 40, 26, W / 2 + tw / 2 + 40, 126), 50, fill=(18, 10, 46), outline=ORO, width=4)
            d.text((W / 2, 76), pregunta, font=f, fill=BLANCO, anchor='mm')
        piezas = [(f'{n_actual}/{s.N}', ORO, TINTA), (f'ZONA {zona + 1} · {Z["n"]}', Z['col'], BLANCO)]
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


def main():
    C.Ciudad = Navidad   # main() de ciudad.py arma con esta clase
    C.main()


if __name__ == '__main__':
    main()
