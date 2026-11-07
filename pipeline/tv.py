#!/usr/bin/env python3
"""Montador v2 — formato programa de TV con personajes animados e imágenes.
Uso:
  python3 pipeline/tv.py --contenido contenido/maqueta_tv.json --banco banco --voces voces/maqueta --out salida/maqueta.mp4
Las voces que falten quedan en silencio (sirve para maquetas).
"""
import argparse, json, os, subprocess, wave, sys, zlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

sys.path.insert(0, os.path.dirname(__file__))
from personajes import sprite, voz_sprite, NOMBRES
from musica import Musica, MusicaArchivos, carpeta_musica
from subtitulos import Subtitulos
from reportlab.graphics.barcode import qrencoder as QR

W, H, FPS, SR = 1920, 1080, 15, 24000
FONT = '/usr/share/fonts/truetype/google-fonts/Poppins-%s.ttf'
if not os.path.exists(FONT % 'Bold'):
    FONT = os.path.join(os.path.dirname(__file__), '..', 'fuentes', 'Poppins-%s.ttf')
_fc = {}
def font(w, s):
    k = (w, s)
    if k not in _fc: _fc[k] = ImageFont.truetype(FONT % w, s)
    return _fc[k]

C = dict(bg1=(18, 12, 52), bg2=(62, 26, 120), white=(255, 255, 255), dim=(64, 56, 104), dimtxt=(150, 140, 190),
         gold=(255, 200, 40), ink=(26, 18, 64), red=(231, 76, 60))
OPC = [((231, 76, 60), 'A'), ((47, 128, 237), 'B'), ((240, 170, 20), 'C'), ((39, 174, 96), 'D')]
NIVEL = [('FÁCIL', (39, 174, 96)), ('MEDIA', (242, 153, 30)), ('DIFÍCIL', (231, 76, 60))]
DOCK_X = 450  # columna izquierda reservada para el personaje
RIVAL_COL = (90, 215, 255)   # celeste de NOVA
# rondas especiales: rótulo de la tarjeta, anuncio de LA VOZ y subtítulo
RONDA = {'misteriosa': ('IMAGEN MISTERIOSA', (142, 68, 173)), 'vf': ('VERDADERO O FALSO', (22, 160, 133)),
         'relampago': ('RONDA RELÁMPAGO', (231, 76, 60))}
ANUNCIO = {'misteriosa': ('an_07_misteriosa', '¡Imagen misteriosa!', 'La foto se aclara con el reloj'),
           'vf': ('an_08_vf', '¡Verdadero o falso!', 'Solo dos opciones… ¿cuál será?'),
           'relampago': ('an_05_relampago', '¡Ronda relámpago!', 'Cinco preguntas · cinco segundos · ¡sin pausa!')}

# ---------------------------------------------------------------- escenario
def escenario():
    y = np.linspace(0, 1, H)[:, None]; x = np.linspace(0, 1, W)[None, :]
    t = np.clip(0.75 * y + 0.25 * x, 0, 1)[..., None]
    base = (np.array(C['bg1']) * (1 - t) + np.array(C['bg2']) * t).astype(np.uint8)
    img = Image.fromarray(base).convert('RGBA')
    luz = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(luz)
    for cx, ang in [(260, 1), (960, 0), (1660, -1)]:  # focos
        d.polygon([(cx - 40, -10), (cx + 40, -10), (cx + 420 * ang + 330, H), (cx + 420 * ang - 330, H)], fill=(255, 255, 255, 16))
    d.ellipse((-200, H - 180, W + 200, H + 260), fill=(255, 200, 40, 26))  # piso
    rng = np.random.default_rng(7)
    for _ in range(70):
        px, py, r = rng.integers(0, W), rng.integers(0, H), rng.integers(1, 4)
        d.ellipse((px - r, py - r, px + r, py + r), fill=(255, 255, 255, int(rng.integers(30, 110))))
    luz = luz.filter(ImageFilter.GaussianBlur(18))
    return Image.alpha_composite(img, luz).convert('RGB')

def qr_img(url, px):
    for v in range(2, 11):
        try:
            q = QR.QRCode(v, QR.QRErrorCorrectLevel.M); q.addData(url); q.make(); break
        except Exception: continue
    n = q.getModuleCount(); b = 2
    m = Image.new('L', (n + 2 * b, n + 2 * b), 255)
    for r in range(n):
        for c in range(n):
            if q.isDark(r, c): m.putpixel((c + b, r + b), 0)
    return m.resize((px, px), Image.NEAREST).convert('RGB')

def wrap(d, txt, f, maxw):
    out, cur = [], ''
    for w in txt.split():
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=f) <= maxw: cur = t
        else: out.append(cur); cur = w
    if cur: out.append(cur)
    return out

def fit(d, txt, weight, maxw, maxh, start, minsize=28, sp=1.18):
    s = start
    while s > minsize:
        f = font(weight, s); ls = wrap(d, txt, f, maxw)
        if len(ls) * s * sp <= maxh and all(d.textlength(l, font=f) <= maxw for l in ls): return f, ls, s
        s -= 2
    f = font(weight, minsize); return f, wrap(d, txt, f, maxw), minsize

def lines(d, ls, f, s, cx, cy, fill, anchor='mm', x=None, sp=1.18):
    tot = len(ls) * s * sp; y = cy - tot / 2
    for l in ls:
        if anchor == 'mm': d.text((cx, y + s * sp / 2), l, font=f, fill=fill, anchor='mm')
        else: d.text((x, y + s * sp / 2), l, font=f, fill=fill, anchor='lm')
        y += s * sp

def caja(img, box, r, fill, outline=None, width=0, sombra=True):
    img = img.convert('RGBA')
    if sombra:
        sx = Image.new('RGBA', img.size, (0, 0, 0, 0)); ds = ImageDraw.Draw(sx)
        x0, y0, x1, y1 = box; ds.rounded_rectangle([x0, y0 + 8, x1, y1 + 16], r, fill=(0, 0, 0, 100))
        img = Image.alpha_composite(img, sx.filter(ImageFilter.GaussianBlur(12)))
    ImageDraw.Draw(img).rounded_rectangle(box, r, fill=fill, outline=outline, width=width)
    return img.convert('RGB')

