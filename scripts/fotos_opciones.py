"""Fotos reales para las alternativas (PRUEBA 6-nov-2026).
Para cada alternativa busca 3-5 candidatas (Pixabay y/o Wikimedia Commons, o bandera), y un modelo CLIP
(sin GPU) elige la que de verdad se parece a la palabra. Si en una pregunta alguna alternativa no pasa el control,
esa pregunta se queda con alternativas de solo texto (todo o nada, para que la pantalla sea pareja).
Uso: python scripts/fotos_opciones.py trabajo/episodio.json contenido/fotos_opciones/ep007.json trabajo/opciones [--hoja hoja.jpg]
Escribe q['o_img'] en el episodio, los créditos en trabajo/img/creditos.json y q['o_score'] para la miniatura.
"""
import io, json, os, re, subprocess, sys, time, unicodedata, urllib.parse, urllib.request
from PIL import Image, ImageDraw

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
UA = {"User-Agent": "QuienSabeMasBot/0.1 (https://github.com/universalventurescorp/quiensabemas)"}
COMMONS = "https://commons.wikimedia.org/w/api.php"
OK_LIC = re.compile(r"^(public domain|pd|cc0|cc by(-sa)? ?[0-9.]*|cc-by(-sa)?-[0-9.]+)", re.I)
UMBRAL = 0.21          # parecido mínimo foto↔palabra (CLIP ViT-B/32)
MARGEN = 0.005         # la foto tiene que parecerse más a SU alternativa que a las otras de la misma pregunta


def get(url, tries=3):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r: return r.read()
        except Exception:
            if k == tries - 1: raise
            time.sleep(2 + 3 * k)


