#!/usr/bin/env python3
"""Shorts en el formato nuevo (7-nov-2026) — 1080x1920, sacados del episodio del día: una pregunta tal cual sale en el
video largo (música alta, subtítulos karaoke, fotos reales en las alternativas, MAX contra NOVA, movimiento) y un
cierre que invita al episodio completo (el «video relacionado» del Short).
Reutiliza las voces ya generadas del episodio y los bancos (var, rival, comedia, shorts): no gasta voz nueva.
Uso:
  python3 pipeline/shorts.py --contenido trabajo/episodio.json --voces voces_ep --salida trabajo/shorts \
      [--tiempos trabajo/video.tiempos.json] [--n 2] [--preguntas 12,30]
Deja trabajo/shorts/short_<n>.mp4 y trabajo/shorts/shorts.json (preguntas usadas, duración, voces faltantes).
"""
import argparse, json, os, random, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

sys.path.insert(0, os.path.dirname(__file__))
import tv
from tv import font, fit, lines, caja, load_wav, sfx, C, OPC, SR, RIVAL_COL, Entrada, Revela
from personajes import sprite, voz_sprite, NOMBRES
from musica import MusicaArchivos, carpeta_musica
from subtitulos import Subtitulos

W, H, FPS = 1080, 1920, 15
SEG = 5            # segundos para responder
ESC = 0.72         # escala del personaje en vertical
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PJ_X, PJ_Y = 205, 170   # personaje arriba a la izquierda (abajo y a la derecha los tapa la interfaz de Shorts)
XR = 975                # borde derecho útil (los botones de Shorts tapan la franja derecha)
CAJAS = (45, 860, XR, 1500)
SUB_Y = 1585


def fondo():
    y = np.linspace(0, 1, H)[:, None]; x = np.linspace(0, 1, W)[None, :]
    t = np.clip(0.8 * y + 0.2 * x, 0, 1)[..., None]
    img = Image.fromarray((np.array(C['bg1']) * (1 - t) + np.array(C['bg2']) * t).astype(np.uint8)).convert('RGBA')
    luz = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(luz)
    for cx, ang in [(180, 1), (900, -1)]:
        d.polygon([(cx - 30, -10), (cx + 30, -10), (cx + 300 * ang + 260, H), (cx + 300 * ang - 260, H)], fill=(255, 255, 255, 14))
    rng = np.random.default_rng(11)
    for _ in range(60):
        px, py, r = rng.integers(0, W), rng.integers(0, H), rng.integers(1, 4)
        d.ellipse((px - r, py - r, px + r, py + r), fill=(255, 255, 255, int(rng.integers(30, 110))))
    return Image.alpha_composite(img, luz.filter(ImageFilter.GaussianBlur(14))).convert('RGB')


