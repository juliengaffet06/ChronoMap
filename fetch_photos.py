#!/usr/bin/env python3
"""Télécharge les photos de Chrono-Map depuis Wikimedia Commons.

Usage :
    python3 fetch_photos.py            télécharge dans ./photos/ puis crée chrono-map-standalone.html
    python3 fetch_photos.py --no-download   reconstruit seulement le HTML autonome depuis ./photos/

Aucune dépendance : bibliothèque standard uniquement.
Résultat : photos/<id>.jpg (pour l'hébergement PWA) et un fichier HTML unique,
sans accès réseau nécessaire, avec les images intégrées.
"""
import base64
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
HTML = HERE / "index.html"
OUT = HERE / "chrono-map-standalone.html"
PHOTOS = HERE / "photos"
UA = "ChronoMapPrototype/0.1 (personal game prototype; Python urllib)"
WIDTH = 1000


def read_catalog():
    src = HTML.read_text(encoding="utf-8")
    block = re.search(r"var PHOTOS=\[(.*?)\n\];", src, re.S).group(1)
    items = re.findall(r'\{id:"([^"]+)",f:"([^"]+)"', block)
    if not items:
        sys.exit("Catalogue de photos introuvable dans index.html")
    return items


def download(photo_id, filename):
    url = ("https://commons.wikimedia.org/wiki/Special:FilePath/"
           + urllib.parse.quote(filename) + "?width=%d" % WIDTH)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        data = r.read()
        ctype = r.headers.get("Content-Type", "")
    if not ctype.startswith("image/") or len(data) < 5000:
        raise ValueError("réponse inattendue (%s, %d octets)" % (ctype, len(data)))
    (PHOTOS / (photo_id + ".jpg")).write_bytes(data)
    return len(data)


def mime_of(data):
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def main():
    skip = "--no-download" in sys.argv
    items = read_catalog()
    PHOTOS.mkdir(exist_ok=True)
    failed = []
    if not skip:
        for pid, fname in items:
            try:
                n = download(pid, fname)
                print("OK   %-15s %6d Ko" % (pid, n // 1024))
            except Exception as e:
                failed.append(pid)
                print("ÉCHEC %-14s %s" % (pid, e))
            time.sleep(1.2)

    data = {}
    for pid, _ in items:
        p = PHOTOS / (pid + ".jpg")
        if p.exists() and p.stat().st_size > 5000:
            raw = p.read_bytes()
            data[pid] = "data:%s;base64,%s" % (mime_of(raw), base64.b64encode(raw).decode("ascii"))

    html = HTML.read_text(encoding="utf-8")
    marker = "<script>\nvar PHOTOS="
    if marker not in html:
        sys.exit("Point d'insertion introuvable dans index.html")
    injected = "<script>window.PHOTO_DATA=" + json.dumps(data) + ";</script>\n" + marker
    OUT.write_text(html.replace(marker, injected, 1), encoding="utf-8")
    print("\n%d/%d photos intégrées -> %s (%d Ko)" % (len(data), len(items), OUT.name, OUT.stat().st_size // 1024))
    if failed:
        print("Photos en échec (le jeu les chargera depuis Commons si possible) :", ", ".join(failed))


if __name__ == "__main__":
    main()
