"""Aplica la revisión de las fotos de las alternativas (la hace Claude mirando trabajo/revision/p###.jpg).
Uso: python scripts/revisar_fotos.py trabajo/episodio.json trabajo/revision
Lee trabajo/revision/veredicto.json = {"12": {"ok": true}, "15": {"ok": false, "motivo": "..."}, ...}
- Pregunta rechazada (o sin veredicto): se queda con alternativas de solo texto (todo o nada).
- Las fotos de la miniatura que caen con su pregunta se descartan (la miniatura elige otras).
Si no hay veredicto.json (la revisión no corrió), por seguridad se quitan TODAS las fotos de alternativas.
"""
import json, os, sys


def main(ep_path, rev):
    ep = json.load(open(ep_path, encoding='utf-8'))
    # veredicto.json o varios veredicto_###.json (la revisión se hace por partes cuando hay muchas preguntas)
    import glob
    ver = {}
    for vf in sorted(glob.glob(os.path.join(rev, 'veredicto*.json'))):
        try: ver.update(json.load(open(vf, encoding='utf-8'))); print('veredicto:', os.path.basename(vf))
        except Exception as e: print('::warning::veredicto ilegible', vf, e)
    if not ver: print('::warning::Sin veredicto de la revisión de fotos: el episodio sale con alternativas de texto')
    ok_n = malas = 0
    for q in ep['preguntas']:
        if not q.get('o_img'): continue
        v = ver.get(str(q['n'])) or {}
        if v.get('ok') is True: ok_n += 1; continue
        malas += 1; print(f"P{q['n']}: fotos rechazadas — {v.get('motivo', 'sin veredicto')}")
        q.pop('o_img', None); q.pop('o_score', None)
    vivas = {f for q in ep['preguntas'] for f in q.get('o_img', [])}
    if ep.get('miniatura_fotos'):
        ep['miniatura_fotos'] = [f for f in ep['miniatura_fotos'] if f in vivas]
        if not ep['miniatura_fotos']: ep.pop('miniatura_fotos')
    json.dump(ep, open(ep_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'Revisión de fotos: {ok_n} preguntas aprobadas, {malas} quedan con texto')


if __name__ == '__main__':
    main(*sys.argv[1:])
