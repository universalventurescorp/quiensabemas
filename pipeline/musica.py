"""Música del programa, sintetizada por código (100 % propia: sin Content ID ni licencias).
- Cama de concurso: acordes suaves, bajo, arpegio y percusión ligera; tonalidad, tempo, progresión y patrones
  cambian con la semilla del episodio (cada episodio suena distinto) y alternan secciones A/B/C dentro del episodio.
- Tema de entrada y de salida (jingle de metales sintéticos).
- Tensión durante el reloj: pulso grave por segundo que se acelera en los 3 últimos.
- Ducking: la cama baja cuando habla alguien y sube en los silencios.
Uso desde tv.py:  M = Musica(semilla); M.mezclar(mix, habla, relojes, temas)
APAGADA por defecto (al usuario no le gustó cómo suena la síntesis): tv.py solo la usa con QSM_MUSICA=1.
Plan: reemplazar las secciones/tema por temas de la Biblioteca de audio de YouTube y conservar el ducking.
"""
import numpy as np
from scipy.ndimage import maximum_filter1d, uniform_filter1d
from scipy.signal import lfilter

SR = 24000
DB = lambda x: 10 ** (x / 20)
# niveles respecto al nivel medio de la voz
NIVEL = dict(cama_voz=-26, cama_libre=-17, tension=-15, tema_libre=-7, tema_voz=-19)

PROG = [[0, 5, 9, 7], [0, 9, 5, 7], [0, 7, 9, 5], [0, 4, 5, 7], [0, 5, 2, 7], [0, 9, 2, 7]]  # grados en semitonos
MAYOR = {0: 'M', 2: 'm', 4: 'm', 5: 'M', 7: 'M', 9: 'm'}


def hz(m): return 440.0 * 2 ** ((m - 69) / 12)


def lp(x, fc):
    a = np.exp(-2 * np.pi * fc / SR); return lfilter([1 - a], [1, -a], x).astype(np.float32)


def env(n, at=0.01, rel=0.1, sus=1.0):
    e = np.full(n, sus, np.float32); a = min(n, int(at * SR)); r = min(n - a, int(rel * SR))
    if a: e[:a] = np.linspace(0, sus, a)
    if r: e[n - r:] = np.linspace(sus, 0, r)
    return e


