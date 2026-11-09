"""Formato rápido «¿A o B?»: deja trabajo/episodio.json listo para buscar fotos y, con --recortar, quita las
preguntas que quedaron sin fotos (todo debe ser visual), se queda con max_preguntas y renumera.
Uso: python scripts/preparar_rapido.py contenido/rapido/muestra.json trabajo            (copia)
     python scripts/preparar_rapido.py --recortar trabajo/episodio.json                  (después de la revisión)
"""
import json, os, shutil, sys


def salida_gh(**kv):
    f = os.environ.get('GITHUB_OUTPUT')
    for k, v in kv.items():
        print(f'{k}={v}')
        if f: open(f, 'a').write(f'{k}={v}\n')


def main():
    if sys.argv[1] == '--recortar':
        p = sys.argv[2]; ep = json.load(open(p, encoding='utf-8'))
        vivas = [q for q in ep['preguntas'] if q.get('o_img')]
        fuera = [q['p'] + ' → ' + q['o'][q['c']] for q in ep['preguntas'] if not q.get('o_img')]
        if fuera: print('Sin fotos (se descartan):', *fuera, sep='\n  ')
        vivas = vivas[:ep.get('max_preguntas', len(vivas))]
        for k, q in enumerate(vivas, 1): q['n'] = k
        ep['preguntas'] = vivas
        json.dump(ep, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f"Quedan {len(vivas)} preguntas con fotos")
        if len(vivas) < ep.get('minimo', 8 if ep.get('muestra') else 120): sys.exit('Muy pocas preguntas con fotos')
        return
    src, dst = sys.argv[1:3]
    os.makedirs(dst, exist_ok=True); shutil.copy(src, os.path.join(dst, 'episodio.json'))
    ep = json.load(open(src, encoding='utf-8')); salida_gh(id=ep['id'])


if __name__ == '__main__':
    main()
