"""Ejecutar UNA vez en tu computadora para autorizar la subida al canal ¿Quién Sabe Más?

    pip install google-auth-oauthlib
    python get_youtube_token.py client_secret.json

Al iniciar sesión, elige la cuenta/canal de ¿Quién Sabe Más? (no otro canal).
Copia los 3 valores que imprime en GitHub > quiensabemas > Settings > Secrets and variables > Actions.
"""
import json
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.force-ssl"]

path = sys.argv[1] if len(sys.argv) > 1 else "client_secret.json"
flow = InstalledAppFlow.from_client_secrets_file(path, SCOPES)
creds = flow.run_local_server(port=0, prompt="consent select_account", access_type="offline")
info = json.load(open(path))["installed"]
print("\nYT_CLIENT_ID          =", info["client_id"])
print("YT_CLIENT_SECRET      =", info["client_secret"])
print("YT_REFRESH_TOKEN_QSM  =", creds.refresh_token)
