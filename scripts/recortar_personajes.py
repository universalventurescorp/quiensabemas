"""Recorta el fondo verde de los personajes (chroma key con despill) y ubica su pantalla/visor.
Uso: python scripts/recortar_personajes.py
Lee  assets/personajes/originales/*.png
Deja assets/personajes/<nombre>.png (RGBA, recortado, alto máx 1200 px)
     assets/personajes/<nombre>_cara.png (máscara L de la pantalla/visor donde se dibuja la cara)
     assets/personajes/<nombre>_brillo.png (reflejo del vidrio, se repinta encima de la cara)
     assets/personajes/geometria.json (caja de la pantalla en cada imagen)
"""
import glob, json, os
import numpy as np
from PIL import Image
from scipy import ndimage

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ORIG = os.path.join(RAIZ, 'assets', 'personajes', 'originales')
DEST = os.path.join(RAIZ, 'assets', 'personajes')
ALTO = 1200


def chroma(rgb):
    f = rgb.astype(np.float32)
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    # cuánto domina el verde sobre los otros canales
    dom = g - np.maximum(r, b)
    a = 1.0 - np.clip((dom - 18) / (70 - 18), 0, 1)          # 0 = fondo, 1 = personaje
    # limpiar: quedarse con los objetos grandes (quita motas)
    lab, n = ndimage.label(a > 0.5)
    if n:
        tam = ndimage.sum(np.ones_like(a), lab, range(1, n + 1))
        keep = np.isin(lab, 1 + np.where(tam > 0.002 * a.size)[0])
        hueco = ndimage.binary_fill_holes(keep)
        a = np.where(ndimage.binary_dilation(hueco, iterations=3), a, 0)
    a = ndimage.gaussian_filter(a, 0.7)
    # despill: el verde no puede superar al mayor de rojo/azul (con margen)
    lim = np.maximum(r, b) + 6
    g2 = np.where(g > lim, lim, g)
    out = np.dstack([r, g2, b, a * 255]).clip(0, 255).astype(np.uint8)
    return out


def pantalla(rgba, reflejo=True):
    """Pantalla/visor: la mancha negra más grande en la mitad superior, más el reflejo gris
    pegado a ella (si no, el centro queda corrido y la cara parece mirar de lado).
    Devuelve (máscara de la cara, máscara del reflejo, caja)."""
    f = rgba.astype(np.float32); h = f.shape[0]
    lum = 0.3 * f[..., 0] + 0.59 * f[..., 1] + 0.11 * f[..., 2]
    sat = f[..., :3].max(-1) - f[..., :3].min(-1)
    opaco = f[..., 3] > 200
    oscuro = (lum < 42) & opaco
    oscuro[int(h * 0.6):] = False
    oscuro = ndimage.binary_opening(oscuro, iterations=3)
    lab, n = ndimage.label(oscuro)
    tam = ndimage.sum(oscuro, lab, range(1, n + 1))
    negro = ndimage.binary_fill_holes(lab == (1 + int(np.argmax(tam))))
    # reflejo: gris poco saturado que toca la parte negra
    gris = (lum < 135) & (sat < 45) & opaco & reflejo
    gris[int(h * 0.6):] = False
    lab, n = ndimage.label(gris | negro)
    ids = np.unique(lab[negro]); ids = ids[ids > 0]
    m = ndimage.binary_closing(np.isin(lab, ids), iterations=4)
    m = ndimage.binary_fill_holes(m)
    # no crecer más allá de un margen razonable de la parte negra
    ys, xs = np.where(negro); w0 = xs.max() - xs.min()
    lim = np.zeros_like(m); lim[ys.min() - 5:ys.max() + 6, max(0, xs.min() - int(0.35 * w0)):xs.max() + int(0.35 * w0)] = True
    m &= lim
    ys, xs = np.where(m)
    suave = ndimage.gaussian_filter(ndimage.binary_erosion(m, iterations=4).astype(np.float32), 2)
    brillo = ndimage.gaussian_filter((m & ~ndimage.binary_dilation(negro, iterations=2)).astype(np.float32), 2.5)
    return suave, brillo, (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))


def main():
    geo = {}
    for p in sorted(glob.glob(os.path.join(ORIG, '*.png'))):
        nom = os.path.splitext(os.path.basename(p))[0]
        im = Image.open(p).convert('RGB')
        rgba = chroma(np.array(im))
        al = rgba[..., 3]
        ys, xs = np.where(al > 10)
        x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
        rgba = rgba[y0:y1, x0:x1]
        esc = min(1.0, ALTO / rgba.shape[0])
        out = Image.fromarray(rgba, 'RGBA')
        if esc < 1:
            out = out.resize((round(out.width * esc), round(out.height * esc)), Image.LANCZOS)
        rg = np.array(out)
        if nom != 'voz':
            m, br, caja = pantalla(rg, reflejo=nom.startswith('nova'))  # MAX: su pantalla ya es simétrica
            Image.fromarray((m * 255).astype(np.uint8), 'L').save(os.path.join(DEST, f'{nom}_cara.png'))
            Image.fromarray((br * 255).astype(np.uint8), 'L').save(os.path.join(DEST, f'{nom}_brillo.png'))
            geo[nom] = {'tam': [out.width, out.height], 'pantalla': caja}
        else:
            geo[nom] = {'tam': [out.width, out.height]}
        out.save(os.path.join(DEST, f'{nom}.png'), optimize=True)
        print(nom, out.size, geo[nom].get('pantalla'))
    json.dump(geo, open(os.path.join(DEST, 'geometria.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
