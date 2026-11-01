"""Crea el archivo público del episodio para la web de salas: web/episodios/<SALA>.json
Uso: python scripts/exportar_episodio.py contenido/maqueta_tv.json salida/maqueta.tiempos.json
La respuesta correcta no va en claro: cada pregunta lleva h = fnv1a("SALA|n|índice correcto"),
y el celular compara el hash de la opción elegida (basta para que no se vea a simple vista).
"""
import json, os, sys


def fnv(s):
    h = 0x811c9dc5
    for ch in s:
        h ^= ord(ch); h = (h * 0x01000193) & 0xffffffff
    return f'{h:08x}'


def main(contenido, tiempos, destino='web/episodios'):
    meta = json.load(open(contenido)); t = json.load(open(tiempos))
    sala = meta['codigo_sala'].upper()
    ep = {
        'sala': sala, 'titulo': meta['titulo'], 'total': meta.get('total_anunciado', len(meta['preguntas'])),
        'tiempos': t['tiempos'],
        'preguntas': [{'n': q['n'], 'p': q['p'], 'o': q['o'], 'h': fnv(f"{sala}|{q['n']}|{q['c']}")} for q in meta['preguntas']],
    }
    os.makedirs(destino, exist_ok=True)
    out = os.path.join(destino, f'{sala}.json')
    json.dump(ep, open(out, 'w'), ensure_ascii=False, separators=(',', ':'))
    print('OK', out)
    return out


if __name__ == '__main__':
    main(*sys.argv[1:])
