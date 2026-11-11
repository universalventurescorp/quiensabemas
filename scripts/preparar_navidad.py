#!/usr/bin/env python3
"""Arma contenido/navidad/navidad001.json: el episodio de Navidad «¡Criamos un DRAGÓN de Navidad!» (11-nov-2026).
Lee las preguntas de contenido/ciudad/preguntas_*.txt (formato: pregunta ; correcta ; incorrecta ; foto ok ; foto mal ; respuesta),
reparte cada una en una de las 9 zonas por su tema (palabras clave), ordena cada zona de fácil a difícil y reparte la dificultad
a lo largo del video, y añade el guion (zonas, dragón, vehículos).
Uso: python3 scripts/preparar_navidad.py [--ver]   (--ver: lista qué pregunta cayó en qué zona)
"""
import json, os, random, re, sys, unicodedata

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
ARCH = ['preguntas_navidad.txt', 'preguntas_a.txt', 'preguntas_b.txt', 'preguntas_c.txt', 'preguntas_d.txt']
# dificultad base por archivo (si el archivo no trae «## nivel N»)
NIVEL_ARCH = {'preguntas_a.txt': 1, 'preguntas_b.txt': 2, 'preguntas_c.txt': 3, 'preguntas_navidad.txt': 2, 'preguntas_d.txt': 2}

ZONAS = ['Tradiciones navideñas', 'Juguetes, inventos y ciencia', 'Animales del bosque y árboles', 'Frío, hielo y agua',
         'Comida y postres', 'Animales del frío', 'Montañas, volcanes y geografía', 'Papá Noel visita este país', 'Planetas y estrellas']

# Reglas en orden (la primera que coincide gana). Se busca en la pregunta y las dos respuestas, en español, sin tildes.
# Zonas algo amplias para que todo encaje en la historia de Nochebuena:
#  1 avenida: Navidad y tradiciones · 2 taller: juguetes, inventos, ciencia, deportes, música, cuerpo
#  3 bosque: animales y plantas · 4 lago: agua, mar, invierno · 5 dulces: comida · 6 Polo Norte: animales del frío
#  7 montaña: montañas, volcanes, desiertos, ríos, dinosaurios · 8 tejados: países, lugares, banderas · 9 cielo: espacio
CLAVES = [
    (8, r'planeta|jupiter|saturno|neptuno|urano|marte\b|venus|mercurio|\bluna\b|el sol\b|del sol\b|\bsol\b|estrella azul|brilla con luz propia|una estrella|cometa|galaxia|via lactea|cohete|espacio|satelite|agujero negro|tardigrado|tierras caben|luz del sol|panel solar'),
    (5, r'oso polar|pinguino|foca|morsa|zorro artico|narval|buho nival|buho de las nieves|\breno|renos|antartida|polo norte|polo sur|alce|\bvicuna|groenlandia|hace frio'),
    (0, r'navid|papa noel|nochebuena|pesebre|nacimiento|reyes? mago|melchor|villancico|noche de paz|jingle|muerdago|corona (navidena|de hojas)|esfera navidena|calcetin navideno|luces navidenas|regalo|caja con lazo|elfo|flor de pascua|campana|canta en navidad|coro|en la punta del arbol|pinata|rockefeller|gorro rojo|25 de diciembre|24 de diciembre|diciembre|muneco de nieve|baston de caramelo|cascanueces'),
    (4, r'paneton|chocolat|turron|galleta|jengibre|dulce|caramelo|fruta|sandia|mango|fresa|coco\b|verdura|brocoli|papa\b|papas fritas|aji\b|picante|ceviche|queso|leche|pizza|sushi|taco|paella|croissant|tamal|plato|bebida|chicha|lomo saltado|gaseosa|azucar|semilla|mani\b|pimiento|vitamina|huevo de avestruz|pavo\b|miel|gallina|da leche|vaca'),
    (7, r'flag:|bandera|capital|pais|esta en (china|brasil|australia|india|la india|londres|italia|egipto|mexico|jordania|cusco|trujillo|paris|estados unidos|japon|africa|peru|nasca)|torre|maravilla|chan chan|chimu|machu|caral|chavin|nasca|nazca|sipan|idioma|rovaniemi|laponia|lima|escudo del peru|pajaro nacional|flor nacional|ciudad mas antigua|habitantes|esfinge|petra|coliseo|golden gate|tower bridge|arco del triunfo|rascacielos'),
    (6, r'volcan|misti|montana|everest|kilimanjaro|monte fuji|desierto|sahara|atacama|rio\b|amazonas|selva amazonica|lago\b|titicaca|catarata|iguazu|salto angel|cascada|canon|colca|oceano|pacifico|\bmar\b|mar muerto|fosa|dinosaur|triceratops|braquiosaurio|estegosaurio|pterodactilo|velociraptor|tiranosaurio|gema|esmeralda|diamante|cactus|aurora boreal|huracan|lugar mas bajo|punto mas profundo|existio'),
    (3, r'hielo|nieve|copo|invierno|iglu|trineo|patin|hockey|esqui|granizo|lluvia|arcoiris|helado|mas frio|bufanda|agua|piscina|waterpolo|flota|barco|submarino|crucero|faro|ballena|tiburon|pez|delfin|pulpo|calamar|medusa|cangrejo|camaron|mantarraya|estrella de mar|crustaceo|branquias|mar\b'),
    (1, r'juguete|tren|pelota|basquet|futbol|tenis|raqueta|tijera|piano|teclas|guitarra|cuerda|charango|cajon|trompeta|quena|instrumento|reloj|binocular|iman|metal|oro\b|cobre|electric|atomo|hidrogeno|osmio|pesado|camion|ruedas|avion|planeador|formula 1|globo|aerogenerador|brujula|paraguas|botella de plastico|organo|piel|hueso|femur|huesos|corazon|sangre|cerebro|dientes|oso de peluche|mar muerto|degradarse|mas antiguo\b'),
    (2, r'.'),   # todo lo demás: animales y plantas → bosque
]
CLAVES = [(z, re.compile(rx)) for z, rx in CLAVES]


