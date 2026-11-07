"""Elige el próximo episodio listo de la cola y deja todo preparado para producirlo.
Uso: python scripts/preparar_episodio.py [--id ep012] [--salida trabajo] [--rehacer]
- Toma el primer contenido/cola/*.json con "estado": "listo" (o el --id indicado) que no esté en publicados/.
- Revisa repetidas contra el banco (si hay, se detiene).
- Busca una foto libre por pregunta (Wikimedia Commons) o usa la bandera indicada.
- Trae el Salón de la fama del episodio anterior desde la web (si ya está en línea).
Escribe trabajo/episodio.json (contenido resuelto) y deja en GITHUB_OUTPUT: id, formato.
"""
import argparse, glob, json, os, subprocess, sys, urllib.request

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))
import buscar_imagenes as bi
import banco


def salida_gh(**kv):
    f = os.environ.get('GITHUB_OUTPUT')
    for k, v in kv.items():
        print(f'{k}={v}')
        if f: open(f, 'a').write(f'{k}={v}\n')


def fama_anterior():
    pubs = sorted(glob.glob(os.path.join(RAIZ, 'publicados', '*.json')))
    if not pubs: return None, []
    prev = json.load(open(pubs[-1]))
    try:
        r = json.loads(urllib.request.urlopen(f"https://quiensabemastv.pages.dev/api/fama?sala={prev['sala']}", timeout=20).read())
        return prev.get('titulo', ''), [x['apodo'] for x in r.get('top', [])][:5]
    except Exception as e:
        print('Salón de la fama no disponible:', e); return prev.get('titulo', ''), []


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--id'); ap.add_argument('--salida', default='trabajo')
    ap.add_argument('--rehacer', action='store_true', help='permite volver a producir un episodio ya subido (con --id)')
    a = ap.parse_args()
    hechos = {os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(RAIZ, 'publicados', '*.json'))}
    cand = []
    for p in sorted(glob.glob(os.path.join(RAIZ, 'contenido', 'cola', '*.json'))):
        ep = json.load(open(p, encoding='utf-8'))
        if ep['id'] in hechos and not (a.rehacer and a.id): continue
        if a.id and ep['id'] != a.id: continue
        if not a.id and ep.get('estado') != 'listo': continue
        cand.append((p, ep))
    if not cand:
        print('No hay episodios listos en la cola.'); salida_gh(id='', formato=''); return
    path, ep = cand[0]
    if not banco.revisar(path):
        sys.exit('El episodio tiene preguntas repetidas: corrígelo antes de producir.')
    os.makedirs(a.salida, exist_ok=True)
    img_dir = os.path.join(a.salida, 'img'); os.makedirs(img_dir, exist_ok=True)
    creditos = {}
    for q in ep['preguntas']:
        if q.get('bandera'):
            b = os.path.join(RAIZ, 'assets', 'banderas', f"{q['bandera']}.png")
            if os.path.exists(b): q['img'] = os.path.relpath(b, RAIZ); q['img_fondo'] = 'blanco'; q.setdefault('img_modo', 'pregunta')
            continue
        if not q.get('img_q'): continue
        try:
            res = bi.buscar(q['img_q'], 1)
        except Exception as e:
            print('sin foto', q['n'], e); res = []
        if not res:
            q.pop('img_modo', None); print(f"P{q['n']}: sin foto libre para «{q['img_q']}»"); continue
        r = res[0]; ext = os.path.splitext(r['url'].split('?')[0])[1].lower() or '.jpg'
        f = f"q{q['n']:03d}{ext}"
        open(os.path.join(img_dir, f), 'wb').write(bi.get(r['url']))
        q['img'] = os.path.relpath(os.path.join(img_dir, f), RAIZ); q.setdefault('img_modo', 'revela')
        creditos[f] = r
    json.dump(creditos, open(os.path.join(img_dir, 'creditos.json'), 'w'), ensure_ascii=False, indent=1)
    de, nombres = fama_anterior()
    if nombres: ep['fama'] = nombres; ep['fama_de'] = de
    json.dump(ep, open(os.path.join(a.salida, 'episodio.json'), 'w'), ensure_ascii=False, indent=1)
    print(f"Listo: {ep['id']} · {len(ep['preguntas'])} preguntas · {len(creditos)} fotos")
    salida_gh(id=ep['id'], formato=ep.get('formato', 'normal'))


if __name__ == '__main__':
    main()