class Vertical:
    def __init__(s, meta):
        s.m = meta; s.bg = fondo(); s._cred = {}; s._fotos = {}
        s.total = meta.get('total_anunciado', len(meta['preguntas']))

    def credito(s, path):
        dd = os.path.dirname(os.path.abspath(path))
        if dd not in s._cred:
            f = os.path.join(dd, 'creditos.json'); s._cred[dd] = json.load(open(f)) if os.path.exists(f) else {}
        return s._cred[dd].get(os.path.basename(path))

    # ---- cabecera: marca, marcador MAX/NOVA, reto y reloj (a la derecha del personaje)
    def cabecera(s, img, marcador, reloj=None, frac=None):
        d = ImageDraw.Draw(img); x0 = 430; cx = (x0 + XR) / 2
        d.text((cx, 190), '¿Quién Sabe Más?', font=font('Bold', 56), fill=C['gold'], anchor='mm')
        s._chips = []
        if marcador:
            f = font('Bold', 34); ws = [d.textlength(f'{n} {p}', font=f) + 40 for n, p in zip(('MAX', 'NOVA'), marcador)]
            x = cx - (sum(ws) + 20) / 2
            for (nom, pts, col), w in zip((('MAX', marcador[0], C['gold']), ('NOVA', marcador[1], RIVAL_COL)), ws):
                d.rounded_rectangle((x, 238, x + w, 290), 26, fill=col); s._chips.append((int(x - 6), 232, int(x + w + 6), 296))
                d.text((x + w / 2, 264), f'{nom} {pts}', font=f, fill=C['ink'], anchor='mm'); x += w + 20
        img = caja(img, (x0, 318, XR, 390), 36, C['red']); d = ImageDraw.Draw(img)
        d.text((cx, 354), '¿LE GANAS A MAX Y A NOVA?', font=font('Bold', 34), fill=C['white'], anchor='mm')
        if reloj is not None:
            col = C['gold'] if isinstance(reloj, int) and reloj > 2 else C['red']
            d.ellipse((cx - 68, 410, cx + 68, 546), fill=col)
            d.text((cx, 480), str(reloj), font=font('Bold', 84 if isinstance(reloj, int) else 40), fill=C['white'], anchor='mm')
        if frac is not None:
            d.rounded_rectangle((45, 590, XR, 616), 13, fill=(56, 46, 100))
            ww = int((XR - 45) * max(0.0, frac))
            if ww > 26: d.rounded_rectangle((45, 590, 45 + ww, 616), 13, fill=C['gold'] if frac > 0.35 else C['red'])
        return img

    def _foto(s, path, w, h, apagada, zoom):
        zoom = round(zoom, 3); k = (path, w, h, apagada, zoom)
        if k not in s._fotos:
            if len(s._fotos) > 48: s._fotos.clear()
            src = Image.open(os.path.join(RAIZ, path)).convert('RGB')
            if path.endswith('.png'):   # bandera: entera, sobre blanco
                src.thumbnail((w - 24, h - 24), Image.LANCZOS); t = Image.new('RGB', (w, h), (255, 255, 255))
                t.paste(src, ((w - src.width) // 2, (h - src.height) // 2)); src = t
            else:
                src = ImageOps.fit(src, (int(w * zoom), int(h * zoom)), Image.LANCZOS, centering=(0.5, 0.4))
                if zoom > 1: ox, oy = (src.width - w) // 2, int((src.height - h) * 0.4); src = src.crop((ox, oy, ox + w, oy + h))
            if apagada: src = Image.blend(src, Image.new('RGB', (w, h), C['ink']), 0.68)
            m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), 18, fill=255)
            s._fotos[k] = (src, m)
        return s._fotos[k]

    def _fichas(s, img, i, x, y, bw, ap):
        if not ap: return img
        quienes = [(n, c) for n, c, k in (('MAX', C['gold'], 'presentador'), ('NOVA', RIVAL_COL, 'copresentadora')) if ap.get(k) == i]
        d = ImageDraw.Draw(img); xr = x + bw - 12
        for nom, col in reversed(quienes):
            f = font('Bold', 32); tw = d.textlength(nom, font=f)
            d.rounded_rectangle((xr - tw - 34, y - 26, xr, y + 22), 24, fill=col, outline=C['white'], width=4)
            d.text((xr - tw / 2 - 17, y - 2), nom, font=f, fill=C['ink'], anchor='mm'); xr -= tw + 44
        return img

    def _tarjetas(s, img, q, modo, ap, zoom):
        """2×2: con foto (foto arriba, letra y nombre abajo) o solo texto si la pregunta no tiene fotos."""
        x0, y0, x1, y1 = CAJAS; g = 24; n = len(q['o']); cols = 2; rows = -(-n // cols)
        bw = (x1 - x0 - g) / cols; bh = (y1 - y0 - g * (rows - 1)) / rows
        fotos = q.get('o_img')
        if not fotos and n == 2: bh = min(bh, 300); y0 = y0 + 60
        for i, txt in enumerate(q['o']):
            col, L = OPC[i]; x = x0 + (i % cols) * (bw + g); y = y0 + (i // cols) * (bh + g)
            ok = i == q['c']; apag = modo == 'revela' and not ok
            s._cajas.append((int(x - 16), int(y - 16), int(x + bw + 16), int(y + bh + 22)))
            if modo == 'revela' and ok: img = caja(img, (x - 9, y - 9, x + bw + 9, y + bh + 9), 30, col, outline=C['white'], width=8)
            else: img = caja(img, (x, y, x + bw, y + bh), 26, C['dim'] if apag else col, sombra=not apag)
            ty = y + bh / 2   # centro del texto
            if fotos:
                pw, ph = int(bw - 20), int(bh - 96)
                src, m = s._foto(fotos[i], pw, ph, apag, zoom); img.paste(src, (int(x + 10), int(y + 10)), m)
                ty = y + bh - 43
            d = ImageDraw.Draw(img); r = 28; cxl = x + 16 + r
            d.ellipse((cxl - r, ty - r, cxl + r, ty + r), fill=(96, 88, 140) if apag else C['white'])
            d.text((cxl, ty), L, font=font('Bold', 34), fill=C['dimtxt'] if apag else col, anchor='mm')
            tx = cxl + r + 14; tw = x + bw - tx - (70 if ok and modo == 'revela' else 14)
            f, ls, sz = fit(d, txt, 'Bold', tw, 80 if fotos else bh - 30, 44 if fotos else 52, 24)
            lines(d, ls, f, sz, 0, ty, C['dimtxt'] if apag else C['white'], anchor='lm', x=tx)
            if modo == 'revela' and ok:
                kx, ky = x + bw - 46, (y + 46 if fotos else ty)
                d.ellipse((kx - 32, ky - 32, kx + 32, ky + 32), fill=C['white'])
                d.line([(kx - 16, ky + 1), (kx - 5, ky + 14), (kx + 17, ky - 13)], fill=col, width=9, joint='curve')
            img = s._fichas(img, i, x, (y + bh - 120) if fotos else (y + bh - 30), bw, ap)
        return img

    def pregunta(s, q, modo='normal', reloj=None, frac=None, marcador=(0, 0), apuestas=None, vacio=False, zoom=1.0):
        s._cajas = []; s._caja_txt = None
        img = s.cabecera(s.bg.copy(), marcador, reloj, frac); d = ImageDraw.Draw(img)
        d.text((W / 2 - 50, 650), f"Pregunta {q['n']} de {s.total}", font=font('Medium', 34), fill=C['dimtxt'], anchor='mm')
        f, ls, sz = fit(d, q['p'], 'Bold', XR - 70, 160, 62, 34); hh = len(ls) * sz * 1.18
        s._caja_txt = (40, int(762 - hh / 2 - 14), XR + 10, int(762 + hh / 2 + 14))
        if vacio: return img
        lines(d, ls, f, sz, (45 + XR) / 2, 762, C['white'])
        return s._tarjetas(img, q, modo, apuestas, zoom)

    def dato(s, q, marcador):
        img = s.cabecera(s.bg.copy(), marcador); d = ImageDraw.Draw(img); col, L = OPC[q['c']]
        img = caja(img, (45, 640, XR, 780), 30, col, outline=C['white'], width=6); d = ImageDraw.Draw(img)
        f, ls, sz = fit(d, f"{L}. {q['o'][q['c']]}", 'Bold', XR - 140, 120, 64, 30)
        lines(d, ls, f, sz, (45 + XR) / 2, 710, C['white'])
        foto = (q.get('o_img') or [None] * 4)[q['c']] or (q.get('img') if q.get('img_modo') == 'revela' else None)
        bx = (45, 850, XR, 1500)
        if foto:
            src, m = s._foto(foto, XR - 45 - 40, 380, False, 1.0); img = caja(img, (45, 830, XR, 1250), 30, (255, 255, 255))
            img.paste(src, (65, 850), m); bx = (45, 1290, XR, 1520)
        img = caja(img, bx, 34, (255, 255, 255)); d = ImageDraw.Draw(img); cx = (45 + XR) / 2
        d.rounded_rectangle((cx - 190, bx[1] - 28, cx + 190, bx[1] + 32), 30, fill=C['gold'])
        d.text((cx, bx[1] + 2), 'DATO CURIOSO', font=font('Bold', 34), fill=C['ink'], anchor='mm')
        f, ls, sz = fit(d, q['d'], 'Medium', bx[2] - bx[0] - 70, bx[3] - bx[1] - 80, 50, 26)
        lines(d, ls, f, sz, cx, (bx[1] + bx[3]) / 2 + 18, C['ink'])
        return img

    def cierre(s, marcador, fotos=()):
        """Invitación al episodio completo: el enlace del «video relacionado» sale abajo, sobre el título del Short."""
        img = s.cabecera(s.bg.copy(), marcador); d = ImageDraw.Draw(img); cx = (45 + XR) / 2
        d.text((cx, 690), '¿Les ganaste?', font=font('Bold', 92), fill=C['gold'], anchor='mm')
        img = caja(img, (60, 790, XR - 15, 1260), 40, (255, 255, 255)); d = ImageDraw.Draw(img)
        d.text((cx, 880), f'Juega las {s.total}', font=font('Bold', 84), fill=C['ink'], anchor='mm')
        d.text((cx, 975), 'contra MAX y NOVA', font=font('Bold', 58), fill=C['ink'], anchor='mm')
        fs = [f for f in fotos if f][:4]
        if fs:   # tira de fotos del episodio: muestra lo que trae el video largo
            tw = (XR - 15 - 60 - 60 - 12 * (len(fs) - 1)) / len(fs)
            for k, f in enumerate(fs):
                src, m = s._foto(f, int(tw), 170, False, 1.0); img.paste(src, (int(90 + k * (tw + 12)), 1040), m)
        else: d.text((cx, 1120), 'en familia, con tu celular', font=font('Medium', 46), fill=(90, 80, 130), anchor='mm')
        img = caja(img, (cx - 330, 1310, cx + 330, 1420), 55, (230, 33, 23)); d = ImageDraw.Draw(img)
        d.text((cx, 1365), 'EPISODIO COMPLETO', font=font('Bold', 50), fill=C['white'], anchor='mm')
        d.text((cx, 1470), 'Toca el enlace de abajo', font=font('Bold', 44), fill=C['white'], anchor='mm')
        for k in range(3):   # flecha hacia el enlace (abajo a la izquierda)
            yy = 1515 + k * 34; d.line([(cx - 34, yy), (cx, yy + 26), (cx + 34, yy)], fill=C['gold'], width=10, joint='curve')
        return img


class Corto(tv.Programa):
    def personaje(s, fr, quien, pose, t):
        b = s.boca(t, quien)
        if quien == 'anunciador':
            sp = voz_sprite(b, int(t * 10) % 12 if b else 0, 520).resize((300, 300), Image.LANCZOS)
            fr.paste(sp, (PJ_X - 150, 340 - 150), sp); return
        k = int(t * FPS) + (17 if quien == 'copresentadora' else 0)
        parp = (k % 61) in (0, 1) or (k % 167) in (0, 1)
        sp, (cx, cy) = sprite(quien, pose, b, parp)
        sp = sp.resize((round(sp.width * ESC), round(sp.height * ESC)), Image.LANCZOS)
        bob = round(3 * np.sin(2 * np.pi * t / 3.4))
        x = round(PJ_X - cx * ESC); y = round(PJ_Y + 60 - cy * ESC) + bob
        x = max(10, min(x, 420 - sp.width)) if sp.width < 410 else 10
        sp = sp.crop((0, 0, sp.width, max(1, 560 - y)))   # recorta la parte baja para no tapar la pregunta
        fr.paste(sp, (x, y), sp)
        d = ImageDraw.Draw(fr)
        d.rounded_rectangle((PJ_X - 75, 515, PJ_X + 75, 560), 22, fill=C['gold'] if quien == 'presentador' else RIVAL_COL)
        d.text((PJ_X, 538), NOMBRES[quien], font=font('Bold', 28), fill=C['ink'], anchor='mm')

    def render(s, out, tmp):
        os.makedirs(tmp, exist_ok=True)
        total = s.t; nfr = int(total * FPS); vid = os.path.join(tmp, 'v.mp4')
        ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                               '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
                               '-pix_fmt', 'yuv420p', '-r', '30', vid], stdin=subprocess.PIPE)
        ei = 0
        if s.subs: s.subs.cerrar()
        for k in range(nfr):
            t = k / FPS
            while ei + 1 < len(s.escenas) and t >= s.escenas[ei + 1][0]: ei += 1
            t0, dur, img, quien, poses = s.escenas[ei]
            fr = s.cuadro(ei, t).copy()
            if quien:
                h = s.hablante(t)
                if h and h != quien and h in poses: quien = h
                s.personaje(fr, quien, poses.get(quien, 'base'), t)
            st = s.subs.estado(t) if s.subs else None
            if st: s.subs.dibujar(fr, st)
            ff.stdin.write(fr.tobytes())
        ff.stdin.close(); ff.wait()
        mix = np.zeros(int(SR * (total + 0.5)), np.float32)
        for at, a in s.audio:
            st = int(at * SR); e = min(len(mix), st + len(a)); mix[st:e] += a[:e - st]
        if s.musica: s.musica.mezclar(mix, s.habla, s.relojes, s.temas)
        pk = np.abs(mix).max()
        if pk > 0.98: mix *= 0.98 / pk
        wav = os.path.join(tmp, 'a.wav')
        with wave.open(wav, 'w') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype(np.int16).tobytes())
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', vid, '-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                        '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', '48000', '-ac', '2', '-c:a', 'aac', '-b:a', '192k',
                        '-shortest', '-movflags', '+faststart', out], check=True)


