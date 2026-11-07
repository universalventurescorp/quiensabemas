"""Busca imágenes libres en Wikimedia Commons (dominio público / CC0 / CC BY / CC BY-SA) y guarda la atribución.
Uso: python scripts/buscar_imagenes.py consultas.json salida/ [--n 4]
consultas.json = {"clave": "texto de búsqueda", ...}
"""
import json, os, re, sys, time, urllib.parse, urllib.request

UA = {"User-Agent": "QuienSabeMasBot/0.1 (https://github.com/universalventurescorp/quiensabemas)"}
API = "https://commons.wikimedia.org/w/api.php"
OK_LIC = re.compile(r"^(public domain|pd|cc0|cc by(-sa)? ?[0-9.]*|cc-by(-sa)?-[0-9.]+)", re.I)


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def strip(html):
    return re.sub(r"<[^>]+>", "", html or "").strip()


def buscar(q, n):
    p = {"action": "query", "format": "json", "generator": "search", "gsrsearch": f"filetype:bitmap {q}",
         "gsrnamespace": 6, "gsrlimit": 25, "prop": "imageinfo", "iiprop": "url|extmetadata|size",
         "iiurlwidth": 1600}
    d = json.loads(get(API + "?" + urllib.parse.urlencode(p)))
    pages = sorted(d.get("query", {}).get("pages", {}).values(), key=lambda x: x.get("index", 99))
    out = []
    for pg in pages:
        ii = (pg.get("imageinfo") or [{}])[0]
        md = ii.get("extmetadata", {})
        lic = strip(md.get("LicenseShortName", {}).get("value", ""))
        w, h = ii.get("width", 0), ii.get("height", 0)
        if not OK_LIC.match(lic) or w < 900 or h < 500 or w < h:
            continue
        out.append({"titulo": pg["title"], "url": ii.get("thumburl") or ii["url"], "pagina": ii.get("descriptionurl"),
                    "licencia": lic, "autor": strip(md.get("Artist", {}).get("value", ""))[:120]})
        if len(out) >= n:
            break
    return out


def main():
    consultas = json.load(open(sys.argv[1]))
    dst = sys.argv[2]
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 4
    os.makedirs(dst, exist_ok=True)
    creditos = {}
    for clave, q in consultas.items():
        try:
            res = buscar(q, n)
        except Exception as e:
            print("ERROR", clave, e); continue
        for i, r in enumerate(res, 1):
            ext = os.path.splitext(urllib.parse.urlparse(r["url"]).path)[1].lower() or ".jpg"
            f = f"{clave}_{i}{ext}"
            try:
                open(f"{dst}/{f}", "wb").write(get(r["url"]))
                creditos[f] = r
                print("OK", f, r["licencia"], r["titulo"])
            except Exception as e:
                print("ERROR descarga", f, e)
            time.sleep(0.5)
    json.dump(creditos, open(f"{dst}/creditos.json", "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
