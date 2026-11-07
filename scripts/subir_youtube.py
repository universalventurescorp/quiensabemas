"""Sube un episodio a @QuienSabeMasTV SIEMPRE EN PRIVADO, con título, descripción (capítulos y créditos de fotos),
etiquetas y miniatura. El dueño revisa en YouTube Studio y lo publica a mano.
Uso: python scripts/subir_youtube.py trabajo/episodio.json trabajo/video.mp4 trabajo/video.tiempos.json trabajo/miniatura.jpg
Deja publicados/<id>.json con el id del video.
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


def hms(t):
    t = int(t); h, r = divmod(t, 3600); m, s = divmod(r, 60)
    return f'{h}:{m:02d}:{s:02d}' if h else f'{m}:{s:02d}'


def descripcion(ep, sync, creditos):
    sala = ep['codigo_sala']
    partes = [
        ep.get('descripcion') or f"¿Quién sabe más en tu casa? {len(ep['preguntas'])} preguntas de {ep['titulo'].lower()} para jugar en familia frente a la tele.",
        '',
        f'🎮 Cómo jugar: escanea el QR del video o entra a quiensabemastv.pages.dev/?sala={sala} · crea tu grupo · cuando digamos «¡YA!», toca EMPEZAR.',
        '¿Sin celular? Anota tus aciertos en un papel y juega igual.',
        '',
        'Capítulos:',
    ]
    partes += [f'{hms(t)} {c}' for t, c in sync.get('capitulos', [])]
    if creditos:
        partes += ['', 'Créditos de las fotos:']
        for f, c in sorted(creditos.items()):
            autor = (c.get('autor') or 'Autor desconocido').split('\n')[0][:80]
            partes.append(f"• {autor} — {c.get('licencia', '')} — {c.get('pagina', '')}")
    partes += ['', 'Presentadores y voces creados con herramientas de IA. Preguntas verificadas por el equipo de ¿Quién Sabe Más?',
               '', '#trivia #preguntasdeculturageneral #juegosenfamilia #quiz']
    d = '\n'.join(partes)
    return d[:4900]


def main(ep_path, video, sync_path, miniatura=None):
    ep = json.load(open(ep_path, encoding='utf-8')); sync = json.load(open(sync_path))
    cred_f = os.path.join(os.path.dirname(os.path.abspath(ep_path)), 'img', 'creditos.json')
    creditos = json.load(open(cred_f)) if os.path.exists(cred_f) else {}
    creds = Credentials(None, refresh_token=os.environ['YT_REFRESH_TOKEN_QSM'], token_uri='https://oauth2.googleapis.com/token',
                        client_id=os.environ['YT_CLIENT_ID'], client_secret=os.environ['YT_CLIENT_SECRET'])
    yt = build('youtube', 'v3', credentials=creds, cache_discovery=False)
    # seguridad: solo subir si la llave abre el canal correcto
    ch = yt.channels().list(part='snippet', mine=True).execute().get('items', [])
    if not any((c['snippet'].get('customUrl') or '').lower() == CANAL for c in ch):
        sys.exit(f'La llave no corresponde a {CANAL}: no subo nada.')
    titulo = (ep.get('titulo_youtube') or f"¿Quién Sabe Más? {ep['titulo']} · {len(ep['preguntas'])} preguntas")[:100]
    body = {
        'snippet': {'title': titulo, 'description': descripcion(ep, sync, creditos), 'categoryId': '24',
                    'tags': (ep.get('tags') or []) + ['trivia', 'preguntas de cultura general', 'juego en familia', 'quiz', 'Quién Sabe Más'],
                    'defaultLanguage': 'es', 'defaultAudioLanguage': 'es'},
        'status': {'privacyStatus': 'private', 'selfDeclaredMadeForKids': False, 'embeddable': True},
    }
    cuando = programada(ep.get('fecha'), json.load(open(os.path.join(RAIZ, 'contenido', 'calendario.json'))).get('publicacion', {}).get('episodio', '17:00'))
    if cuando: body['status']['publishAt'] = cuando; print('Se publicará solo:', cuando, 'UTC')
    req = yt.videos().insert(part='snippet,status', body=body, media_body=MediaFileUpload(video, chunksize=64 * 1024 * 1024, resumable=True))
    resp = None; t0 = time.time()
    while resp is None:
        st, resp = req.next_chunk()
        if st: print(f'Subiendo… {int(st.progress() * 100)}%', flush=True)
    vid = resp['id']; print('Subido EN PRIVADO:', vid, f'({(time.time() - t0) / 60:.1f} min)')
    if miniatura and os.path.exists(miniatura):
        try: yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(miniatura)).execute(); print('Miniatura lista')
        except Exception as e: print('No se pudo poner la miniatura:', e)
    os.makedirs(os.path.join(RAIZ, 'publicados'), exist_ok=True)
    json.dump({'id': ep['id'], 'video': vid, 'titulo': ep['titulo'], 'sala': ep['codigo_sala'], 'formato': ep.get('formato', 'normal'),
               'duracion': sync['duracion'], 'subido': time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime()), 'privacidad': 'private', 'publica': cuando},
              open(os.path.join(RAIZ, 'publicados', f"{ep['id']}.json"), 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main(*sys.argv[1:])