def elegir(Q, n, ya=()):
    """Preferencia: alternativas con foto real, luego foto en la pregunta; medias/difíciles; repartidas en el episodio."""
    N = len(Q)
    def puntaje(q):
        if q['n'] in ya or q.get('ronda') in ('relampago', 'vf') or len(q['p']) > 110 or max(len(o) for o in q['o']) > 34: return -1
        s = 4 if q.get('o_img') else (2 if q.get('img_modo') == 'pregunta' and q.get('img') else 0)
        s += 2 if (q['n'] - 1) * 3 // N >= 1 else 0
        return s
    cand = sorted([q for q in Q if puntaje(q) >= 0], key=lambda q: (-puntaje(q), q['n']))
    out = []
    for q in cand:
        if all(abs(q['n'] - o['n']) >= max(3, N // 10) for o in out): out.append(q)
        if len(out) == n: break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--contenido', required=True); ap.add_argument('--voces', default='')
    ap.add_argument('--banco', default=os.path.join(RAIZ, 'banco')); ap.add_argument('--salida', required=True)
    ap.add_argument('--tiempos', default='', help='tiempos del video largo (para usar las mismas apuestas de MAX y NOVA)')
    ap.add_argument('--n', type=int, default=0, help='cuántos Shorts (0 = 2 normal, 4 maratón)')
    ap.add_argument('--preguntas', default='', help='números de pregunta separados por coma (opcional)')
    a = ap.parse_args()
    meta = json.load(open(a.contenido, encoding='utf-8')); Q = meta['preguntas']
    n = a.n or (4 if meta.get('formato') == 'maraton' else 2)
    sel = [q for q in Q if str(q['n']) in a.preguntas.split(',')] if a.preguntas else elegir(Q, n)
    os.makedirs(a.salida, exist_ok=True)
    S = sfx(); semilla = sum(map(ord, meta.get('id', meta['codigo_sala'])))
    apuestas = {}
    if a.tiempos and os.path.exists(a.tiempos): apuestas = json.load(open(a.tiempos)).get('apuestas', {})
    bancos = [os.path.join(RAIZ, 'banco', b) for b in ('var', 'rival', 'comedia', 'shorts')]
    TXT = {}
    for d in [a.banco] + bancos:
        f = os.path.join(d, 'indice.json')
        if os.path.exists(f): TXT.update({k: v.get('texto', '') for k, v in json.load(open(f, encoding='utf-8')).items()})
    cm = carpeta_musica(RAIZ); os.environ.setdefault('QSM_MUSICA_ALTA', '1')
    fuente = os.path.join(RAIZ, 'fuentes', 'Poppins-Black.ttf')
    todas_fotos = [q['o_img'][q['c']] for q in Q if q.get('o_img')]
    hechos = []
    for j, q in enumerate(sel):
        faltan = []; rnd = random.Random(semilla * 7 + q['n']); dicho = {}

        def voz(clave):
            for vd in bancos:
                vs = sorted(f for f in os.listdir(vd) if f.startswith(clave + '__') and f.endswith('.wav')) if os.path.isdir(vd) else []
                if vs:
                    f = vs[rnd.randrange(len(vs))]; dicho['t'] = TXT.get(f[:-4], ''); return load_wav(os.path.join(vd, f))
            for d in (a.voces, a.banco):
                if d and os.path.exists(f'{d}/{clave}.wav'):
                    dicho['t'] = TXT.get(clave, ''); return load_wav(f'{d}/{clave}.wav')
            faltan.append(clave); dicho['t'] = ''; return np.zeros(int(SR * 1.2), np.float32)

        V = Vertical(meta); G = Corto(); key = f"q{q['n']:02d}"
        if cm: G.musica = MusicaArchivos(cm, semilla + q['n'])
        G.subs = Subtitulos(W, H, FPS, fuente, tv.FONT % 'Bold', 50, XR, SUB_Y)
        pantalla_q = '¿Quién Sabe Más? ' + q['p'] + ' ' + ' '.join(q['o'])
        texto_ep = {f'{key}_respuesta': q['tr'], f'{key}_dato': q['td']}

        def decir(img, claves, quien_pantalla, poses, pad=0.3, pre=0.0, pantalla=''):
            t = G.t + pre
            for clave, quien in claves:
                arr = voz(clave); txt = texto_ep.get(clave) or dicho.get('t', '')
                G.voz(arr, t, quien, txt if not clave.endswith('_pregunta') else None, pantalla); t += len(arr) / SR + 0.1
            G.escena(img, t - G.t + pad, quien_pantalla, poses)

        # MAX y NOVA eligen lo mismo que en el video largo (si se conoce); si no, como allá: aciertan ~70 %
        if str(q['n']) in apuestas: am, an = apuestas[str(q['n'])]
        else:
            otras = [i for i in range(len(q['o'])) if i != q['c']]
            am = q['c'] if rnd.random() < 0.72 else rnd.choice(otras); an = q['c'] if rnd.random() < 0.72 else rnd.choice(otras)
        apu = {'presentador': am, 'copresentadora': an}; L = 'ABCD'
        pts = (int(am == q['c']), int(an == q['c']))

        # 1) la pregunta se ve desde el primer cuadro (entra con rebote) y MAX la lee
        G.sonido(S['whoosh'], gain=0.8)
        full = V.pregunta(q); cj, ct = list(V._cajas), V._caja_txt
        ent = Entrada(full, V.pregunta(q, vacio=True), cj, ct)
        decir(ent, [(f'{key}_pregunta', 'presentador')], 'presentador', {'presentador': 'senala'}, pad=0.2, pre=0.15)
        # 2) cuenta regresiva (las fotos se acercan despacio)
        t0 = G.t; cache = {}
        for sec in range(SEG): G.sonido(S['tick_hi'] if sec >= SEG - 2 else S['tick'], at=t0 + sec, gain=0.8)
        def tfn(t, cache=cache):
            r = max(1, SEG - int(t)); fr = round((1 - t / SEG) * 30) / 30
            if (r, fr) not in cache: cache.clear(); cache[(r, fr)] = V.pregunta(q, reloj=r, frac=fr, zoom=1 + 0.07 * (1 - fr))
            return cache[(r, fr)]
        G.relojes.append((t0, float(SEG)))
        G.escena(tfn, float(SEG), 'presentador', {'presentador': 'piensa'})
        G.sonido(S['tiempo'], gain=0.7)
        # 3) ¡Tiempo! y cada uno dice qué eligió (fichas sobre las tarjetas)
        img_y = V.pregunta(q, reloj='¡YA!', frac=0, zoom=1.07)
        decir(img_y, [('pr_04_tiempo', 'presentador')], 'presentador', {'presentador': 'frente'}, pad=0.05, pre=0.1)
        img_a = V.pregunta(q, reloj='¡YA!', frac=0, apuestas=apu, zoom=1.07)
        decir(img_a, [(f'pr_apuesta_{L[am]}', 'presentador'), (f'co_apuesta_{L[an]}', 'copresentadora'), ('co_08_correcta', 'copresentadora')],
              'presentador', {'presentador': 'senala', 'copresentadora': 'presenta'}, pad=0.1, pantalla=pantalla_q)
        # 4) revelación animada (la correcta late, chispas, el marcador suma)
        G.sonido(S['ding'], at=G.t + 0.2, gain=0.9)
        img_r = V.pregunta(q, modo='revela', apuestas=apu, marcador=pts, zoom=1.07); cj = list(V._cajas); chips = list(V._chips)
        sube = [chips[k] for k, v in enumerate((am, an)) if v == q['c'] and k < len(chips)]
        vac = V.pregunta(q, modo='revela', marcador=pts, vacio=True)
        rev = Revela(img_r, img_a, vac, cj[q['c']] if q['c'] < len(cj) else None, sube, V.cabecera(V.bg.copy(), None), semilla=q['n'])
        decir(rev, [(f'{key}_respuesta', 'copresentadora')], 'copresentadora', {'copresentadora': 'aplaude'}, pad=0.5, pre=0.2, pantalla=pantalla_q)
        # 5) la pulla (como en el episodio): el que acertó se burla, el otro se excusa
        m_ok, n_ok = am == q['c'], an == q['c']
        pu = ([('pr_pulla', 'presentador'), ('co_excusa', 'copresentadora')] if m_ok and not n_ok else
              [('co_pulla', 'copresentadora'), ('pr_excusa', 'presentador')] if n_ok and not m_ok else
              [('pr_ambos_bien' if rnd.random() < 0.5 else 'co_ambos_bien', 'presentador')] if m_ok else
              [('co_ambos_mal' if rnd.random() < 0.5 else 'pr_ambos_mal', 'copresentadora')])
        if pu[0][0].startswith('co_ambos_bien'): pu = [(pu[0][0], 'copresentadora')]
        if pu[0][0].startswith('pr_ambos_mal'): pu = [(pu[0][0], 'presentador')]
        decir(img_r, pu, pu[0][1], {'presentador': 'celebra' if m_ok else 'piensa', 'copresentadora': 'celebra' if n_ok else 'sorpresa'},
              pad=0.4, pantalla=pantalla_q)
        # 6) dato curioso
        if q.get('d'):
            decir(V.dato(q, pts), [('co_02_dato', 'copresentadora'), (f'{key}_dato', 'copresentadora')], 'copresentadora',
                  {'copresentadora': 'presenta'}, pad=0.6, pantalla='Dato curioso ' + q['o'][q['c']] + ' ' + q['d'])
        # 7) cierre: invitación al episodio completo
        otras_f = [f for f in todas_fotos if f not in (q.get('o_img') or [])]
        rnd.shuffle(otras_f)
        quien_cta = 'copresentadora' if j % 2 == 0 else 'presentador'
        decir(V.cierre(pts, otras_f[:4]), [(('co' if quien_cta == 'copresentadora' else 'pr') + '_short_cta', quien_cta)], quien_cta,
              {quien_cta: 'saluda'}, pad=1.4, pantalla='¿Les ganaste? Juega las contra MAX y NOVA episodio completo toca el enlace de abajo')
        out = os.path.join(a.salida, f'short_{j + 1}.mp4')
        print(f"Short {j + 1}: pregunta {q['n']} · {G.t:.1f} s · fotos {'sí' if q.get('o_img') else 'no'}" + (f' · faltan voces {faltan}' if faltan else ''))
        if G.t > 58: print('  aviso: pasa de 58 s')
        G.render(out, os.path.join(a.salida, f'tmp{j}'))
        hechos.append({'archivo': out, 'n': q['n'], 'pregunta': q['p'], 'duracion': round(G.t, 1), 'faltan': faltan,
                       'fotos': bool(q.get('o_img'))})
    json.dump({'id': meta.get('id'), 'titulo': meta['titulo'], 'total': meta.get('total_anunciado', len(Q)), 'shorts': hechos},
              open(os.path.join(a.salida, 'shorts.json'), 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
