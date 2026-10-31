"""Comprueba que la llave de YouTube abre el canal @QuienSabeMasTV. No sube nada."""
import os, sys
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

creds = Credentials(None, refresh_token=os.environ["YT_REFRESH_TOKEN_QSM"], token_uri="https://oauth2.googleapis.com/token",
                    client_id=os.environ["YT_CLIENT_ID"], client_secret=os.environ["YT_CLIENT_SECRET"])
yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
r = yt.channels().list(part="snippet,statistics,status", mine=True).execute()
for c in r.get("items", []):
    print("Canal:", c["snippet"]["title"], "| handle:", c["snippet"].get("customUrl"),
          "| subs:", c["statistics"].get("subscriberCount"), "| videos:", c["statistics"].get("videoCount"),
          "| madeForKids:", c.get("status", {}).get("madeForKids"))
ok = any((c["snippet"].get("customUrl") or "").lower() == "@quiensabemastv" for c in r.get("items", []))
print("OK: es @QuienSabeMasTV" if ok else "ATENCIÓN: no es @QuienSabeMasTV")
sys.exit(0 if ok else 1)
