"""Subtítulos tipo karaoke (estilo Shorts) para las charlas de MAX, NOVA y LA VOZ.
- De 2 a 4 palabras a la vez, abajo al centro, letra gruesa blanca con borde oscuro.
- La palabra que se está diciendo se pinta del color de quien habla y "salta" un poquito al aparecer.
- Los tiempos de cada palabra se reparten por sílabas dentro del tramo con voz del clip (sin GPU).
Se activa con QSM_SUBTITULOS=1 (tv.py).
"""
import os, re, unicodedata
from PIL import Image, ImageDraw, ImageFont

COLOR = {'presentador': (255, 200, 40), 'copresentadora': (90, 215, 255), 'anunciador': (140, 235, 110)}
BLANCO, BORDE = (255, 255, 255), (16, 10, 44)
MAX_PAL, MAX_CAR = 3, 22
POP_SEG = 0.14
VOCAL = re.compile(r'[aeiouáéíóúü]+', re.I)


def silabas(w):
    if re.search(r'\d', w): return max(1, 2 * len(re.sub(r'\D', '', w)))
    return max(1, len(VOCAL.findall(w)))


def norm(w):
    w = ''.join(c for c in unicodedata.normalize('NFD', w.lower()) if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9ñ]', '', w)


def ya_escrito(grupo, vistas):
    """El bloque ya se lee en pantalla si todas sus palabras con contenido (4+ letras) están escritas allí."""
    ws = [norm(w) for w, _, _ in grupo]; largas = [w for w in ws if len(w) >= 4]
    if not largas: return all(w in vistas for w in ws if w)
    return all(w in vistas for w in largas)


def pausa(w):
    if re.search(r'(\.\.\.|…|[.!?¡¿])["»)]*$', w): return 1.4
    if re.search(r'[,;:]["»)]*$', w): return 0.8
    return 0.0


class Subtitulos:
    def __init__(s, W, H, fps, fuente_black, fuente_bold, x0, x1, cy):
        s.W, s.H, s.fps = W, H, fps
        s.fuente = fuente_black if os.path.exists(fuente_black) else fuente_bold
        s.x0, s.x1, s.cy = x0, x1, cy
        s.bloques = []   # (t0, t1, quien, [(palabra, t0, t1)])
        s._fc, s._capa = {}, {}
        s._i = 0

    def font(s, sz):
        if sz not in s._fc: s._fc[sz] = ImageFont.truetype(s.fuente, sz)
        return s._fc[sz]

    def agregar(s, at, lv, quien, texto, pantalla=''):
        """at: inicio del clip (s); lv: niveles de boca por cuadro (0 = silencio)."""
        pal = texto.split()
        if not pal or lv is None or not len(lv): return
        voz = [i for i, v in enumerate(lv) if v > 0]
        if not voz: return
        a, b = at + voz[0] / s.fps, at + (voz[-1] + 1) / s.fps
        pesos = [silabas(w) + pausa(w) for w in pal]
        tot = sum(pesos); t = a; tiempos = []
        for w, p in zip(pal, pesos):
            dur = (b - a) * p / tot
            hablar = (b - a) * silabas(w) / tot
            tiempos.append((w, t, t + max(hablar, dur * 0.6))); t += dur
        vistas = {norm(w) for w in pantalla.split()}
        grupo = []
        for k, (w, t0, t1) in enumerate(tiempos):
            grupo.append((w, t0, t1))
            largo = sum(len(x[0]) + 1 for x in grupo)
            sig = tiempos[k + 1][0] if k + 1 < len(tiempos) else ''
            if (len(grupo) >= MAX_PAL or pausa(w) or k + 1 == len(tiempos)
                    or largo + len(sig) > MAX_CAR):
                if not ya_escrito(grupo, vistas): s.bloques.append([grupo[0][1], grupo[-1][2], quien, grupo])
                grupo = []
        s.bloques.sort(key=lambda x: x[0])

    def cerrar(s):
        """Cada bloque se queda en pantalla un poco más, sin pisar al siguiente."""
        for i, bl in enumerate(s.bloques):
            nxt = s.bloques[i + 1][0] if i + 1 < len(s.bloques) else bl[1] + 1
            bl[1] = min(bl[1] + 0.3, nxt)

    def estado(s, t):
        bl = s.bloques
        if not bl: return None
        if s._i >= len(bl) or bl[s._i][0] > t: s._i = 0   # por si se pide un t anterior
        while s._i + 1 < len(bl) and bl[s._i + 1][0] <= t: s._i += 1
        t0, t1, quien, pal = bl[s._i]
        if not (t0 <= t < t1): return None
        k = 0
        for j, (w, a, b) in enumerate(pal):
            if t >= a: k = j
        pop = t - pal[k][1] < POP_SEG
        return (s._i, k, pop)

    def capa(s, st):
        if st in s._capa: return s._capa[st]
        if len(s._capa) > 40: s._capa.clear()
        i, k, pop = st; _, _, quien, pal = s.bloques[i]
        palabras = [w for w, _, _ in pal]
        ancho_max = s.x1 - s.x0
        sz = 70
        while sz > 40:
            f = s.font(sz); esp = sz * 0.28
            ws = [f.getlength(w) for w in palabras]
            if sum(ws) + esp * (len(ws) - 1) + 30 <= ancho_max: break
            sz -= 4
        f = s.font(sz); fg = s.font(int(sz * 1.12)); esp = sz * 0.28
        ws = [(fg if (j == k and pop) else f).getlength(w) for j, w in enumerate(palabras)]
        total = sum(ws) + esp * (len(ws) - 1)
        alto = int(sz * 2.0)
        img = Image.new('RGBA', (s.W, alto), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
        x = (s.x0 + s.x1) / 2 - total / 2; yc = alto / 2
        col = COLOR.get(quien, COLOR['presentador'])
        for j, w in enumerate(palabras):
            fj = fg if (j == k and pop) else f
            d.text((x, yc), w, font=fj, fill=col if j == k else BLANCO, anchor='lm',
                   stroke_width=max(5, sz // 10), stroke_fill=BORDE)
            x += ws[j] + esp
        s._capa[st] = (img, int(s.cy - alto / 2))
        return s._capa[st]

    def dibujar(s, fr, st):
        img, y = s.capa(st)
        fr.paste(img, (0, y), img)
