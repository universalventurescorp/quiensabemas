"""Banco central de preguntas: garantiza que ninguna pregunta se repita en todo el canal.
Uso:
  python scripts/banco.py revisar contenido/cola/ep012.json   # falla si hay repetidas (contra el banco y dentro del archivo)
  python scripts/banco.py registrar contenido/cola/ep012.json # las agrega al banco (al producir el episodio)
  python scripts/banco.py resumen                              # cuántas hay, por tema
El banco vive en banco/preguntas.jsonl (una línea por pregunta: clave normalizada, texto, respuesta, episodio).
"""
import difflib, json, os, re, sys, unicodedata

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BANCO = os.path.join(RAIZ, 'banco', 'preguntas.jsonl')
VACIAS = set('el la los las un una unos unas de del al a en y o que cual cuál cuales es son fue se su sus por para con como este esta estos estas '
             'eso esa ese mas más muy lo le les qué quien quién donde dónde cuando cuándo cuanto cuánto cuantos cuántos'.split())


def norm(t):
    t = unicodedata.normalize('NFD', t.lower())
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    t = re.sub(r'[^a-z0-9 ]+', ' ', t)
    return ' '.join(w for w in t.split() if w not in VACIAS)


def clave(q):
    return norm(q['p']) + ' => ' + norm(q['o'][q['c']])


def cargar():
    if not os.path.exists(BANCO): return []
    return [json.loads(l) for l in open(BANCO, encoding='utf-8') if l.strip()]


def parecidas(a, b):
    """Misma pregunta con otras palabras: texto muy parecido y misma respuesta, o idéntico."""
    pa, ra = a.split(' => '); pb, rb = b.split(' => ')
    if pa == pb: return True
    if ra != rb: return False
    r = difflib.SequenceMatcher(None, pa, pb).ratio()
    if r >= 0.72: return True
    sa, sb = set(pa.split()), set(pb.split())
    return len(sa & sb) / max(1, len(sa | sb)) >= 0.6


def revisar(path):
    ep = json.load(open(path, encoding='utf-8'))
    banco = cargar(); previas = [b['k'] for b in banco]
    # índice por respuesta para no comparar todo contra todo
    por_resp = {}
    for b in banco: por_resp.setdefault(b['k'].split(' => ')[1], []).append(b)
    problemas, vistas = [], []
    for q in ep['preguntas']:
        k = clave(q); r = k.split(' => ')[1]; p = k.split(' => ')[0]
        for b in por_resp.get(r, []) + [b for b in banco if b['k'].split(' => ')[0] == p]:
            if parecidas(k, b['k']):
                problemas.append(f"P{q['n']}: «{q['p']}» repite una del banco ({b['ep']}): «{b['p']}»"); break
        for n2, k2 in vistas:
            if parecidas(k, k2):
                problemas.append(f"P{q['n']}: repite la P{n2} de este mismo episodio"); break
        vistas.append((q['n'], k))
        if len(q['o']) != 4 or not (0 <= q['c'] < 4): problemas.append(f"P{q['n']}: debe tener 4 opciones y c entre 0 y 3")
        if len(set(norm(o) for o in q['o'])) < 4: problemas.append(f"P{q['n']}: opciones repetidas")
    print(f"{path}: {len(ep['preguntas'])} preguntas · banco con {len(previas)} · problemas: {len(problemas)}")
    for x in problemas: print('  -', x)
    return not problemas


def registrar(path):
    ep = json.load(open(path, encoding='utf-8')); eid = ep.get('id', os.path.basename(path))
    ya = {b['k'] for b in cargar()}
    n = 0
    with open(BANCO, 'a', encoding='utf-8') as f:
        for q in ep['preguntas']:
            k = clave(q)
            if k in ya: continue
            f.write(json.dumps({'k': k, 'p': q['p'], 'r': q['o'][q['c']], 'tema': q.get('tema', ''), 'ep': eid}, ensure_ascii=False) + '\n'); n += 1
    print(f'Registradas {n} preguntas de {eid}')


if __name__ == '__main__':
    acc = sys.argv[1]
    if acc == 'revisar': sys.exit(0 if all(revisar(p) for p in sys.argv[2:]) else 1)
    elif acc == 'registrar': [registrar(p) for p in sys.argv[2:]]
    elif acc == 'resumen':
        b = cargar(); temas = {}
        for x in b: temas[x.get('tema') or '—'] = temas.get(x.get('tema') or '—', 0) + 1
        print(len(b), 'preguntas'); [print(f'  {t}: {n}') for t, n in sorted(temas.items(), key=lambda x: -x[1])]
