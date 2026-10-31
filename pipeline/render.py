#!/usr/bin/env python3
"""Montador automático de videos de ¿Quién Sabe Más?
Uso:
  python3 render.py --preguntas preguntas_v01.json --banco DIR_BANCO --voces DIR_VOCES_NUEVAS --out video.mp4 [--preview]
Si falta una voz nueva, deja un silencio del largo estimado (sirve para maquetas).
"""
import argparse, json, os, subprocess, wave, math, shutil, textwrap
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from reportlab.graphics.barcode import qrencoder as QR

W, H, FPS, SR = 1920, 1080, 30, 24000
F = '/usr/share/fonts/truetype/google-fonts/Poppins-%s.ttf'
def font(w, s): return ImageFont.truetype(F % w, s)

C = dict(bg1=(24, 16, 64), bg2=(58, 28, 120), white=(255, 255, 255), dim=(70, 62, 110), dimtxt=(150, 140, 190),
         gold=(255, 200, 40), panel=(255, 255, 255))
OPC = [((231, 76, 60), 'A'), ((47, 128, 237), 'B'), ((242, 180, 30), 'C'), ((39, 174, 96), 'D')]
NIVEL = [('FÁCIL', (39, 174, 96)), ('MEDIA', (242, 153, 30)), ('DIFÍCIL', (231, 76, 60))]

# ---------------- utilidades de imagen ----------------
def fondo():
    y = np.linspace(0, 1, H)[:, None]
    x = np.linspace(0, 1, W)[None, :]
    t = np.clip(0.65 * y + 0.35 * x, 0, 1)[..., None]
    a = np.array(C['bg1'])[None, None]; b = np.array(C['bg2'])[None, None]
    img = Image.fromarray((a * (1 - t) + b * t).astype(np.uint8))
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for cx, cy, r, al in [(1700, 120, 380, 22), (150, 950, 320, 18), (1000, 1150, 500, 12), (-50, 80, 220, 14)]:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, al))
    ov = ov.filter(ImageFilter.GaussianBlur(40))
    return Image.alpha_composite(img.convert('RGBA'), ov).convert('RGB')

def qr_img(url, px):
    for v in range(2, 11):
        try:
            q = QR.QRCode(v, QR.QRErrorCorrectLevel.M); q.addData(url); q.make(); break
        except Exception:
            continue
    n = q.getModuleCount(); b = 2
    m = Image.new('L', (n + 2 * b, n + 2 * b), 255)
    for r in range(n):
        for c in range(n):
            if q.isDark(r, c): m.putpixel((c + b, r + b), 0)
    return m.resize((px, px), Image.NEAREST).convert('RGB')

def wrap(d, txt, fnt, maxw):
    words, lines, cur = txt.split(), [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=fnt) <= maxw: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def fit_text(d, txt, weight, maxw, maxh, start, minsize=30, spacing=1.18):
    s = start
    while s >= minsize:
        f = font(weight, s); ls = wrap(d, txt, f, maxw)
        if len(ls) * s * spacing <= maxh: return f, ls, s
        s -= 2
    f = font(weight, minsize); return f, wrap(d, txt, f, maxw), minsize

def center_lines(d, ls, f, s, cx, cy, fill, spacing=1.18):
    total = len(ls) * s * spacing; y = cy - total / 2
    for l in ls:
        d.text((cx, y + s * spacing / 2), l, font=f, fill=fill, anchor='mm'); y += s * spacing

def rrect(d, box, r, **kw): d.rounded_rectangle(box, r, **kw)

