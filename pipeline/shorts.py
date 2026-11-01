#!/usr/bin/env python3
"""Shorts «¿La sabes en 5 segundos?» — 1080x1920, sacados del episodio del día (anzuelo hacia el video largo).
Reutiliza las voces ya generadas del episodio (q##_pregunta, q##_respuesta, q##_dato) y las frases fijas del banco:
no gasta voz nueva.
Uso:
  python3 pipeline/shorts.py --contenido trabajo/episodio.json --voces voces_ep --salida trabajo/shorts [--n 2] [--preguntas 12,30]
Deja trabajo/shorts/short_<n>.mp4 y trabajo/shorts/shorts.json (preguntas usadas, títulos).
"""
import argparse, json, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
import tv
from tv import font, fit, lines, caja, foto, load_wav, sfx, C, OPC, SR
from personajes import sprite, voz_sprite, NOMBRES

W, H, FPS = 1080, 1920, 15
SEG = 5            # segundos para responder
ESC = 0.72         # escala del personaje en vertical
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# zona del personaje (arriba a la izquierda: abajo y a la derecha los tapa la interfaz de Shorts)
PJ_X, PJ_Y = 205, 170   # centro de la pantalla/visor del personaje


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
        s.m = meta; s.bg = fondo(); s._cred = {}

    def credito(s, path):
        dd = os.path.dirname(os.path.abspath(path))
        if dd not in s._cred:
            f = os.path.join(dd, 'creditos.json'); s._cred[dd] = json.load(open(f)) if os.path.exists(f) else {}
        c = s._cred[dd].get(os.path.basename(path))
        if not c: return None
        return f"Foto: {(c.get('autor') or 'Wikimedia Commons').split(chr(10))[0][:30]} · {c.get('licencia', '')}"

    def cabecera(s, img, reloj=None, frac=None):
        d = ImageDraw.Draw(img); x0 = 430; cx = (x0 + W - 40) / 2
        d.text((cx, 205), '¿Quién Sabe Más?', font=font('Bold', 58), fill=C['gold'], anchor='mm')
        img = caja(img, (x0, 270, W - 40, 350), 40, C['red']); d = ImageDraw.Draw(img)
        d.text((cx, 311), f'¿LA SABES EN {SEG} SEGUNDOS?', font=font('Bold', 36), fill=C['white'], anchor='mm')
        if reloj is not None:
            col = C['gold'] if isinstance(reloj, int) and reloj > 2 else C['red']
            d.ellipse((cx - 80, 385, cx + 80, 545), fill=col)
            d.text((cx, 467), str(reloj), font=font('Bold', 96 if isinstance(reloj, int) else 44), fill=C['white'], anchor='mm')
        if frac is not None:
            d.rounded_rectangle((60, 600, W - 60, 626), 13, fill=(56, 46, 100))
            ww = int((W - 120) * max(0.0, frac))
            if ww > 26: d.rounded_rectangle((60, 600, 60 + ww, 626), 13, fill=C['gold'] if frac > 0.35 else C['red'])
        return img

    def opciones(s, img, q, modo, box, cols):
        x0, y0, x1, y1 = box; g = 22; rows = -(-len(q['o']) // cols)
        bw = (x1 - x0 - g * (cols - 1)) / cols; bh = (y1 - y0 - g * (rows - 1)) / rows
        for i, txt in enumerate(q['o']):
            col, L = OPC[i]; x = x0 + (i % cols) * (bw + g); y = y0 + (i // cols) * (bh + g)
            ok = i == q['c']; apag = modo == 'revela' and not ok
            if modo == 'revela' and ok:
                img = caja(img, (x - 8, y - 8, x + bw + 8, y + bh + 8), 28, col, outline=C['white'], width=7)
            else:
                img = caja(img, (x, y, x + bw, y + bh), 24, C['dim'] if apag else col, sombra=not apag)
            d = ImageDraw.Draw(img); r = min(36, bh / 2 - 12); cy = y + bh / 2
            d.ellipse((x + 18, cy - r, x + 18 + 2 * r, cy + r), fill=(96, 88, 140) if apag else C['white'])
            d.text((x + 18 + r, cy), L, font=font('Bold', int(r * 1.2)), fill=C['dimtxt'] if apag else col, anchor='mm')
            tx = x + 36 + 2 * r
            f, ls, sz = fit(d, txt, 'Bold', bw - (tx - x) - (86 if ok and modo == 'revela' else 20), bh - 16, 50, 26)
            lines(d, ls, f, sz, 0, cy, C['dimtxt'] if apag else C['white'], anchor='lm', x=tx)
            if modo == 'revela' and ok:
                cx = x + bw - 50; d.ellipse((cx - 32, cy - 32, cx + 32, cy + 32), fill=C['white'])
                d.line([(cx - 16, cy + 1), (cx - 5, cy + 14), (cx + 17, cy - 13)], fill=col, width=9, joint='curve')
        return img

    def pregunta(s, q, modo='normal', reloj=None, frac=None):
        img = s.cabecera(s.bg.copy(), reloj, frac); d = ImageDraw.Draw(img)
        con_foto = bool(q.get('img')) and q.get('img_modo') == 'pregunta'
        if con_foto:
            f, ls, sz = fit(d, q['p'], 'Bold', W - 120, 190, 62, 34)
            lines(d, ls, f, sz, W / 2, 745, C['white'])
            p = os.path.join(RAIZ, q['img'])
            img = foto(img, p, (90, 870, W - 90, 1250), q.get('img_fondo'), s.credito(p))
            img = s.opciones(img, q, modo, (60, 1290, W - 60, 1610), 2)
        else:
            f, ls, sz = fit(d, q['p'], 'Bold', W - 120, 330, 72, 36)
            lines(d, ls, f, sz, W / 2, 810, C['white'])
            img = s.opciones(img, q, modo, (60, 1010, W - 140, 1600), 1)
        return img

    def dato(s, q):
        img = s.cabecera(s.bg.copy()); d = ImageDraw.Draw(img); col, L = OPC[q['c']]
        img = caja(img, (60, 650, W - 60, 790), 30, col, outline=C['white'], width=6); d = ImageDraw.Draw(img)
        f, ls, sz = fit(d, f"{L}. {q['o'][q['c']]}", 'Bold', W - 200, 120, 64, 30)
        lines(d, ls, f, sz, W / 2, 720, C['white'])
        bx = (60, 850, W - 60, 1550)
        if q.get('img') and q.get('img_modo') == 'revela':
            p = os.path.join(RAIZ, q['img'])
            img = foto(img, p, (90, 850, W - 90, 1200), None, s.credito(p)); bx = (60, 1250, W - 60, 1620)
        img = caja(img, bx, 34, (255, 255, 255)); d = ImageDraw.Draw(img); cx = W / 2
        d.rounded_rectangle((cx - 190, bx[1] - 28, cx + 190, bx[1] + 32), 30, fill=C['gold'])
        d.text((cx, bx[1] + 2), 'DATO CURIOSO', font=font('Bold', 34), fill=C['ink'], anchor='mm')
        f, ls, sz = fit(d, q['d'], 'Medium', bx[2] - bx[0] - 80, bx[3] - bx[1] - 100, 54, 28)
        lines(d, ls, f, sz, cx, (bx[1] + bx[3]) / 2 + 20, C['ink'])
        return img

    def cierre(s, total):
        img = s.cabecera(s.bg.copy()); d = ImageDraw.Draw(img); cx = W / 2
        d.text((cx, 720), '¿La sabías?', font=font('Bold', 96), fill=C['gold'], anchor='mm')
        d.text((cx, 830), 'Escríbelo en los comentarios', font=font('Medium', 46), fill=C['white'], anchor='mm')
        img = caja(img, (80, 930, W - 80, 1330), 40, (255, 255, 255)); d = ImageDraw.Draw(img)
        d.text((cx, 1030), f'Juega las {total}', font=font('Bold', 76), fill=C['ink'], anchor='mm')
        d.text((cx, 1120), 'preguntas completas', font=font('Bold', 62), fill=C['ink'], anchor='mm')
        d.text((cx, 1230), 'en familia, con tu celular', font=font('Medium', 44), fill=(90, 80, 130), anchor='mm')
        img = caja(img, (cx - 300, 1400, cx + 300, 1520), 60, (230, 33, 23)); d = ImageDraw.Draw(img)
        d.text((cx, 1460), 'EPISODIO COMPLETO', font=font('Bold', 46), fill=C['white'], anchor='mm')
        d.text((cx, 1590), '@QuienSabeMasTV', font=font('Bold', 52), fill=C['gold'], anchor='mm')
        return img


class Corto(tv.Programa):
    def personaje(s, fr, quien, pose, t):
        b = s.boca(t, quien)
        if quien == 'anunciador':
            sp = voz_sprite(b, int(t * 10) % 12 if b else 0, 520)
            sp = sp.resize((300, 300), Image.LANCZOS)
            fr.paste(sp, (PJ_X - 150, 340 - 150), sp); return
        k = int(t * FPS) + (17 if quien == 'copresentadora' else 0)
        parp = (k % 61) in (0, 1) or (k % 167) in (0, 1)
        sp, (cx, cy) = sprite(quien, pose, b, parp)
        sp = sp.resize((round(sp.width * ESC), round(sp.height * ESC)), Image.LANCZOS)
        bob = round(3 * np.sin(2 * np.pi * t / 3.4))
        x = round(PJ_X - cx * ESC); y = round(PJ_Y + 60 - cy * ESC) + bob
        x = max(10, min(x, 420 - sp.width)) if sp.width < 410 else 10
        # recorta la parte baja para no tapar la pregunta
        sp = sp.crop((0, 0, sp.width, max(1, 560 - y)))
        fr.paste(sp, (x, y), sp)
        d = ImageDraw.Draw(fr)
        d.rounded_rectangle((PJ_X - 75, 515, PJ_X + 75, 560), 22, fill=C['gold'])
        d.text((PJ_X, 538), NOMBRES[quien], font=font('Bold', 28), fill=C['ink'], anchor='mm')

    def render(s, out, tmp):
        os.makedirs(tmp, exist_ok=True)
        total = s.t; nfr = int(total * FPS); vid = os.path.join(tmp, 'v.mp4')
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
                kk = int(t * FPS) + (17 if quien == 'copresentadora' else 0)
                key = (id(base), quien, pose, s.boca(t, quien), (kk % 61) in (0, 1) or (kk % 167) in (0, 1),
                       round(3 * np.sin(2 * np.pi * t / 3.4)), int(t * 10) % 12 if quien == 'anunciador' else 0)
                if key not in cache:
                    if len(cache) > 200: cache.clear()
                    fr = base.copy(); s.personaje(fr, quien, pose, t); cache[key] = fr.tobytes()
                ff.stdin.write(cache[key])
            else:
                ff.stdin.write(base.tobytes())
        ff.stdin.close(); ff.wait()
        mix = np.zeros(int(SR * (total + 0.5)), np.float32)
        for at, a in s.audio:
            st = int(at * SR); e = min(len(mix), st + len(a)); mix[st:e] += a[:e - st]
        pk = np.abs(mix).max()
        if pk > 0.98: mix *= 0.98 / pk
        wav = os.path.join(tmp, 'a.wav')
        with wave.open(wav, 'w') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype(np.int16).tobytes())
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', vid, '-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                        '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', '48000', '-ac', '2', '-c:a', 'aac', '-b:a', '192k',
                        '-shortest', '-movflags', '+faststart', out], check=True)


