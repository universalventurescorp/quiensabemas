"""Personajes originales del canal, dibujados por código (sin derechos de terceros).
Cada personaje tiene 3 estados de boca (0 cerrada, 1 media, 2 abierta) y parpadeo.
"""
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFilter

S = 2  # dibujar al doble y reducir = bordes suaves


def _ojo(d, cx, cy, r, cerrado, iris=(60, 35, 20)):
    if cerrado:
        d.arc((cx - r, cy - r * 0.6, cx + r, cy + r * 0.9), 200, 340, fill=(40, 25, 20), width=int(5 * S))
        return
    d.ellipse((cx - r, cy - r * 1.15, cx + r, cy + r * 1.15), fill=(255, 255, 255))
    d.ellipse((cx - r * 0.62, cy - r * 0.62, cx + r * 0.62, cy + r * 0.62), fill=iris)
    d.ellipse((cx - r * 0.3, cy - r * 0.3, cx + r * 0.3, cy + r * 0.3), fill=(15, 10, 10))
    d.ellipse((cx + r * 0.05, cy - r * 0.45, cx + r * 0.38, cy - r * 0.12), fill=(255, 255, 255))


def _boca(d, cx, cy, w, estado, labio=(150, 50, 60)):
    if estado == 0:
        d.arc((cx - w, cy - w * 0.7, cx + w, cy + w * 0.55), 20, 160, fill=labio, width=int(7 * S))
        return
    h = w * (0.45 if estado == 1 else 0.85)
    d.chord((cx - w, cy - h * 0.35, cx + w, cy + h), 0, 180, fill=(90, 20, 35))
    d.rectangle((cx - w * 0.75, cy - h * 0.35, cx + w * 0.75, cy - h * 0.35 + h * 0.22), fill=(255, 255, 255))
    if estado == 2:
        d.ellipse((cx - w * 0.45, cy + h * 0.35, cx + w * 0.45, cy + h * 0.95), fill=(220, 90, 100))


def _max(estado, parpadeo):
    W, H = 520 * S, 600 * S
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    piel, piel_s = (196, 140, 100), (172, 118, 82)
    # cuerpo: saco morado, camisa blanca, corbatín dorado
    d.rounded_rectangle((60 * S, 420 * S, 460 * S, 640 * S), 120 * S, fill=(92, 52, 170))
    d.polygon([(200 * S, 420 * S), (320 * S, 420 * S), (260 * S, 540 * S)], fill=(250, 250, 250))
    d.polygon([(200 * S, 420 * S), (150 * S, 440 * S), (248 * S, 560 * S)], fill=(70, 38, 140))
    d.polygon([(320 * S, 420 * S), (370 * S, 440 * S), (272 * S, 560 * S)], fill=(70, 38, 140))
    d.polygon([(225 * S, 440 * S), (260 * S, 458 * S), (225 * S, 476 * S)], fill=(255, 196, 40))
    d.polygon([(295 * S, 440 * S), (260 * S, 458 * S), (295 * S, 476 * S)], fill=(255, 196, 40))
    d.ellipse((248 * S, 448 * S, 272 * S, 468 * S), fill=(230, 170, 20))
    # cuello y cabeza
    d.rectangle((222 * S, 360 * S, 298 * S, 430 * S), fill=piel_s)
    d.ellipse((120 * S, 90 * S, 400 * S, 400 * S), fill=piel)
    d.ellipse((105 * S, 225 * S, 150 * S, 290 * S), fill=piel); d.ellipse((370 * S, 225 * S, 415 * S, 290 * S), fill=piel)
    # pelo con jopo
    d.chord((115 * S, 70 * S, 405 * S, 300 * S), 180, 360, fill=(35, 22, 18))
    d.ellipse((150 * S, 40 * S, 330 * S, 150 * S), fill=(35, 22, 18))
    d.rectangle((122 * S, 180 * S, 140 * S, 222 * S), fill=(35, 22, 18)); d.rectangle((380 * S, 180 * S, 398 * S, 222 * S), fill=(35, 22, 18))
    # cejas
    d.line((175 * S, 200 * S, 228 * S, 192 * S), fill=(35, 22, 18), width=int(11 * S))
    d.line((292 * S, 192 * S, 345 * S, 200 * S), fill=(35, 22, 18), width=int(11 * S))
    _ojo(d, 205 * S, 240 * S, 24 * S, parpadeo); _ojo(d, 315 * S, 240 * S, 24 * S, parpadeo)
    d.arc((242 * S, 255 * S, 278 * S, 300 * S), 300, 60, fill=piel_s, width=int(6 * S))
    d.ellipse((165 * S, 285 * S, 200 * S, 305 * S), fill=(214, 128, 105)); d.ellipse((320 * S, 285 * S, 355 * S, 305 * S), fill=(214, 128, 105))
    _boca(d, 260 * S, 330 * S, 42 * S, estado)
    return im


