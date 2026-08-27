"""
sonde_race.py -- ou trouver la position dans la Race ATP ?

On teste plusieurs sites et on regarde lesquels repondent ET
contiennent le nom du joueur. Le but n'est pas encore de parser :
c'est de savoir quelle porte est ouverte.

    python sonde_race.py
"""

import re

import requests

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/120.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/json",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

CANDIDATS = [
    ("live-tennis.eu (Race)",
     "https://live-tennis.eu/en/atp-race"),

    ("live-tennis.eu (classement live)",
     "https://live-tennis.eu/en/official-atp-ranking"),

    ("tennisexplorer (Race)",
     "https://www.tennisexplorer.com/ranking/atp-men/?race=1"),

    ("ATP Tour officiel (Race)",
     "https://www.atptour.com/en/rankings/singles?rankRange=0-100&rankType=rankRace"),

    ("Ultimate Tennis Statistics",
     "https://www.ultimatetennisstatistics.com/rankingsTable?rankType=POINTS&season=2026"),
]

CIBLE = "Fils"


def sonder(nom, url):
    print(f"\n--- {nom}")
    print(f"    {url}")
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
    except Exception as e:
        print(f"    [ERREUR] {type(e).__name__} : {e}")
        return

    ctype = r.headers.get("Content-Type", "?").split(";")[0]
    marque = "OK  " if r.status_code == 200 else "FAIL"
    print(f"    [{marque}] {r.status_code}  |  {ctype}  |  {len(r.content)} octets")

    if r.status_code != 200:
        print(f"    corps : {r.text[:120].replace(chr(10), ' ')}")
        return

    occurrences = r.text.count(CIBLE)
    print(f"    '{CIBLE}' apparait {occurrences} fois")

    if occurrences:
        # on montre le contexte : c'est la qu'on verra si le rang est a cote
        m = re.search(CIBLE, r.text)
        extrait = r.text[max(0, m.start() - 400):m.start() + 250]
        extrait = re.sub(r"\s+", " ", extrait)
        print(f"    contexte :\n      ...{extrait}...")
    else:
        print("    /!\\ nom absent : page vide, chargee en JS, ou protegee")


if __name__ == "__main__":
    print("Sondage des sources pour la Race ATP")
    print("=" * 68)
    for nom, url in CANDIDATS:
        sonder(nom, url)
    print("\n" + "=" * 68)
    print("Colle la sortie : on choisira la source et on ecrira le parseur.")