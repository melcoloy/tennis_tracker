"""
annuaire.py -- liste des joueurs classes, pour l'autocompletion.

Source : la page de classement ATP de live-tennis.eu, qu'on sait deja
lire (meme balisage que la Race). Plusieurs centaines de noms avec leur
orthographe exacte, ce qui evite les erreurs de conversion vers
l'identifiant Tennis Abstract.

Limite assumee : seuls les joueurs actuellement classes y figurent.
Un joueur retire (Federer, Tsonga) ne sera pas propose, mais reste
accessible en tapant son nom a la main.

    python annuaire.py
"""

import html as _html
import json
import re
import time
from pathlib import Path

import requests

import cache

URL = "https://live-tennis.eu/en/official-atp-ranking"
DOSSIER = Path("cache")
FICHIER = DOSSIER / "annuaire.json"
DUREE_VIE = 7 * 24 * 3600      # le classement bouge une fois par semaine

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/120.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}



def _decoder(reponse):
    """
    Choisit le bon encodage avant de lire le texte.

    Quand un serveur ne declare pas de charset, requests suppose
    Latin-1 (heritage de la specification HTTP). live-tennis.eu sert
    de l'UTF-8 sans le declarer : sans ce correctif, 'Felix' devient
    'FA©lix' et l'identifiant qui en decoule n'existe pas.
    """
    if "charset" not in reponse.headers.get("Content-Type", "").lower():
        reponse.encoding = reponse.apparent_encoding or "utf-8"
    return reponse.text

def analyser(html):
    """
    Extrait (rang, nom, pays) de chaque ligne du tableau.

    Le tableau contient des lignes parasites -- publicites, en-tetes
    intermediaires -- qui n'ont pas de cellule 'pn'. On les ignore
    plutot que de supposer une structure reguliere.
    """
    joueurs = []
    vus = set()

    for ligne in re.split(r"<tr\b", html):
        nom = re.search(r"class=[\"']?pn[\"']?[^>]*>(.*?)</td>", ligne, re.S)
        rang = re.search(r"class=[\"']?rk[\"']?[^>]*>\s*(\d+)", ligne)
        if not nom or not rang:
            continue

        propre = _html.unescape(re.sub(r"<[^>]+>", "", nom.group(1)))
        propre = propre.replace("\xa0", " ")
        propre = re.sub(r"^[^0-9A-Za-z\u00C0-\u024F]+", "", propre).strip()
        if not propre or propre in vus:
            continue
        vus.add(propre)

        pays = re.findall(r"class=[\"']?sm[\"']?[^>]*>([A-Z]{3})</td>", ligne)

        joueurs.append({
            "nom": propre,
            "rang": int(rang.group(1)),
            "pays": pays[0] if pays else "",
            "slug": cache.slugifier(propre),
        })

    if not joueurs:
        raise ValueError("aucun joueur trouve -- le balisage a change ?")

    return sorted(joueurs, key=lambda j: j["rang"])


def charger(force=False):
    """Liste des joueurs, depuis le cache si possible."""
    if not force and FICHIER.exists():
        c = json.loads(FICHIER.read_text(encoding="utf-8"))
        if time.time() - c.get("horodatage", 0) < DUREE_VIE:
            return c["joueurs"]

    try:
        r = requests.get(URL, headers=HEADERS, timeout=25)
        r.raise_for_status()
        joueurs = analyser(_decoder(r))

        DOSSIER.mkdir(exist_ok=True)
        FICHIER.write_text(
            json.dumps({"horodatage": time.time(), "joueurs": joueurs},
                       ensure_ascii=False, indent=2),
            encoding="utf-8")
        return joueurs

    except Exception as e:
        if FICHIER.exists():
            return json.loads(FICHIER.read_text(encoding="utf-8"))["joueurs"]
        print(f"[!] annuaire indisponible : {e}")
        return []


if __name__ == "__main__":
    j = charger(force=True)
    print(f"{len(j)} joueurs\n")
    for x in j[:12]:
        print(f"  #{x['rang']:<4} {x['nom']:<26} {x['pays']}  -> {x['slug']}")