def sin_tildes(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')


def foto(s):
    s = s.strip(); k, v = s.split(':', 1)
    if k == 'flag': return {'flag': v.strip()}
    if k == 'px': return {'q': v.strip(), 'src': 'px'}
    q, must = v.split('|'); return {'q': q.strip(), 'src': 'cm', 'must': must.strip()}


def leer():
    filas = []
    for a in ARCH:
        p = os.path.join(RAIZ, 'contenido', 'ciudad', a)
        if not os.path.exists(p): continue
        nivel = NIVEL_ARCH[a]; zona_fija = None
        for ln in open(p, encoding='utf-8'):
            ln = ln.strip()
            if not ln or ln.startswith('# '): continue
            m = re.match(r'##\s*nivel\s*(\d)', ln)
            if m: nivel = int(m.group(1)); continue
            m = re.match(r'##\s*zona\s*(\d)', ln)        # «## zona N» fuerza la zona de las filas siguientes
            if m: zona_fija = int(m.group(1)) - 1; continue
            if ln.startswith('#'): continue
            c = [x.strip() for x in ln.split(' ; ')]
            if len(c) != 6: sys.exit(f'{a}: fila mal formada: {ln}')
            filas.append(dict(p=c[0], ok=c[1], mal=c[2], fok=c[3], fmal=c[4], tr=c[5], nivel=nivel, arch=a, zona_fija=zona_fija))
    return filas


# Correcciones a mano: (respuesta correcta, palabra de la pregunta) → zona (1..9)
FIJAS = {('Loro', 'imitando'): 3, ('Toro', 'cuernos'): 3, ('Rana dardo', 'venenosa'): 3, ('Globo aerostático', 'aire'): 2,
         ('Jaguar', 'felino'): 3, ('Caballo', 'rápido'): 3, ('Búho', 'nocturno'): 3, ('Cóndor', 'alto'): 3, ('Lobo', 'carne'): 3,
         ('Pavo real', 'colores'): 3, ('Avestruz', 'huevos'): 3, ('Avestruz', 'grande'): 3, ('Velociraptor', 'pavo'): 7,
         ('Camello', 'desierto'): 7, ('Calcetín navideño', 'chimenea'): 1, ('Búho', 'vuela'): 3, ('Pulpo', 'brazos'): 4,
         ('Medusa', 'mar'): 4, ('Faro', 'mar'): 4, ('Estrella de mar', 'brazo'): 4, ('Pez vela', 'mar'): 4, ('Pez linterna', 'mar'): 4,
         ('Helado', 'frío'): 4, ('Bufanda', 'invierno'): 4, ('Girasol', 'Sol'): 3, ('Aerogenerador', 'viento'): 2}


def zona_de(f):
    if f['zona_fija'] is not None: return f['zona_fija']
    for (ok, pal), z in FIJAS.items():
        if f['ok'] == ok and pal in f['p']: return z - 1
    if 'flag:' in f['fok']: return 7
    txt = sin_tildes(' '.join([f['p'], f['ok'], f['mal']]))
    for z, rx in CLAVES:
        if rx.search(txt): return z
    return None


# Guion: vehículo de cada zona (índice de zona → vehículo, se pone en la 1.ª pregunta de la zona)
VEH_ZONA = {0: 'corre', 1: 'patineta', 2: 'trineo_madera', 3: 'patines', 4: 'carrito', 5: 'reno', 6: 'corre', 7: 'pato', 8: 'trineo'}


def main():
    ver = '--ver' in sys.argv
    filas = leer()
    vistas, unicas = set(), []
    for f in filas:
        k = (sin_tildes(f['p']), frozenset((sin_tildes(f['ok']), sin_tildes(f['mal']))))
        if k in vistas: continue
        vistas.add(k); unicas.append(f)
    # no repetir lo que ya salió en episodios publicados (banco de preguntas)
    usadas = set()
    bp = os.path.join(RAIZ, 'banco', 'preguntas.jsonl')
    if os.path.exists(bp):
        for ln in open(bp, encoding='utf-8'):
            try: q = json.loads(ln)
            except Exception: continue
            usadas.add((sin_tildes(q.get('p', '')), sin_tildes(q.get('r', ''))))
    rep = [f for f in unicas if (sin_tildes(f['p']), sin_tildes(f['ok'])) in usadas]
    unicas = [f for f in unicas if (sin_tildes(f['p']), sin_tildes(f['ok'])) not in usadas]

    por_zona = {z: [] for z in range(9)}; sin = []
    for f in unicas:
        z = zona_de(f)
        (sin if z is None else por_zona[z]).append(f)
    # las que no encajan en ningún tema: a la zona con menos preguntas
    for f in sin:
        z = min(range(9), key=lambda z: len(por_zona[z])); por_zona[z].append(f); f['sin_tema'] = True

    r = random.Random(1225)
    preg, inicios = [], []
    for z in range(9):
        lista = por_zona[z]; r.shuffle(lista)
        # dentro de la zona, de fácil a difícil, pero la dificultad sube también a lo largo del video:
        # al principio solo niveles bajos primero; al final las difíciles (orden estable por nivel)
        lista.sort(key=lambda f: f['nivel'])
        inicios.append(len(preg))
        for f in lista:
            c = r.randint(0, 1)
            o = [f['ok'], f['mal']] if c == 0 else [f['mal'], f['ok']]
            of = [foto(f['fok']), foto(f['fmal'])] if c == 0 else [foto(f['fmal']), foto(f['fok'])]
            if any('flag' in x for x in of) and not all('flag' in x for x in of): sys.exit(f"mezcla bandera y foto: {f['p']}")
            preg.append({'n': len(preg) + 1, 'p': f['p'], 'o': o, 'c': c, 'tp': f['p'], 'tr': f['tr'], 'o_fotos': of,
                         'zona': z + 1, 'nivel': f['nivel']})
    vehiculos = {str(inicios[z] + 1): v for z, v in VEH_ZONA.items()}   # +1: arrancan justo después del cartel
    N = len(preg)
    dragon = {'meta_huevo': 5, 'antes_5': 'nace', f'antes_{inicios[2]}': 'crece:joven', f'antes_{inicios[5]}': 'crece:adulto'}
    ep = {
        '_nota': 'Episodio de Navidad (11-nov-2026). Escrito con scripts/preparar_navidad.py desde contenido/ciudad/preguntas_*.txt. '
                 'Se descartan las preguntas sin fotos; «zonas» guarda la 1.ª pregunta de cada zona y se recalcula tras el recorte.',
        'id': 'navidad001', 'formato': 'rapido', 'max_preguntas': 460, 'minimo': 300,
        'titulo': '¡Criamos un DRAGÓN de Navidad!',
        'titulo_youtube': '¿A o B? 🎄 ¡Criamos un DRAGÓN de Navidad! 🐉 Preguntas de Navidad | ¿Quién Sabe Más?',
        'descripcion': 'Es Nochebuena y MAX y NOVA encuentran un regalo con un HUEVO DE DRAGÓN 🎁🐉 Cada respuesta correcta lo alimenta: '
                       'nace, crece… ¡y al final tira el trineo de Papá Noel! 9 zonas navideñas y cientos de preguntas ¿A o B? '
                       '¿Cuántas aciertas? Escribe tu número en los comentarios 👇',
        'tags': ['a o b', 'preguntas de navidad', 'navidad', 'quiz de navidad', 'trivia navideña', 'preguntas de cultura general',
                 'dragón', 'quiz para niños', 'qué prefieres'],
        'zonas': inicios, 'zona_de': [q['zona'] for q in preg], 'vehiculos': vehiculos, 'dragon': dragon,
        'preguntas': preg,
    }
    os.makedirs(os.path.join(RAIZ, 'contenido', 'navidad'), exist_ok=True)
    out = os.path.join(RAIZ, 'contenido', 'navidad', 'navidad001.json')
    json.dump(ep, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{N} preguntas ({len(rep)} ya usadas en el banco y descartadas, {len(sin)} sin tema claro)')
    for z in range(9): print(f'  zona {z + 1} {ZONAS[z]:32s} {len(por_zona[z]):3d}')
    if ver:
        for q in preg: print(q['zona'], q['nivel'], q['p'], '→', q['o'][q['c']])
        print('SIN TEMA:'); [print('  ', f['p'], f['ok'], f['mal']) for f in sin]


if __name__ == '__main__':
    main()
