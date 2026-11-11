"""Clip de Flow/Veo sobre verde → cuadros PNG con transparencia que se repiten en bucle (11-nov-2026).
Uso: python scripts/clip_verde.py clip.mp4 assets/navidad/anim/<nombre> [--alto 640] [--min 1.0] [--max 4.0]
Busca dentro del clip el tramo que mejor empalma consigo mismo (cuadro final ≈ cuadro inicial), recorta el verde,
recorta todos los cuadros con la MISMA caja (para que no tiemble) y los guarda como 000.png, 001.png…
"""
import argparse, os, subprocess
import numpy as np
from PIL import Image, ImageFilter


def alfa_verde(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    verde = g - np.maximum(r, b)
    al = 1 - np.clip((verde - 25) / 55, 0, 1)
    a[..., 1] = np.minimum(g, np.maximum(r, b) + 6)   # quita el reflejo verde de los bordes
    return al


def leer(clip):
    w, h = map(int, subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                                    '-of', 'csv=p=0', clip], capture_output=True, text=True).stdout.strip().split(','))
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', clip, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('clip'); ap.add_argument('out')
    ap.add_argument('--alto', type=int, default=640); ap.add_argument('--fps', type=float, default=24)
    ap.add_argument('--min', type=float, default=1.0); ap.add_argument('--max', type=float, default=4.0)
    ap.add_argument('--saltar', type=float, default=0.3, help='segundos del inicio que no se usan')
    a = ap.parse_args()
    F = leer(a.clip); n = len(F)
    # el mejor bucle: i..j con F[j] parecido a F[i]
    pq = F[:, ::8, ::8].astype(np.float32)
    s0 = int(a.saltar * a.fps); best = None
    for i in range(s0, n):
        for j in range(i + int(a.min * a.fps), min(n, i + int(a.max * a.fps) + 1)):
            dif = float(np.abs(pq[i] - pq[j]).mean())
            if best is None or dif < best[0]: best = (dif, i, j)
    dif, i, j = best
    print(f'Bucle: cuadros {i}..{j} ({(j - i) / a.fps:.2f} s), diferencia {dif:.2f}')
    sel = F[i:j]
    alfas = []; rgbs = []
    for f in sel:
        x = f.astype(np.float32); al = alfa_verde(x); alfas.append(al); rgbs.append(x)
    union = np.max(np.stack(alfas), 0) > 0.5
    ys, xs = np.nonzero(union); y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    os.makedirs(a.out, exist_ok=True)
    for f in os.listdir(a.out):
        if f.endswith('.png'): os.remove(os.path.join(a.out, f))
    for k, (x, al) in enumerate(zip(rgbs, alfas)):
        m = Image.fromarray((al * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
        im = Image.fromarray(x.clip(0, 255).astype(np.uint8)).convert('RGBA'); im.putalpha(m)
        im = im.crop((x0, y0, x1, y1))
        im = im.resize((round(im.width * a.alto / im.height), a.alto), Image.LANCZOS)
        im.save(os.path.join(a.out, f'{k:03d}.png'), optimize=True)
    print(f'{len(sel)} cuadros → {a.out} ({im.size[0]}x{im.size[1]})')


if __name__ == '__main__':
    main()