class Musica:
    def __init__(s, semilla):
        r = np.random.default_rng(semilla)
        s.r = r
        s.raiz = 48 + int(r.integers(0, 12))           # Do3 … Si3
        s.bpm = float(r.choice([104, 108, 112, 116, 120]))
        s.beat = 60.0 / s.bpm
        s.prog = PROG[int(r.integers(0, len(PROG)))]
        s.brillo = float(r.uniform(1800, 3200))       # timbre del pad
        s.L = int(round(8 * 4 * s.beat * SR))          # sección = 8 compases
        s.secciones = [s._seccion(k) for k in range(3)]
        orden = [0, 0, 1, 0, 2, 1, 0, 1, 2, 2]
        s.orden = [orden[(i + int(r.integers(0, 10))) % 10] for i in range(10)]
        s._tema = s._jingle()
        s._tension = {}

    # ---------------------------------------------------------------- instrumentos
    def _acorde(s, grado):
        tipo = MAYOR.get(grado % 12, 'M'); b = s.raiz + grado
        return [b, b + (3 if tipo == 'm' else 4), b + 7]

    def _pad(s, notas, n):
        t = np.arange(n) / SR; out = np.zeros(n, np.float32)
        for m in notas:
            for det in (-0.12, 0.12):
                f = hz(m + 12) * 2 ** (det / 12)
                for h, a in ((1, 1), (2, .35), (3, .18), (4, .08)):
                    out += a * np.sin(2 * np.pi * f * h * t + h).astype(np.float32)
        return lp(out, s.brillo) * env(n, .25, .35) * 0.05

    def _pluck(s, m, n):
        t = np.arange(n) / SR; f = hz(m)
        x = sum(a * np.sin(2 * np.pi * f * h * t) for h, a in ((1, 1), (2, .5), (3, .25), (5, .1)))
        return (x * np.exp(-t * 9)).astype(np.float32) * env(n, .003, .02) * 0.10

    def _bajo(s, m, n):
        t = np.arange(n) / SR; f = hz(m - 12)
        x = np.sin(2 * np.pi * f * t) + .3 * np.sin(4 * np.pi * f * t)
        return (x * np.exp(-t * 2.2)).astype(np.float32) * env(n, .005, .05) * 0.16

    def _bombo(s):
        n = int(.35 * SR); t = np.arange(n) / SR
        fase = 2 * np.pi * np.cumsum(45 + 90 * np.exp(-t * 30)) / SR
        return (np.sin(fase) * np.exp(-t * 11)).astype(np.float32) * 0.28

    def _plato(s, largo=.05):
        n = int(largo * SR); x = s.r.standard_normal(n).astype(np.float32)
        x = x - lp(x, 6000); return x * np.exp(-np.arange(n) / SR * 60).astype(np.float32) * 0.05

    def _palmas(s):
        n = int(.18 * SR); x = s.r.standard_normal(n).astype(np.float32)
        x = lp(x, 2500) - lp(x, 900); t = np.arange(n) / SR
        return x * np.exp(-t * 22).astype(np.float32) * 0.22

    # ---------------------------------------------------------------- secciones (loops sin costura)
    def _seccion(s, k):
        L = s.L; out = np.zeros(L + SR * 2, np.float32); comp = int(round(4 * s.beat * SR)); b = s.beat
        patrones = [[0, 1, 2, 1, 0, 1, 2, 1], [0, 2, 1, 2, 0, 2, 1, 2], [0, 1, 2, 3, 2, 1, 0, 1]]
        pat = patrones[(k + int(s.r.integers(0, 3))) % 3]
        for c in range(8):
            g = s.prog[c % 4]; notas = s._acorde(g); t0 = c * comp
            out[t0:t0 + comp + int(.35 * SR)] += s._pad(notas, comp + int(.35 * SR))
            bajo = notas[0] - 12
            for bt in ((0, 2) if k != 1 else (0, 1.5, 2, 3.5)):
                st = t0 + int(bt * b * SR); out[st:st + int(b * SR * 1.5)] += s._bajo(bajo + 12, int(b * SR * 1.5))
            if k != 2 or c % 2 == 0:   # la sección C deja respirar el arpegio
                arp = notas + [notas[0] + 12]
                for i in range(8):
                    st = t0 + int(i * b / 2 * SR); m = arp[pat[i] % len(arp)] + 12
                    out[st:st + int(b * SR)] += s._pluck(m, int(b * SR)) * (0.8 if i % 2 else 1)
            for q in range(4):  # percusión
                st = t0 + int(q * b * SR)
                if k != 1 and q in (0, 2): bb = s._bombo(); out[st:st + len(bb)] += bb
                if k == 2 and q in (1, 3): pp = s._palmas(); out[st:st + len(pp)] += pp
                for h in (0, .5):
                    if k == 1 and h == 0: continue
                    ht = st + int(h * b * SR); pl = s._plato(); out[ht:ht + len(pl)] += pl * (1 if h else .6)
        out[:SR * 2] += out[L:L + SR * 2]   # la cola vuelve al inicio: el loop no tiene costura
        return out[:L] * (0.9 if k == 1 else 1.0)

    # ---------------------------------------------------------------- tema de entrada / salida
    def _metal(s, m, n):
        t = np.arange(n) / SR; f = hz(m); x = np.zeros(n, np.float32)
        vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) * np.clip(t * 3, 0, 1)
        for h in range(1, 9): x += (1 / h) * np.sin(2 * np.pi * f * h * np.cumsum(vib) / SR).astype(np.float32)
        x = lp(x, 900 + 2600 * np.clip(t[-1] * 2, 0, 1))
        return x * env(n, .03, .12) * 0.09

    def _jingle(s):
        b = 60 / 132; n = int(b * 10 * SR); out = np.zeros(n + SR, np.float32); R = s.raiz + 12
        mel = [(0, 0, .5), (.5, 4, .5), (1, 7, .5), (1.5, 12, 1.5), (3, 9, .5), (3.5, 7, .5), (4, 9, .5), (4.5, 12, .5),
               (5, 14, 1), (6, 16, 3.5)]
        for at, iv, du in mel:
            st = int(at * b * SR); nn = int(du * b * SR); out[st:st + nn] += s._metal(R + iv, nn)
            out[st:st + nn] += s._metal(R + iv - 12, nn) * 0.5
        for at, g in ((0, 0), (3, 5), (5, 7), (6, 0)):  # golpes de acorde + bombo
            st = int(at * b * SR); nn = int((1.5 if at < 6 else 3.5) * b * SR)
            for m in s._acorde(g): out[st:st + nn] += s._metal(m, nn) * 0.45
            bb = s._bombo(); out[st:st + len(bb)] += bb * 1.3
        pl = np.concatenate([s._plato(1.6)]) * 4; st = int(6 * b * SR); out[st:st + len(pl)] += pl
        return out * 1.4

    # ---------------------------------------------------------------- tensión del reloj
    def tension(s, seg):
        seg = int(round(seg))
        if seg in s._tension: return s._tension[seg]
        n = int(seg * SR); out = np.zeros(n + SR, np.float32); t = np.arange(n) / SR
        dr = (np.sin(2 * np.pi * hz(s.raiz - 12) * t) + .5 * np.sin(2 * np.pi * hz(s.raiz - 5) * t)).astype(np.float32)
        out[:n] += lp(dr, 400) * env(n, .4, .3) * 0.06
        golpes = [k for k in range(seg)] + [k + .5 for k in range(max(0, seg - 3), seg)]
        for k in golpes:
            st = int(k * SR); m = s.raiz - 12 + (1 if k >= seg - 3 else 0)
            out[st:st + int(.4 * SR)] += s._bajo(m + 12, int(.4 * SR)) * 1.3
            bb = s._bombo(); out[st:st + len(bb)] += bb * .6
        sub = int(max(0, seg - 3) * SR); ts = np.arange(n - sub) / SR   # subida en los últimos 3 s
        sw = np.sin(2 * np.pi * np.cumsum(hz(s.raiz + 12) * 2 ** (ts / 3)) / SR).astype(np.float32)
        out[sub:n] += sw * np.linspace(0, .05, n - sub, dtype=np.float32)
        s._tension[seg] = out[:n]; return out[:n]

    # ---------------------------------------------------------------- mezcla final con ducking
    def mezclar(s, mix, habla, relojes, temas):
        n = len(mix); K = 240                                         # control cada 10 ms
        nc = n // K + 1
        voz = np.zeros(nc, np.float32)
        for t0, t1, q, lv in habla:
            voz[int(t0 * 100):int(t1 * 100) + 1] = 1
        if voz.any():
            sel = np.repeat(voz[:n // K] > 0, K)[:n]; muestra = mix[:len(sel)][sel][::50]
            ref = float(np.sqrt(np.mean(muestra ** 2))) if len(muestra) else 0.1
        else:
            ref = 0.1
        ref = max(ref, 0.02)
        voz = uniform_filter1d(maximum_filter1d(voz, 35), 10)         # suelta en 0,35 s, ataque suave
        reloj = np.zeros(nc, np.float32)
        for t0, seg in relojes: reloj[int(t0 * 100):int((t0 + seg) * 100)] = 1
        reloj = uniform_filter1d(reloj, 30)                           # fundido de 0,3 s
        cama_rms = np.mean([np.sqrt(np.mean(x ** 2)) for x in s.secciones])
        gl, gv = DB(NIVEL['cama_libre']) * ref / cama_rms, DB(NIVEL['cama_voz']) * ref / cama_rms
        g = (gl + (gv - gl) * voz) * (1 - reloj)
        # sin cama en los temas de entrada y salida (suena el jingle)
        for t, cual in temas:
            a = int(t * 100); b = a + int(len(s._tema) / SR * 100)
            g[a:b] *= np.clip(np.abs(np.arange(a, min(b, nc)) - (a + b) / 2) / ((b - a) / 2) * 3 - 2, 0, 1)
        CH = SR * 60
        for a in range(0, n, CH):
            b = min(n, a + CH); idx = np.arange(a, b)
            sec = (idx // s.L) % len(s.orden); off = idx % s.L
            cama = np.empty(b - a, np.float32)
            for k in range(3):
                m = np.array(s.orden)[sec] == k
                if m.any(): cama[m] = s.secciones[k][off[m]]
            gc = np.interp(idx / K, np.arange(nc), g).astype(np.float32)
            mix[a:b] += cama * gc
        tr = DB(NIVEL['tension']) * ref / max(1e-6, np.sqrt(np.mean(s.tension(10) ** 2)))
        for t0, seg in relojes:
            x = s.tension(seg); st = int(t0 * SR); e = min(n, st + len(x)); mix[st:e] += x[:e - st] * tr
        tm = s._tema; tr_rms = np.sqrt(np.mean(tm ** 2))
        for t, cual in temas:
            st = int(t * SR); e = min(n, st + len(tm))
            if e <= st: continue
            vz = np.interp(np.arange(st, e) / K, np.arange(nc), voz)
            gt = (DB(NIVEL['tema_libre']) + (DB(NIVEL['tema_voz']) - DB(NIVEL['tema_libre'])) * vz) * ref / tr_rms
            mix[st:e] += tm[:e - st] * gt.astype(np.float32)
        return mix
