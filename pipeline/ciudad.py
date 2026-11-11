#!/usr/bin/env python3
"""«¿A o B?» EN LA CIUDAD (10-nov-2026, muestra pedida por Luis).
MAX y NOVA atraviesan una ciudad nocturna por una autopista elevada entre rascacielos: subidas, caídas enormes,
curvas, túnel de luces, un puente roto (caen y la nave los rescata) y una vuelta de cabeza.
Las alternativas son DOS PUERTAS (A y B) que viajan por la carretera con ellos: el que acierta revienta su puerta,
el que falla se estrella contra una pared falsa (¡PLAF!). La respuesta correcta SE UNE AL EQUIPO y vuela con ellos.
Todo acelera; al final, «modo relámpago»: las puertas casi no se ven.
Reutiliza del montador rápido: fotos, voces, sonidos, subtítulos, música y la salida de video.
Uso:
  python3 pipeline/ciudad.py --contenido trabajo/ciudad.json --voces voces_ep --out trabajo/video.mp4 [--cuadros 3,10]
"""
import argparse, json, math, os, random, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

sys.path.insert(0, os.path.dirname(__file__))
import rapido as R0
from rapido import (W, H, SR, FPS, RAIZ, font, ORO, BLANCO, TINTA, MAXC, NOVAC, VERDE, ROJO,
                    ease_out, ease_back, clamp, pegar_centro, retrato, leer, tono, ruido, lp)
from personajes import voz_sprite
import mundos

HZ = 430                 # línea del horizonte
SEG = 200                # largo de un tramo de carretera
ROADW = 900              # semiancho de la autopista
BX = ROADW * 1.32        # donde empiezan los edificios
CAMH = 1000              # altura de la cámara
DEPTH = 1 / math.tan(math.radians(50))   # profundidad de cámara (campo de visión 100°)
ZP = CAMH * DEPTH        # plano donde están los corredores
DRAW = 210               # tramos que se dibujan hacia adelante
PW, PH = 960, 1080 / 2
ZHOLD, ZRUN = 1650.0, 1020.0   # distancia de las puertas mientras se lee / donde chocan con los corredores
PUERTA_W, PUERTA_H = 860, 1000 # tamaño de cada puerta (mundo)
PX = 470                       # centro de cada puerta respecto del centro de la carretera
VP_C = (960, 820)
COL_A, COL_B = (255, 70, 170), (60, 220, 255)
ZONAS = ['AVENIDA NEÓN', 'CIELO DE LA CIUDAD']


