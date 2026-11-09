"""Quita el fondo verde de las imágenes de MAX y NOVA corriendo de espaldas (Google Flow) y deja PNG recortados.
Uso: python scripts/recortar_corredores.py   (lee assets/corredores/*_raw.jpg —las imágenes de Flow—, escribe <nombre>.png; los _raw no se guardan en el repo)
"""
import glob, os
import numpy as np
from PIL import Image, ImageFilter

D = os.path.join(os.path.dirname(__file__), '..', 'assets', 'corredores')
for f in sorted(glob.glob(os.path.join(D, '*_raw.jpg'))):
    a = np.asarray(Image.open(f).convert('RGB')).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    verde = g - np.maximum(r, b)
    alfa = 1 - np.clip((verde - 25) / 55, 0, 1)
    a[..., 1] = np.minimum(g, np.maximum(r, b) + 6)          # quita el reflejo verde de los bordes
    m = Image.fromarray((alfa * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1))
    im = Image.fromarray(a.clip(0, 255).astype(np.uint8)).convert('RGBA'); im.putalpha(m)
    im = im.crop(im.getchannel('A').point(lambda v: 255 if v > 40 else 0).getbbox())
    im = im.resize((round(im.width * 900 / im.height), 900), Image.LANCZOS)
    out = f.replace('_raw.jpg', '.png'); im.save(out); print(out, im.size)
