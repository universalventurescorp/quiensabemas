"""3 miniaturas para «Probar y comparar» de YouTube Studio (1280×720), misma marca, distinto gancho:
  A · MAX   — MAX señala una pregunta real del episodio con sus 4 opciones (se lee como «juego» al instante).
  B · NOVA  — NOVA sorprendida + el reto en letras enormes (emoción + desafío).
  C · MARCA — logo grande, número enorme y los dos presentadores (reconocimiento de canal).
Uso: python pipeline/miniaturas_ab.py contenido/cola/ep001.json salida/ [--n 6] [--foto assets/...jpg]
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(__file__))
import miniatura as M
import tv

W, H = M.W, M.H
PREG = None  # pregunta corta para la miniatura A (--pregunta)
ORO, TINTA, ROJO, BLANCO = M.ORO, M.TINTA, M.ROJO, M.BLANCO


def fondo(halo_x=900):
    lz = tv.escenario().resize((W, H), Image.LANCZOS).convert('RGBA')
    luz = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(luz)
    d.ellipse((halo_x - 380, 0, halo_x + 380, 760), fill=(170, 110, 255, 80))
    lz.alpha_composite(luz.filter(ImageFilter.GaussianBlur(80)))
    return lz


def marco(lz):
    d = ImageDraw.Draw(lz)
    d.rectangle((0, 0, W - 1, H - 1), outline=ORO, width=10)
    d.rectangle((10, 10, W - 11, H - 11), outline=(120, 70, 10), width=2)


def logo(lz, size=40, xy=(18, 10)):
    lg = M.etiqueta('¿Quién Sabe Más?', size, ORO, TINTA, pad=(28, 10))
    lz.alpha_composite(lg, xy)
    return lg


def chip(letra, txt, col, w, h=78):
    """Botón de opción como en el programa: círculo con la letra + texto."""
    c = Image.new('RGBA', (w + 8, h + 8), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    d.rounded_rectangle((4, 4, w + 3, h + 3), h // 2, fill=(30, 22, 74), outline=col, width=6)
    r = h // 2 - 10; cx = 4 + h // 2
    d.ellipse((cx - r, 4 + h // 2 - r, cx + r, 4 + h // 2 + r), fill=col)
    d.text((cx, 4 + h // 2), letra, font=tv.font('Bold', 38), fill=BLANCO, anchor='mm')
    sz = 36
    while sz > 24 and d.textlength(txt, font=tv.font('Bold', sz)) > w - (cx + r + 16) - 18: sz -= 2
    d.text((cx + r + 16, 4 + h // 2), txt, font=tv.font('Bold', sz), fill=BLANCO, anchor='lm')
    return M.sombra(c, 8, 140, 6)


# ------------------------------------------------------------ A · MAX
def var_max(ep, q, foto):
    lz = fondo(1060)
    fw, fh = 600, 330
    lz.alpha_composite(M.sombra(M.marco_foto(foto, None, fw, fh, giro=0), 16, 170, 12), (40, 92))
    # pregunta corta sobre la foto
    preg = (PREG or q.get('p_corta') or q['p']).upper()
    capa = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    M.texto(capa, (352, 470), preg if len(preg) <= 26 else '¿LA SABES?', tv.font('Bold', 46), BLANCO, borde=7, anchor='mm')
    lz.alpha_composite(capa)
    # 4 opciones (2×2), ninguna marcada
    cols = [c for c, _ in tv.OPC]
    for i, (txt, col) in enumerate(zip(q['o'], cols)):
        x = 40 + (i % 2) * 312; y = 512 + (i // 2) * 92
        lz.alpha_composite(chip('ABCD'[i], txt, col, 296), (x, y))
    # MAX grande señalando hacia la pregunta
    mx, (cx, cy) = M.busto('presentador', 'senala', 215, 'feliz')
    mx = mx.transpose(Image.FLIP_LEFT_RIGHT); cx = mx.width - cx  # que señale a la izquierda
    lz.alpha_composite(M.sombra(mx, 22, 130, 0), (int(1000 - cx), int(285 - cy)))
    logo(lz)
    e = M.etiqueta(f'{ep.get("total_anunciado") or len(ep["preguntas"])} PREGUNTAS', 40, ROJO, BLANCO, giro=-4)
    lz.alpha_composite(e, (W - e.width - 24, 18))
    marco(lz); return lz.convert('RGB')


# ------------------------------------------------------------ B · NOVA
def var_nova(ep, q, foto):
    lz = fondo(1000)
    reto = (ep.get('reto_miniatura') or '¿Cuántas sabes?').upper()
    # foto de fondo a la izquierda, oscurecida, para que el texto mande
    f = M.marco_foto(foto, None, 560, 330, giro=4)
    lz.alpha_composite(M.sombra(f, 16, 160, 12), (60, 120))
    # reto en dos líneas enormes
    pal = reto.split(); mitad = (len(pal) + 1) // 2
    l1, l2 = ' '.join(pal[:mitad]), ' '.join(pal[mitad:])
    capa = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    M.texto(capa, (40, 560), l1, tv.font('Bold', 92), BLANCO, borde=10)
    M.texto(capa, (40, 680), l2, tv.font('Bold', 118), ORO, borde=12)
    lz.alpha_composite(capa)
    # NOVA sorprendida, grande, a la derecha
    nv, (cx, cy) = M.busto('copresentadora', 'presenta', 230, 'sorpresa')
    nv = nv.transpose(Image.FLIP_LEFT_RIGHT); cx = nv.width - cx  # presenta hacia el reto
    lz.alpha_composite(M.sombra(nv, 22, 140, 0), (int(1010 - cx), int(270 - cy)))
    logo(lz)
    marco(lz); return lz.convert('RGB')


# ------------------------------------------------------------ C · MARCA
def var_marca(ep, q, foto):
    lz = fondo(640)
    total = str(ep.get('total_anunciado') or len(ep['preguntas']))
    # logo grande arriba al centro
    lg = M.etiqueta('¿Quién Sabe Más?', 78, ORO, TINTA, pad=(44, 14))
    lz.alpha_composite(lg, ((W - lg.width) // 2, 22))
    # número enorme al centro
    capa = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    M.texto(capa, (W // 2, 470), total, tv.font('Bold', 330), ORO, borde=16, anchor='ms')
    M.texto(capa, (W // 2, 580), 'PREGUNTAS', tv.font('Bold', 84), BLANCO, borde=10, anchor='ms')
    lz.alpha_composite(capa)
    e = M.etiqueta('¡JUEGA EN FAMILIA!', 40, ROJO, BLANCO, giro=-3)
    lz.alpha_composite(e, ((W - e.width) // 2, 600))
    # presentadores a los lados
    mx, (mcx, mcy) = M.busto('presentador', 'celebra2', 210)
    nv, (ncx, ncy) = M.busto('copresentadora', 'aplaude', 175)
    lz.alpha_composite(M.sombra(mx, 20, 130, 0), (int(170 - mcx), int(370 - mcy)))
    lz.alpha_composite(M.sombra(nv, 20, 130, 0), (int(1110 - ncx), int(360 - ncy)))
    marco(lz); return lz.convert('RGB')


def hoja(minis, out):
    """Vista previa: las 3 en tamaño celular (168×94) y escritorio (360×202), como en el feed."""
    can = Image.new('RGB', (1240, 560), (15, 15, 15)); d = ImageDraw.Draw(can); f = tv.font('Medium', 22)
    for i, (nom, m) in enumerate(minis):
        x = 30 + i * 400
        d.text((x, 14), nom, font=tv.font('Bold', 26), fill=(255, 255, 255))
        can.paste(m.resize((360, 202), Image.LANCZOS), (x, 56))
        d.text((x, 272), 'escritorio 360×202', font=f, fill=(170, 170, 170))
        can.paste(m.resize((168, 94), Image.LANCZOS), (x, 320))
        d.text((x, 424), 'celular 168×94', font=f, fill=(170, 170, 170))
    can.save(out, quality=92)


def main():
    a = sys.argv[1:]
    ep = json.load(open(a[0], encoding='utf-8')); out = a[1]; os.makedirs(out, exist_ok=True)
    n = int(a[a.index('--n') + 1]) if '--n' in a else 6
    q = next(x for x in ep['preguntas'] if x['n'] == n)
    global PREG
    PREG = a[a.index('--pregunta') + 1] if '--pregunta' in a else None
    foto = a[a.index('--foto') + 1] if '--foto' in a else M.elegir_foto(ep)[0]
    minis = [('A · MAX', var_max(ep, q, foto)), ('B · NOVA', var_nova(ep, q, foto)), ('C · MARCA', var_marca(ep, q, foto))]
    for i, (nom, m) in enumerate(minis, 1):
        m.save(os.path.join(out, f'miniatura_{i}_{nom.split()[-1].lower()}.jpg'), quality=92)
    hoja(minis, os.path.join(out, 'vista_previa.jpg'))
    print('OK', out)


if __name__ == '__main__':
    main()