# ---------------------------------------------------------------- fondo
def _fondo():
    """Cielo nocturno + luna + dos capas de rascacielos lejanos (se desplazan en las curvas) + abismo con luces."""
    y = np.linspace(0, 1, H)[:, None, None]
    top, mid, bot = np.array([10, 6, 34]), np.array([88, 30, 120]), np.array([255, 110, 120])
    k = np.clip(y / (HZ / H), 0, 1)
    g = np.where(k < 0.75, top + (mid - top) * (k / 0.75), mid + (bot - mid) * ((k - 0.75) / 0.25))
    abajo = np.array([8, 4, 22]) + (np.array([40, 16, 60]) - np.array([8, 4, 22])) * np.clip(1 - (y - HZ / H) / 0.5, 0, 1)
    g = np.where(y < HZ / H, g, abajo)
    cielo = Image.fromarray(np.broadcast_to(g, (H, W, 3)).astype(np.uint8)).convert('RGBA')
    d = ImageDraw.Draw(cielo, 'RGBA'); r = np.random.default_rng(4)
    for _ in range(220):
        x, yy, rr = r.integers(0, W), r.integers(0, HZ - 120), r.uniform(0.7, 2.4)
        d.ellipse((x - rr, yy - rr, x + rr, yy + rr), fill=(255, 255, 255, int(r.integers(70, 230))))
    glow = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dg = ImageDraw.Draw(glow)
    dg.ellipse((1460, 40, 1700, 280), fill=(255, 230, 200, 140))
    cielo = Image.alpha_composite(cielo, glow.filter(ImageFilter.GaussianBlur(40)))
    ImageDraw.Draw(cielo).ellipse((1520, 100, 1640, 220), fill=(255, 244, 225))
    # abismo: luces de la ciudad muy abajo
    d = ImageDraw.Draw(cielo, 'RGBA')
    for _ in range(1400):
        yy = HZ + 4 + (r.random() ** 1.7) * (H - HZ); x = r.integers(0, W)
        rr = 0.6 + 2.2 * (yy - HZ) / (H - HZ); c = [(255, 200, 90), (120, 220, 255), (255, 90, 190)][int(r.integers(0, 3))]
        d.ellipse((x - rr, yy - rr, x + rr, yy + rr), fill=c + (int(r.integers(90, 220)),))
    sky = cielo.convert('RGB')
    # siluetas lejanas (dos capas, más anchas que la pantalla para desplazarlas)
    capas = []
    for i, (col, hmax, ven) in enumerate([((44, 20, 84), 260, (255, 170, 90)), ((26, 12, 56), 170, (120, 220, 255))]):
        im = Image.new('RGBA', (W * 2, 300), (0, 0, 0, 0)); d = ImageDraw.Draw(im, 'RGBA'); rr = np.random.default_rng(20 + i)
        x = 0
        while x < W * 2:
            w = int(rr.integers(40, 130)); h = int(rr.uniform(0.25, 1.0) * hmax)
            d.rectangle((x, 300 - h, x + w, 300), fill=col + (255,))
            if rr.random() < 0.3: d.rectangle((x + w // 2 - 2, 300 - h - 30, x + w // 2 + 2, 300 - h), fill=col + (255,))
            for _ in range(int(w * h / 600)):
                wx, wy = x + rr.integers(3, max(4, w - 3)), 300 - rr.integers(4, max(5, h - 4))
                d.rectangle((wx, wy, wx + 2, wy + 3), fill=ven + (int(rr.integers(60, 180)),))
            x += w + int(rr.integers(0, 14))
        capas.append(im)
    return sky, capas


# ---------------------------------------------------------------- pista (tramos con curva, altura y marcas)
class Pista:
    def __init__(s, nseg, sem):
        s.n = nseg; s.y = np.zeros(nseg + 2); s.curva = np.zeros(nseg + 2)
        s.tunel = np.zeros(nseg + 2, bool); s.vacio = np.zeros(nseg + 2, bool)
        r = np.random.default_rng(sem)
        i = np.arange(nseg + 2)
        s.y += 220 * np.sin(i / 70.0) + 60 * np.sin(i / 23.0 + 1)   # ondulación suave de fondo
        s.edif = {-1: [], 1: []}
        for lado in (-1, 1):
            j = 0
            while j < nseg:
                L = int(r.integers(3, 9)); h = float(r.uniform(2600, 11000))
                hue = r.integers(0, 4)
                cuerpo = [(34, 20, 70), (24, 26, 64), (48, 22, 72), (20, 18, 48)][hue]
                luz = [(255, 205, 110), (110, 225, 255), (255, 110, 200), (180, 255, 150)][int(r.integers(0, 4))]
                pisos = r.random(80) < r.uniform(0.35, 0.85)
                s.edif[lado].append(dict(s0=j, s1=j + L, h=h, cuerpo=cuerpo, luz=luz, pisos=pisos,
                                         letrero=r.random() < 0.18, prof=float(r.uniform(1400, 2600))))
                j += L + int(r.integers(1, 3))
        s._idx = {}

    def suave(s, a, b, alto):
        """Sube (o baja) la carretera 'alto' unidades entre los tramos a y b, con curva suave; lo de después queda desplazado."""
        a, b = int(a), int(max(a + 1, b))
        if a >= s.n: return
        k = np.arange(a, min(b, s.n + 2)); u = (k - a) / (b - a)
        s.y[a:min(b, s.n + 2)] += alto * (0.5 - 0.5 * np.cos(np.pi * u))
        s.y[min(b, s.n + 2):] += alto

    def caida(s, a, b, alto):
        """Caída que empieza suave y termina en picada (como montaña rusa)."""
        a, b = int(a), int(max(a + 1, b))
        k = np.arange(a, min(b, s.n + 2)); u = (k - a) / (b - a)
        s.y[a:min(b, s.n + 2)] -= alto * (u ** 2 * (3 - 2 * u))
        s.y[min(b, s.n + 2):] -= alto

    def curvas(s, a, b, fuerza):
        a, b = int(a), int(b); k = np.arange(a, min(b, s.n + 2))
        s.curva[a:min(b, s.n + 2)] += fuerza * np.sin(2 * np.pi * (k - a) / max(1, b - a)) * np.sin(np.pi * (k - a) / max(1, b - a))

    def edificios_en(s, lado, j):
        return s.edif[lado]


# ---------------------------------------------------------------- puertas
class Puerta:
    """Puerta A/B con foto (se dibuja una vez grande y luego se escala)."""
    def __init__(s, foto, letra, col):
        s.foto, s.letra, s.col = foto, letra, col
        w, h = 900, int(900 * PUERTA_H / PUERTA_W); b = 26
        im = Image.new('RGBA', (w, h + 90), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        g = Image.new('RGBA', im.size, (0, 0, 0, 0)); dg = ImageDraw.Draw(g)   # resplandor neón
        dg.rounded_rectangle((10, 100, w - 10, h + 80), 60, outline=col + (255,), width=40)
        im = Image.alpha_composite(im, g.filter(ImageFilter.GaussianBlur(18))); d = ImageDraw.Draw(im)
        d.rounded_rectangle((18, 108, w - 18, h + 72), 54, fill=(14, 8, 36, 255), outline=col + (255,), width=b)
        ph = foto.cuadro(w - 2 * b - 40, h - 2 * b - 40 - 120, 1.0)
        m = Image.new('L', ph.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, ph.width - 1, ph.height - 1), 34, fill=255)
        im.paste(ph, (18 + b + 20, 108 + b + 20), m)
        # nombre
        nom = foto.nombre.upper(); f = font('Black', 78)
        while d.textlength(nom, font=f) > w - 120 and f.size > 36: f = font('Black', f.size - 4)
        d.text((w / 2, h + 72 - b - 70), nom, font=f, fill=BLANCO, anchor='mm', stroke_width=6, stroke_fill=TINTA)
        # letra A / B arriba
        d.ellipse((w / 2 - 95, 0, w / 2 + 95, 190), fill=col, outline=BLANCO, width=12)
        d.text((w / 2, 98), letra, font=font('Black', 130), fill=BLANCO, anchor='mm', stroke_width=6, stroke_fill=TINTA)
        s.img = im; s._c = {}
        # circulito de la foto para el equipo
        c = foto.cuadro(300, 300, 1.0); m = Image.new('L', (300, 300), 0); ImageDraw.Draw(m).ellipse((0, 0, 299, 299), fill=255)
        bub = Image.new('RGBA', (330, 330), (0, 0, 0, 0)); db = ImageDraw.Draw(bub)
        db.ellipse((0, 0, 329, 329), fill=ORO + (255,)); bub.paste(c, (15, 15), m)
        s.burbuja = bub

    def escala(s, w):
        w = int(max(8, w)); k = int(round(math.log(w) * 40))
        if k not in s._c:
            if len(s._c) > 60: s._c.clear()
            ww = int(math.exp(k / 40)); s._c[k] = s.img.resize((ww, max(1, int(ww * s.img.height / s.img.width))), Image.BILINEAR)
        return s._c[k]


_bub = {}
def burbuja(p, d):
    k = (id(p), int(d))
    if k not in _bub:
        if len(_bub) > 300: _bub.clear()
        _bub[k] = p.burbuja.resize((max(4, int(d)), max(4, int(d))), Image.BILINEAR)
    return _bub[k]


# ---------------------------------------------------------------- sonidos extra
def sonidos_extra(S):
    L = int(SR * 0.9); t = np.arange(L) / SR; r = np.random.default_rng(12)
    v = lp(ruido(L, 31), 9000) - lp(ruido(L, 31), 2500); v = v * np.exp(-5 * t) * 0.7
    for _ in range(26):   # tintineo de vidrio
        st = int(r.uniform(0, 0.5) * SR); seg = tono(r.uniform(2500, 6500), 0.25, r.uniform(0.04, 0.1), 18); v[st:st + len(seg)] += seg[:L - st]
    S['vidrio'] = v.astype(np.float32)
    L = int(SR * 0.5); t = np.arange(L) / SR
    S['plaf'] = (0.8 * np.sin(2 * np.pi * (120 - 80 * t) * t) * np.exp(-9 * t) + lp(ruido(L, 33), 900) * 0.6 * np.exp(-14 * t)).astype(np.float32)
    L = int(SR * 0.6); t = np.arange(L) / SR
    S['boing'] = (0.25 * np.sin(2 * np.pi * np.cumsum(300 + 250 * np.sin(2 * np.pi * 9 * t) * np.exp(-3 * t)) / SR) * np.exp(-4 * t)).astype(np.float32)
    L = int(SR * 2.4); t = np.arange(L) / SR   # viento de la caída
    S['viento'] = (lp(ruido(L, 41), 1200) * 0.5 * np.sin(np.pi * t / t[-1]) ** 1.5).astype(np.float32)
    S['union'] = (tono(880, 0.12, 0.18, 20) + np.pad(tono(1320, 0.3, 0.2, 9), (int(SR * 0.08), 0))[:int(SR * 0.12)]).astype(np.float32)
    u = np.concatenate([tono(880, 0.1, 0.18, 20), tono(1320, 0.35, 0.2, 8)]); S['union'] = u.astype(np.float32)
    return S


# ---------------------------------------------------------------- el programa
class Ciudad(R0.Show):
    def __init__(s, meta, voces):
        super().__init__(meta, voces)
        s.S = sonidos_extra(s.S)
        s.bancoc = os.path.join(RAIZ, 'banco', 'ciudad')
        f = os.path.join(s.bancoc, 'indice.json')
        if os.path.exists(f): s.TXT.update({k: v.get('texto', '') for k, v in json.load(open(f, encoding='utf-8')).items()})
        s.EST = {k: v[1][0] for k, v in json.load(open(os.path.join(RAIZ, 'contenido', 'ciudad_voces.json'), encoding='utf-8'))['variantes'].items()}
        s.ev = meta.get('eventos', {})            # {"3": "bajada", "antes_6": "puente", ...}
        s.zonas = []; s.feat = []                  # (t0, t1, tipo, extra) rasgos de la pista
        s.nave_desde = None; s.rolls = []; s.caidas_corr = []
        s.veh = [(0.0, 'corre')]
        s.drag = [(0.0, 'huevo')]                  # etapa del dragón de la serie: huevo → bebe → joven → gigante                   # (desde, vehículo) — cambia por pregunta según meta['vehiculos']

    def clip(s, clave, est=''):
        if os.path.isdir(s.bancoc) and any(f.startswith(clave + '__') for f in os.listdir(s.bancoc)):
            b = s.banco; s.banco = s.bancoc
            try: return super().clip(clave, est)
            finally: s.banco = b
        return super().clip(clave, est or s.EST.get(clave, ''))

    # ---- guion
    def armar(s):
        Q, N, Rt = s.Q, s.N, s.R
        pts = [0, 0]; s.pts_t = []; s.tiempos, s.capitulos, s.apuestas = [], [], {}
        s._fotos = {}; s.puertas = {}; s.equipo = []      # (t, idx) se une
        s.vel = []; s.capitulos.append((0.0, f'Zona 1: {ZONAS[0].title()}'))
        s.son('whoosh', 0.0, 0.8); s.t = 0.3
        s.vel.append((0.0, 3200))
        fin = s.decir('an_ciudad_intro', 0.4); s.esc.append((0.0, fin + 0.2, ('intro',))); s.t = fin + 0.25
        t0 = s.t; s.son('campana', t0, 0.6); f = s.decir('an_huevo', t0 + 0.1)          # el huevo de dragón
        s.esc.append((t0, f + 0.3, ('huevo',))); s.t = f + 0.3; s.huevo_t = t0
        reacciones = 0
        for idx, q in enumerate(Q):
            Rt.p = idx / max(1, N - 1); n = q['n']
            modo = 'relampago' if Rt.p > 0.85 else 'rapido' if Rt.p > 0.6 else 'normal'
            # ---- eventos ENTRE preguntas
            s.antes_pregunta(idx)          # gancho (navidad.py: cartel de zona)
            ev = s.ev.get(f'antes_{idx}')
            de = s.m.get('dragon', {}).get(f'antes_{idx}')
            if de == 'nace':   # ¡NACE EL DRAGÓN!
                t0 = s.t; s.son('tiempo', t0, 0.5)
                s.audio.append((t0, R0.riser(1.6))); s.son('golpe', t0 + 1.6, 1.0); s.son('fanfarria', t0 + 1.65, 1.0); s.son('aplausos', t0 + 1.7, 0.9)
                f = s.decir('an_nace', t0 + 1.8); f = s.decir('co_nace', f + 0.1)
                s.drag.append((t0 + 1.6, 'bebe')); s.esc.append((t0, f + 0.4, ('nace', t0 + 1.6))); s.t = f + 0.4
            elif de and de.startswith('crece'):   # 'crece' o 'crece:<etapa>'
                et_ = de.split(':')[1] if ':' in de else 'joven'
                t0 = s.t; s.son('whoosh', t0, 1.0); s.son('golpe', t0 + 0.6, 0.9); s.son('fanfarria', t0 + 0.65, 0.7)
                f = s.decir('an_crece' if et_ == 'joven' else f'an_crece_{et_}', t0 + 0.7)
                s.drag.append((t0 + 0.6, et_)); s.esc.append((t0, f + 0.3, ('crece', t0 + 0.6, et_))); s.t = f + 0.3
            if ev == 'puente':
                t0 = s.t; f1 = s.decir('an_puente', t0 + 0.1); s.son('whoosh', t0, 0.8)
                f2 = s.decir('pr_puente', f1 + 0.05); ts = f2 + 0.05; f3 = s.decir('co_salta', ts)
                s.son('boing', ts, 0.8); s.son('viento', ts + 0.3, 0.9)
                tc = max(f3, ts + 1.2) + 0.3    # caen al vacío
                s.son('cae', tc, 1.0)
                tn = tc + 1.1; s.son('fanfarria', tn, 0.8); s.son('golpe', tn + 0.9, 0.8)
                f4 = s.decir('an_dragon_salva', tn + 0.1); s.veh.append((tn + 0.8, 'dragon')); s.drag.append((tn, 'gigante'))
                fin = max(f4, tn + 1.6) + 0.2
                s.feat.append((t0, ts + 0.6, 'puente', (t0, ts, tc, tn, fin)))
                s.esc.append((t0, fin, ('puente', ts, tc, tn))); s.nave_desde = tn + 0.8
                s.vel.append((t0, 5200)); s.t = fin
                s.capitulos.append((t0, f'Zona 2: {ZONAS[1].title()}'))
                # cartel de zona
                t0 = s.t; s.son('golpe', t0 + 0.1, 1.0); f = s.decir('an_nivel_2', t0 + 0.2)
                s.esc.append((t0, f + 0.3, ('nivel', 1))); s.t = f + 0.3
            elif ev == 'vuelta':
                t0 = s.t; s.son('whoosh', t0, 1.0); f = s.decir('an_vuelta', t0 + 0.05)
                dur = max(2.2, f - t0 + 0.4); s.rolls.append((t0 + 0.2, t0 + dur)); s.son('whoosh', t0 + dur - 0.6, 1.0)
                s.esc.append((t0, t0 + dur + 0.1, ('vuelta',))); s.t = t0 + dur + 0.1
            elif ev == 'relampago':
                t0 = s.t; s.son('golpe', t0, 1.0); f = s.decir('an_relampago', t0 + 0.15)
                s.esc.append((t0, f + 0.25, ('relampago',))); s.drops.append(t0); s.t = f + 0.25
            nv = s.m.get('vehiculos', {}).get(str(idx))
            if nv and nv != s.vehiculo_en(s.t):   # ¡vehículo sorpresa!
                t0 = s.t; s.son('whoosh', t0, 1.0); s.son('pop', t0 + 0.3, 1.0); s.son('fanfarria', t0 + 0.2, 0.6)
                s.veh.append((t0 + 0.3, nv)); f = s.decir(f'an_{nv}', t0 + 0.35)
                s.esc.append((t0, f + 0.25, ('vehiculo', nv))); s.t = f + 0.25
            v = s.velocidad_c(Rt.p); s.vel.append((s.t, v)); s.tempos.append((s.t, Rt.musica))
            # ---- la pregunta
            t_abre = s.t; lleg = Rt.pausa(0.6) if modo != 'relampago' else 0.25
            s.son('whoosh', t_abre, 0.9)
            tipo = s.ev.get(str(idx))
            ini = t_abre + Rt.pausa(0.2)
            if tipo == 'tunel' and s.habla_ev(idx): ini = s.decir('an_tunel', t_abre + 0.1) + 0.05
            if tipo == 'curvas' and s.habla_ev(idx): ini = s.decir('an_curvas', t_abre + 0.1) + 0.05
            if modo == 'relampago':   # no se lee: solo la banda de la pregunta
                fin_p = t_abre + lleg + 0.35 + 0.5 * (1 - (Rt.p - 0.85) / 0.15)
                if q.get('tp'): s.subs.agregar(t_abre + 0.05, np.ones(8, int), 'anunciador', q['tp'], '')
            else:
                fin_p = s.decir(f'q{n:02d}_pregunta', max(ini, t_abre + lleg * 0.6), q['tp'])
            tc = fin_p + Rt.pausa(0.1); dc = {'normal': Rt.cuenta, 'rapido': 1.0, 'relampago': 0.45}[modo]
            if s.agil and modo == 'normal': dc = min(dc, 2.0)    # navidad v2 (Luis): sin esperas largas
            if tipo == 'bajada':   # en la cuenta empieza la caída: todo (puertas incluidas) se va para abajo
                f = s.decir('an_bajada', fin_p + 0.05) if s.habla_ev(idx) else fin_p + 0.1; tc = f + 0.05; dc = max(dc, 2.0)
                s.feat.append((t_abre, tc, 'cima', None)); s.feat.append((tc, tc + dc + 0.6, 'caida', None))
                s.audio.append((tc + 0.1, s.S['viento'])); s.decir('pr_grito', tc + 0.3); s.decir('co_grito', tc + 1.1)
            for k in range(3): s.son('tick_hi' if k == 2 else 'tick', tc + k * dc / 3, 0.9)
            s.audio.append((tc, R0.riser(dc))); s.cuentas.append((tc, tc + dc))
            tt = tc + dc; s.son('tiempo', tt, 0.8)
            fin_t = s.decir('an_tiempo', tt + 0.05) if modo == 'normal' and not s.agil else tt + 0.1
            dif = min(5, int(Rt.p * 6)); ap = {}
            for k, pr in (('presentador', [0.72, 0.66, 0.62, 0.58, 0.55, 0.52][dif]), ('copresentadora', [0.70, 0.66, 0.6, 0.57, 0.55, 0.52][dif])):
                ap[k] = q['c'] if s.rr.random() < pr else 1 - q['c']
            s.apuestas[str(n)] = [ap['presentador'], ap['copresentadora']]
            t_m = fin_t + Rt.pausa(0.05); s.son('pop', t_m)
            if modo == 'normal' and (not s.agil or idx % 4 == 0):
                fin_m = s.decir(s.variante_pick('presentador', ap['presentador']), t_m)
                t_n = fin_m + 0.05 - (0.2 if Rt.p > 0.4 else 0); s.son('pop', t_n)
                fin_n = s.decir(s.variante_pick('copresentadora', ap['copresentadora']), t_n)
            else:
                t_n = t_m + 0.12; s.son('pop', t_n); fin_m = fin_n = t_n + 0.25
            # choque con las puertas
            tr = max(fin_m, fin_n) + Rt.pausa(0.1)
            vuelo = {'normal': 0.42, 'rapido': 0.3, 'relampago': 0.2}[modo]
            tch = tr + vuelo          # momento del impacto
            s.son('whoosh', tr, 0.8); s.son('vidrio', tch, 0.9); s.son('campana', tch, 0.8); s.son('aplausos', tch + 0.05, 0.6)
            m_ok, n_ok = ap['presentador'] == q['c'], ap['copresentadora'] == q['c']
            if s.nave_desde is None or tr < s.nave_desde:
                if not m_ok or not n_ok: s.son('plaf', tch + 0.02, 1.0); s.son('boing', tch + 0.75, 0.7)
            pts[0] += m_ok; pts[1] += n_ok; s.pts_t.append((tch, pts[0], pts[1]))
            if modo == 'relampago':
                fin_r = tch + 0.55
            else:
                fin_r = s.decir(f'q{n:02d}_respuesta', tch + 0.15, q['tr'])
            s.equipo.append((tch + 0.15, idx)); s.son('union', tch + 0.75, 0.8)
            fin = max(fin_r, tch + 1.0) + Rt.pausa(0.15)
            # reacción (golpe o se une al equipo), 1 de cada 2 en modo normal
            if modo == 'normal' and (not s.agil or idx % 4 == 2):
                reacciones += 1
                en_nave = s.nave_desde is not None and tr >= s.nave_desde
                if (not m_ok or not n_ok) and not en_nave and reacciones % 2:
                    fin = s.decir('pr_plaf' if not m_ok else 'co_plaf', fin) + 0.1
                elif idx < 2 or reacciones % 3 == 0:
                    fin = s.decir('an_equipo', fin) + 0.1
            s.esc.append((t_abre, fin, ('pregunta', idx, dict(lleg=lleg, tc=tc, dc=dc, tt=tt, t_m=t_m, t_n=t_n, tr=tr, tch=tch, ap=ap, modo=modo, vuelo=vuelo))))
            if tipo in ('tunel', 'curvas', 'colinas', 'curvas2', 'subida', 'zigzag'): s.feat.append((t_abre, fin, tipo, None))
            s.despues_pregunta(idx, t_abre, fin, tc)
            s.tiempos.append({'n': n, 'abre': round(t_abre, 2), 'reloj': round(tc, 2), 'cierra': round(tt, 2)})
            s.t = fin
        # final: todo el equipo
        Rt.p = 1.0; t0 = s.t; s.son('fanfarria', t0, 0.9); s.capitulos.append((t0, 'El equipo completo'))
        s.pts_t.append((t0, pts[0], pts[1]))
        fin = s.decir('an_final_equipo', t0 + 0.3)
        quien = 'pr_gana' if pts[0] > pts[1] else 'co_gana' if pts[1] > pts[0] else 'an_empate'
        fin = s.decir(quien, fin + 0.15)
        s.esc.append((t0, fin + 1.8, ('final', pts[0] > pts[1], pts[0] == pts[1])))
        s.t = fin + 1.8; s.vel.append((t0, 2500)); s.tempos.append((t0, 1.3)); s.final_pts = tuple(pts)
        # distancia recorrida
        n_fr = int(s.t * FPS) + 2; v = np.zeros(n_fr)
        for i, (t, vv) in enumerate(s.vel):
            a = int(t * FPS); b = int(s.vel[i + 1][0] * FPS) if i + 1 < len(s.vel) else n_fr
            v[a:b] = vv
        k = int(FPS * 0.8); v = np.convolve(np.pad(v, (k, k), mode='edge'), np.ones(2 * k + 1) / (2 * k + 1), 'same')[k:-k]   # sin saltos de velocidad
        s.velk = v; s.dist = np.cumsum(v / FPS); s.paso = np.cumsum((2.2 + v / 3000) / FPS)
        s.construir_pista()

    def antes_pregunta(s, idx):
        pass

    def despues_pregunta(s, idx, t_abre, fin, tc):
        pass

    puerta_limita = True
    puerta_techo = 0
    agil = False
    def puerta_z(s, t, esc, Pq, a):
        """Distancia de las puertas: llegan, esperan mientras se lee y salen disparadas al choque."""
        tr, tch = Pq['tr'], Pq['tch']; lt = t - esc[0]
        if t < tr: return ZHOLD + (26000 - ZHOLD) * (1 - ease_out(clamp(lt / max(0.05, Pq['lleg']))))
        return ZHOLD - (ZHOLD - ZRUN) * clamp((t - tr) / Pq['vuelo']) ** 1.6 - max(0, t - tch) * 3600 * a

    def puerta_xy(s, z, i, idx, t, Pq):
        return s.en_s(z, (-PX if i == 0 else PX), 0)

    def puerta_tam(s, idx, i):
        return 1.0

    def habla_ev(s, idx):
        """¿El anunciador presenta el rasgo de la pista de esta pregunta? (navidad.py: solo a veces)"""
        return True

    def dragon_en(s, t):
        v = 'huevo'
        for t0, n in s.drag:
            if t >= t0: v = n
        return v

    def vehiculo_en(s, t):
        v = 'corre'
        for t0, n in s.veh:
            if t >= t0: v = n
        return v

    def veh_desde(s, t):
        d = 0.0
        for t0, n in s.veh:
            if t >= t0: d = t0
        return d

    def velocidad_c(s, p):
        base = 3200 + 9000 * p ** 1.3
        return base * (1.25 if s.nave_desde is not None else 1.0)

    def d_en(s, t):
        return float(s.dist[min(len(s.dist) - 1, max(0, int(t * FPS)))])

    def construir_pista(s):
        nseg = int((s.dist[-1] + DRAW * SEG * 1.2) / SEG) + 10
        P = Pista(nseg, s.sem)
        sg = lambda t: s.d_en(t) / SEG
        for t0, t1, tipo, x in s.feat:
            a, b = sg(t0), sg(t1)
            if tipo == 'cima': P.suave(a + (b - a) * 0.15, b + 6, 2600)
            elif tipo == 'caida': P.caida(a + 6, b + 10, 9000)
            elif tipo == 'curvas': P.curvas(a, b + 25, 5.5)
            elif tipo == 'curvas2': P.curvas(a, b + 25, 9.0)
            elif tipo == 'zigzag': P.curvas(a, (a + b) / 2 + 10, 8.0); P.curvas((a + b) / 2 + 10, b + 25, -8.0)
            elif tipo == 'subida': P.suave(a, b + 20, 5200)
            elif tipo == 'colinas':
                k = np.arange(int(a), min(int(b) + 30, P.n)); P.y[k] += 1600 * np.sin((k - a) / 9.0) ** 2
            elif tipo == 'tunel': P.tunel[int(a) + 8:int(b) + 22] = True
            elif tipo == 'puente':
                ta, ts, tc, tn, fin = x
                g0 = int(sg(ts)) + int(ZP / SEG) + 4; g1 = int(sg(tn + 1.2)) + 30   # el hueco empieza justo delante de ellos
                P.vacio[g0:g1] = True
                r = np.random.default_rng(77)
                for lado in (-1, 1):
                    for e in P.edif[lado]:
                        if e['s0'] > g0: e['h'] = -float(r.uniform(400, 3200)); e['letrero'] = r.random() < 0.45
        P.curvas(sg(2) , sg(2) + 260, 1.6)   # alguna curva suave al empezar
        s.P = P
        s.fondo, s.skyline = _fondo()
        cab = np.zeros(len(s.dist))
        for k in range(len(s.dist)):
            i0 = int((s.dist[k] + ZP) / SEG); pend = (P.y[min(P.n, i0 + 14)] - P.y[min(P.n, i0)]) / (14 * SEG)
            cab[k] = np.clip(-pend * 650, -200, 460)     # bajando: el horizonte sube (miramos hacia abajo)
        k = int(FPS * 0.35); s.cabeceo = np.convolve(np.pad(cab, (k, k), mode='edge'), np.ones(2 * k + 1) / (2 * k + 1), 'same')[k:-k]

    # ---- proyección
    def proyectar(s, k):
        """Proyecta los tramos visibles. Devuelve listas por tramo: (j, z, scale, xoff, ycam)."""
        cam = s.dist[min(k, len(s.dist) - 1)]; P = s.P
        base = int(cam // SEG); frac = (cam % SEG) / SEG
        zp_s = (cam + ZP) / SEG; i0 = int(zp_s); u = zp_s - i0
        camY = P.y[i0] * (1 - u) + P.y[i0 + 1] * u + CAMH
        s.hz = HZ + float(s.cabeceo[min(k, len(s.cabeceo) - 1)])      # cabeceo de cámara en subidas y caídas
        xs = []; x = 0.0; dx = -P.curva[base] * frac
        for i in range(DRAW + 2):
            j = base + i
            if j >= P.n: break
            z = j * SEG - cam
            xs.append((j, z, x))
            x += dx; dx += P.curva[j]
        s._cam, s._camY = cam, camY
        s._fila = xs
        s._skyx = getattr(s, '_skyx', 0.0)
        return xs

    def skyx_de(s, k):
        """Desplazamiento acumulado del fondo con las curvas hasta el cuadro k (antes se sumaba cuadro a cuadro)."""
        if not hasattr(s, '_skyx_arr'):
            n = len(s.dist); P = s.P
            idx = np.minimum((np.asarray(s.dist[:n], dtype=np.float64) // SEG).astype(int), P.n - 1)
            s._skyx_arr = np.cumsum(np.asarray(P.curva, dtype=np.float64)[idx] * 0.9)
        a = s._skyx_arr
        return float(a[min(k, len(a) - 1)])

    def pt(s, j_i, X, Y):
        """Punto de mundo (X lateral, Y alto) sobre el tramo de índice local j_i → pantalla."""
        j, z, xoff = s._fila[j_i]
        if z < 30: z = 30
        sc = DEPTH / z
        return (PW + sc * (X + xoff) * PW, s.hz - sc * (Y - s._camY) * PH, sc)

    def en_s(s, srel, X, Y):
        """Proyección de un objeto a distancia srel delante de la cámara (interpola entre tramos)."""
        f = s._fila; cam = s._cam; sa = cam + srel; j = int(sa // SEG); j_i = j - f[0][0]
        if j_i < 0: j_i = 0
        if j_i >= len(f) - 1: j_i = len(f) - 2
        u = clamp((sa - f[j_i][0] * SEG) / SEG)
        xoff = f[j_i][2] * (1 - u) + f[j_i + 1][2] * u
        yb = s.P.y[f[j_i][0]] * (1 - u) + s.P.y[f[j_i + 1][0]] * u
        z = max(30.0, srel); sc = DEPTH / z
        return PW + sc * (X + xoff) * PW, s.hz - sc * (Y + yb - s._camY) * PH, sc

    # ---- dibujo del mundo
    def mundo(s, fr, t, k):
        P = s.P; fila = s.proyectar(k)
        # desplazamiento del fondo con la curva
        s._skyx = s.skyx_de(k)     # precalculado: igual en cualquier máquina y en cualquier tramo (armado repartido)
        dz = int(s.hz - HZ)
        zona = 0 if (s.nave_desde is None or t < s.nave_desde - 0.6) else 1
        tira, hy = FONDOS[zona]; ox = int(s._skyx * 0.5) % (tira.width // 2); oy = hy - HZ - dz
        fr.paste(tira.crop((ox, oy, ox + W, oy + H)))
        for a0, a1, tipo, x in s.feat:   # cayendo al vacío: se ve la ciudad desde arriba
            if tipo == 'puente':
                ta, ts, tc, tn, fin = x; u = clamp((t - tc + 0.2) / 0.5) * (1 - clamp((t - tn - 0.4) / 0.5))
                if u > 0: fr.paste(Image.blend(fr, VACIO, u))
        s._fr = fr
        d = ImageDraw.Draw(fr, 'RGBA')
        # proyecciones por tramo
        pr = []
        for j_i, (j, z, xoff) in enumerate(fila):
            if z <= 40: pr.append(None); continue
            sc = DEPTH / z; cx = PW + sc * xoff * PW; sy = s.hz - sc * (P.y[j] - s._camY) * PH
            pr.append((cx, sy, sc, z))
        # visibilidad (lo que tapa una cima)
        vis = [False] * len(pr); maxy = H + 400
        for i in range(len(pr) - 1):
            a, b = pr[i], pr[i + 1]
            if a is None or b is None: continue
            if b[1] < maxy: vis[i] = True; maxy = min(maxy, b[1])
        fog = lambda c, z: tuple(int(c[q] + (np.array((70, 30, 100))[q] - c[q]) * min(1, z / (DRAW * SEG * 0.95)) ** 1.4) for q in range(3))
        # de lejos a cerca: carretera, túnel y edificios
        edif = {(-1): [e for e in P.edif[-1]], 1: [e for e in P.edif[1]]}
        base = fila[0][0]
        porTramo = {}
        for lado in (-1, 1):
            for e in edif[lado]:
                if e['s1'] < base or e['s0'] > base + len(pr) - 2: continue
                porTramo.setdefault(max(e['s0'], base + 1), []).append((lado, e))
        for i in range(len(pr) - 2, -1, -1):
            a, b = pr[i], pr[i + 1]
            j = fila[i][0]
            if a is not None and b is not None and vis[i] and not P.vacio[j]:
                (x1, y1, s1, z1), (x2, y2, s2, z2) = a, b
                w1, w2 = s1 * ROADW * PW, s2 * ROADW * PW; v1, v2 = s1 * BX * PW, s2 * BX * PW
                par = (j // 3) % 2
                d.polygon([(x1 - v1, y1), (x1 + v1, y1), (x2 + v2, y2), (x2 - v2, y2)], fill=fog((58, 46, 92) if par else (50, 40, 82), z1))   # vereda
                d.polygon([(x1 - w1, y1), (x1 + w1, y1), (x2 + w2, y2), (x2 - w2, y2)], fill=fog((30, 26, 48) if par else (26, 22, 42), z1))   # asfalto
                r1, r2 = w1 * 0.06, w2 * 0.06   # bordes de neón
                for sg_ in (-1, 1):
                    d.polygon([(x1 + sg_ * w1, y1), (x1 + sg_ * (w1 - r1), y1), (x2 + sg_ * (w2 - r2), y2), (x2 + sg_ * w2, y2)], fill=fog((255, 60, 200) if sg_ < 0 else (40, 220, 255), z1 * 0.6))
                if j % 4 < 2:   # línea del medio dorada
                    l1, l2 = w1 * 0.025, w2 * 0.025
                    d.polygon([(x1 - l1, y1), (x1 + l1, y1), (x2 + l2, y2), (x2 - l2, y2)], fill=fog(ORO, z1 * 0.7))
            # edificios que empiezan en este tramo
            for lado, e in porTramo.get(j, []):
                if not P.tunel[e['s0']]: s.edificio(d, e, lado, base, pr)
            # túnel: paredes y techo en cada tramo, arcos de neón cada 4
            if P.tunel[j] and a is not None and b is not None:
                x1, y1, s1, z1 = a; x2, y2, s2, z2 = b
                top = s.hz - s1 * (P.y[j] + 2900 - s._camY) * PH; top2 = s.hz - s2 * (P.y[j + 1] + 2900 - s._camY) * PH
                xl, xr, xl2, xr2 = x1 - s1 * BX * PW, x1 + s1 * BX * PW, x2 - s2 * BX * PW, x2 + s2 * BX * PW
                osc = fog((30, 16, 58) if (j // 2) % 2 else (24, 12, 48), z1)
                d.polygon([(xl, y1), (xl, top), (xl2, top2), (xl2, y2)], fill=osc); d.polygon([(xr, y1), (xr, top), (xr2, top2), (xr2, y2)], fill=osc)
                d.polygon([(xl, top), (xr, top), (xr2, top2), (xl2, top2)], fill=fog((14, 8, 30), z1))
                if j % 4 == 0:
                    col = [(255, 60, 200), (40, 220, 255), ORO][(j // 4) % 3]
                    wd = max(1, int(110 * s2))
                    d.line([(xl2, y2), (xl2, top2), (xr2, top2), (xr2, y2)], fill=fog(col, z2 * 0.4) + (255,), width=wd, joint='curve')
                    d.line([(xl2 + wd, y2 - 4), (xr2 - wd, y2 - 4)], fill=fog(col, z2 * 0.5) + (255,), width=max(1, wd // 3))

    def edificio(s, d, e, lado, base, pr):
        P = s.P
        a_i = e['s0'] - base; b_i = min(e['s1'] - base, len(pr) - 1)
        a_i = max(a_i, 1)
        while a_i < b_i and pr[a_i] is None: a_i += 1
        if a_i >= b_i or pr[b_i] is None: return
        (xa, ya, sa, za), (xb, yb, sb, zb) = pr[a_i], pr[b_i]
        Y0 = P.y[e['s0']]; top = Y0 + e['h']; bot = Y0 - 30000
        def py_(sc, Y): return s.hz - sc * (Y - s._camY) * PH
        Xa = xa + lado * sa * BX * PW; Xb = xb + lado * sb * BX * PW
        if max(abs(Xa - PW), abs(Xb - PW)) > PW * 6 and za < 400: return
        ta, tb = py_(sa, top), py_(sb, top); ba, bb = min(H + 50, py_(sa, bot)), min(H + 50, py_(sb, bot))
        fz = min(1, za / (DRAW * SEG * 0.95)) ** 1.3
        def fog(c, f=fz): return tuple(int(c[q] + ((70, 30, 100)[q] - c[q]) * f) for q in range(3))
        if ta >= ba - 1: return
        fr = s._fr; tex, kk = FACHADAS[(e['s0'] * 7 + (lado > 0)) % len(FACHADAS)], 1024 / 2400
        def yvis(sc): return s._camY - (H + 60 - s.hz) / (sc * PH)
        Ya, Yb = max(bot, yvis(sa)), max(bot, yvis(sb))
        va, vb = min(tex.height - 2, (top - Ya) * kk), min(tex.height - 2, (top - Yb) * kk)
        u0 = ((base + a_i) - e['s0']) * SEG * kk + e['s0'] * 37 % 1024; u1 = u0 + (b_i - a_i) * SEG * kk
        luzf = 1 - fz
        # cara lateral (mira a la carretera): foto de Flow en perspectiva
        quad = [(Xa, ta), (Xb, tb), (Xb, py_(sb, Yb)), (Xa, py_(sa, Ya))]
        pegar_quad(fr, tex, quad, [(u0, 0), (u1, 0), (u1, vb), (u0, va)], fog=fz, sombra=0.35)
        # cara frontal (mira a la cámara)
        Xo = xa + lado * sa * (BX + e['prof']) * PW
        x0, x1 = (Xo, Xa) if lado < 0 else (Xa, Xo)
        if e['s0'] - base >= 2 and abs(x1 - x0) > 1:
            pegar_quad(fr, tex, [(min(x0, x1), ta), (max(x0, x1), ta), (max(x0, x1), py_(sa, Ya)), (min(x0, x1), py_(sa, Ya))],
                       [(u0, 0), (u0 + e['prof'] * kk, 0), (u0 + e['prof'] * kk, va), (u0, va)], fog=fz, sombra=0.0)
        if e['letrero'] and ba - ta > 120:   # letrero de neón en la azotea
            wl = abs(x1 - x0) * 0.8; hl = max(4, wl * 0.22); cxl = (x0 + x1) / 2
            d.rounded_rectangle((cxl - wl / 2, ta - hl - 4, cxl + wl / 2, ta - 4), int(hl / 3), fill=fog((255, 60, 170) if lado < 0 else (40, 210, 255)))
            if hl > 14: d.text((cxl, ta - hl / 2 - 4), '¿A o B?', font=font('Black', max(8, int(hl * 0.7))), fill=BLANCO, anchor='mm')

    # ---- corredores
    def corredores(s, fr, t, xm, xn, extra):
        c = s.corr; en_nave = s.nave_desde is not None and t >= s.nave_desde
        if not hasattr(c, 'mc'): c.mc, c.nc, c.nave = R0._corredores_extra()
        fase = s.paso[min(int(t * FPS), len(s.paso) - 1)]
        ym = yn = 0.0; fm = fn = 0.82; aplm = apln = None; ocultar = extra.get('ocultar', ())
        cae = extra.get('cae')   # 0..1 caída al vacío
        veh = s.vehiculo_en(t); V = vehiculos_flow(c)
        if en_nave or veh in ('dragon', 'carrito', 'pato'):
            v = veh if veh in ('dragon', 'carrito', 'pato') else 'dragon'
            u = clamp((t - s.veh_desde(t)) / 0.45)   # aparece con un salto («pop»)
            x = (xm + xn) / 2; ang = (xm + xn - 1920) / 1920 * 14
            y = 1140 + 14 * math.sin(t * (3.2 if v == 'dragon' else 5)) + extra.get('dy', 0) + 500 * (1 - ease_back(u)) - 240 * extra.get('alto', 1) * math.sin(math.pi * clamp(extra.get('salto', 0)))
            im = V[v]
            if v == 'dragon':   # aleteo: las alas suben y bajan (se estira un poco a lo ancho y a lo alto)
                a = math.sin(t * 4.5); im = im.resize((int(im.width * (1 + 0.04 * a)), int(im.height * (1 - 0.025 * a))), Image.BILINEAR)
            if v == 'pato': ang += 6 * math.sin(t * 4)
            im = im.rotate(-ang, Image.BILINEAR, expand=True)
            fr.paste(im, (int(x - im.width / 2), int(y - im.height)), im)
            return
        k2 = int(fase) % 2; P_ = poses_flow(c)
        for quien, x, ph in (('copresentadora', xn, 0.5), ('presentador', xm, 0.0)):
            if quien in ocultar: continue
            hab = s.hablando(t, quien)
            im = (c.nova_mira if hab else c.nova[k2]) if quien == 'copresentadora' else (c.max_mira if hab else c.max[k2])
            q_ = 'max' if quien == 'presentador' else 'nova'
            tabla = s.vehiculo_en(t) == 'patineta' and not extra.get('salto') and cae is None
            if tabla: im = vehiculos_flow(c)[q_ + '_patineta']                  # patineta cohete (Flow)
            if extra.get('salto'): im = P_[q_ + '_salta']                       # saltando (Flow)
            if cae is not None or extra.get('flota', 0) > 0.35 or extra.get('plaf_' + quien) is not None:
                im = P_[q_ + '_estrella']                                       # cayendo en estrella (Flow)
            bob = abs(math.sin(math.pi * (fase + ph))) * 12
            f = 0.82; y = H + 22 - bob
            if tabla and im is vehiculos_flow(c)[q_ + '_patineta']:
                u = clamp((t - s.veh_desde(t)) / 0.45); y = H + 40 - 18 * abs(math.sin(t * 2.2 + ph * 3)) + 400 * (1 - ease_back(u))
                x += 30 * math.sin(t * 1.7 + ph * 4)
            sal = extra.get('salto', 0)
            if sal: y -= 260 * extra.get('alto', 1) * math.sin(math.pi * clamp(sal)) ; f *= 1 - 0.1 * math.sin(math.pi * clamp(sal))
            if cae is not None: y += 900 * cae ** 2; f *= 1 - 0.45 * cae
            fl = extra.get('flota', 0)
            if fl: y -= 70 * fl + 18 * math.sin(t * 9 + ph * 6); x += 22 * math.sin(t * 5 + ph * 3) * fl
            pl = extra.get('plaf_' + quien)
            if pl is not None:   # vuelve cayendo desde arriba, rebotando, con estrellitas
                u = clamp(pl); y = -200 + (H + 22 + 200) * ease_out(min(1, u * 1.6)); f *= 1.0
            e = c.esc(im, f)
            fr.paste(e, (int(x - e.width / 2), int(y - e.height)), e)
            if pl is not None and pl < 1.3:
                d = ImageDraw.Draw(fr, 'RGBA')
                for kk in range(5):   # estrellitas girando sobre la cabeza
                    a = t * 7 + kk * 2 * math.pi / 5; sx, sy = x + math.cos(a) * 95, y - e.height - 10 + math.sin(a) * 26
                    estrella(d, sx, sy, 20, ORO)

    # ---- cuadro
    def frame(s, k):
        t = k / FPS; fr = Image.new('RGB', (W, H)); s._etq = []
        s.mundo(fr, t, k)
        vel = float(s.velk[min(k, len(s.velk) - 1)]); fuerza = clamp((vel - 7000) / 6000)
        esc = None
        for e in s.esc:
            if e[0] <= t < e[1]: esc = e; break
        s.pose = {'presentador': 'base', 'copresentadora': 'base'}
        xm, xn = 690.0, 1230.0; extra = {}; n_actual = 1; zona = 0 if (s.nave_desde is None or t < s.nave_desde - 3) else 1
        preg = None; cont = None; frente = []
        for t0, t1, tipo, x in s.feat:   # la caída: todos flotan un poco
            if tipo == 'caida' and t0 <= t < t1: extra['flota'] = math.sin(math.pi * (t - t0) / (t1 - t0))
        if esc and esc[2][0] == 'pregunta':
            idx, Pq = esc[2][1], esc[2][2]; q = s.Q[idx]; n_actual = idx + 1; preg = q['p']
            ap = Pq['ap']; tr, tch = Pq['tr'], Pq['tch']; a = 1 + idx / max(1, s.N - 1)
            if t < Pq['tc']: s.pose = {'presentador': 'senala', 'copresentadora': 'presenta'}
            elif t < Pq['tt']: s.pose = {'presentador': 'piensa', 'copresentadora': 'base'}
            elif t < tch: s.pose = {'presentador': 'frente', 'copresentadora': 'presenta'}
            else:
                m_ok, n_ok = ap['presentador'] == q['c'], ap['copresentadora'] == q['c']
                s.pose = {'presentador': 'celebra' if m_ok else 'piensa', 'copresentadora': 'celebra' if n_ok else 'sorpresa'}
            for quien, t0 in (('presentador', Pq['t_m']), ('copresentadora', Pq['t_n'])):
                u = ease_out(clamp((t - t0) / (0.3 / a)))
                lado = ap[quien]; dest = (590 if lado == 0 else 1330)
                if quien == 'presentador': xm = 690 + (dest - 690 - (0 if lado == 0 else 40)) * u
                else: xn = 1230 + (dest - 1230 + (0 if lado == 1 else 40)) * u
            puertas = s.puertas_de(idx, q)
            # distancia de las puertas
            z = s.puerta_z(t, esc, Pq, a)
            en_nave = s.nave_desde is not None and t >= s.nave_desde
            if en_nave:
                cen = (590 if ap['presentador'] == 0 else 1330) * 0.5 + (590 if ap['copresentadora'] == 0 else 1330) * 0.5
                if t >= tr: cen = cen + ((590 if q['c'] == 0 else 1330) - cen) * ease_out(clamp((t - tr) / (Pq['vuelo'] * 0.8)))
                xm = xn = cen
            if z > 200:
                for i in (0, 1):
                    ok = i == q['c']
                    if t >= tch and ok: continue       # la correcta ya reventó
                    cx, cy, sc = s.puerta_xy(z, i, idx, t, Pq)
                    wpx = sc * PUERTA_W * PW * s.puerta_tam(idx, i)
                    im = puertas[i].escala(wpx)
                    if t < tr and s.puerta_limita: cy = min(max(cy, 230 + im.height), 790)
                    elif t < tr and s.puerta_techo: cy = max(cy, s.puerta_techo + im.height)   # que no se metan bajo el HUD
                    item = (cx, cy, im, i, ok, sc)
                    (frente if z < ZRUN + 60 else s._atras_lista(t)).append(item)
            s._ctx = dict(q=q, Pq=Pq, t=t, en_nave=en_nave, z=z)
            # cuenta
            if Pq['tc'] <= t < Pq['tt']:
                dc = Pq['dc']; k3 = min(2, int((t - Pq['tc']) / (dc / 3))); u = ((t - Pq['tc']) / (dc / 3)) % 1
                cont = (str(3 - k3), ORO if k3 < 2 else ROJO, 1 + 0.35 * max(0, 1 - u * 4))
            elif Pq['tt'] <= t < Pq['t_m'] + 0.2 and Pq['modo'] == 'normal':
                cont = ('¡TIEMPO!', ROJO, 1.0 + 0.2 * max(0, 1 - (t - Pq['tt']) * 5))
            # el que falló: aplastado contra la pared y vuelve cayendo
            if not en_nave and t >= tch:
                for quien in ('presentador', 'copresentadora'):
                    if ap[quien] != q['c']:
                        extra['plaf_' + quien] = (t - tch - 0.45) / 0.6 if t - tch > 0.45 else None
                        if t - tch <= 0.45: extra.setdefault('ocultar', ()); extra['ocultar'] += (quien,)
        elif esc and esc[2][0] == 'puente':
            _, ts, tc, tn = esc[2]; n_actual = s._siguiente(esc)
            if ts <= t < tc: extra['salto'] = (t - ts) / (tc - ts)
            elif tc <= t < tn: extra['cae'] = clamp((t - tc) / 0.9)
            elif t >= tn:   # la nave sube desde abajo con ellos
                extra['dy'] = 600 * (1 - ease_out(clamp((t - tn) / 0.9)))
            s.pose = {'presentador': 'sorpresa' if False else 'piensa', 'copresentadora': 'sorpresa'}
        elif esc and esc[2][0] == 'nivel':
            n_actual = s._siguiente(esc); zona = 1
        elif esc and esc[2][0] in ('vuelta', 'relampago', 'intro', 'vehiculo', 'huevo', 'nace', 'crece'):
            n_actual = s._siguiente(esc)
            s.pose = {'presentador': 'celebra2', 'copresentadora': 'celebra'}
        elif esc and esc[2][0] == 'final':
            n_actual = s.N; gana_max = esc[2][1]
            s.pose = {'presentador': 'celebra2' if gana_max else 'piensa', 'copresentadora': 'sorpresa' if gana_max else 'celebra'}
            if esc[2][2]: s.pose = {'presentador': 'celebra', 'copresentadora': 'aplaude'}
        # puertas de atrás, corredores, puertas de adelante
        s.dibujar_puertas(fr, s._atras_lista(t, sacar=True), t)
        en_nave = s.nave_desde is not None and t >= s.nave_desde
        s.corredores(fr, t, xm, xn, extra)
        s.dibujar_puertas(fr, frente, t, adelante=True)
        if esc and esc[2][0] == 'pregunta' and 0 <= t - esc[2][2]['tch'] < 0.55: s.estallido(fr, t - esc[2][2]['tch'], s.Q[esc[2][1]])
        s.escolta(fr, t)
        s.mascota(fr, t, esc)
        s.etiquetas(fr)
        if fuerza > 0.02: mundos.lineas_velocidad(fr, t, fuerza)
        # vuelta de cabeza: gira todo el mundo
        for r0, r1 in s.rolls:
            if r0 <= t < r1:
                ang = 360 * (0.5 - 0.5 * math.cos(math.pi * (t - r0) / (r1 - r0)))
                fr = fr.resize((int(W * 1.3), int(H * 1.3)), Image.BILINEAR).rotate(ang, Image.BILINEAR).crop((int(W * 0.15), int(H * 0.15), int(W * 0.15) + W, int(H * 0.15) + H))
        s.centro(fr, t, cont)
        s.carteles(fr, t, esc)
        s.hud_c(fr, t, n_actual, zona, preg); s.franja(fr, t)
        st = s.subs.estado(t)
        if st: s.subs.dibujar(fr, st)
        for t0 in [e[0] for e in s.esc if e[2][0] in ('nivel', 'relampago')]:
            if t0 <= t < t0 + 0.25: fr.paste(Image.new('RGB', (W, H), (255, 255, 255)), (0, 0), Image.new('L', (W, H), int(230 * (1 - (t - t0) / 0.25))))
        if fuerza > 0.25:
            r = random.Random(k); dx, dy = int(r.uniform(-1, 1) * 8 * fuerza), int(r.uniform(-1, 1) * 6 * fuerza)
            fr = fr.transform(fr.size, Image.AFFINE, (1, 0, dx, 0, 1, dy), Image.BILINEAR)
        return fr

    def _atras_lista(s, t, sacar=False):
        if getattr(s, '_al_t', None) != t: s._al = []; s._al_t = t
        if sacar: l = s._al; s._al = []; return l
        return s._al

    def _siguiente(s, esc):
        i = s.esc.index(esc); nxt = next((x for x in s.esc[i + 1:] if x[2][0] == 'pregunta'), None)
        return nxt[2][1] + 1 if nxt else s.N

    def puertas_de(s, idx, q):
        if idx not in s.puertas:
            if len(s.puertas) > 4: s.puertas.pop(next(iter(s.puertas)))
            f = s.fotos(q); s.puertas[idx] = [Puerta(f[0], 'A', COL_A), Puerta(f[1], 'B', COL_B)]
        return s.puertas[idx]

    def etiquetas(s, fr):
        """Los nombres de las puertas, encima de todo (que MAX, NOVA o el vehículo nunca los tapen)."""
        d = ImageDraw.Draw(fr, 'RGBA')
        for cx, y, e, nom, col in getattr(s, '_etq', []):
            f = font('Black', max(12, int(78 * e)))
            while d.textlength(nom, font=f) > 780 * e and f.size > 12: f = font('Black', f.size - 2)
            tw = d.textlength(nom, font=f); hh = f.size * 1.35
            d.rounded_rectangle((cx - tw / 2 - 22 * e, y - hh / 2, cx + tw / 2 + 22 * e, y + hh / 2), int(hh / 2), fill=(14, 8, 36, 235), outline=col + (255,), width=max(2, int(6 * e)))
            d.text((cx, y), nom, font=f, fill=BLANCO, anchor='mm')
        s._etq = []

    def dibujar_puertas(s, fr, lista, t, adelante=False):
        if not lista: return
        c = s._ctx; q, Pq = c['q'], c['Pq']
        d = ImageDraw.Draw(fr, 'RGBA')
        for cx, cy, im, i, ok, sc in sorted(lista, key=lambda x: x[5]):
            y = cy - im.height
            fr.paste(im, (int(cx - im.width / 2), int(y)), im)
            esc_ = im.width / 900
            if esc_ > 0.25 and t < Pq['tch']: s._etq.append((cx, y + im.height * 0.9, esc_, s.puertas_de(c_idx(s, q), q)[i].foto.nombre.upper(), (COL_A, COL_B)[i]))
            # fichas MAX / NOVA arriba de la puerta
            fichas = [(nom, col) for quien, nom, col, t0 in (('presentador', 'MAX', MAXC, Pq['t_m']), ('copresentadora', 'NOVA', NOVAC, Pq['t_n']))
                      if t >= t0 and Pq['ap'][quien] == i]
            if fichas and esc_ > 0.2:
                ff = font('Black', max(10, int(54 * esc_))); x = cx - (len(fichas) - 1) * 130 * esc_
                for nom, col in fichas:
                    tw = d.textlength(nom, font=ff); hh = ff.size * 1.3
                    d.rounded_rectangle((x - tw / 2 - 20 * esc_, y + 150 * esc_ - hh / 2 + 40 * esc_, x + tw / 2 + 20 * esc_, y + 150 * esc_ + hh / 2 + 40 * esc_), int(hh / 2), fill=col, outline=BLANCO, width=max(2, int(5 * esc_)))
                    d.text((x, y + 190 * esc_), nom, font=ff, fill=TINTA, anchor='mm'); x += 260 * esc_
            if t >= Pq['tch'] - 0.02 and not ok:   # pared falsa: ladrillos y una X roja
                h = im.height; w = im.width
                for fy in range(int(y + 110 * esc_), int(y + h), max(6, int(60 * esc_))):
                    d.line([(cx - w * 0.44, fy), (cx + w * 0.44, fy)], fill=(120, 40, 40, 200), width=max(1, int(6 * esc_)))
                L = w * 0.28; my = y + h * 0.55
                d.line([(cx - L, my - L), (cx + L, my + L)], fill=ROJO + (255,), width=max(4, int(60 * esc_)))
                d.line([(cx - L, my + L), (cx + L, my - L)], fill=ROJO + (255,), width=max(4, int(60 * esc_)))
                if not c['en_nave']:   # el que se equivocó, aplastado contra la pared
                    for quien in ('presentador', 'copresentadora'):
                        if Pq['ap'][quien] == i and t - Pq['tch'] <= 0.45:
                            ims = poses_flow(s.corr)['max_estrella' if quien == 'presentador' else 'nova_estrella']
                            ww, hh = int(ims.width * esc_ * 1.45), int(ims.height * esc_ * 0.82)
                            if ww > 4 and hh > 4:
                                aa = ims.resize((ww, hh), Image.BILINEAR); fr.paste(aa, (int(cx - ww / 2 + (60 * esc_ if quien == 'copresentadora' else -60 * esc_)), int(my - hh / 2)), aa)
                    tx = 'PLAF!'; ff = font('Black', max(10, int(150 * esc_)))
                    d.text((cx, y + 60 * esc_), '¡' + tx, font=ff, fill=ORO, anchor='mm', stroke_width=max(2, int(10 * esc_)), stroke_fill=TINTA)

    def estallido(s, u, q):
        pass

    def mascota(s, fr, t, esc):
        """El dragón de la serie: el huevo que se alimenta, su nacimiento y cómo crece."""
        et = s.dragon_en(t); d = ImageDraw.Draw(fr, 'RGBA')
        correctas = len([1 for t0, _ in s.equipo if t >= t0])
        meta = int(s.m.get('dragon', {}).get('meta_huevo', 4))
        tipo = esc[2][0] if esc else ''
        if tipo == 'nace':   # escena grande: el huevo tiembla, se raja y nace
            tn = esc[2][1]
            if t < tn:
                u = clamp((t - esc[0]) / max(0.1, tn - esc[0])); sh = 18 * u * math.sin(t * 60)
                im = dragon_img('huevo', int(520 + 80 * u)); x, y = W / 2 + sh, 640
                for r_ in range(3):   # resplandor creciente
                    R = (300 + 120 * r_) * (0.6 + u); d.ellipse((x - R, y - R, x + R, y + R), fill=(255, 190, 60, int(40 * u)))
                fr.paste(im, (int(x - im.width / 2), int(y - im.height / 2)), im)
            else:
                u = clamp((t - tn) / 0.5); sc = max(0.05, ease_back(u)) if u < 1 else 1.0
                for k_ in range(14):   # destellos
                    a_ = k_ * 2 * math.pi / 14 + t; R = 380 + 40 * math.sin(t * 6 + k_)
                    estrella(d, W / 2 + math.cos(a_) * R * 1.3, 620 + math.sin(a_) * R * 0.75, 22, ORO)
                im = dragon_img('bebe_nace', max(20, int(640 * sc))); fr.paste(im, (int(W / 2 - im.width / 2), int(660 - im.height / 2)), im)
                ff = font('Black', max(10, int(150 * sc)))
                d.text((W / 2, 250), '¡NACIÓ!', font=ff, fill=ORO, anchor='mm', stroke_width=12, stroke_fill=TINTA)
                if t - tn < 0.25: fr.paste(Image.new('RGB', (W, H), (255, 255, 255)), (0, 0), Image.new('L', (W, H), int(255 * (1 - (t - tn) / 0.25))))
            return
        if tipo == 'crece':
            tc = esc[2][1]
            if t >= tc:
                u = clamp((t - tc) / 0.5); sc = max(0.05, ease_back(u)) if u < 1 else 1.0
                im = dragon_img('joven', max(20, int(820 * sc))); fr.paste(im, (int(W / 2 - im.width / 2), int(600 - im.height / 2)), im)
                d.text((W / 2, 230), '¡CRECIÓ!', font=font('Black', max(10, int(150 * sc))), fill=ORO, anchor='mm', stroke_width=12, stroke_fill=TINTA)
                if t - tc < 0.25: fr.paste(Image.new('RGB', (W, H), (255, 255, 255)), (0, 0), Image.new('L', (W, H), int(255 * (1 - (t - tc) / 0.25))))
                return
        if tipo == 'huevo':   # lo encuentran: aparece grande en el centro
            u = clamp((t - esc[0]) / 0.5); sc = max(0.05, ease_back(u)) if u < 1 else 1.0
            im = dragon_img('huevo', max(20, int(520 * sc))); y = 620 + 14 * math.sin(t * 3)
            R = 330; d.ellipse((W / 2 - R, y - R, W / 2 + R, y + R), fill=(255, 190, 60, 45))
            fr.paste(im, (int(W / 2 - im.width / 2), int(y - im.height / 2)), im)
            d.text((W / 2, 250), '¡UN HUEVO DE DRAGÓN!', font=font('Black', max(10, int(110 * sc))), fill=ORO, anchor='mm', stroke_width=10, stroke_fill=TINTA)
            return
        if t < getattr(s, 'huevo_t', 0) or s.vehiculo_en(t) == 'dragon': return
        # acompañante a la derecha (de abajo hacia arriba según la etapa)
        if et == 'huevo':
            g = clamp(correctas / meta); y = 900 + 10 * math.sin(t * 3); x = 1700 + 6 * math.sin(t * 40) * (g > 0.7)
            R = 140 + 60 * g; d.ellipse((x - R, y - R, x + R, y + R), fill=(255, 190, 60, int(30 + 60 * g)))
            im = dragon_img('huevo', 230); fr.paste(im, (int(x - im.width / 2), int(y - im.height / 2)), im)
            w = 230; d.rounded_rectangle((x - w / 2, y + 135, x + w / 2, y + 165), 15, fill=(18, 10, 46, 230), outline=ORO, width=3)
            d.rounded_rectangle((x - w / 2 + 4, y + 139, x - w / 2 + 4 + (w - 8) * g, y + 161), 11, fill=ORO)
            d.text((x, y + 150), f'{min(correctas, meta)}/{meta}', font=font('Black', 22), fill=TINTA if g > 0.5 else BLANCO, anchor='mm')
        elif et == 'bebe':
            x = 1650 + 50 * math.sin(t * 1.3); y = 700 + 30 * math.sin(t * 2.6)
            im = dragon_img('bebe_vuela', 260); a_ = math.sin(t * 9)
            im = im.resize((int(im.width * (1 + 0.08 * a_)), int(im.height * (1 - 0.04 * a_))), Image.BILINEAR)
            fr.paste(im, (int(x - im.width / 2), int(y - im.height / 2)), im)
        elif et == 'joven':
            x = 1620 + 60 * math.sin(t * 1.1); y = 640 + 35 * math.sin(t * 2.2)
            im = dragon_img('joven', 420); a_ = math.sin(t * 6)
            im = im.resize((int(im.width * (1 + 0.06 * a_)), int(im.height * (1 - 0.03 * a_))), Image.BILINEAR)
            fr.paste(im, (int(x - im.width / 2), int(y - im.height / 2)), im)

    def escolta(s, fr, t):
        """Los integrantes del equipo: el nuevo aparece grande y vuela a su lugar; los últimos 4 vuelan con ellos; el resto, en la franja."""
        if not hasattr(s, 'P'): return
        unidos = [(t0, idx) for t0, idx in s.equipo if t >= t0]
        if not unidos or t >= s.esc[-1][0]: return
        d = ImageDraw.Draw(fr, 'RGBA')
        slots = [(250, 640), (1670, 640), (150, 430), (1770, 430)]
        cola = unidos[-4:]; viejos = unidos[:-4]
        for k, (t0, idx) in enumerate(cola):
            p = s.puertas_de(idx, s.Q[idx])[s.Q[idx]['c']]
            sx, sy = slots[(len(unidos) - len(cola) + k) % 4]
            sy += 18 * math.sin(t * 3 + k * 1.7); sx += 10 * math.sin(t * 2.3 + k)
            u = clamp((t - t0) / 0.7)
            if u < 1:   # sale de la puerta (centro de la carretera) grande y vuela a su lugar
                x0, y0 = (590 if s.Q[idx]['c'] == 0 else 1330), 520
                e = ease_out(u); x = x0 + (sx - x0) * e; y = y0 + (sy - y0) * e - 160 * math.sin(math.pi * u); dd = 380 - 220 * e
            else: x, y, dd = sx, sy, 160
            b = burbuja(p, dd); fr.paste(b, (int(x - dd / 2), int(y - dd / 2)), b)
            if u < 1 and t - t0 > 0.15:
                txt = '¡SE UNE AL EQUIPO!'; ff = font('Black', 46)
                d.text((x, y - dd / 2 - 30), txt, font=ff, fill=BLANCO, anchor='mm', stroke_width=7, stroke_fill=TINTA)

    def franja(s, fr, t):
        unidos = [(t0, idx) for t0, idx in s.equipo if t >= t0]
        if not unidos: return
        d = ImageDraw.Draw(fr, 'RGBA')
        n = len(unidos); f = font('Black', 28); vis_ = unidos[-8:]
        x0 = s._pill_fin + 20; w = 150 + 48 * len(vis_)
        d.rounded_rectangle((x0, 146, x0 + w, 194), 24, fill=(18, 10, 46, 235), outline=ORO, width=3)
        d.text((x0 + 20, 170), f'EQUIPO {n}', font=f, fill=ORO, anchor='lm')
        x = x0 + 150
        for t0, idx in vis_:
            p = s.puertas_de(idx, s.Q[idx])[s.Q[idx]['c']]; b = burbuja(p, 42); fr.paste(b, (int(x), 149), b); x += 48


    def carteles(s, fr, t, esc):
        d = ImageDraw.Draw(fr)
        if esc and esc[2][0] == 'nivel':
            u = clamp((t - esc[0]) / 0.25); sc = max(0.01, ease_back(u))
            if sc > 0.02:
                d.text((W / 2, 400), 'ZONA 2', font=font('Black', max(10, int(170 * sc))), fill=(242, 153, 30), anchor='mm', stroke_width=12, stroke_fill=BLANCO)
                d.text((W / 2, 545), ZONAS[1], font=font('Black', max(10, int(90 * sc))), fill=ORO, anchor='mm', stroke_width=8, stroke_fill=TINTA)
        if esc and esc[2][0] == 'relampago':
            u = clamp((t - esc[0]) / 0.25); sc = max(0.01, ease_back(u))
            if sc > 0.02:
                d.text((W / 2, 430), '⚡ MODO RELÁMPAGO ⚡'.replace('⚡', ''), font=font('Black', max(10, int(120 * sc))), fill=ORO, anchor='mm', stroke_width=12, stroke_fill=TINTA)
                d.text((W / 2, 560), '¡NO PARPADEES!', font=font('Black', max(10, int(80 * sc))), fill=BLANCO, anchor='mm', stroke_width=8, stroke_fill=TINTA)
        if esc and esc[2][0] == 'final':
            u = clamp((t - esc[0]) / 0.3); sc = max(0.05, ease_back(u)); pm, pn = s.final_pts
            d.text((W / 2, 360), '¡EQUIPO COMPLETO!', font=font('Black', max(10, int(130 * sc))), fill=ORO, anchor='mm', stroke_width=10, stroke_fill=TINTA)
            d.text((W / 2, 490), f'MAX {pm}  ·  NOVA {pn}' + ('  ·  ¡EMPATE!' if pm == pn else ''), font=font('Black', max(10, int(76 * sc))), fill=BLANCO, anchor='mm', stroke_width=8, stroke_fill=TINTA)
            d.text((W / 2, 600), '¿Cuántas sacaste? Escríbelo abajo', font=font('Black', max(10, int(56 * sc))), fill=BLANCO, anchor='mm', stroke_width=6, stroke_fill=TINTA)
            # desfile del equipo completo
            n = len(s.equipo); dd = min(150, 1700 // max(1, n))
            for k, (t0, idx) in enumerate(s.equipo):
                uu = clamp((t - esc[0] - 0.2 - k * 0.08) / 0.4)
                if uu <= 0: continue
                p = s.puertas_de(idx, s.Q[idx])[s.Q[idx]['c']]; b = burbuja(p, dd * ease_back(uu) if uu < 1 else dd)
                x = W / 2 + (k - (n - 1) / 2) * (dd + 14); y = 760 + 14 * math.sin(t * 4 + k)
                fr.paste(b, (int(x - b.width / 2), int(y - b.height / 2)), b)

    def centro(s, fr, t, cont):
        d = ImageDraw.Draw(fr); cx, cy = VP_C if (s.nave_desde is None or t < s.nave_desde) else (300, 860)
        if cont is not None:
            txt, col, sc = cont; r = 84 * sc
            d.ellipse((cx - r - 8, cy - r - 8, cx + r + 8, cy + r + 8), fill=BLANCO); d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)
            d.text((cx, cy + 4), txt, font=font('Black', int((100 if len(txt) < 3 else 32) * sc)), fill=BLANCO, anchor='mm')
            return
        if s.hablando(t, 'anunciador'):
            b = s.boca(t, 'anunciador'); sp = voz_sprite(b, int(t * 12) % 12 if b else 0).resize((230, 230), Image.BILINEAR)
            pegar_centro(fr, sp, cx, cy)

    def hud_c(s, fr, t, n_actual, zona, pregunta):
        d = ImageDraw.Draw(fr)
        if pregunta:
            f = font('Black', 64); tw = d.textlength(pregunta, font=f)
            while tw > 1180 and f.size > 36: f = font('Black', f.size - 4); tw = d.textlength(pregunta, font=f)
            d.rounded_rectangle((W / 2 - tw / 2 - 40, 26, W / 2 + tw / 2 + 40, 126), 50, fill=(18, 10, 46), outline=ORO, width=4)
            d.text((W / 2, 76), pregunta, font=f, fill=BLANCO, anchor='mm')
        piezas = [(f'{n_actual}/{s.N}', ORO, TINTA), (f'ZONA {zona + 1} · {ZONAS[zona]}', [(39, 174, 96), (242, 153, 30)][zona], BLANCO)]
        f = font('Bold', 30); anchos = [d.textlength(p, font=f) + 44 for p, _, _ in piezas]
        neq = len([1 for t0, _ in s.equipo if t >= t0]); extra_w = (170 + 48 * min(8, neq)) if neq else 0
        x = W / 2 - (sum(anchos) + 20 + extra_w) / 2
        for (txt, bg, fg), w in zip(piezas, anchos):
            d.rounded_rectangle((x, 146, x + w, 194), 24, fill=bg); d.text((x + w / 2, 170), txt, font=f, fill=fg, anchor='mm'); x += w + 20
        s._pill_fin = x - 20
        (pm, pn), pop = s.marcador_en(t)
        for quien, nom, col, pts_, x0, pp in (('presentador', 'MAX', MAXC, pm, 24, pop[0]), ('copresentadora', 'NOVA', NOVAC, pn, W - 24 - 230, pop[1])):
            hab = s.hablando(t, quien)
            d.rounded_rectangle((x0, 20, x0 + 230, 290), 26, fill=(18, 10, 46), outline=col, width=6 if hab else 3)
            b = s.boca(t, quien); k = int(t * FPS) + (17 if quien == 'copresentadora' else 0)
            r = retrato(quien, s.pose.get(quien, 'base'), b, (k % 61) in (0, 1)); fr.paste(r, (x0 + 15, 30), r)
            sc = 1.35 if pp else 1.0; d = ImageDraw.Draw(fr)
            d.rounded_rectangle((x0 + 10, 232, x0 + 220, 282), 25, fill=col)
            d.text((x0 + 115, 257), f'{nom} {pts_}', font=font('Black', int(40 * sc)), fill=TINTA, anchor='mm')


def _cargar_fotos():
    """Fondos y fachadas de Google Flow (10-nov). Los fondos se arman como una tira alta (cielo arriba, ciudad abajo),
    duplicada en espejo a lo ancho para poder desplazarla en las curvas sin cortes."""
    D = os.path.join(RAIZ, 'assets', 'ciudad'); op = lambda n: Image.open(os.path.join(D, n + '.jpg')).convert('RGB')
    vac = ImageOps.fit(op('vacio'), (W, H), Image.LANCZOS)
    fondos = []
    for n, horiz in (('cielo1', 860), ('cielo2', 355)):
        im = op(n); esc = 2304 / im.width; im = im.resize((2304, round(im.height * esc)), Image.LANCZOS); hy = round(horiz * esc)
        top = 900; T = Image.new('RGB', (2304, top + im.height + 1400), im.getpixel((10, 4)))
        T.paste(im, (0, top))
        abajo = vac.resize((2304, round(H * 2304 / W)), Image.LANCZOS)
        abajo = Image.blend(abajo, Image.new('RGB', abajo.size, (8, 4, 22)), 0.35); T.paste(abajo, (0, top + im.height - 2))
        g = Image.new('L', (2304, 120)); g.putdata([int(255 * (y / 119)) for y in range(120) for _ in range(2304)])
        T.paste(im.crop((0, im.height - 120, 2304, im.height)), (0, top + im.height - 120), ImageOps.invert(g))
        tira = Image.new('RGB', (4608, T.height)); tira.paste(T, (0, 0)); tira.paste(ImageOps.mirror(T), (2304, 0))
        fondos.append((tira, top + hy))
    fach = []
    for n in ('fachada_vidrio', 'fachada_neon', 'fachada_depto'):
        im = op(n); at = Image.new('RGB', (im.width * 3, im.height * 6))
        for i in range(3):
            for j in range(6): at.paste(im if (i + j) % 2 == 0 else ImageOps.mirror(im), (i * im.width, j * im.height))
        fach.append(at)
    return fondos, vac, fach


FONDOS, VACIO, FACHADAS = _cargar_fotos()
_NIEBLA = (60, 26, 92)


def _coef(dst, src):
    """Coeficientes de PIL PERSPECTIVE: punto de pantalla → punto de la textura."""
    A, B = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    try: return np.linalg.solve(np.array(A, float), np.array(B, float))
    except np.linalg.LinAlgError: return None


def pegar_quad(fr, tex, quad, src, fog=0.0, sombra=0.0):
    """Pega la textura (zona src) deformada sobre el cuadrilátero quad de la pantalla, con niebla y sombra."""
    xs = [p[0] for p in quad]; ys = [p[1] for p in quad]
    x0, y0 = max(0, int(min(xs))), max(0, int(min(ys))); x1, y1 = min(W, int(max(xs)) + 1), min(H, int(max(ys)) + 1)
    if x1 - x0 < 1 or y1 - y0 < 1: return
    c = _coef([(x - x0, y - y0) for x, y in quad], src)
    if c is None: return
    im = tex.transform((x1 - x0, y1 - y0), Image.PERSPECTIVE, tuple(c), Image.BILINEAR)
    oscuro = min(0.92, sombra + 0.85 * fog)
    if oscuro > 0.01: im = Image.blend(im, Image.new('RGB', im.size, _NIEBLA if fog > sombra else (6, 4, 16)), oscuro)
    m = Image.new('L', im.size, 0); ImageDraw.Draw(m).polygon([(x - x0, y - y0) for x, y in quad], fill=255)
    fr.paste(im, (x0, y0), m)


_DRAG = {}
def dragon_img(n, alto):
    """Etapas del dragón de la serie (Flow, 10-nov): huevo, bebe_nace, bebe_vuela, joven, gigante (con MAX y NOVA montados)."""
    k = (n, alto)
    if k not in _DRAG:
        im = Image.open(os.path.join(RAIZ, 'assets', 'dragon', n + '.png')).convert('RGBA')
        _DRAG[k] = im.resize((max(1, round(im.width * alto / im.height)), alto), Image.LANCZOS)
    return _DRAG[k]


def vehiculos_flow(c):
    """Vehículos de Flow (10-nov): patinetas cohete, dragón dorado, carrito de supermercado con cohete, pato de hule con cohetes."""
    if not hasattr(c, '_veh'):
        D = os.path.join(RAIZ, 'assets', 'corredores'); c._veh = {}
        for n, alto in (('max_patineta', 470), ('nova_patineta', 470), ('dragon', 600), ('carrito', 520), ('pato', 480)):
            im = Image.open(os.path.join(D, ('dragon_abajo' if n == 'dragon' else n) + '.png')).convert('RGBA')
            c._veh[n] = im.resize((round(im.width * alto / im.height), alto), Image.LANCZOS)
    return c._veh


def poses_flow(c):
    """Poses nuevas de Flow (10-nov): saltando y en estrella (cayendo / aplastado), al alto de los corredores."""
    if not hasattr(c, '_flow'):
        D = os.path.join(RAIZ, 'assets', 'corredores'); c._flow = {}
        for n in ('max_salta', 'max_estrella', 'nova_salta', 'nova_estrella'):
            im = Image.open(os.path.join(D, n + '.png')).convert('RGBA'); alto = 440 if 'salta' in n else 470
            c._flow[n] = im.resize((round(im.width * alto / im.height), alto), Image.LANCZOS)
    return c._flow


def c_idx(s, q):
    return s.Q.index(q)


def estrella(d, x, y, r, col):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5; rr = r if i % 2 == 0 else r * 0.45
        pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
    d.polygon(pts, fill=col + (255,), outline=BLANCO)


def _estallido(s, fr, u, q):
    """La puerta correcta revienta en pedazos que salen hacia la cámara."""
    idx = s.Q.index(q); p = s.puertas_de(idx, q)[q['c']]
    if not hasattr(s, '_trozos'): s._trozos = {}
    if idx not in s._trozos:
        base = p.escala(1400); r = random.Random(idx); tr = []
        n, m = 5, 4; tw, th = base.width / n, base.height / m
        for i in range(n):
            for j in range(m):
                im = base.crop((int(i * tw), int(j * th), int((i + 1) * tw), int((j + 1) * th)))
                tr.append((im, (i + 0.5) / n - 0.5, (j + 0.5) / m - 0.5, r.uniform(-1, 1), r.uniform(0.6, 1.4)))
        s._trozos = {idx: tr}
    cx = 590 if q['c'] == 0 else 1330; cy = 560
    for im, ox, oy, rot, vel in s._trozos[idx]:
        e = u * vel * 1.6; sc = 0.5 + 0.9 * e
        x = cx + ox * 900 * (1 + 2.6 * e); y = cy + oy * 700 * (1 + 2.2 * e) + 700 * e * e
        w, h = max(2, int(im.width * sc * 0.42)), max(2, int(im.height * sc * 0.42))
        a = im.resize((w, h), Image.BILINEAR).rotate(rot * 300 * u, Image.BILINEAR, expand=True)
        if u > 0.3:
            al = a.getchannel('A').point(lambda v: int(v * max(0, 1 - (u - 0.3) / 0.25))); a.putalpha(al)
        fr.paste(a, (int(x - a.width / 2), int(y - a.height / 2)), a)
    if u < 0.15:
        fr.paste(Image.new('RGB', (W, H), (255, 255, 255)), (0, 0), Image.new('L', (W, H), int(90 * (1 - u / 0.15))))


Ciudad.estallido = _estallido


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--contenido', required=True); ap.add_argument('--voces', default='')
    ap.add_argument('--out', required=True); ap.add_argument('--tmp', default='tmp'); ap.add_argument('--miniatura')
    ap.add_argument('--cuadros', help='solo guardar estos segundos como JPG (prueba), p. ej. 1,5,9')
    ap.add_argument('--tramo', type=int, help='armado repartido: renderizar solo este tramo (0..tramos-1), sin audio')
    ap.add_argument('--tramos', type=int, default=1)
    ap.add_argument('--solo-audio', action='store_true', help='solo la mezcla de audio en --out (.wav)')
    a = ap.parse_args()
    meta = json.load(open(a.contenido, encoding='utf-8'))
    meta['preguntas'] = [q for q in meta['preguntas'] if q.get('o_img')]
    S = Ciudad(meta, a.voces); S.armar()
    print(f'Duración: {S.t / 60:.2f} min · {S.N} preguntas · MAX {S.final_pts[0]} - NOVA {S.final_pts[1]}')
    sync = {'formato': 'ciudad', 'ya': 0, 'total': S.N, 'duracion': round(S.t, 2), 'tiempos': S.tiempos, 'apuestas': S.apuestas,
            'capitulos': [[round(t, 1), c] for t, c in S.capitulos], 'faltan': sorted(set(S.faltan))}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(sync, open(os.path.splitext(a.out)[0] + '.tiempos.json', 'w'), ensure_ascii=False, indent=1)
    if S.faltan: print('Voces faltantes (silencio):', sorted(set(S.faltan)))
    if a.miniatura: R0.miniatura(meta, a.miniatura)
    os.makedirs(a.tmp, exist_ok=True)
    if a.cuadros:
        S.corr = R0.Corredores(); S.subs.cerrar()
        for sec in a.cuadros.split(','):
            S.frame(int(float(sec) * FPS)).save(os.path.join(a.tmp, f'cuadro_{sec}.jpg'), quality=85)
        return
    if a.solo_audio:
        audio_solo(S, a.out); print('OK audio', a.out); return
    if a.tramo is not None:
        render_tramo(S, a.out, a.tramo, a.tramos); print('OK tramo', a.tramo, a.out); return
    S.render(a.out, a.tmp); print('OK', a.out)


# ---------------------------------------------------------------- armado repartido (varias máquinas)
def _ffmpeg_video(out):
    return subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                             '-i', '-', *(['-vf', 'scale=3840:2160:flags=lanczos'] if os.environ.get('QSM_4K') else []),
                             '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18' if os.environ.get('QSM_4K') else '20',
                             '-pix_fmt', 'yuv420p', '-g', str(FPS * 2), out], stdin=subprocess.PIPE)


def render_tramo(S, out, i, n):
    """Solo los cuadros del tramo i de n (sin audio). Los tramos se unen con concat -c copy en el job final."""
    import time
    S.corr = R0.Corredores(); S.subs.cerrar()
    nfr = int(S.t * FPS); k0, k1 = nfr * i // n, nfr * (i + 1) // n
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    ff = _ffmpeg_video(out); t0 = time.time()
    for k in range(k0, k1):
        ff.stdin.write(S.frame(k).convert('RGB').tobytes())
        if (k - k0) % (FPS * 30) == 0: print(f'  tramo {i}: {(k - k0) / FPS / 60:.1f}/{(k1 - k0) / FPS / 60:.1f} min · {(time.time() - t0) / 60:.1f} min', flush=True)
    ff.stdin.close(); ff.wait()
    json.dump({'tramo': i, 'de': n, 'k0': k0, 'k1': k1}, open(out + '.json', 'w'))


def audio_solo(S, wav_out):
    """Mezcla de voces + efectos + música de todo el episodio (igual que Show.render) en un WAV."""
    import wave
    mix = np.zeros(int(R0.SR * (S.t + 0.5)), np.float32)
    for at, a in S.audio:
        st = int(at * R0.SR); e = min(len(mix), st + len(a))
        if e > st: mix[st:e] += a[:e - st]
    mix = S.musica(mix)
    pk = np.abs(mix).max()
    if pk > 0.98: mix *= 0.98 / pk
    with wave.open(wav_out, 'w') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(R0.SR); w.writeframes((mix * 32767).astype(np.int16).tobytes())


if __name__ == '__main__':
    main()