def foto(img, path, box, fondo=None, credito=None, pix=0):
    x0, y0, x1, y1 = box; w, h = x1 - x0, y1 - y0
    img = caja(img, (x0 - 10, y0 - 10, x1 + 10, y1 + 10), 30, (255, 255, 255))
    src = Image.open(path).convert('RGB')
    if fondo == 'blanco':
        src.thumbnail((w - 80, h - 80)); can = Image.new('RGB', (w, h), (255, 255, 255))
        can.paste(src, ((w - src.width) // 2, (h - src.height) // 2)); src = can
    else:
        src = ImageOps.fit(src, (w, h), Image.LANCZOS)
    if pix > 1:  # imagen misteriosa: bloques grandes que se achican con el reloj
        src = src.resize((max(1, w // pix), max(1, h // pix)), Image.BILINEAR).resize((w, h), Image.NEAREST)
    mask = Image.new('L', (w, h), 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, w, h), 22, fill=255)
    img.paste(src, (x0, y0), mask)
    if credito:
        d = ImageDraw.Draw(img); f = font('Regular', 18)
        tw = d.textlength(credito, font=f)
        d.rounded_rectangle((x1 - tw - 24, y1 - 34, x1 - 6, y1 - 8), 8, fill=(0, 0, 0))
        d.text((x1 - 15, y1 - 21), credito, font=f, fill=(230, 230, 230), anchor='rm')
    return img

# ---------------------------------------------------------------- foto en movimiento (Ken Burns)
CAJA_PREG = (DOCK_X + 10, 270, DOCK_X + 10 + 760, 270 + 520)
CAJA_DATO = (DOCK_X + 10, 360, DOCK_X + 10 + 700, 360 + 500)
KB_SEG, KB_ZOOM = 30.0, 0.14   # recorrido completo en 30 s (pregunta → reloj → respuesta → dato), zoom 14 %
_kb_src, _kb_mask, _kb_vivo = {}, {}, [None, None]


def _kb_grande(path, w, h):
    k = (path, w, h)
    if k not in _kb_src:
        if len(_kb_src) > 6: _kb_src.clear()
        src = Image.open(path).convert('RGB')
        _kb_src[k] = ImageOps.fit(src, (round(w * (1 + KB_ZOOM + 0.02)), round(h * (1 + KB_ZOOM + 0.02))), Image.LANCZOS)
    return _kb_src[k]


def _kb_mascara(box, credito):
    k = (box, credito)
    if k not in _kb_mask:
        x0, y0, x1, y1 = box; w, h = x1 - x0, y1 - y0
        m = Image.new('L', (w, h), 0); d = ImageDraw.Draw(m); d.rounded_rectangle((0, 0, w, h), 22, fill=255)
        if credito:  # el crédito queda fijo encima
            tw = d.textlength(credito, font=font('Regular', 18)); d.rectangle((w - tw - 26, h - 36, w, h), fill=0)
        _kb_mask[k] = m
    return _kb_mask[k]


class Movil:
    """Escena cuya foto se mueve lento (zoom y desplazamiento). base: pantalla fija (Image) o función t→Image.
    El movimiento sigue el reloj del episodio (t_ini) para que no salte entre escenas de la misma pregunta."""
    def __init__(s, base, path, box, credito, semilla, t_ini, t_esc):
        s.fn = base if callable(base) else None
        s.z = None if s.fn else (base.size, zlib.compress(base.tobytes(), 1))
        s.path, s.box, s.cred, s.t_ini, s.t_esc = path, box, credito, t_ini, t_esc
        s.zin = semilla % 2 == 0; s.dx = (-1, 1)[(semilla // 2) % 2]; s.dy = (-1, 0, 1)[(semilla // 4) % 3]

    def __call__(s, t):
        if s.fn: base = s.fn(t)
        else:
            if _kb_vivo[0] is not s: _kb_vivo[:] = [s, Image.frombytes('RGB', s.z[0], zlib.decompress(s.z[1]))]
            base = _kb_vivo[1]
        x0, y0, x1, y1 = s.box; w, h = x1 - x0, y1 - y0
        big = _kb_grande(s.path, w, h); BW, BH = big.size
        p = min(1.0, max(0.0, (s.t_esc + t - s.t_ini) / KB_SEG)); p = 0.5 - 0.5 * np.cos(np.pi * p)
        z = 1 + KB_ZOOM * (p if s.zin else 1 - p)
        ww, hh = BW / z, BH / z; mx, my = (BW - ww) / 2, (BH - hh) / 2
        cx, cy = BW / 2 + s.dx * mx * 0.9, BH / 2 + s.dy * my * 0.9
        cuadro = big.resize((w, h), Image.BILINEAR, box=(cx - ww / 2, cy - hh / 2, cx + ww / 2, cy + hh / 2))
        fr = base.copy(); fr.paste(cuadro, (x0, y0), _kb_mascara(s.box, s.cred))
        return fr


# ---------------------------------------------------------------- pantallas
class Pantallas:
    def __init__(s, meta, url, raiz):
        s.m = meta; s.raiz = raiz; s.bg = escenario()
        s.qr_s = qr_img(url, 140); s.qr_l = qr_img(url, 400)
        s._cred = {}

    def credito(s, path):
        dd = os.path.dirname(os.path.abspath(path))  # cada carpeta de fotos trae su creditos.json
        if dd not in s._cred:
            f = os.path.join(dd, 'creditos.json'); s._cred[dd] = json.load(open(f)) if os.path.exists(f) else {}
        c = s._cred[dd].get(os.path.basename(path))
        if not c: return None
        autor = c['autor'].split('\n')[0][:40] or 'Wikimedia Commons'
        return f"Foto: {autor} · {c['licencia']}"

    def barra(s, img, etiqueta=None, marcador=None):
        d = ImageDraw.Draw(img)
        d.text((50, 58), '¿Quién Sabe Más?', font=font('Bold', 38), fill=C['gold'], anchor='lm')
        if marcador:   # PRUEBA «MAX contra NOVA»: marcador en la barra de arriba
            x = 470
            for nom, pts, col in (('MAX', marcador[0], C['gold']), ('NOVA', marcador[1], RIVAL_COL)):
                f = font('Bold', 30); tw = d.textlength(f'{nom} {pts}', font=f)
                d.rounded_rectangle((x, 36, x + tw + 36, 80), 22, fill=col)
                d.text((x + 18 + tw / 2, 58), f'{nom} {pts}', font=f, fill=C['ink'], anchor='mm'); x += tw + 52
        if etiqueta: d.text((W / 2 + 120, 58), etiqueta, font=font('Medium', 32), fill=C['white'], anchor='mm')
        img.paste(s.qr_s, (W - 50 - 140, 18))
        d.text((W - 210, 46), 'Juega en', font=font('Medium', 22), fill=C['dimtxt'], anchor='rm')
        d.text((W - 210, 86), f"sala {s.m['codigo_sala']}", font=font('Bold', 34), fill=C['white'], anchor='rm')
        return img

    def lobby(s, cuenta=None):
        img = s.bg.copy(); d = ImageDraw.Draw(img)
        d.text((W / 2, 130), '¿Quién Sabe Más?', font=font('Bold', 104), fill=C['gold'], anchor='mm')
        d.text((W / 2, 225), s.m['titulo'], font=font('Medium', 48), fill=C['white'], anchor='mm')
        img = caja(img, (560, 300, 1000, 740), 28, (255, 255, 255)); img.paste(s.qr_l, (580, 320))
        d = ImageDraw.Draw(img); x = 1060
        for i, t in enumerate(['Escanea el código', 'Escribe tu apodo', 'Al oír «¡YA!» toca EMPEZAR']):
            d.ellipse((x, 330 + i * 80, x + 56, 386 + i * 80), fill=C['gold'])
            d.text((x + 28, 358 + i * 80), str(i + 1), font=font('Bold', 34), fill=C['ink'], anchor='mm')
            d.text((x + 76, 358 + i * 80), t, font=font('Medium', 42), fill=C['white'], anchor='lm')
        d.text((x, 600), 'Sala', font=font('Medium', 32), fill=C['dimtxt'], anchor='lm')
        img = caja(img, (x, 630, x + 400, 740), 22, (255, 255, 255)); d = ImageDraw.Draw(img)
        d.text((x + 200, 686), s.m['codigo_sala'], font=font('Bold', 76), fill=C['ink'], anchor='mm')
        d.text((780, 780), 'quiensabemastv.pages.dev', font=font('Medium', 34), fill=C['white'], anchor='mm')
        d.text((W / 2 + 200, 850), '¿Sin celular? Anota tus aciertos en un papel y juega igual.', font=font('Regular', 36), fill=C['dimtxt'], anchor='mm')
        if cuenta is not None:
            d.ellipse((W - 220, 860, W - 80, 1000), fill=C['gold'])
            d.text((W - 150, 932), str(cuenta), font=font('Bold', 80), fill=C['ink'], anchor='mm')
        return img

    def tarjeta(s, n, total, ronda=None):
        img = s.barra(s.bg.copy()); d = ImageDraw.Draw(img)
        nv = RONDA.get(ronda) or NIVEL[min(2, (n - 1) * 3 // total)]; cx = DOCK_X + (W - DOCK_X) / 2
        hw = max(150, d.textlength(nv[0], font=font('Bold', 40)) / 2 + 40)
        d.rounded_rectangle((cx - hw, 300, cx + hw, 370), 35, fill=nv[1])
        d.text((cx, 336), nv[0], font=font('Bold', 40), fill=C['white'], anchor='mm')
        d.text((cx, 530), f'PREGUNTA {n}', font=font('Bold', 150), fill=C['white'], anchor='mm')
        d.text((cx, 670), f'de {total}', font=font('Medium', 56), fill=C['dimtxt'], anchor='mm')
        return img

    _fotos = {}

    def _foto_opcion(s, path, w, h, apagada):
        k = (path, w, h, apagada)
        if k not in s._fotos:
            if len(s._fotos) > 64: s._fotos.clear()
            src = Image.open(os.path.join(s.raiz, path)).convert('RGB')
            if path.endswith('.png'):   # bandera: entera, sobre blanco
                src.thumbnail((w - 24, h - 24), Image.LANCZOS); t = Image.new('RGB', (w, h), (255, 255, 255))
                t.paste(src, ((w - src.width) // 2, (h - src.height) // 2)); src = t
            else:
                src = ImageOps.fit(src, (w, h), Image.LANCZOS, centering=(0.5, 0.38))
            if apagada: src = Image.blend(src, Image.new('RGB', (w, h), C['ink']), 0.68)
            m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), 18, fill=255)
            s._fotos[k] = (src, m)
        return s._fotos[k]

    def _tarjetas(s, img, q, modo, box):
        """Alternativas como tarjetas: foto grande a la izquierda, nombre a la derecha, letra sobre la foto."""
        x0, y0, x1, y1 = box; g = 26; n = len(q['o']); cols = 2; rows = -(-n // cols)
        bw = (x1 - x0 - g) / cols; bh = (y1 - y0 - g * (rows - 1)) / rows
        if n == 2: bh = min(bh * 2 + g, 420); y0 = y0 + (y1 - y0 - bh) / 2
        for i, txt in enumerate(q['o']):
            col, L = OPC[i]; x = x0 + (i % cols) * (bw + g); y = y0 + (i // cols) * (bh + g)
            ok = i == q['c']; apag = modo == 'revela' and not ok
            if modo == 'revela' and ok:
                img = caja(img, (x - 9, y - 9, x + bw + 9, y + bh + 9), 30, col, outline=C['white'], width=8)
            else:
                img = caja(img, (x, y, x + bw, y + bh), 26, C['dim'] if apag else col, sombra=not apag)
            ph = int(bh - 24); pw = int(min(bw * 0.52, ph * 1.4))
            src, m = s._foto_opcion(q['o_img'][i], pw, ph, apag)
            img.paste(src, (int(x + 12), int(y + 12)), m)
            d = ImageDraw.Draw(img); r = 30; cx, cy = x + 12 + r + 10, y + 12 + r + 10
            d.ellipse((cx - r - 4, cy - r - 4, cx + r + 4, cy + r + 4), fill=C['white'] if not apag else (96, 88, 140))
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=C['dim'] if apag else col)
            d.text((cx, cy), L, font=font('Bold', 36), fill=C['dimtxt'] if apag else C['white'], anchor='mm')
            tx = x + 12 + pw + 24; tw = x + bw - tx - (80 if ok and modo == 'revela' else 20)
            f, ls, sz = fit(d, txt, 'Bold', tw, bh - 40, 56, 26)
            lines(d, ls, f, sz, 0, y + bh / 2, C['dimtxt'] if apag else C['white'], anchor='lm', x=tx)
            if modo == 'revela' and ok:
                kx, ky = x + bw - 48, y + 48; d.ellipse((kx - 34, ky - 34, kx + 34, ky + 34), fill=C['white'])
                d.line([(kx - 17, ky + 1), (kx - 5, ky + 15), (kx + 18, ky - 14)], fill=col, width=10, joint='curve')
            img = s._fichas(img, i, x, y, bw)
        return img

    def _fichas(s, img, i, x, y, bw):
        """Fichas MAX / NOVA sobre la alternativa que eligió cada uno."""
        ap = getattr(s, '_apuestas', None)
        if not ap: return img
        quienes = [(n, c) for n, c, k in (('MAX', C['gold'], 'presentador'), ('NOVA', RIVAL_COL, 'copresentadora')) if ap.get(k) == i]
        d = ImageDraw.Draw(img); xr = x + bw - 14
        for nom, col in reversed(quienes):
            f = font('Bold', 34); tw = d.textlength(nom, font=f)
            d.rounded_rectangle((xr - tw - 36, y - 28, xr, y + 22), 25, fill=col, outline=C['white'], width=4)
            d.text((xr - tw / 2 - 18, y - 3), nom, font=f, fill=C['ink'], anchor='mm'); xr -= tw + 46
        return img

    def _opciones(s, img, q, modo, box, cols):
        x0, y0, x1, y1 = box; g = 26
        rows = -(-len(q['o']) // cols); bw = (x1 - x0 - g * (cols - 1)) / cols; bh = (y1 - y0 - g * (rows - 1)) / rows
        for i, txt in enumerate(q['o']):
            col, L = OPC[i]; x = x0 + (i % cols) * (bw + g); y = y0 + (i // cols) * (bh + g)
            ok = i == q['c']; apag = modo == 'revela' and not ok
            if modo == 'revela' and ok:
                img = caja(img, (x - 8, y - 8, x + bw + 8, y + bh + 8), 28, col, outline=C['white'], width=7)
            else:
                img = caja(img, (x, y, x + bw, y + bh), 24, C['dim'] if apag else col, sombra=not apag)
            d = ImageDraw.Draw(img); r = min(40, bh / 2 - 12); cy = y + bh / 2
            d.ellipse((x + 20, cy - r, x + 20 + 2 * r, cy + r), fill=(96, 88, 140) if apag else C['white'])
            d.text((x + 20 + r, cy), L, font=font('Bold', int(r * 1.2)), fill=C['dimtxt'] if apag else col, anchor='mm')
            tx = x + 40 + 2 * r; f, ls, sz = fit(d, txt, 'Bold', bw - (tx - x) - (90 if ok and modo == 'revela' else 24), bh - 20, 48, 26)
            lines(d, ls, f, sz, 0, cy, C['dimtxt'] if apag else C['white'], anchor='lm', x=tx)
            if modo == 'revela' and ok:
                cx = x + bw - 52; d.ellipse((cx - 34, cy - 34, cx + 34, cy + 34), fill=C['white'])
                d.line([(cx - 17, cy + 1), (cx - 5, cy + 15), (cx + 18, cy - 14)], fill=col, width=10, joint='curve')
            img = s._fichas(img, i, x, y, bw)
        return img

    def pregunta(s, n, total, q, modo='normal', reloj=None, frac=None, pix=0, marcador=None, apuestas=None):
        s._apuestas = apuestas
        img = s.barra(s.bg.copy(), f'Pregunta {n} de {total}', marcador); d = ImageDraw.Draw(img)
        con_foto = q.get('img') and q.get('img_modo') == 'pregunta'
        if con_foto:
            f, ls, sz = fit(d, q['p'], 'Bold', W - DOCK_X - 90, 110, 60)
            lines(d, ls, f, sz, DOCK_X + (W - DOCK_X) / 2 - 20, 185, C['white'])
            p = os.path.join(s.raiz, q['img'])
            img = foto(img, p, CAJA_PREG, q.get('img_fondo'), s.credito(p), pix)
            img = s._opciones(img, q, modo, (DOCK_X + 820, 270, W - 50, 790), 1)
        elif q.get('o_img'):   # PRUEBA: alternativas con foto real (tarjetas 2×2)
            f, ls, sz = fit(d, q['p'], 'Bold', W - DOCK_X - 440, 150, 60)   # sin tocar el QR de la esquina
            lines(d, ls, f, sz, DOCK_X + (W - DOCK_X) / 2 - 20, 215, C['white'])
            img = s._tarjetas(img, q, modo, (DOCK_X + 10, 300, W - 50, 872))
        else:
            f, ls, sz = fit(d, q['p'], 'Bold', W - DOCK_X - 110, 250, 70)
            lines(d, ls, f, sz, DOCK_X + (W - DOCK_X) / 2 - 20, 300, C['white'])
            box = (DOCK_X + 10, 500, W - 50, 800) if len(q['o']) == 2 else (DOCK_X + 10, 460, W - 50, 830)
            img = s._opciones(img, q, modo, box, 2)
        d = ImageDraw.Draw(img)
        if frac is not None:
            yb = 900; x0b, x1b = DOCK_X + 10, W - 230
            d.rounded_rectangle((x0b, yb, x1b, yb + 34), 17, fill=(56, 46, 100))
            ww = int((x1b - x0b) * max(0.0, frac))
            if ww > 34: d.rounded_rectangle((x0b, yb, x0b + ww, yb + 34), 17, fill=C['gold'] if frac > 0.3 else C['red'])
        if reloj is not None:
            cx, cy = W - 130, 917; col = C['gold'] if isinstance(reloj, int) and reloj > 3 else C['red']
            d.ellipse((cx - 72, cy - 72, cx + 72, cy + 72), fill=col)
            d.text((cx, cy + 2), str(reloj), font=font('Bold', 84 if isinstance(reloj, int) else 40), fill=C['white'], anchor='mm')
        return img

    def dato(s, n, total, q, marcador=None):
        img = s.barra(s.bg.copy(), f'Pregunta {n} de {total}', marcador); d = ImageDraw.Draw(img)
        col, L = OPC[q['c']]
        img = caja(img, (DOCK_X + 10, 180, W - 50, 300), 30, col, outline=C['white'], width=6); d = ImageDraw.Draw(img)
        d.ellipse((DOCK_X + 40, 200, DOCK_X + 120, 280), fill=C['white'])
        d.text((DOCK_X + 80, 240), L, font=font('Bold', 50), fill=col, anchor='mm')
        f, ls, sz = fit(d, q['o'][q['c']], 'Bold', W - DOCK_X - 300, 110, 70)
        lines(d, ls, f, sz, DOCK_X + (W - DOCK_X) / 2 + 30, 240, C['white'])
        if q.get('img'):  # la foto acompaña al dato (también la de la pregunta, ya nítida)
            p = os.path.join(s.raiz, q['img'])
            img = foto(img, p, CAJA_DATO, q.get('img_fondo'), s.credito(p))
            bx = (DOCK_X + 760, 370, W - 50, 870)
        else:
            bx = (DOCK_X + 10, 370, W - 50, 870)
        img = caja(img, bx, 34, (255, 255, 255)); d = ImageDraw.Draw(img)
        cx = (bx[0] + bx[2]) / 2
        d.rounded_rectangle((cx - 190, bx[1] - 28, cx + 190, bx[1] + 32), 30, fill=C['gold'])
        d.text((cx, bx[1] + 2), 'DATO CURIOSO', font=font('Bold', 34), fill=C['ink'], anchor='mm')
        f, ls, sz = fit(d, q['d'], 'Medium', bx[2] - bx[0] - 90, bx[3] - bx[1] - 110, 54)
        lines(d, ls, f, sz, cx, (bx[1] + bx[3]) / 2 + 20, C['ink'])
        return img

    def tabla(s, n, total):
        img = s.barra(s.bg.copy(), f'Vamos {n} de {total}'); d = ImageDraw.Draw(img); cx = DOCK_X + (W - DOCK_X) / 2
        d.text((cx, 270), '¿Cómo vas?', font=font('Bold', 100), fill=C['gold'], anchor='mm')
        img = caja(img, (DOCK_X + 60, 380, W - 100, 720), 34, (255, 255, 255)); d = ImageDraw.Draw(img)
        d.text((cx, 480), 'Tu puesto está en tu celular', font=font('Bold', 58), fill=C['ink'], anchor='mm')
        d.text((cx, 590), 'Sin celular: cuenta tus aciertos hasta ahora', font=font('Medium', 40), fill=(90, 80, 130), anchor='mm')
        d.text((cx, 850), '¿Llegaste tarde? Escanea el código de arriba y entra ya.', font=font('Medium', 38), fill=C['white'], anchor='mm')
        return img

    def anuncio(s, grande, chico=None):
        img = s.barra(s.bg.copy()); d = ImageDraw.Draw(img)
        f, ls, sz = fit(d, grande, 'Bold', 1100, 360, 130)
        lines(d, ls, f, sz, W / 2 + 230, 470 if chico else 520, C['gold'])
        if chico: d.text((W / 2 + 230, 760), chico, font=font('Medium', 48), fill=C['white'], anchor='mm')
        return img

    def rangos(s, total=30):
        img = s.barra(s.bg.copy()); d = ImageDraw.Draw(img); cx = DOCK_X + (W - DOCK_X) / 2
        d.text((cx, 200), '¿Qué tan genio eres?', font=font('Bold', 84), fill=C['gold'], anchor='mm')
        lo = 0
        for i, (lim, t, col) in enumerate(RANGOS):
            hi = min(total, int(lim * total - 1e-9)) if lim <= 1 else total
            r = f'{lo} – {hi}' if hi > lo else f'{hi}'
            lo = hi + 1
            y = 310 + i * 140
            img = caja(img, (DOCK_X + 80, y, W - 120, y + 115), 26, col); d = ImageDraw.Draw(img)
            d.text((DOCK_X + 130, y + 57), r, font=font('Bold', 52), fill=C['white'], anchor='lm')
            d.text((DOCK_X + 560, y + 57), t, font=font('Bold', 52), fill=C['white'], anchor='lm')
        d.text((cx, 900), '¡Cuéntanos tu puntaje en los comentarios!', font=font('Medium', 42), fill=C['white'], anchor='mm')
        return img

    def fama(s, nombres, de=''):
        img = s.barra(s.bg.copy()); d = ImageDraw.Draw(img); cx = DOCK_X + (W - DOCK_X) / 2
        d.text((cx, 200), 'Salón de la fama', font=font('Bold', 92), fill=C['gold'], anchor='mm')
        if de: d.text((cx, 290), f'Los mejores de «{de}»', font=font('Medium', 40), fill=C['dimtxt'], anchor='mm')
        for i, nom in enumerate(nombres[:5]):
            y = 360 + i * 115
            img = caja(img, (DOCK_X + 160, y, W - 200, y + 95), 26, (255, 255, 255) if i else C['gold']); d = ImageDraw.Draw(img)
            d.text((DOCK_X + 220, y + 48), f'{i + 1}', font=font('Bold', 54), fill=C['ink'], anchor='mm')
            d.text((DOCK_X + 290, y + 48), str(nom)[:14], font=font('Bold', 54), fill=C['ink'], anchor='lm')
        d.text((cx, 970), 'Juega desde tu celular y sal aquí la próxima vez', font=font('Medium', 38), fill=C['white'], anchor='mm')
        return img

    def final(s):
        img = s.barra(s.bg.copy()); d = ImageDraw.Draw(img); cx = DOCK_X + (W - DOCK_X) / 2
        d.text((cx, 260), '¡Gracias por jugar!', font=font('Bold', 110), fill=C['gold'], anchor='mm')
        img = caja(img, (cx - 340, 400, cx + 340, 540), 70, (230, 33, 23)); d = ImageDraw.Draw(img)
        d.text((cx, 470), 'SUSCRÍBETE', font=font('Bold', 72), fill=C['white'], anchor='mm')
        d.text((cx, 650), 'Nueva partida cada semana', font=font('Medium', 50), fill=C['white'], anchor='mm')
        d.text((cx, 750), '@QuienSabeMasTV', font=font('Bold', 56), fill=C['gold'], anchor='mm')
        return img

# ---------------------------------------------------------------- audio
def load_wav(p):
    with wave.open(p) as w:
        sr, n, ch, sw = w.getframerate(), w.getnframes(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(n)
    a = (np.frombuffer(raw, np.int16).astype(np.float32) / 32768) if sw == 2 else (np.frombuffer(raw, np.int32).astype(np.float32) / 2**31)
    if ch > 1: a = a.reshape(-1, ch).mean(1)
    if sr != SR: a = np.interp(np.linspace(0, len(a) - 1, int(len(a) * SR / sr)), np.arange(len(a)), a)
    return a.astype(np.float32)

def tono(f, dur, vol=0.25, dec=30):
    t = np.arange(int(SR * dur)) / SR; return (vol * np.sin(2 * np.pi * f * t) * np.exp(-dec * t)).astype(np.float32)

def sfx():
    S = dict(tick=tono(1400, 0.06, 0.18, 60), tick_hi=tono(1900, 0.08, 0.26, 45))
    ding = np.zeros(int(SR * 1.2), np.float32)
    for k, f in enumerate([880, 1108.7, 1318.5]):
        st = int(k * 0.09 * SR); seg = tono(f, 1.2 - k * 0.09, 0.22, 4); ding[st:st + len(seg)] += seg
    t = np.arange(int(SR * 0.45)) / SR; nz = np.random.default_rng(1).standard_normal(len(t)).astype(np.float32)
    S['whoosh'] = (np.convolve(nz, np.ones(30) / 30, 'same') * np.sin(np.pi * t / t[-1]) ** 2 * 0.35).astype(np.float32)
    S['ding'] = ding
    buzz = tono(220, 0.7, 0.16, 3) + tono(233, 0.7, 0.16, 3); S['tiempo'] = buzz
    fan = np.zeros(int(SR * 2.0), np.float32)
    for k, f in enumerate([523.25, 659.25, 783.99, 1046.5]):
        st = int(k * 0.14 * SR); seg = tono(f, 2.0 - k * 0.14, 0.2, 2.5); fan[st:st + len(seg)] += seg
    S['fanfare'] = fan
    return S

# ---------------------------------------------------------------- línea de tiempo
class Programa:
    def __init__(s):
        s.escenas = []   # (t0, dur, fn(t)->img | img, quien)
        s.audio = []     # (t, arr)
        s.habla = []     # (t0, t1, quien, envolvente por frame)
        s.t = 0.0
        s.subs = None   # subtítulos karaoke (QSM_SUBTITULOS=1)
        s.relojes, s.temas, s.musica = [], [], None   # para la música: (t, seg) del reloj y (t, cual) de los temas

    def sonido(s, arr, at=None, gain=1.0): s.audio.append((s.t if at is None else at, arr * gain))

    def escena(s, img, dur, quien=None, poses=None):
        """poses: {quien: pose}. Si habla otro personaje que está en poses, se cambia a él."""
        if isinstance(img, Image.Image):  # comprimida: un maratón tiene miles de pantallas y no caben en memoria
            img = ('z', img.size, zlib.compress(img.tobytes(), 1))
        s.escenas.append((s.t, dur, img, quien, poses or {})); s.t += dur

    def cuadro(s, ei, t):
        """Pantalla base de la escena ei en el instante t (se descomprime una vez por escena)."""
        t0, dur, img, quien, poses = s.escenas[ei]
        if callable(img): return img(t - t0)
        if getattr(s, '_vivo', (None,))[0] != ei:
            s._vivo = (ei, Image.frombytes('RGB', img[1], zlib.decompress(img[2])))
        return s._vivo[1]

    def voz(s, arr, at, quien, texto=None, pantalla=''):
        s.audio.append((at, arr))
        hop = SR // FPS; n = max(1, len(arr) // hop)
        env = np.array([np.sqrt(np.mean(arr[i * hop:(i + 1) * hop] ** 2) + 1e-9) for i in range(n)])
        ref = max(np.percentile(env, 92), 1e-4)
        lv = np.clip(np.round(env / ref * 4), 0, 4).astype(int); lv[env < 0.012] = 0
        s.habla.append((at, at + len(arr) / SR, quien, lv))
        if s.subs and texto: s.subs.agregar(at, lv, quien, texto, pantalla)

    def boca(s, t, quien):
        for t0, t1, q, lv in s.habla:
            if q == quien and t0 <= t < t1:
                return int(lv[min(len(lv) - 1, int((t - t0) * FPS))])
        return 0

    def hablante(s, t):
        for t0, t1, q, lv in s.habla:
            if t0 <= t < t1: return q
        return None

    def personaje(s, fr, quien, pose, t):
        """Pega el personaje (o LA VOZ) en la columna izquierda del cuadro fr."""
        b = s.boca(t, quien)
        if quien == 'anunciador':
            sp = voz_sprite(b, int(t * 10) % 12 if b else 0)
            fr.paste(sp, (DOCK_X // 2 - sp.width // 2, 600 - sp.height // 2), sp)
            return
        k = int(t * FPS) + (17 if quien == 'copresentadora' else 0)
        parp = (k % 61) in (0, 1) or (k % 167) in (0, 1)
        bob = round(4 * np.sin(2 * np.pi * t / 3.4))
        sp, (cx, cy) = sprite(quien, pose, b, parp)
        cyp = (650 if quien == 'presentador' else 610) + bob
        x = round(DOCK_X / 2 - cx); y = round(cyp - cy)
        if x < 0: x = 0
        if x + sp.width > DOCK_X + 30: x = max(0, DOCK_X + 30 - sp.width)
        fr.paste(sp, (x, y), sp)
        d = ImageDraw.Draw(fr); cxn = DOCK_X / 2
        # más arriba: abajo lo tapa la barra de reproducción de YouTube
        d.rounded_rectangle((cxn - 85, H - 156, cxn + 85, H - 104), 26, fill=C['gold'])
        d.text((cxn, H - 130), NOMBRES[quien], font=font('Bold', 32), fill=C['ink'], anchor='mm')

    def render(s, out, tmp):
        os.makedirs(tmp, exist_ok=True)
        total = s.t; nfr = int(total * FPS)
        vid = os.path.join(tmp, 'video.mp4')
        ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                               '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
                               '-pix_fmt', 'yuv420p', '-r', '30', vid], stdin=subprocess.PIPE)
        ei = 0; cache = {}
        if s.subs: s.subs.cerrar()
        for k in range(nfr):
            t = k / FPS
            st = s.subs.estado(t) if s.subs else None
            while ei + 1 < len(s.escenas) and t >= s.escenas[ei + 1][0]: ei += 1
            t0, dur, img, quien, poses = s.escenas[ei]
            base = s.cuadro(ei, t)
            if quien:
                h = s.hablante(t)
                if h and h != quien and h in poses: quien = h
                pose = poses.get(quien, 'base')
                if quien == 'anunciador':
                    b = s.boca(t, quien); key = (id(base), quien, b, int(t * 10) % 12 if b else 0)
                else:
                    k = int(t * FPS) + (17 if quien == 'copresentadora' else 0)
                    key = (id(base), quien, pose, s.boca(t, quien), (k % 61) in (0, 1) or (k % 167) in (0, 1),
                           round(4 * np.sin(2 * np.pi * t / 3.4)))
                key = key + (st,)
                if key not in cache or cache[key][0] is not base:
                    if len(cache) > 90: cache.clear()
                    fr = base.copy(); s.personaje(fr, quien, pose, t)
                    if st: s.subs.dibujar(fr, st)
                    cache[key] = (base, fr.tobytes())
                ff.stdin.write(cache[key][1])
            else:
                key = ('b', id(base), st)
                if key not in cache or cache[key][0] is not base:
                    if len(cache) > 60: cache.clear()
                    if st:
                        fr = base.copy(); s.subs.dibujar(fr, st); cache[key] = (base, fr.tobytes())
                    else: cache[key] = (base, base.tobytes())
                ff.stdin.write(cache[key][1])
        ff.stdin.close(); ff.wait()
        mix = np.zeros(int(SR * (total + 0.5)), np.float32)
        for at, a in s.audio:
            st = int(at * SR); e = min(len(mix), st + len(a)); mix[st:e] += a[:e - st]
        if getattr(s, 'musica', None): s.musica.mezclar(mix, s.habla, s.relojes, s.temas)
        pk = np.abs(mix).max()
        if pk > 0.98: mix *= 0.98 / pk
        wav = os.path.join(tmp, 'audio.wav')
        with wave.open(wav, 'w') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype(np.int16).tobytes())
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', vid, '-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                        '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', '48000', '-ac', '2', '-c:a', 'aac', '-b:a', '192k',
                        '-shortest', '-movflags', '+faststart', out], check=True)

# ---------------------------------------------------------------- guion del programa
RANGOS = [(0.34, 'Aprendiz curioso', (47, 128, 237)), (0.67, 'Sabelotodo en camino', (39, 174, 96)),
          (0.91, 'Experto', (240, 170, 20)), (1.01, '¡GENIO TOTAL!', (231, 76, 60))]  # mismo criterio que la web
VARIANTES = 'banco/var'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--contenido', required=True); ap.add_argument('--banco', default='banco')
    ap.add_argument('--voces', default=''); ap.add_argument('--out', required=True)
    ap.add_argument('--tmp', default='tmp'); ap.add_argument('--lobby', type=int, default=6)
    a = ap.parse_args()
    raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    meta = json.load(open(a.contenido)); Q = meta['preguntas']; N = meta.get('total_anunciado', len(Q))
    P = Pantallas(meta, f"https://quiensabemastv.pages.dev/?sala={meta['codigo_sala']}", raiz)
    G = Programa(); S = sfx(); faltan = []
    VOZ_DE = {'pr': 'presentador', 'co': 'copresentadora', 'an': 'anunciador'}
    ex = meta.get('extra_tts', {})
    # variantes de las frases fijas: rotan dentro del episodio y cambian de punto de partida en cada episodio
    var_dir = os.path.join(raiz, VARIANTES); semilla = sum(map(ord, meta.get('id', meta['codigo_sala']))); uso = {}
    cm = carpeta_musica(raiz)   # temas de la Biblioteca de audio de YouTube (si están descifrados)
    if cm and not os.environ.get('QSM_SIN_MUSICA'): G.musica = MusicaArchivos(cm, semilla)
    elif os.environ.get('QSM_MUSICA_SINTE'): G.musica = Musica(semilla)
    KB = not os.environ.get('QSM_SIN_MOVIMIENTO')
    if os.environ.get('QSM_SUBTITULOS'):
        fd = os.path.join(raiz, 'fuentes')
        G.subs = Subtitulos(W, H, FPS, os.path.join(fd, 'Poppins-Black.ttf'), FONT % 'Bold', DOCK_X + 20, W - 250, 985)
    TXT = {}
    rival_dir = os.path.join(raiz, 'banco', 'rival')
    for f in (os.path.join(raiz, 'banco', 'indice.json'), os.path.join(var_dir, 'indice.json'), os.path.join(rival_dir, 'indice.json')):
        if os.path.exists(f): TXT.update({k: v.get('texto', '') for k, v in json.load(open(f, encoding='utf-8')).items()})
    # sin subtítulo: lo que ya sale escrito grande en pantalla (pregunta, dato curioso y los anuncios)
    # lo que ya está escrito en pantalla mientras suena cada clip: esas palabras no se subtitulan (sí las que faltan)
    LOBBY = 'Escanea el código Escribe tu apodo Al oír ¡YA! toca EMPEZAR ¿Sin celular? Anota tus aciertos en un papel y juega igual. sala ' + meta['codigo_sala']
    QN = {f"q{q['n']:02d}": q for q in Q}

    def en_pantalla(clave):
        base = '¿Quién Sabe Más? ' + meta['titulo']
        q = QN.get(clave[:3])
        if q and clave.endswith('_pregunta'): return base + ' ' + q['p'] + ' ' + ' '.join(q['o'])
        if q and clave.endswith('_respuesta'): return base + ' ' + q['p'] + ' ' + ' '.join(q['o'])
        if q and clave.endswith('_dato'): return base + ' Dato curioso ' + q['o'][q['c']] + ' ' + q['d']
        if clave.startswith('an_'): return base + ' ' + ' '.join(' '.join(v[1:]) for v in ANUNCIO.values()) + ' ¡Pregunta final! ¡Y el ganador es…! Míralo en tu celular ¡YA! Toca EMPEZAR en tu celular'
        if clave in ('pr_01_celulares', 'co_06_sincelular', 'pr_intro', 'co_intro', 'pr_02_empezamos'): return base + ' ' + LOBBY
        return base
    dicho = {}

    def mover(img, q, caja, t_ini):
        """Foto con movimiento lento (no en banderas ni mientras la imagen misteriosa está pixelada)."""
        if not KB or not q.get('img') or q.get('img_fondo') == 'blanco': return img
        p = os.path.join(raiz, q['img'])
        return Movil(img, p, caja, P.credito(p), q['n'] * 7 + semilla, t_ini, G.t)

    def variante(clave):
        for vd in (var_dir, rival_dir):
            if not os.path.isdir(vd): continue
            n = len([f for f in os.listdir(vd) if f.startswith(clave + '__') and f.endswith('.wav')])
            if not n: continue
            k = (semilla + uso.get(clave, 0) * 7) % n; uso[clave] = uso.get(clave, 0) + 1
            return f'{vd}/{clave}__{k}.wav'
        return None

    def voz(clave, est=''):
        v = variante(clave)
        if v and os.path.exists(v):
            dicho['t'] = TXT.get(os.path.basename(v)[:-4]) or TXT.get(clave) or est; return load_wav(v)
        dicho['t'] = (ex[clave][1] if clave in ex else '') or est or TXT.get(clave, '')
        for d in (a.voces, a.banco):
            if d and os.path.exists(f'{d}/{clave}.wav'): return load_wav(f'{d}/{clave}.wav')
        faltan.append(clave); return np.zeros(int(SR * max(1.0, len(est) / 15)), np.float32)

    def quien(clave):
        if clave.startswith('q'): return 'presentador' if clave.endswith('_pregunta') else 'copresentadora'
        if clave in ex: return ex[clave][0]
        return VOZ_DE.get(clave[:2], 'presentador')

    def decir(img, clips, quien_pantalla=None, pad=0.35, pre=0.0, poses=None):
        """clips: lista de (clave, texto_estimado). Cada clip anima a su personaje."""
        t = G.t + pre
        for clave, est in clips:
            arr = voz(clave, est); G.voz(arr, t, quien(clave), dicho.get('t'), en_pantalla(clave))
            t += len(arr) / SR + 0.12
        G.escena(img, t - G.t + pad, quien_pantalla, poses)

    capitulos = [(0.0, 'Bienvenida')]
    # --- apertura
    if G.musica: G.temas.append((0.0, 'entrada'))
    else: G.sonido(S['fanfare'], gain=0.8)
    RAPIDO = bool(os.environ.get('QSM_ARRANQUE_RAPIDO'))   # PRUEBA: la pregunta 1 en los primeros segundos
    RIVAL = bool(os.environ.get('QSM_RIVALIDAD')) and os.path.isdir(rival_dir)   # PRUEBA: MAX contra NOVA
    import random as _rnd
    rr = _rnd.Random(semilla * 31 + 7); pts = [0, 0]   # [MAX, NOVA]
    MC = lambda: tuple(pts) if RIVAL else None

    def apostar(q):
        """Cada uno elige: aciertan ~70 % de las veces (algo menos en las difíciles); si fallan, otra al azar."""
        dif = (q['n'] - 1) * 3 // N; out = {}
        for k, p in (('presentador', [0.85, 0.72, 0.58][dif]), ('copresentadora', [0.85, 0.72, 0.6][dif])):
            out[k] = q['c'] if rr.random() < p else rr.choice([i for i in range(len(q['o'])) if i != q['c']])
        return out

    def como_jugar():
        """Arranque rápido: la explicación del QR y el salón de la fama van después de la pregunta 3."""
        decir(P.lobby(), [('pr_01_celulares', '')], 'presentador', pad=0.6, poses={'presentador': 'saluda'})
        decir(P.lobby(), [('co_06_sincelular', '')], 'copresentadora', pad=1.5, poses={'copresentadora': 'saluda'})
        if meta.get('fama'):   # sin capítulo propio: YouTube exige capítulos de 10 s o más
            decir(P.fama(meta['fama'], meta.get('fama_de', '')), [('co_fama', ex.get('co_fama', ['', ''])[1])], 'copresentadora', pad=2.0,
                  poses={'copresentadora': 'aplaude'})

    if RAPIDO:
        decir(P.anuncio('¡¿Quién Sabe Más?!', meta['titulo']), [('an_01_marca', '')], 'anunciador', pad=0.2, pre=0.3)
        if RIVAL: decir(P.anuncio('MAX contra NOVA', '…y tú contra los dos'), [('an_rival', '')], 'anunciador', pad=0.3)
    else:
      decir(P.anuncio('¡¿Quién Sabe Más?!', meta['titulo']), [('an_01_marca', ''), ('an_tema', ex.get('an_tema', ['', ''])[1])], 'anunciador', pre=0.6)
    if not RAPIDO:
     decir(P.lobby(), [('pr_intro', ex.get('pr_intro', ['', ''])[1]), ('pr_01_celulares', '')], 'presentador', poses={'presentador': 'saluda'})
     decir(P.lobby(), [('co_intro', ex.get('co_intro', ['', ''])[1])], 'copresentadora', poses={'copresentadora': 'saluda'})
    if meta.get('fama') and not RAPIDO:
        capitulos.append((G.t, 'Salón de la fama'))
        decir(P.fama(meta['fama'], meta.get('fama_de', '')), [('co_fama', ex.get('co_fama', ['', ''])[1])], 'copresentadora', pad=4.0,
              poses={'copresentadora': 'aplaude'})
    if RAPIDO: t_ya = G.t
    else:
     for i in range(a.lobby):
        G.sonido(S['tick'], at=G.t, gain=0.6); G.escena(P.lobby(cuenta=a.lobby - i), 1.0, 'presentador', {'presentador': 'frente'})
     decir(P.anuncio('¡YA!', 'Toca EMPEZAR en tu celular'), [('pr_02_empezamos', '')], 'presentador', poses={'presentador': 'celebra2'})
     t_ya = G.t - 0.35  # referencia de sincronía: justo cuando el presentador dice «¡Ya!»
    tiempos = []
    bloque = 10 if len(Q) <= 120 else 25

    previa = None; RELOJ = {}
    for idx, q in enumerate(Q):
        n = q['n']; key = f'q{n:02d}'; ronda = q.get('ronda')
        if ronda == 'misteriosa' and not (q.get('img') and q.get('img_modo') == 'pregunta'): ronda = None  # sin foto no hay misterio
        relam = ronda == 'relampago'; seg = 5 if relam else 10
        if idx % bloque == 0:
            fin = Q[min(len(Q), idx + bloque) - 1]['n']
            capitulos.append((G.t, f'Preguntas {n} a {fin}' if fin != n else f'Pregunta {n}'))
        if n == N:
            capitulos.append((G.t, 'Pregunta final'))
            G.sonido(S['fanfare'], gain=0.7); decir(P.anuncio('¡Pregunta final!'), [('an_03_final', '')], 'anunciador', pad=0.5, pre=0.3)
        elif ronda in ANUNCIO and ronda != previa:
            clave_an, grande, chico = ANUNCIO[ronda]
            if relam: capitulos.append((G.t, 'Ronda relámpago'))
            G.sonido(S['fanfare'], gain=0.6)
            decir(P.anuncio(grande, chico), [(clave_an, grande)], 'anunciador', pad=0.8, pre=0.3)
        previa = ronda
        G.sonido(S['whoosh'], gain=0.8)
        G.escena(P.tarjeta(n, N, ronda), 1.0 if relam else 1.6, 'presentador', {'presentador': 'base'})
        t_abre = G.t
        pix0 = 34 if ronda == 'misteriosa' else 0
        con_foto = bool(q.get('img')) and q.get('img_modo') == 'pregunta'
        mueve = con_foto and not pix0   # la misteriosa ya se mueve con el pixelado
        img_p = P.pregunta(n, N, q, pix=pix0, marcador=MC())
        decir(mover(img_p, q, CAJA_PREG, t_abre) if mueve else img_p, [(f'{key}_pregunta', q['tp'])], 'presentador', pad=0.3,
              poses={'presentador': 'senala'})
        if idx < 2: G.voz(voz('pr_03_segundos'), G.t + 0.1, 'presentador')
        t0 = G.t
        for sec in range(seg): G.sonido(S['tick_hi'] if sec >= seg - 3 else S['tick'], at=t0 + sec, gain=0.8)
        def tfn(t, q=q, n=n, seg=seg, pix0=pix0, mc=MC()):
            r = max(1, seg - int(t)); fr = round((1 - t / seg) * 40) / 40
            px = round(pix0 * (r - 1) / (seg - 1)) if pix0 else 0  # se aclara segundo a segundo
            k = (n, r, fr)
            if k not in RELOJ:
                RELOJ.clear()  # un solo cuadro vivo a la vez: con 90+ preguntas la memoria se llenaba
                RELOJ[k] = P.pregunta(n, N, q, reloj=r, frac=fr, pix=px, marcador=mc)
            return RELOJ[k]
        G.relojes.append((t0, float(seg)))
        G.escena(mover(tfn, q, CAJA_PREG, t_abre) if mueve else tfn, float(seg), 'presentador', {'presentador': 'piensa'})
        t_kb = t_abre if mueve else G.t   # la misteriosa empieza a moverse recién al revelarse
        G.sonido(S['tiempo'], gain=0.7)
        tiempos.append({'n': n, 'abre': round(t_abre - t_ya, 2), 'reloj': round(t0 - t_ya, 2), 'cierra': round(G.t - t_ya, 2)})
        if relam:  # sin pausa: directo a la respuesta, sin dato curioso
            G.sonido(S['ding'], at=G.t + 0.1, gain=0.9)
            img_r = P.pregunta(n, N, q, modo='revela', marcador=MC())
            decir(mover(img_r, q, CAJA_PREG, t_kb) if con_foto else img_r, [(f'{key}_respuesta', q['tr'])], 'copresentadora', pad=0.6, pre=0.1,
                  poses={'copresentadora': 'aplaude'})
        else:
            img_y = P.pregunta(n, N, q, reloj='¡YA!', frac=0, marcador=MC())
            ap = None
            if RIVAL:   # después del «¡Tiempo!»: cada uno dice qué eligió (el espectador ya respondió)
                ap = apostar(q); L = 'ABCD'
                decir(mover(img_y, q, CAJA_PREG, t_kb) if con_foto else img_y, [('pr_04_tiempo', '')], 'presentador', pad=0.05, pre=0.1,
                      poses={'presentador': 'frente'})
                img_a = P.pregunta(n, N, q, reloj='¡YA!', frac=0, marcador=MC(), apuestas=ap)
                decir(mover(img_a, q, CAJA_PREG, t_kb) if con_foto else img_a,
                      [(f"pr_apuesta_{L[ap['presentador']]}", ''), (f"co_apuesta_{L[ap['copresentadora']]}", ''), ('co_08_correcta', '')],
                      'presentador', pad=0.1, poses={'presentador': 'senala', 'copresentadora': 'presenta'})
                img_y = img_a
            else:
                decir(mover(img_y, q, CAJA_PREG, t_kb) if con_foto else img_y, [('pr_04_tiempo', ''), ('co_08_correcta', '')], 'copresentadora', pad=0.1, pre=0.1,
                      poses={'copresentadora': 'presenta', 'presentador': 'frente'})
            if ap:
                pts[0] += ap['presentador'] == q['c']; pts[1] += ap['copresentadora'] == q['c']
            G.sonido(S['ding'], at=G.t + 0.2, gain=0.9)
            dificil = (n - 1) * 3 // N >= 2
            rev = 'celebra' if n == N else ('sorpresa' if dificil and n % 2 == 0 else 'aplaude')
            img_r = P.pregunta(n, N, q, modo='revela', marcador=MC(), apuestas=ap)
            decir(mover(img_r, q, CAJA_PREG, t_kb) if con_foto else img_r, [(f'{key}_respuesta', q['tr'])], 'copresentadora', pad=0.9, pre=0.2,
                  poses={'copresentadora': rev})
            decir(mover(P.dato(n, N, q, marcador=MC()), q, CAJA_DATO, t_kb if con_foto else G.t), [('co_02_dato', ''), (f'{key}_dato', q['td'])], 'copresentadora', pad=1.2,
                  poses={'copresentadora': 'presenta'})
        if RAPIDO and idx == 2: como_jugar()
        sig = Q[idx + 1] if idx + 1 < len(Q) else None
        if (idx + 1) % 5 == 0 and n != N and not (relam and sig and sig.get('ronda') == 'relampago'):
            charla = [(c, ex[c][1]) for c in (f'charla{n:02d}_pr', f'charla{n:02d}_co') if c in ex]
            decir(P.tabla(n, N), charla or [('pr_08_tabla', '')], 'presentador', pad=2.5,
                  poses={'presentador': 'base', 'copresentadora': 'presenta'})
    # --- cierre
    capitulos.append((G.t, 'Resultados'))
    decir(P.anuncio('¡Y el ganador es…!', 'Míralo en tu celular'), [('an_04_ganador', '')], 'anunciador', pad=0.8)
    G.sonido(S['fanfare'], gain=0.8)
    decir(P.rangos(len(Q)), [('co_05_felicidades', ''), ('pr_cierre', ex.get('pr_cierre', ['', ''])[1])], 'presentador', pad=3.0,
          poses={'presentador': 'celebra', 'copresentadora': 'celebra'})
    if RIVAL:
        if pts[0] == pts[1]: pts[1] += 1   # sin empates: siempre hay revancha
        gana_max = pts[0] > pts[1]
        capitulos.append((G.t, 'MAX contra NOVA: resultado'))
        G.sonido(S['fanfare'], gain=0.7)
        decir(P.anuncio(f"¡Ganó {'MAX' if gana_max else 'NOVA'}!", f'MAX {pts[0]}  ·  NOVA {pts[1]}'),
              [('pr_gana_final' if gana_max else 'co_gana_final', ''), ('co_revancha' if gana_max else 'pr_revancha', '')],
              'presentador' if gana_max else 'copresentadora', pad=1.5,
              poses={'presentador': 'celebra' if gana_max else 'piensa', 'copresentadora': 'sorpresa' if gana_max else 'celebra'})
        print(f'MAX contra NOVA: {pts[0]} - {pts[1]}')
    if G.musica: G.temas.append((G.t, 'salida'))
    decir(P.final(), [('pr_12_suscribanse', ''), ('co_07_otra', ''), ('pr_13_despedida', '')], 'presentador', pad=3.0,
          poses={'presentador': 'saluda', 'copresentadora': 'saluda'})
    if RAPIDO and len(capitulos) > 1 and capitulos[1][0] < 10:   # la pregunta 1 arranca enseguida: su capítulo empieza en 0:00
        capitulos = [(0.0, capitulos[1][1])] + capitulos[2:]
    print(f'Duración: {G.t/60:.1f} min · escenas: {len(G.escenas)}')
    sync = {'sala': meta['codigo_sala'], 'titulo': meta['titulo'], 'total': N, 'ya': round(t_ya, 2), 'duracion': round(G.t, 2),
            'tiempos': tiempos, 'capitulos': [[round(t, 1), c] for t, c in capitulos], 'faltan': sorted(set(faltan))}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(sync, open(os.path.splitext(a.out)[0] + '.tiempos.json', 'w'), ensure_ascii=False, indent=1)
    if faltan: print('Voces faltantes (silencio):', sorted(set(faltan)))
    if os.environ.get('QSM_SOLO_TIEMPOS'): return
    G.render(a.out, a.tmp); print('OK', a.out)

if __name__ == '__main__':
    main()
