"""Miniatura 1280×720 del episodio: MAX y NOVA, el tema en grande y el reto.
Uso: python pipeline/miniatura.py trabajo/episodio.json trabajo/miniatura.jpg
"""
import json, os, sys
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(__file__))
from personajes import sprite
import tv

W, H = 1280, 720


def main(ep_path, out):
    ep = json.load(open(ep_path, encoding='utf-8'))
    bg = tv.escenario().resize((W, H)).convert('RGBA')
    d = ImageDraw.Draw(bg)
    reto = ep.get('reto_miniatura') or f"¿Llegas a la {len(ep['preguntas'])}?"
    tema = ep.get('tema_miniatura') or ep['titulo']
    f, ls, sz = tv.fit(d, tema.upper(), 'Bold', 560, 300, 104, 44, sp=1.05)
    tv.lines(d, ls, f, sz, 0, 300, (255, 255, 255), anchor='lm', x=60, sp=1.05)
    d.rounded_rectangle((60, 520, 60 + d.textlength(reto, font=tv.font('Bold', 64)) + 60, 620), 30, fill=(255, 200, 40))
    d.text((90, 570), reto, font=tv.font('Bold', 64), fill=(26, 18, 64), anchor='lm')
    d.text((60, 70), '¿Quién Sabe Más?', font=tv.font('Bold', 52), fill=(255, 200, 40), anchor='lm')
    if ep.get('formato') == 'maraton':
        d.rounded_rectangle((60, 120, 470, 180), 20, fill=(231, 76, 60)); d.text((265, 150), 'MARATÓN 3 HORAS', font=tv.font('Bold', 38), fill=(255, 255, 255), anchor='mm')
    max_, (cx, cy) = sprite('presentador', 'celebra', 3, False)
    nova, (nx, ny) = sprite('copresentadora', 'sorpresa', 0, False)
    k = 1.25
    max_ = max_.resize((int(max_.width * k), int(max_.height * k)))
    bg.alpha_composite(nova, (W - nova.width - 330, H - nova.height + 140))
    bg.alpha_composite(max_, (W - max_.width + 110, H - max_.height + 260))
    bg.convert('RGB').save(out, quality=90)
    print('OK', out)


if __name__ == '__main__':
    main(*sys.argv[1:])
