"""Recorta el verde de una imagen de Flow con VARIOS animales en fila y guarda cada animal como PNG aparte.
Uso: python scripts/separar_animales.py entrada.jpg assets/navidad/publico prefijo nombre1,nombre2,...
(los nombres van de izquierda a derecha; si hay más figuras que nombres, se numeran)
"""
import os, sys
import numpy as np
from PIL import Image, ImageFilter
from scipy.ndimage import label, find_objects, binary_dilation


def alfa_verde(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    verde = g - np.maximum(r, b)
    al = 1 - np.clip((verde - 25) / 55, 0, 1)
    a[..., 1] = np.minimum(g, np.maximum(r, b) + 6)   # quita el reflejo verde de los bordes
    return al


def main():
    ent, out, pref = sys.argv[1:4]; nombres = sys.argv[4].split(',') if len(sys.argv) > 4 else []
    os.makedirs(out, exist_ok=True)
    a = np.asarray(Image.open(ent).convert('RGB')).astype(np.float32)
    al = alfa_verde(a)
    m = binary_dilation(al > 0.5, iterations=int(os.environ.get('DIL', '6')))          # une partes sueltas del mismo animal (astas, bufanda)
    lb, n = label(m); objs = find_objects(lb)
    piezas = [(sl[1].start, k + 1, sl) for k, sl in enumerate(objs) if (sl[0].stop - sl[0].start) * (sl[1].stop - sl[1].start) > 0.004 * m.size]
    piezas.sort()
    mask = Image.fromarray((al * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1))
    rgb = Image.fromarray(a.clip(0, 255).astype(np.uint8))
    for i, (_, k, sl) in enumerate(piezas):
        sub = (lb[sl] == k)
        y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
        im = rgb.crop((x0, y0, x1, y1)).convert('RGBA')
        mk = np.asarray(mask.crop((x0, y0, x1, y1))) * sub
        im.putalpha(Image.fromarray(mk.astype(np.uint8)))
        im = im.crop(im.getchannel('A').point(lambda v: 255 if v > 40 else 0).getbbox())
        if im.height < 500: im = im.resize((round(im.width * 500 / im.height), 500), Image.LANCZOS)
        nom = nombres[i] if i < len(nombres) else f'{i + 1}'
        p = os.path.join(out, f'{pref}_{nom}.png'); im.save(p); print(p, im.size)


if __name__ == '__main__':
    main()