def elegir(Q, n, ya=()):
    """Preguntas medias/difíciles, cortas y que quepan en vertical; prioriza las que tienen foto."""
    N = len(Q)
    def puntaje(q):
        if q['n'] in ya or q.get('ronda') == 'relampago' or len(q['p']) > 110 or max(len(o) for o in q['o']) > 34: return -1
        s = 2 if q.get('img_modo') == 'pregunta' else (1 if q.get('img') else 0)
        s += 2 if (q['n'] - 1) * 3 // N >= 1 else 0
        return s
    cand = sorted([q for q in Q if puntaje(q) >= 0], key=lambda q: (-puntaje(q), q['n']))
    # repartidas a lo largo del episodio, no todas seguidas
    out = []
    for q in cand:
        if all(abs(q['n'] - o['n']) >= max(3, N // 10) for o in out): out.append(q)
        if len(out) == n: break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--contenido', required=True); ap.add_argument('--voces', default='')
    ap.add_argument('--banco', default=os.path.join(RAIZ, 'banco')); ap.add_argument('--salida', required=True)
    ap.add_argument('--n', type=int, default=0, help='cuántos Shorts (0 = 2 normal, 4 maratón)')
    ap.add_argument('--preguntas', default='', help='números de pregunta separados por coma (opcional)')
    a = ap.parse_args()
    meta = json.load(open(a.contenido, encoding='utf-8')); Q = meta['preguntas']; total = meta.get('total_anunciado', len(Q))
    n = a.n or (4 if meta.get('formato') == 'maraton' else 2)
    sel = [q for q in Q if str(q['n']) in a.preguntas.split(',')] if a.preguntas else elegir(Q, n)
    os.makedirs(a.salida, exist_ok=True)
    S = sfx(); var_dir = os.path.join(RAIZ, 'banco', 'var'); semilla = sum(map(ord, meta.get('id', meta['codigo_sala'])))
    hechos = []
    for j, q in enumerate(sel):
        faltan = []

        def voz(clave, alt=True):
            if alt and os.path.isdir(var_dir):
                vs = sorted(f for f in os.listdir(var_dir) if f.startswith(clave + '__') and f.endswith('.wav'))
                if vs: return load_wav(os.path.join(var_dir, vs[(semilla + j * 5) % len(vs)]))
            for d in (a.voces, a.banco):
                if d and os.path.exists(f'{d}/{clave}.wav'): return load_wav(f'{d}/{clave}.wav')
            faltan.append(clave); return np.zeros(int(SR * 1.5), np.float32)

        V = Vertical(meta); G = Corto(); key = f"q{q['n']:02d}"

        def decir(img, clips, quien_pantalla, poses, pad=0.3, pre=0.0):
            t = G.t + pre
            for arr, quien in clips:
                G.voz(arr, t, quien); t += len(arr) / SR + 0.1
            G.escena(img, t - G.t + pad, quien_pantalla, poses)

        # 1) gancho + pregunta: la pregunta se ve desde el primer cuadro
        G.sonido(S['whoosh'], gain=0.8)
        decir(V.pregunta(q), [(voz('an_01_marca', False), 'anunciador')], 'anunciador', {}, pad=0.1)
        decir(V.pregunta(q), [(voz(f'{key}_pregunta'), 'presentador')], 'presentador', {'presentador': 'senala'}, pad=0.2)
        # 2) cuenta regresiva
        t0 = G.t
        for sec in range(SEG): G.sonido(S['tick_hi'] if sec >= SEG - 2 else S['tick'], at=t0 + sec, gain=0.8)
        cache = {}
        def tfn(t, q=q, cache=cache):
            r = max(1, SEG - int(t)); fr = round((1 - t / SEG) * 30) / 30
            if (r, fr) not in cache: cache[(r, fr)] = V.pregunta(q, reloj=r, frac=fr)
            return cache[(r, fr)]
        G.escena(tfn, float(SEG), 'presentador', {'presentador': 'piensa'})
        G.sonido(S['tiempo'], gain=0.7)
        # 3) revelación + dato
        G.sonido(S['ding'], at=G.t + 0.3, gain=0.9)
        decir(V.pregunta(q, modo='revela'), [(voz('pr_04_tiempo'), 'presentador'), (voz(f'{key}_respuesta'), 'copresentadora')],
              'copresentadora', {'copresentadora': 'aplaude', 'presentador': 'frente'}, pad=0.6)
        if q.get('d'):
            decir(V.dato(q), [(voz(f'{key}_dato'), 'copresentadora')], 'copresentadora', {'copresentadora': 'presenta'}, pad=0.8)
        # 4) cierre: anzuelo al episodio completo
        decir(V.cierre(total), [(voz('co_07_otra'), 'copresentadora')], 'copresentadora', {'copresentadora': 'saluda'}, pad=1.2)
        out = os.path.join(a.salida, f'short_{j + 1}.mp4')
        print(f"Short {j + 1}: pregunta {q['n']} · {G.t:.1f} s" + (f' · faltan voces {faltan}' if faltan else ''))
        if G.t > 58: print('  aviso: pasa de 58 s')
        G.render(out, os.path.join(a.salida, f'tmp{j}'))
        hechos.append({'archivo': out, 'n': q['n'], 'pregunta': q['p'], 'duracion': round(G.t, 1), 'faltan': faltan})
    json.dump({'id': meta.get('id'), 'titulo': meta['titulo'], 'total': total, 'shorts': hechos},
              open(os.path.join(a.salida, 'shorts.json'), 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
