"""Miniatura de marca 1280×720 — siempre la misma plantilla para que el canal se reconozca al instante en el feed:
fondo morado con focos y marco dorado, logo arriba a la izquierda, la foto más llamativa del episodio en grande,
MAX y NOVA de busto celebrando a la derecha, el número enorme de preguntas y el reto en una etiqueta roja.
Uso: python pipeline/miniatura.py trabajo/episodio.json trabajo/miniatura.jpg [--feed prueba_feed.png]
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFilter, ImageOps
sys.path.insert(0, os.path.dirname(__file__))
import personajes
import tv

W, H = 1280, 720
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ORO, TINTA, ROJO, BLANCO = (255, 200, 40), (26, 18, 64), (226, 38, 54), (255, 255, 255)


# ------------------------------------------------------------ foto del episodio
def elegir_foto(ep):
    """La foto más llamativa: primero una foto-pregunta normal (no la misteriosa, para no regalar la respuesta),
    luego fotos del dato, luego la misteriosa, y la bandera solo si no hay nada más."""
    if ep.get('img_miniatura'):
        return ep['img_miniatura'], None
    mejor = None
    for q in ep['preguntas']:
        p = q.get('img')
        if not p or not os.path.exists(os.path.join(RAIZ, p)): continue
        bandera = bool(q.get('bandera')) or '/banderas/' in p
        if bandera: pts = 1
        elif q.get('img_modo') == 'pregunta' and q.get('ronda') != 'misteriosa': pts = 4
        elif q.get('img_modo') == 'pregunta': pts = 2
        else: pts = 3
        try:
            w, h = Image.open(os.path.join(RAIZ, p)).size
        except Exception:
            continue
        if min(w, h) < 360: pts -= 2          # muy chica: se ve borrosa en grande
        if mejor is None or pts > mejor[0]: mejor = (pts, p, q.get('img_fondo'))
    return (mejor[1], mejor[2]) if mejor else (None, None)


def marco_foto(path, fondo, w, h, giro=-3):
    src = Image.open(os.path.join(RAIZ, path)).convert('RGB')
    if fondo == 'blanco':
        src.thumbnail((w - 70, h - 70), Image.LANCZOS); can = Image.new('RGB', (w, h), BLANCO)
        can.paste(src, ((w - src.width) // 2, (h - src.height) // 2)); src = can
    else:
        src = ImageOps.fit(src, (w, h), Image.LANCZOS, centering=(0.5, 0.45))
        src = src.point(lambda v: min(255, int(v * 1.06)))  # un pelín más viva
    b = 12; tarj = Image.new('RGBA', (w + 2 * b, h + 2 * b), (0, 0, 0, 0)); d = ImageDraw.Draw(tarj)
    d.rounded_rectangle((0, 0, w + 2 * b - 1, h + 2 * b - 1), 26, fill=BLANCO)
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), 18, fill=255)
    tarj.paste(src, (b, b), m)
    d.rounded_rectangle((3, 3, w + 2 * b - 4, h + 2 * b - 4), 24, outline=ORO, width=5)
    return tarj.rotate(giro, Image.BICUBIC, expand=True)


def sin_foto(w, h):
    """Si el episodio no trae fotos: tarjeta de signos de pregunta (sigue reconocible)."""
    t = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(t)
    d.rounded_rectangle((0, 0, w - 1, h - 1), 26, fill=(70, 34, 140), outline=ORO, width=8)
    d.text((w / 2, h / 2), '?', font=tv.font('Bold', int(h * 0.8)), fill=ORO, anchor='mm')
    return t.rotate(-3, Image.BICUBIC, expand=True)


def sombra(capa, rad=16, alfa=150, dy=12):
    a = capa.getchannel('A').point(lambda v: v * alfa // 255)
    s = Image.new('RGBA', capa.size, (0, 0, 0, 0)); s.putalpha(a)
    s = s.filter(ImageFilter.GaussianBlur(rad))
    out = Image.new('RGBA', (capa.width, capa.height + dy), (0, 0, 0, 0))
    out.alpha_composite(s, (0, dy)); out.alpha_composite(capa, (0, 0))
    return out


# ------------------------------------------------------------ personajes grandes
def busto(quien, pose, ancho_cara, expr=None):
    """El mismo sprite del programa, pero dibujado a más resolución para la miniatura."""
    orig, orig_e = personajes.escala, dict(personajes.EXPRESION)
    if expr: personajes.EXPRESION[pose] = expr
    try:
        n = f'{personajes.PREFIJO[quien]}_{pose}'; g = personajes.GEO[n]['pantalla']
        personajes.escala = lambda q, p: ancho_cara / (g[2] - g[0])
        im, c = personajes.sprite.__wrapped__(quien, pose, 0, False)
    finally:
        personajes.escala = orig; personajes.EXPRESION.clear(); personajes.EXPRESION.update(orig_e)
    return im, c


# ------------------------------------------------------------ texto con borde
def texto(capa, xy, txt, f, fill, borde=0, col_borde=TINTA, anchor='ls'):
    d = ImageDraw.Draw(capa)
    if borde:
        sm = Image.new('RGBA', capa.size, (0, 0, 0, 0))
        ImageDraw.Draw(sm).text((xy[0], xy[1] + 8), txt, font=f, fill=(0, 0, 0, 170), anchor=anchor, stroke_width=borde, stroke_fill=(0, 0, 0, 170))
        capa.alpha_composite(sm.filter(ImageFilter.GaussianBlur(10)))
    d.text(xy, txt, font=f, fill=fill, anchor=anchor, stroke_width=borde, stroke_fill=col_borde)


def etiqueta(txt, size, fondo, col_txt, giro=0, pad=(34, 16)):
    f = tv.font('Bold', size); tw = ImageDraw.Draw(Image.new('L', (1, 1))).textlength(txt, font=f)
    w, h = int(tw + 2 * pad[0]), int(size * 1.15 + 2 * pad[1])
    e = Image.new('RGBA', (w + 8, h + 8), (0, 0, 0, 0)); d = ImageDraw.Draw(e)
    d.rounded_rectangle((4, 4, w + 3, h + 3), h // 2, fill=fondo, outline=BLANCO, width=5)
    d.text((w / 2 + 4, h / 2 + 4), txt, font=f, fill=col_txt, anchor='mm')
    return sombra(e.rotate(giro, Image.BICUBIC, expand=True), 10, 140, 8)


# ------------------------------------------------------------ plantilla
def componer(ep):
    maraton = ep.get('formato') == 'maraton'
    total = ep.get('total_anunciado') or len(ep['preguntas'])
    reto = (ep.get('reto_miniatura') or '').strip()
    if maraton: reto = '¡MARATÓN 3 HORAS!'
    elif not reto or len(reto) > 20: reto = '¿Cuántas sabes?'

    lienzo = tv.escenario().resize((W, H), Image.LANCZOS).convert('RGBA')
    luz = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dl = ImageDraw.Draw(luz)
    dl.ellipse((660, 40, 1320, 760), fill=(170, 110, 255, 70))   # halo detrás de los presentadores
    dl.ellipse((-120, 120, 760, 700), fill=(255, 200, 40, 26))   # luz cálida detrás de la foto
    lienzo.alpha_composite(luz.filter(ImageFilter.GaussianBlur(70)))

    # foto del episodio, grande y algo inclinada
    p, fondo = elegir_foto(ep)
    fw, fh = 640, 400
    tarj = marco_foto(p, fondo, fw, fh) if p else sin_foto(fw + 24, fh + 24)
    lienzo.alpha_composite(sombra(tarj, 18, 170, 14), (34, 92))

    # presentadores de busto, celebrando (como la foto de perfil)
    max_, (mx, my) = busto('presentador', 'celebra2', 225)
    nova, (nx, ny) = busto('copresentadora', 'aplaude', 185)
    lienzo.alpha_composite(sombra(max_, 20, 120, 0), (int(860 - mx), int(318 - my)))
    lienzo.alpha_composite(sombra(nova, 20, 140, 0), (int(1180 - nx), int(305 - ny)))

    # número enorme + PREGUNTAS (abajo a la izquierda, sobre el borde de la foto)
    capa = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    num = str(total); fN = tv.font('Bold', 220)
    texto(capa, (40, 690), num, fN, ORO, borde=12)
    nw = ImageDraw.Draw(capa).textlength(num, font=fN)
    texto(capa, (40 + nw + 22, 678), 'PREGUNTAS', tv.font('Bold', 60), BLANCO, borde=8)
    lienzo.alpha_composite(capa)

    # reto: etiqueta roja tipo sticker sobre la esquina de la foto
    e = etiqueta(reto, 44 if len(reto) <= 16 else 38, ROJO, BLANCO, giro=5)
    lienzo.alpha_composite(e, (max(20, 690 - e.width + 40), 470 - e.height // 2 - 40))

    # logo fijo arriba a la izquierda
    lg = etiqueta('¿Quién Sabe Más?', 40, ORO, TINTA, giro=0, pad=(28, 10))
    lienzo.alpha_composite(lg, (18, 10))

    # marco dorado de la marca
    d = ImageDraw.Draw(lienzo)
    d.rectangle((0, 0, W - 1, H - 1), outline=ORO, width=10)
    d.rectangle((10, 10, W - 11, H - 11), outline=(120, 70, 10), width=2)
    return lienzo.convert('RGB')


def prueba_feed(mini, out):
    """Cómo se ve en el feed del celular (168×94) y en la página de inicio de escritorio (360×202)."""
    can = Image.new('RGB', (620, 260), (15, 15, 15)); d = ImageDraw.Draw(can)
    a = mini.resize((168, 94), Image.LANCZOS); b = mini.resize((360, 202), Image.LANCZOS)
    can.paste(a, (20, 40)); can.paste(b, (230, 40))
    f = tv.font('Medium', 16)
    d.text((20, 20), 'Celular 168×94', font=f, fill=(200, 200, 200)); d.text((230, 20), 'Escritorio 360×202', font=f, fill=(200, 200, 200))
    can.save(out)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    ep = json.load(open(args[0], encoding='utf-8'))
    mini = componer(ep)
    mini.save(args[1], quality=92)
    if '--feed' in sys.argv:
        prueba_feed(mini, sys.argv[sys.argv.index('--feed') + 1])
    print('OK', args[1])


if __name__ == '__main__':
    main()