def _sofi(estado, parpadeo):
    W, H = 520 * S, 600 * S
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    piel, piel_s = (226, 178, 140), (205, 155, 118)
    pelo = (70, 32, 22)
    # pelo largo detrás
    d.rounded_rectangle((95 * S, 140 * S, 425 * S, 520 * S), 140 * S, fill=pelo)
    # cuerpo: blusa coral, collar
    d.rounded_rectangle((70 * S, 430 * S, 450 * S, 640 * S), 120 * S, fill=(240, 96, 90))
    d.chord((200 * S, 395 * S, 320 * S, 470 * S), 0, 180, fill=piel_s)
    for i, x in enumerate(range(205, 320, 16)):
        d.ellipse(((x - 6) * S, (448 + abs(262 - x) * -0.25 + 18) * S, (x + 6) * S, (460 + abs(262 - x) * -0.25 + 18) * S), fill=(255, 235, 170))
    d.rectangle((225 * S, 360 * S, 295 * S, 440 * S), fill=piel_s)
    d.ellipse((128 * S, 95 * S, 392 * S, 400 * S), fill=piel)
    # flequillo
    d.chord((118 * S, 75 * S, 402 * S, 290 * S), 180, 360, fill=pelo)
    d.pieslice((110 * S, 60 * S, 300 * S, 260 * S), 180, 300, fill=pelo)
    # aretes
    d.ellipse((120 * S, 300 * S, 140 * S, 320 * S), fill=(255, 200, 40)); d.ellipse((380 * S, 300 * S, 400 * S, 320 * S), fill=(255, 200, 40))
    d.arc((178 * S, 188 * S, 232 * S, 212 * S), 200, 340, fill=pelo, width=int(8 * S))
    d.arc((288 * S, 188 * S, 342 * S, 212 * S), 200, 340, fill=pelo, width=int(8 * S))
    _ojo(d, 205 * S, 245 * S, 24 * S, parpadeo, (40, 90, 60)); _ojo(d, 315 * S, 245 * S, 24 * S, parpadeo, (40, 90, 60))
    d.arc((245 * S, 262 * S, 275 * S, 300 * S), 300, 60, fill=piel_s, width=int(6 * S))
    d.ellipse((165 * S, 290 * S, 200 * S, 310 * S), fill=(235, 130, 130)); d.ellipse((320 * S, 290 * S, 355 * S, 310 * S), fill=(235, 130, 130))
    _boca(d, 260 * S, 335 * S, 38 * S, estado, (200, 60, 80))
    return im


def _mic(estado, parpadeo):
    W, H = 520 * S, 600 * S
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    oro, oro2 = (255, 200, 40), (215, 150, 20)
    for k in range(estado + 1):  # ondas de sonido
        r = (180 + k * 55) * S
        for sx in (-1, 1):
            a0, a1 = (150, 210) if sx < 0 else (-30, 30)
            d.arc((260 * S - r, 220 * S - r, 260 * S + r, 220 * S + r), a0, a1, fill=(255, 220, 120), width=int(12 * S))
    d.rounded_rectangle((180 * S, 60 * S, 340 * S, 330 * S), 80 * S, fill=oro)
    for y in range(90, 320, 26):
        d.line((195 * S, y * S, 325 * S, y * S), fill=oro2, width=int(5 * S))
    d.rounded_rectangle((170 * S, 300 * S, 350 * S, 340 * S), 18 * S, fill=(60, 40, 90))
    d.arc((140 * S, 180 * S, 380 * S, 420 * S), 0, 180, fill=(200, 200, 215), width=int(16 * S))
    d.rectangle((250 * S, 418 * S, 270 * S, 520 * S), fill=(200, 200, 215))
    d.rounded_rectangle((170 * S, 515 * S, 350 * S, 555 * S), 20 * S, fill=(60, 40, 90))
    return im


DIBUJOS = {'presentador': _max, 'copresentadora': _sofi, 'anunciador': _mic}
NOMBRES = {'presentador': 'MAX', 'copresentadora': 'SOFI', 'anunciador': 'LA VOZ'}


@lru_cache(maxsize=64)
def sprite(quien, estado=0, parpadeo=False, alto=420):
    im = DIBUJOS[quien](estado, parpadeo)
    w = int(im.width * alto / im.height)
    return im.resize((w, alto), Image.LANCZOS)