def shadow_box(img, box, r, fill, outline=None, width=0, sh=14):
    sx = Image.new('RGBA', img.size, (0, 0, 0, 0)); ds = ImageDraw.Draw(sx)
    x0, y0, x1, y1 = box
    ds.rounded_rectangle([x0, y0 + sh // 2, x1, y1 + sh], r, fill=(0, 0, 0, 90))
    sx = sx.filter(ImageFilter.GaussianBlur(10))
    base = Image.alpha_composite(img.convert('RGBA'), sx)
    d = ImageDraw.Draw(base); d.rounded_rectangle(box, r, fill=fill, outline=outline, width=width)
    return base.convert('RGB')

# ---------------- pantallas ----------------
class Pantallas:
    def __init__(s, meta, url):
        s.meta = meta; s.bg = fondo(); s.qr_s = qr_img(url, 150); s.qr_l = qr_img(url, 420)

    def barra(s, img, etiqueta=None):
        d = ImageDraw.Draw(img)
        d.text((60, 62), '¿Quién Sabe Más?', font=font('Bold', 40), fill=C['gold'], anchor='lm')
        if etiqueta: d.text((W / 2, 62), etiqueta, font=font('Medium', 34), fill=C['white'], anchor='mm')
        # QR + sala siempre visibles
        img.paste(s.qr_s, (W - 60 - 150, 20))
        d.text((W - 230, 50), 'Sala', font=font('Medium', 26), fill=C['dimtxt'], anchor='rm')
        d.text((W - 230, 92), s.meta['codigo_sala'], font=font('Bold', 44), fill=C['white'], anchor='rm')
        return img

    def lobby(s, segs_left=None):
        img = s.bg.copy(); d = ImageDraw.Draw(img)
        d.text((W / 2, 150), '¿Quién Sabe Más?', font=font('Bold', 110), fill=C['gold'], anchor='mm')
        d.text((W / 2, 250), s.meta['titulo'], font=font('Medium', 52), fill=C['white'], anchor='mm')
        img = shadow_box(img, (250, 330, 250 + 480, 330 + 480), 28, (255, 255, 255)); img.paste(s.qr_l, (280, 360))
        d = ImageDraw.Draw(img)
        x = 820
        d.text((x, 370), '1. Escanea el código con tu celular', font=font('Medium', 44), fill=C['white'], anchor='lm')
        d.text((x, 450), '2. Escribe tu nombre', font=font('Medium', 44), fill=C['white'], anchor='lm')
        d.text((x, 530), '3. ¡Responde rápido y gana puntos!', font=font('Medium', 44), fill=C['white'], anchor='lm')
        d.text((x, 640), 'Código de sala', font=font('Medium', 36), fill=C['dimtxt'], anchor='lm')
        img = shadow_box(img, (x, 670, x + 420, 790), 22, (255, 255, 255)); d = ImageDraw.Draw(img)
        d.text((x + 210, 732), s.meta['codigo_sala'], font=font('Bold', 84), fill=C['bg1'], anchor='mm')
        d.text((W / 2, 900), '¿Sin celular? Jueguen en voz alta y anoten sus puntos en un papel.',
               font=font('Regular', 38), fill=C['dimtxt'], anchor='mm')
        d.text((W / 2, 960), 'quiensabemastv.pages.dev', font=font('Medium', 34), fill=C['white'], anchor='mm')
        if segs_left is not None:
            d.text((W - 120, 950), str(segs_left), font=font('Bold', 90), fill=C['gold'], anchor='mm')
        return img

    def tarjeta(s, n, total):
        img = s.barra(s.bg.copy()); d = ImageDraw.Draw(img)
        nv = NIVEL[min(2, (n - 1) * 3 // total)]
        rrect(d, (W / 2 - 150, 330, W / 2 + 150, 400), 35, fill=nv[1])
        d.text((W / 2, 366), nv[0], font=font('Bold', 40), fill=C['white'], anchor='mm')
        d.text((W / 2, 560), f'PREGUNTA {n}', font=font('Bold', 150), fill=C['white'], anchor='mm')
        d.text((W / 2, 700), f'de {total}', font=font('Medium', 56), fill=C['dimtxt'], anchor='mm')
        return img

    def pregunta(s, n, total, q, modo='normal', reloj=None, frac=None):
        """modo: normal | revela ; reloj: número del contador; frac: 0..1 barra restante"""
        img = s.barra(s.bg.copy(), f'Pregunta {n} de {total}')
        d = ImageDraw.Draw(img)
        f, ls, sz = fit_text(d, q['p'], 'Bold', 1500, 260, 72)
        center_lines(d, ls, f, sz, W / 2, 300, C['white'])
        bw, bh, gx, gy, y0 = 830, 170, 40, 36, 500
        x0 = (W - 2 * bw - gx) / 2
        for i, txt in enumerate(q['o']):
            col, letra = OPC[i]
            x = x0 + (i % 2) * (bw + gx); y = y0 + (i // 2) * (bh + gy)
            ok = (i == q['c'])
            if modo == 'revela' and not ok:
                fill, tcol, lcol = C['dim'], C['dimtxt'], C['dim']
                img = shadow_box(img, (x, y, x + bw, y + bh), 26, fill, sh=6)
            elif modo == 'revela' and ok:
                img = shadow_box(img, (x - 10, y - 10, x + bw + 10, y + bh + 10), 32, col, outline=C['white'], width=8)
                tcol, lcol = C['white'], col
            else:
                img = shadow_box(img, (x, y, x + bw, y + bh), 26, col); tcol, lcol = C['white'], col
            d = ImageDraw.Draw(img)
            d.ellipse((x + 28, y + bh / 2 - 46, x + 120, y + bh / 2 + 46),
                      fill=(255, 255, 255) if not (modo == 'revela' and not ok) else (95, 86, 140))
            d.text((x + 74, y + bh / 2), letra, font=font('Bold', 54),
                   fill=lcol if not (modo == 'revela' and not ok) else C['dimtxt'], anchor='mm')
            ft, lt, st = fit_text(d, txt, 'Bold', bw - 210, bh - 30, 54, 30)
            tl = len(lt) * st * 1.15; ty = y + bh / 2 - tl / 2
            for l in lt:
                d.text((x + 150, ty + st * 1.15 / 2), l, font=ft, fill=tcol, anchor='lm'); ty += st * 1.15
            if modo == 'revela' and ok:
                cx, cy = x + bw - 70, y + bh / 2
                d.ellipse((cx - 44, cy - 44, cx + 44, cy + 44), fill=C['white'])
                d.line([(cx - 22, cy + 2), (cx - 6, cy + 20), (cx + 24, cy - 18)], fill=col, width=12, joint='curve')
        # temporizador
        if frac is not None:
            yb = 960; d.rounded_rectangle((120, yb, W - 260, yb + 34), 17, fill=(255, 255, 255, 40) and (60, 50, 105))
            ww = int((W - 380) * max(0.0, frac))
            if ww > 34:
                colb = C['gold'] if frac > 0.3 else (231, 76, 60)
                d.rounded_rectangle((120, yb, 120 + ww, yb + 34), 17, fill=colb)
        if reloj is not None:
            cx, cy = W - 150, 977
            colr = C['gold'] if (reloj if isinstance(reloj, int) else 0) > 3 else (231, 76, 60)
            d.ellipse((cx - 70, cy - 70, cx + 70, cy + 70), fill=colr)
            if isinstance(reloj, int):
                d.text((cx, cy + 2), str(reloj), font=font('Bold', 84), fill=C['white'], anchor='mm')
            else:
                d.text((cx, cy + 2), reloj, font=font('Bold', 36), fill=C['white'], anchor='mm')
        return img

    def dato(s, n, total, q):
        img = s.barra(s.bg.copy(), f'Pregunta {n} de {total}'); d = ImageDraw.Draw(img)
        f, ls, sz = fit_text(d, q['p'], 'Medium', 1500, 120, 44)
        center_lines(d, ls, f, sz, W / 2, 210, C['dimtxt'])
        col, letra = OPC[q['c']]
        img = shadow_box(img, (360, 300, W - 360, 450), 30, col, outline=C['white'], width=6); d = ImageDraw.Draw(img)
        d.ellipse((400, 329, 492, 421), fill=C['white'])
        d.text((446, 375), letra, font=font('Bold', 54), fill=col, anchor='mm')
        ft, lt, st = fit_text(d, q['o'][q['c']], 'Bold', W - 720 - 220, 120, 66, 36)
        center_lines(d, lt, ft, st, W / 2 + 40, 375, C['white'])
        img = shadow_box(img, (200, 520, W - 200, 940), 34, (255, 255, 255)); d = ImageDraw.Draw(img)
        rrect(d, (W / 2 - 200, 495, W / 2 + 200, 555), 30, fill=C['gold'])
        d.text((W / 2, 526), 'DATO CURIOSO', font=font('Bold', 36), fill=C['bg1'], anchor='mm')
        f, ls, sz = fit_text(d, q['d'], 'Medium', W - 560, 330, 58)
        center_lines(d, ls, f, sz, W / 2, 745, C['bg1'])
        return img

    def tabla(s, n, total):
        img = s.barra(s.bg.copy(), f'Vamos {n} de {total}'); d = ImageDraw.Draw(img)
        d.text((W / 2, 300), 'Tabla de posiciones', font=font('Bold', 100), fill=C['gold'], anchor='mm')
        img = shadow_box(img, (360, 420, W - 360, 760), 34, (255, 255, 255)); d = ImageDraw.Draw(img)
        d.text((W / 2, 520), 'Mira tu puesto en tu celular', font=font('Bold', 64), fill=C['bg1'], anchor='mm')
        d.text((W / 2, 640), '¿Sin celular? Sumen sus puntos: 1 por respuesta correcta.',
               font=font('Medium', 40), fill=(90, 80, 130), anchor='mm')
        d.text((W / 2, 880), '¿Llegaste tarde? Escanea el código de arriba y entra ahora.',
               font=font('Medium', 40), fill=C['white'], anchor='mm')
        return img

    def anuncio(s, grande, chico=None, col=None):
        img = s.barra(s.bg.copy()); d = ImageDraw.Draw(img)
        f, ls, sz = fit_text(d, grande, 'Bold', 1600, 380, 140)
        center_lines(d, ls, f, sz, W / 2, 470 if chico else 540, col or C['gold'])
        if chico: d.text((W / 2, 760), chico, font=font('Medium', 52), fill=C['white'], anchor='mm')
        return img

    def final(s):
        img = s.barra(s.bg.copy()); d = ImageDraw.Draw(img)
        d.text((W / 2, 260), '¡Gracias por jugar!', font=font('Bold', 120), fill=C['gold'], anchor='mm')
        img = shadow_box(img, (W / 2 - 360, 420, W / 2 + 360, 560), 70, (230, 33, 23)); d = ImageDraw.Draw(img)
        d.text((W / 2, 490), 'SUSCRÍBETE', font=font('Bold', 72), fill=C['white'], anchor='mm')
        d.text((W / 2, 680), 'Activa la campanita para la próxima partida', font=font('Medium', 50), fill=C['white'], anchor='mm')
        d.text((W / 2, 780), '@QuienSabeMasTV', font=font('Bold', 56), fill=C['gold'], anchor='mm')
        return img

# ---------------- audio ----------------
def load_wav(p):
    with wave.open(p) as w:
        sr, n, ch, sw = w.getframerate(), w.getnframes(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(n)
    if sw == 2: a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    elif sw == 4: a = np.frombuffer(raw, np.int32).astype(np.float32) / 2**31
    else: raise ValueError(p)
    if ch > 1: a = a.reshape(-1, ch).mean(1)
    if sr != SR:
        x = np.linspace(0, len(a) - 1, int(len(a) * SR / sr)); a = np.interp(x, np.arange(len(a)), a)
    return a.astype(np.float32)

def tono(f, dur, vol=0.25, dec=30):
    t = np.arange(int(SR * dur)) / SR
    return (vol * np.sin(2 * np.pi * f * t) * np.exp(-dec * t)).astype(np.float32)

def sfx():
    tick = tono(1400, 0.06, 0.18, 60)
    tick_hi = tono(1900, 0.08, 0.26, 45)
    ding = np.zeros(int(SR * 1.2), np.float32)
    for k, f in enumerate([880, 1108.7, 1318.5]):
        st = int(k * 0.09 * SR); seg = tono(f, 1.2 - k * 0.09, 0.22, 4); ding[st:st + len(seg)] += seg
    t = np.arange(int(SR * 0.45)) / SR
    noise = np.random.default_rng(1).standard_normal(len(t)).astype(np.float32)
    env = np.sin(np.pi * t / t[-1]) ** 2
    # barrido suave (whoosh) con filtro paso bajo móvil sencillo
    wh = np.convolve(noise, np.ones(30) / 30, 'same') * env * 0.35
    buzz = np.zeros(int(SR * 0.7), np.float32)
    for f in (220, 233):
        buzz += tono(f, 0.7, 0.16, 3)
    fanfare = np.zeros(int(SR * 2.0), np.float32)
    for k, f in enumerate([523.25, 659.25, 783.99, 1046.5]):
        st = int(k * 0.14 * SR); seg = tono(f, 2.0 - k * 0.14, 0.2, 2.5); fanfare[st:st + len(seg)] += seg
    return dict(tick=tick, tick_hi=tick_hi, ding=ding, whoosh=wh.astype(np.float32), tiempo=buzz, fanfare=fanfare)

# ---------------- montaje ----------------
class Montaje:
    def __init__(s, tmp):
        s.tmp = tmp; s.segs = []; s.audio = []; s.t = 0.0; s.k = 0

    def clip(s, arr, at=None, gain=1.0):
        s.audio.append(((s.t if at is None else at), arr * gain))

    def still(s, img, dur):
        p = f'{s.tmp}/s{s.k:04d}.png'; img.save(p); s.segs.append(('still', p, dur)); s.k += 1; s.t += dur

    def frames(s, fn, dur):
        """fn(t)->PIL image, renderizado a 15 fps (suficiente para barra/contador)."""
        d = f'{s.tmp}/f{s.k:04d}'; os.makedirs(d, exist_ok=True)
        n = int(round(dur * 15)); last = None
        for i in range(n):
            im = fn(i / 15)
            im.save(f'{d}/{i:05d}.png', compress_level=1)
        s.segs.append(('frames', d, dur)); s.k += 1; s.t += dur

    def render(s, out, crf=20):
        parts = []
        for i, (kind, src, dur) in enumerate(s.segs):
            o = f'{s.tmp}/p{i:04d}.mp4'
            if kind == 'still':
                cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-loop', '1', '-framerate', str(FPS), '-i', src, '-t', f'{dur:.3f}',
                       '-c:v', 'libx264', '-preset', 'veryfast', '-tune', 'stillimage', '-crf', str(crf), '-pix_fmt', 'yuv420p', '-r', str(FPS), o]
            else:
                cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-framerate', '15', '-i', f'{src}/%05d.png', '-t', f'{dur:.3f}',
                       '-c:v', 'libx264', '-preset', 'veryfast', '-crf', str(crf), '-pix_fmt', 'yuv420p', '-r', str(FPS), o]
            subprocess.run(cmd, check=True); parts.append(o)
        lst = f'{s.tmp}/lista.txt'
        open(lst, 'w').write(''.join(f"file '{p}'\n" for p in parts))
        vid = f'{s.tmp}/video.mp4'
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', vid], check=True)
        total = int(SR * (s.t + 0.5)); mix = np.zeros(total, np.float32)
        for at, a in s.audio:
            st = int(at * SR); e = min(total, st + len(a)); mix[st:e] += a[:e - st]
        pk = np.abs(mix).max()
        if pk > 0.98: mix *= 0.98 / pk
        wav = f'{s.tmp}/audio.wav'
        with wave.open(wav, 'w') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype(np.int16).tobytes())
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', vid, '-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                        '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', '48000', '-ac', '2', '-c:a', 'aac', '-b:a', '192k',
                        '-shortest', '-movflags', '+faststart', out], check=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--preguntas', required=True); ap.add_argument('--banco', required=True)
    ap.add_argument('--voces', default=''); ap.add_argument('--out', required=True)
    ap.add_argument('--preview', action='store_true'); ap.add_argument('--tmp', default='/home/claude/qsm/tmp')
    ap.add_argument('--lobby', type=int, default=20, help='segundos de cuenta regresiva en la sala de espera')
    a = ap.parse_args()
    meta = json.load(open(a.preguntas)); Q = meta['preguntas']; N = len(Q)
    shutil.rmtree(a.tmp, ignore_errors=True); os.makedirs(a.tmp)
    url = f"https://quiensabemastv.pages.dev/?sala={meta['codigo_sala']}"
    P = Pantallas(meta, url); M = Montaje(a.tmp); S = sfx()
    faltan = []

    def voz(clave, texto_est=''):
        for d in (a.voces, a.banco):
            if d and os.path.exists(f'{d}/{clave}.wav'): return load_wav(f'{d}/{clave}.wav')
        faltan.append(clave)
        return np.zeros(int(SR * max(1.2, len(texto_est) / 15)), np.float32)

    def say(img, clips, pad=0.35, pre=0.0):
        """muestra img mientras suenan los clips en serie."""
        t0 = M.t + pre; dur = pre
        for c in clips:
            M.clip(c, at=t0 + (dur - pre)); dur += len(c) / SR + 0.12
        M.still(img, dur + pad)

    # ---------- sala de espera ----------
    lob = P.lobby()
    M.clip(S['fanfare'], gain=0.8)
    say(lob, [voz('an_01_marca'), voz('an_02_bienvenida'), voz('an_tema', 'Hoy jugamos: ¡Cultura general, Perú y el mundo!'),
              voz('pr_01_celulares'), voz('co_06_sincelular'), voz('pr_10_rapido')], pad=0.5, pre=0.8)
    L = a.lobby if not a.preview else 6
    def lobby_fn(t):
        return P.lobby(segs_left=max(1, L - int(t)))
    for sec in range(L):
        M.clip(S['tick'], at=M.t + sec, gain=0.6)
    M.frames(lobby_fn, L) if L <= 8 else [M.still(P.lobby(segs_left=L - i), 1.0) for i in range(L)]
    say(P.anuncio('¡Empezamos!', f"{N} preguntas · de fácil a difícil"),
        [voz('pr_02_empezamos'), voz('pr_intro', 'Son treinta preguntas, de la más fácil a la más difícil. ¡A jugar!')], pad=0.4)

    idx = list(range(N)) if not a.preview else [0, 1, 4, N - 1]
    for i in idx:
        n = i + 1; q = Q[i]; key = f'q{n:02d}'
        if n == N:
            M.clip(S['fanfare'], gain=0.7)
            say(P.anuncio('¡Pregunta final!'), [voz('an_03_final')], pad=0.6, pre=0.3)
        elif n == N // 2 + 1:
            say(P.anuncio('¡Mitad del juego!'), [voz('an_06_mitad')], pad=0.5)
        # tarjeta
        M.clip(S['whoosh'], gain=0.8)
        say(P.tarjeta(n, N), [voz(f'pr_n{n:02d}')], pad=0.5, pre=0.25)
        # lectura
        say(P.pregunta(n, N, q), [voz(f'{key}_pregunta', q['tp'])], pad=0.3)
        # temporizador 10 s
        if n <= 2: M.clip(voz('pr_03_segundos'), at=M.t + 0.1)
        t0 = M.t
        for sec in range(10):
            M.clip(S['tick_hi'] if sec >= 7 else S['tick'], at=t0 + sec, gain=0.8)
        cache = {}
        def tfn(t, q=q, n=n):
            r = max(1, 10 - int(t)); fr = 1 - t / 10
            k = (r, round(fr * 60))
            if k not in cache: cache[k] = P.pregunta(n, N, q, reloj=r, frac=fr)
            return cache[k]
        M.frames(tfn, 10.0)
        # ¡tiempo! + suspenso
        M.clip(S['tiempo'], gain=0.7)
        say(P.pregunta(n, N, q, reloj='¡YA!', frac=0), [voz('pr_04_tiempo'), voz('co_08_correcta')], pad=0.15, pre=0.1)
        # revelación
        M.clip(S['ding'], gain=0.9)
        say(P.pregunta(n, N, q, modo='revela'), [voz(f'{key}_respuesta', q['tr'])], pad=1.0, pre=0.25)
        # dato curioso
        say(P.dato(n, N, q), [voz('co_02_dato'), voz(f'{key}_dato', q['td'])], pad=1.2)
        # tabla cada 5
        if n % 5 == 0 and n != N:
            extra = [voz('pr_09_renida')] if n == 20 else []
            say(P.tabla(n, N), [voz('pr_08_tabla')] + extra, pad=3.0)
    # ---------- cierre ----------
    say(P.anuncio('¡Y el ganador es…!', 'Mira tu celular: ahí aparece el ranking final'), [voz('an_04_ganador')], pad=0.8)
    M.clip(S['fanfare'], gain=0.8)
    say(P.anuncio('¡Felicidades!', 'Y si jugaron en papel: ¡cuenten sus puntos!'), [voz('co_05_felicidades')], pad=1.0)
    say(P.final(), [voz('pr_12_suscribanse'), voz('co_07_otra'), voz('pr_13_despedida')], pad=3.0)
    print(f'Duración: {M.t/60:.1f} min · segmentos: {len(M.segs)}')
    if faltan: print('Voces faltantes (silencio):', len(faltan), faltan[:6], '...')
    M.render(a.out)
    print('OK', a.out)

if __name__ == '__main__':
    main()
