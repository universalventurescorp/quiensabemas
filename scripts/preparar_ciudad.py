#!/usr/bin/env python3
"""Arma el guion de la muestra «¿A o B? en la ciudad» a partir de un episodio rápido ya preparado (con fotos).
Toma las primeras N preguntas con fotos y les asigna los momentos de la pista.
Uso: python3 scripts/preparar_ciudad.py trabajo/episodio.json trabajo/ciudad.json [--n 10]
"""
import argparse, json

# Guion de la muestra (índices 0..9): cada pregunta trae algo nuevo.
EVENTOS = {
    '0': 'colinas',          # avenida con subidas y bajadas
    '1': 'tunel',            # túnel de luces de neón
    '2': 'bajada',           # cima y caída enorme EN la cuenta: las puertas caen con ellos
    '3': 'curvas',           # curvas cerradas
    'antes_5': 'puente',     # se acaba la carretera → saltan → caen → la nave los rescata (zona 2)
    '5': 'colinas',
    'antes_6': 'vuelta',     # vuelta completa de cabeza
    '7': 'bajada',
    'antes_8': 'relampago',  # modo relámpago: ya no se lee nada, las puertas casi no se ven
}
# Vehículo sorpresa (índice de pregunta → vehículo). El dragón llega solo en el rescate del puente.
VEHICULOS = {'2': 'patineta', '7': 'carrito', '8': 'pato', '9': 'dragon'}
# El dragón de la serie: el huevo se alimenta con las respuestas correctas, nace, crece y en el puente ya es gigante.
DRAGON = {'meta_huevo': 3, 'antes_3': 'nace', 'antes_4': 'crece'}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('entrada'); ap.add_argument('salida'); ap.add_argument('--n', type=int, default=10)
    a = ap.parse_args()
    ep = json.load(open(a.entrada, encoding='utf-8'))
    qs = [q for q in ep['preguntas'] if q.get('o_img')][:a.n]
    out = {'id': 'ciudad-muestra', 'formato': 'rapido', 'muestra': True,
           'titulo': '¿A o B? EN LA CIUDAD (MUESTRA)', 'titulo_youtube': 'MUESTRA · ¿A o B? en la ciudad',
           'descripcion': 'Muestra privada del formato en la ciudad. No publicar.', 'tags': [],
           'eventos': EVENTOS, 'vehiculos': VEHICULOS, 'dragon': DRAGON, 'preguntas': qs, 'extra_tts': ep.get('extra_tts', {})}
    json.dump(out, open(a.salida, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(qs)} preguntas →', a.salida)


if __name__ == '__main__':
    main()
