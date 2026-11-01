#!/usr/bin/env python3
"""Montador v2 — formato programa de TV con personajes animados e imágenes.
Uso:
  python3 pipeline/tv.py --contenido contenido/maqueta_tv.json --banco banco --voces voces/maqueta --out salida/maqueta.mp4
Las voces que falten quedan en silencio (sirve para maquetas).
"""
import argparse, json, os, subprocess, wave, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

sys.path.insert(0, os.path.dirname(__file__))
from personajes import sprite, voz_sprite, NOMBRES
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

def foto(img, path, box, fondo=None, credito=None):
    x0, y0, x1, y1 = box; w, h = x1 - x0, y1 - y0
    img = caja(img, (x0 - 10, y0 - 10, x1 + 10, y1 + 10), 30, (255, 255, 255))
    src = Image.open(path).convert('RGB')
    if fondo == 'blanco':
        src.thumbnail((w - 80, h - 80)); can = Image.new('RGB', (w, h), (255, 255, 255))
        can.paste(src, ((w - src.width) // 2, (h - src.height) // 2)); src = can
    else:
        src = ImageOps.fit(src, (w, h), Image.LANCZOS)
    mask = Image.new('L', (w, h), 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, w, h), 22, fill=255)
    img.paste(src, (x0, y0), mask)
    if credito:
        d = ImageDraw.Draw(img); f = font('Regular', 18)
        tw = d.textlength(credito, font=f)
        d.rounded_rectangle((x1 - tw - 24, y1 - 34, x1 - 6, y1 - 8), 8, fill=(0, 0, 0))
        d.text((x1 - 15, y1 - 21), credito, font=f, fill=(230, 230, 230), anchor='rm')
    return img

# ---------------------------------------------------------------- pantallas
class Pantallas:
    def __init__(s, meta, url, raiz):
        s.m = meta; s.raiz = raiz; s.bg = escenario()
        s.qr_s = qr_img(url, 140); s.qr_l = qr_img(url, 400)
        cred = os.path.join(raiz, 'assets', 'maqueta', 'creditos.json')
        s.cred = json.load(open(cred)) if os.path.exists(cred) else {}

    def credito(s, path):
        c = s.cred.get(os.path.basename(path))
        if not c: return None
        autor = c['autor'].split('\n')[0][:40] or 'Wikimedia Commons'
        return f"Foto: {autor} · {c['licencia']}"

    def barra(s, img, etiqueta=None):
        d = ImageDraw.Draw(img)
        d.text((50, 58), '¿Quién Sabe Más?', font=font('Bold', 38), fill=C['gold'], anchor='lm')
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
        for i, t in enumerate(['Escanea el código', 'Escribe tu apodo', '¡Responde rápido!']):
            d.ellipse((x, 330 + i * 80, x + 56, 386 + i * 80), fill=C['gold'])
            d.text((x + 28, 358 + i * 80), str(i + 1), font=font('Bold', 34), fill=C['ink'], anchor='mm')
            d.text((x + 76, 358 + i * 80), t, font=font('Medium', 42), fill=C['white'], anchor='lm')
        d.text((x, 600), 'Sala', font=font('Medium', 32), fill=C['dimtxt'], anchor='lm')
        img = caja(img, (x, 630, x + 400, 740), 22, (255, 255, 255)); d = ImageDraw.Draw(img)
        d.text((x + 200, 686), s.m['codigo_sala'], font=font('Bold', 76), fill=C['ink'], anchor='mm')
        d.text((W / 2 + 200, 850), '¿Sin celular? Anota tus aciertos en un papel y juega igual.', font=font('Regular', 36), fill=C['dimtxt'], anchor='mm')
        if cuenta is not None:
            d.ellipse((W - 220, 860, W - 80, 1000), fill=C['gold'])
            d.text((W - 150, 932), str(cuenta), font=font('Bold', 80), fill=C['ink'], anchor='mm')
        return img

    def tarjeta(s, n, total):
        img = s.barra(s.bg.copy()); d = ImageDraw.Draw(img)
        nv = NIVEL[min(2, (n - 1) * 3 // total)]; cx = DOCK_X + (W - DOCK_X) / 2
        d.rounded_rectangle((cx - 150, 300, cx + 150, 370), 35, fill=nv[1])
        d.text((cx, 336), nv[0], font=font('Bold', 40), fill=C['white'], anchor='mm')
        d.text((cx, 530), f'PREGUNTA {n}', font=font('Bold', 150), fill=C['white'], anchor='mm')
        d.text((cx, 670), f'de {total}', font=font('Medium', 56), fill=C['dimtxt'], anchor='mm')
        return img

    def _opciones(s, img, q, modo, box, cols):
        x0, y0, x1, y1 = box; g = 26
        rows = 4 // cols; bw = (x1 - x0 - g * (cols - 1)) / cols; bh = (y1 - y0 - g * (rows - 1)) / rows
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
        return img

    def pregunta(s, n, total, q, modo='normal', reloj=None, frac=None):
        img = s.barra(s.bg.copy(), f'Pregunta {n} de {total}'); d = ImageDraw.Draw(img)
        con_foto = q.get('img') and q.get('img_modo') == 'pregunta'
        if con_foto:
            f, ls, sz = fit(d, q['p'], 'Bold', W - DOCK_X - 90, 110, 60)
            lines(d, ls, f, sz, DOCK_X + (W - DOCK_X) / 2 - 20, 185, C['white'])
            p = os.path.join(s.raiz, q['img'])
            img = foto(img, p, (DOCK_X + 10, 270, DOCK_X + 10 + 760, 270 + 520), q.get('img_fondo'), s.credito(p))
            img = s._opciones(img, q, modo, (DOCK_X + 820, 270, W - 50, 790), 1)
        else:
            f, ls, sz = fit(d, q['p'], 'Bold', W - DOCK_X - 110, 250, 70)
            lines(d, ls, f, sz, DOCK_X + (W - DOCK_X) / 2 - 20, 300, C['white'])
            img = s._opciones(img, q, modo, (DOCK_X + 10, 460, W - 50, 830), 2)
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

    def dato(s, n, total, q):
        img = s.barra(s.bg.copy(), f'Pregunta {n} de {total}'); d = ImageDraw.Draw(img)
        col, L = OPC[q['c']]
        img = caja(img, (DOCK_X + 10, 180, W - 50, 300), 30, col, outline=C['white'], width=6); d = ImageDraw.Draw(img)
        d.ellipse((DOCK_X + 40, 200, DOCK_X + 120, 280), fill=C['white'])
        d.text((DOCK_X + 80, 240), L, font=font('Bold', 50), fill=col, anchor='mm')
        f, ls, sz = fit(d, q['o'][q['c']], 'Bold', W - DOCK_X - 300, 110, 70)
        lines(d, ls, f, sz, DOCK_X + (W - DOCK_X) / 2 + 30, 240, C['white'])
        foto_rev = q.get('img') and q.get('img_modo') == 'revela'
        if foto_rev:
            p = os.path.join(s.raiz, q['img'])
            img = foto(img, p, (DOCK_X + 10, 360, DOCK_X + 10 + 700, 360 + 500), None, s.credito(p))
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

    def rangos(s):
        img = s.barra(s.bg.copy()); d = ImageDraw.Draw(img); cx = DOCK_X + (W - DOCK_X) / 2
        d.text((cx, 200), '¿Qué tan genio eres?', font=font('Bold', 84), fill=C['gold'], anchor='mm')
        filas = [('0 – 10', 'Aprendiz curioso', (47, 128, 237)), ('11 – 20', 'Sabelotodo en camino', (39, 174, 96)),
                 ('21 – 27', 'Experto', (240, 170, 20)), ('28 – 30', '¡GENIO TOTAL!', (231, 76, 60))]
        for i, (r, t, col) in enumerate(filas):
            y = 310 + i * 140
            img = caja(img, (DOCK_X + 80, y, W - 120, y + 115), 26, col); d = ImageDraw.Draw(img)
            d.text((DOCK_X + 130, y + 57), r, font=font('Bold', 52), fill=C['white'], anchor='lm')
            d.text((DOCK_X + 520, y + 57), t, font=font('Bold', 52), fill=C['white'], anchor='lm')
        d.text((cx, 900), '¡Cuéntanos tu puntaje en los comentarios!', font=font('Medium', 42), fill=C['white'], anchor='mm')
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

    def sonido(s, arr, at=None, gain=1.0): s.audio.append((s.t if at is None else at, arr * gain))

    def escena(s, img, dur, quien=None, poses=None):
        """poses: {quien: pose}. Si habla otro personaje que está en poses, se cambia a él."""
        s.escenas.append((s.t, dur, img, quien, poses or {})); s.t += dur

    def voz(s, arr, at, quien):
        s.audio.append((at, arr))
        hop = SR // FPS; n = max(1, len(arr) // hop)
        env = np.array([np.sqrt(np.mean(arr[i * hop:(i + 1) * hop] ** 2) + 1e-9) for i in range(n)])
        ref = max(np.percentile(env, 92), 1e-4)
        lv = np.clip(np.round(env / ref * 4), 0, 4).astype(int); lv[env < 0.012] = 0
        s.habla.append((at, at + len(arr) / SR, quien, lv))

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
        d.rounded_rectangle((cxn - 85, H - 92, cxn + 85, H - 40), 26, fill=C['gold'])
        d.text((cxn, H - 66), NOMBRES[quien], font=font('Bold', 32), fill=C['ink'], anchor='mm')

    def render(s, out, tmp):
        os.makedirs(tmp, exist_ok=True)
        total = s.t; nfr = int(total * FPS)
        vid = os.path.join(tmp, 'video.mp4')
        ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                               '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
                               '-pix_fmt', 'yuv420p', '-r', '30', vid], stdin=subprocess.PIPE)
        ei = 0; cache = {}
        for k in range(nfr):
            t = k / FPS
            while ei + 1 < len(s.escenas) and t >= s.escenas[ei + 1][0]: ei += 1
            t0, dur, img, quien, poses = s.escenas[ei]
            base = img(t - t0) if callable(img) else img
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
                if key not in cache:
                    if len(cache) > 300: cache.clear()
                    fr = base.copy(); s.personaje(fr, quien, pose, t)
                    cache[key] = fr.tobytes()
                ff.stdin.write(cache[key])
            else:
                key = ('b', id(base))
                if key not in cache:
                    if len(cache) > 200: cache.clear()
                    cache[key] = base.tobytes()
                ff.stdin.write(cache[key])
        ff.stdin.close(); ff.wait()
        mix = np.zeros(int(SR * (total + 0.5)), np.float32)
        for at, a in s.audio:
            st = int(at * SR); e = min(len(mix), st + len(a)); mix[st:e] += a[:e - st]
        pk = np.abs(mix).max()
        if pk > 0.98: mix *= 0.98 / pk
        wav = os.path.join(tmp, 'audio.wav')
        with wave.open(wav, 'w') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype(np.int16).tobytes())
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', vid, '-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                        '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', '48000', '-ac', '2', '-c:a', 'aac', '-b:a', '192k',
                        '-shortest', '-movflags', '+faststart', out], check=True)

