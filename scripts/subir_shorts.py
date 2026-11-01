"""Sube los Shorts del episodio a @QuienSabeMasTV SIEMPRE EN PRIVADO, con el enlace al episodio completo.
Uso: python scripts/subir_shorts.py trabajo/episodio.json trabajo/shorts/shorts.json
Lee el id del video largo de publicados/<id>.json y agrega ahí la lista de Shorts subidos.
Un Short con voces faltantes o de más de 60 s no se sube.
"""
import json, os, sys, time
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CANAL = '@quiensabemastv'


def programada(fecha, hora, dias=0):
    """Fecha de publicación automática en UTC (RFC 3339) si está activada en contenido/calendario.json; si no, None."""
    import datetime as dt
    cal = json.load(open(os.path.join(RAIZ, 'contenido', 'calendario.json'), encoding='utf-8')).get('publicacion', {})
    if not cal.get('automatica') or not fecha: return None
    h, m = map(int, hora.split(':'))
    t = dt.datetime.fromisoformat(fecha) + dt.timedelta(days=dias, hours=h + 5, minutes=m)  # Lima = UTC-5
    ahora = dt.datetime.utcnow() + dt.timedelta(minutes=30)
    return max(t, ahora).strftime('%Y-%m-%dT%H:%M:%SZ')


def main(ep_path, shorts_path):
    ep = json.load(open(ep_path, encoding='utf-8')); sh = json.load(open(shorts_path, encoding='utf-8'))
    pub_f = os.path.join(RAIZ, 'publicados', f"{ep['id']}.json")
    pub = json.load(open(pub_f)) if os.path.exists(pub_f) else {}
    largo = pub.get('video')
    cred_f = os.path.join(os.path.dirname(os.path.abspath(ep_path)), 'img', 'creditos.json')
    creditos = json.load(open(cred_f)) if os.path.exists(cred_f) else {}
    preg = {q['n']: q for q in ep['preguntas']}
    creds = Credentials(None, refresh_token=os.environ['YT_REFRESH_TOKEN_QSM'], token_uri='https://oauth2.googleapis.com/token',
                        client_id=os.environ['YT_CLIENT_ID'], client_secret=os.environ['YT_CLIENT_SECRET'])
    yt = build('youtube', 'v3', credentials=creds, cache_discovery=False)
    ch = yt.channels().list(part='snippet', mine=True).execute().get('items', [])
    if not any((c['snippet'].get('customUrl') or '').lower() == CANAL for c in ch):
        sys.exit(f'La llave no corresponde a {CANAL}: no subo nada.')
    subidos = pub.get('shorts', [])
    horas = json.load(open(os.path.join(RAIZ, 'contenido', 'calendario.json'))).get('publicacion', {}).get('shorts', ['12:00', '20:00'])
    for k, s in enumerate(sh['shorts']):
        if s.get('faltan') or s['duracion'] > 60:
            print(f"Short de la pregunta {s['n']} NO se sube: faltan voces o dura más de 60 s"); continue
        q = preg.get(s['n'], {})
        p = q.get('p', s['pregunta'])
        titulo = f'¿La sabes en 5 segundos? {p}'
        if len(titulo) > 88: titulo = '¿La sabes en 5 segundos? 🤔'
        titulo += ' #shorts'
        desc = [f'¿La sabías? Escribe tu respuesta en los comentarios 👇', '']
        if largo:
            desc += [f"🎮 Juega las {sh['total']} preguntas completas en familia: https://youtu.be/{largo}", '']
        desc += ['Juega con tu celular en quiensabemastv.pages.dev · Suscríbete a @QuienSabeMasTV']
        foto = os.path.basename(q.get('img', ''))
        if foto in creditos:
            c = creditos[foto]
            desc += ['', f"Foto: {(c.get('autor') or 'Autor desconocido').split(chr(10))[0][:80]} — {c.get('licencia', '')} — {c.get('pagina', '')}"]
        desc += ['', 'Presentadores y voces creados con herramientas de IA.', '', '#trivia #quiz #culturageneral #shorts']
        body = {'snippet': {'title': titulo[:100], 'description': '\n'.join(desc)[:4900], 'categoryId': '24',
                            'tags': ['trivia', 'quiz', 'cultura general', 'shorts', 'Quién Sabe Más'],
                            'defaultLanguage': 'es', 'defaultAudioLanguage': 'es'},
                'status': {'privacyStatus': 'private', 'selfDeclaredMadeForKids': False, 'embeddable': True}}
        cuando = programada(ep.get('fecha'), horas[k % len(horas)], k // len(horas))  # maratón: 2 el sábado, 2 el domingo
        if cuando: body['status']['publishAt'] = cuando
        try:
            req = yt.videos().insert(part='snippet,status', body=body, media_body=MediaFileUpload(s['archivo'], resumable=True))
            resp = None
            while resp is None: _, resp = req.next_chunk()
        except Exception as e:
            print(f"Falló la subida del Short {s['n']}: {e}"); continue
        print(f"Short subido EN PRIVADO: {resp['id']} (pregunta {s['n']})")
        subidos.append({'video': resp['id'], 'n': s['n'], 'titulo': titulo, 'privacidad': 'private',
                        'subido': time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())})
    if pub:
        pub['shorts'] = subidos
        json.dump(pub, open(pub_f, 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main(*sys.argv[1:])