def plano(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')


def strip(html): return re.sub(r"<[^>]+>", "", html or "").strip()


def pixabay(q, n=5):
    key = os.environ.get('PIXABAY_API_KEY')
    if not key: return []
    p = dict(key=key, q=q, image_type='all', safesearch='true', per_page=max(3, n), lang='en')
    d = json.loads(get('https://pixabay.com/api/?' + urllib.parse.urlencode(p)))
    out = []
    for h in d.get('hits', [])[:n]:
        out.append({'url': h['largeImageURL'], 'pagina': h['pageURL'], 'licencia': 'Pixabay Content License',
                    'autor': h.get('user', ''), 'fuente': 'Pixabay'})
    time.sleep(0.8)
    return out


def commons(q, n=5, must=None, no=()):
    p = {"action": "query", "format": "json", "generator": "search", "gsrsearch": f"filetype:bitmap {q}",
         "gsrnamespace": 6, "gsrlimit": 30, "prop": "imageinfo", "iiprop": "url|extmetadata|size", "iiurlwidth": 1000}
    d = json.loads(get(COMMONS + "?" + urllib.parse.urlencode(p)))
    pages = sorted(d.get("query", {}).get("pages", {}).values(), key=lambda x: x.get("index", 99))
    out = []
    for pg in pages:
        ii = (pg.get("imageinfo") or [{}])[0]; md = ii.get("extmetadata", {})
        lic = strip(md.get("LicenseShortName", {}).get("value", ""))
        w, h = ii.get("width", 0), ii.get("height", 0)
        if not OK_LIC.match(lic) or min(w, h) < 380: continue
        if must and plano(must) not in plano(pg['title']): continue
        if any(plano(x) in plano(pg['title']) for x in no): continue
        out.append({'url': ii.get('thumburl') or ii['url'], 'pagina': ii.get('descriptionurl'), 'licencia': lic,
                    'autor': strip(md.get('Artist', {}).get('value', ''))[:120], 'fuente': 'Wikimedia Commons',
                    'titulo': pg['title']})
        if len(out) >= n: break
    time.sleep(0.5)
    return out


def bandera(code, dst):
    svg = f'/tmp/{code}.svg'
    open(svg, 'wb').write(get(f'https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/{code}.svg'))
    subprocess.run(['rsvg-convert', '-w', '800', svg, '-o', dst], check=True)


class Clip:
    def __init__(s):
        import torch, open_clip
        s.torch = torch
        s.m, _, s.pre = open_clip.create_model_and_transforms('ViT-B-32', pretrained='laion2b_s34b_b79k')
        s.tok = open_clip.get_tokenizer('ViT-B-32'); s.m.eval()

    def texto(s, frases):
        with s.torch.no_grad():
            t = s.m.encode_text(s.tok(frases)); return t / t.norm(dim=-1, keepdim=True)

    def imagen(s, ims):
        with s.torch.no_grad():
            x = s.torch.stack([s.pre(i) for i in ims]); v = s.m.encode_image(x); return v / v.norm(dim=-1, keepdim=True)


def candidatas(c):
    if c.get('src') == 'px':
        r = pixabay(c['q']) or commons(c['q'], must=c.get('must'))
    else:
        r = commons(c['q'], must=c.get('must'), no=c.get('not', ())) or ([] if c.get('must') else pixabay(c['q']))
    ims = []
    for x in r:
        try:
            im = Image.open(io.BytesIO(get(x['url']))).convert('RGB'); im.thumbnail((900, 900)); ims.append((im, x))
        except Exception as e:
            print('  descarga falló', x['url'][:80], e)
    return ims


def main():
    ep_path, cons_path, dst = sys.argv[1:4]
    hoja = sys.argv[sys.argv.index('--hoja') + 1] if '--hoja' in sys.argv else None
    ep = json.load(open(ep_path, encoding='utf-8')); cons = json.load(open(cons_path, encoding='utf-8'))
    os.makedirs(dst, exist_ok=True)
    cred_f = os.path.join(os.path.dirname(os.path.abspath(ep_path)), 'img', 'creditos.json')
    os.makedirs(os.path.dirname(cred_f), exist_ok=True)
    creditos = json.load(open(cred_f)) if os.path.exists(cred_f) else {}
    clip = Clip(); hojas = []; ok_n = 0
    for q in ep['preguntas']:
        cs = cons.get(str(q['n']))
        if not cs or (q.get('img_modo') == 'pregunta'): continue
        eleg = []
        if all('flag' in c for c in cs):
            for i, c in enumerate(cs):
                f = os.path.join(dst, f"o{q['n']:03d}_{i}.png"); bandera(c['flag'], f); eleg.append((f, None, 1.0))
        else:
            prompts = [('a portrait photo of ' if c.get('must') else 'a photo of ') + c['q'] for c in cs]
            T = clip.texto(prompts)
            for i, c in enumerate(cs):
                ims = candidatas(c)
                if not ims: print(f"P{q['n']} «{q['o'][i]}»: sin candidatas"); eleg = None; break
                S = (clip.imagen([im for im, _ in ims]) @ T.T).numpy()   # candidatas × alternativas
                best, bs = None, -1
                for k, (im, meta) in enumerate(ims):
                    own = float(S[k, i]); otras = max([float(S[k, j]) for j in range(len(cs)) if j != i] or [0])
                    vale = own >= UMBRAL and (own >= otras + MARGEN or c.get('must'))
                    if vale and own > bs: best, bs = (im, meta), own
                if not best:
                    print(f"P{q['n']} «{q['o'][i]}»: ninguna foto pasó ({', '.join(f'{float(S[k, i]):.3f}' for k in range(len(ims)))})")
                    eleg = None; break
                f = os.path.join(dst, f"o{q['n']:03d}_{i}.jpg"); best[0].save(f, quality=90)
                eleg.append((f, best[1], bs))
        if not eleg: continue
        q['o_img'] = [os.path.relpath(f, RAIZ) for f, _, _ in eleg]; q['o_score'] = [round(sc, 3) for _, _, sc in eleg]
        for f, meta, _ in eleg:
            if meta: creditos[os.path.basename(f)] = meta
        ok_n += 1; print(f"P{q['n']}: OK  " + ' · '.join(f"{o} ({sc:.2f})" for o, (_, _, sc) in zip(q['o'], eleg)))
        hojas.append((q, [f for f, _, _ in eleg]))
    json.dump(ep, open(ep_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(creditos, open(cred_f, 'w'), ensure_ascii=False, indent=1)
    print(f'Listo: {ok_n} preguntas con fotos en las alternativas')
    if hoja and hojas:   # hoja de contacto para revisar
        cw, ch = 220, 150; img = Image.new('RGB', (cw * 4 + 260, ch * len(hojas)), (20, 14, 50)); d = ImageDraw.Draw(img)
        for r, (q, fs) in enumerate(hojas):
            d.text((8, r * ch + 8), f"P{q['n']}", fill=(255, 200, 40))
            for i, f in enumerate(fs):
                t = Image.open(f).convert('RGB'); t.thumbnail((cw - 8, ch - 30)); img.paste(t, (260 + i * cw, r * ch + 4))
                d.text((260 + i * cw, r * ch + ch - 22), q['o'][i][:28], fill=(255, 255, 255))
            d.text((8, r * ch + 30), q['p'][:34], fill=(200, 200, 220))
        img.save(hoja, quality=80)


if __name__ == '__main__':
    main()