# ---------------------------------------------------------------- guion del programa
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

    def voz(clave, est=''):
        for d in (a.voces, a.banco):
            if d and os.path.exists(f'{d}/{clave}.wav'): return load_wav(f'{d}/{clave}.wav')
        faltan.append(clave); return np.zeros(int(SR * max(1.0, len(est) / 15)), np.float32)

    def decir(img, clips, quien_pantalla=None, pad=0.35, pre=0.0, poses=None):
        """clips: lista de (clave, texto_estimado). Cada clip anima a su personaje."""
        t = G.t + pre
        for clave, est in clips:
            arr = voz(clave, est); who = VOZ_DE.get(clave[:2], 'presentador')
            if clave.startswith('q'): who = 'presentador' if clave.endswith('_pregunta') else 'copresentadora'
            G.voz(arr, t, who); t += len(arr) / SR + 0.12
        G.escena(img, t - G.t + pad, quien_pantalla, poses)

    ex = meta.get('extra_tts', {})
    # --- apertura
    G.sonido(S['fanfare'], gain=0.8)
    decir(P.anuncio('¡¿Quién Sabe Más?!', meta['titulo']), [('an_01_marca', ''), ('an_tema', ex.get('an_tema', ['', ''])[1])], 'anunciador', pre=0.6)
    decir(P.lobby(), [('pr_intro', ex.get('pr_intro', ['', ''])[1]), ('pr_01_celulares', '')], 'presentador', poses={'presentador': 'saluda'})
    decir(P.lobby(), [('co_intro', ex.get('co_intro', ['', ''])[1])], 'copresentadora', poses={'copresentadora': 'saluda'})
    for i in range(a.lobby):
        G.sonido(S['tick'], at=G.t, gain=0.6); G.escena(P.lobby(cuenta=a.lobby - i), 1.0, 'presentador', {'presentador': 'frente'})
    decir(P.anuncio('¡Empezamos!'), [('pr_02_empezamos', '')], 'presentador', poses={'presentador': 'celebra2'})

    for q in Q:
        n = q['n']; key = f'q{n:02d}'
        if n == N:
            G.sonido(S['fanfare'], gain=0.7); decir(P.anuncio('¡Pregunta final!'), [('an_03_final', '')], 'anunciador', pad=0.5, pre=0.3)
        G.sonido(S['whoosh'], gain=0.8)
        decir(P.tarjeta(n, N), [(f'pr_n{n:02d}', '')], 'presentador', pad=0.4, pre=0.2, poses={'presentador': 'base'})
        decir(P.pregunta(n, N, q), [(f'{key}_pregunta', q['tp'])], 'presentador', pad=0.3, poses={'presentador': 'senala'})
        if n <= 2: G.voz(voz('pr_03_segundos'), G.t + 0.1, 'presentador')
        t0 = G.t
        for sec in range(10): G.sonido(S['tick_hi'] if sec >= 7 else S['tick'], at=t0 + sec, gain=0.8)
        cache = {}
        def tfn(t, q=q, n=n, cache=cache):
            r = max(1, 10 - int(t)); fr = round((1 - t / 10) * 40) / 40
            if (r, fr) not in cache: cache[(r, fr)] = P.pregunta(n, N, q, reloj=r, frac=fr)
            return cache[(r, fr)]
        G.escena(tfn, 10.0, 'presentador', {'presentador': 'piensa'})
        G.sonido(S['tiempo'], gain=0.7)
        decir(P.pregunta(n, N, q, reloj='¡YA!', frac=0), [('pr_04_tiempo', ''), ('co_08_correcta', '')], 'copresentadora', pad=0.1, pre=0.1,
              poses={'copresentadora': 'presenta', 'presentador': 'frente'})
        G.sonido(S['ding'], at=G.t + 0.2, gain=0.9)
        dificil = (n - 1) * 3 // N >= 2
        rev = 'celebra' if n == N else ('sorpresa' if dificil and n % 2 == 0 else 'aplaude')
        decir(P.pregunta(n, N, q, modo='revela'), [(f'{key}_respuesta', q['tr'])], 'copresentadora', pad=0.9, pre=0.2,
              poses={'copresentadora': rev})
        decir(P.dato(n, N, q), [('co_02_dato', ''), (f'{key}_dato', q['td'])], 'copresentadora', pad=1.2,
              poses={'copresentadora': 'presenta'})
        if n % 5 == 0 and n != N:
            decir(P.tabla(n, N), [('pr_08_tabla', '')], 'presentador', pad=3.0, poses={'presentador': 'base'})
    # --- cierre
    decir(P.anuncio('¡Y el ganador es…!', 'Míralo en tu celular'), [('an_04_ganador', '')], 'anunciador', pad=0.8)
    G.sonido(S['fanfare'], gain=0.8)
    decir(P.rangos(), [('co_05_felicidades', ''), ('pr_cierre', ex.get('pr_cierre', ['', ''])[1])], 'presentador', pad=3.0,
          poses={'presentador': 'celebra', 'copresentadora': 'celebra'})
    decir(P.final(), [('pr_12_suscribanse', ''), ('co_07_otra', ''), ('pr_13_despedida', '')], 'presentador', pad=3.0,
          poses={'presentador': 'saluda', 'copresentadora': 'saluda'})
    print(f'Duración: {G.t/60:.1f} min · escenas: {len(G.escenas)}')
    if faltan: print('Voces faltantes (silencio):', faltan)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    G.render(a.out, a.tmp); print('OK', a.out)

if __name__ == '__main__':
    main()
