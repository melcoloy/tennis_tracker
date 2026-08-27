"""
Sondage de sources alternatives.

SofaScore est verrouille. On teste ici plusieurs pistes sans cle d'API
pour voir lesquelles repondent et renvoient quelque chose d'exploitable.

    python sonde_sources.py
"""

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept": "*/*"}

# Chaque entree : (description, url, ce qu'on espere y trouver)
SOURCES = [
    ("TennisAbstract - matchs du joueur",
     "https://www.tennisabstract.com/jsmatches/ArthurFils.js",
     "un fichier JS contenant un tableau de matchs"),

    ("TennisAbstract - carriere",
     "https://www.tennisabstract.com/jsmatches/ArthurFilsCareer.js",
     "resume de carriere par saison"),

    ("TennisAbstract - fiche joueur",
     "https://www.tennisabstract.com/cgi-bin/player-classic.cgi?p=ArthurFils",
     "page HTML, pour verifier l'orthographe de l'identifiant"),

    ("Ultimate Tennis Statistics - recherche",
     "https://www.ultimatetennisstatistics.com/playerAutocomplete?term=Fils",
     "JSON avec l'id interne du joueur"),

    ("Wikipedia FR - API (plan de secours)",
     "https://fr.wikipedia.org/api/rest_v1/page/summary/Arthur_Fils",
     "resume, utile seulement pour la biographie"),
]


def sonder(nom, url, espoir):
    print(f"\n--- {nom}")
    print(f"    attendu : {espoir}")
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
    except Exception as e:
        print(f"    [ERREUR] {type(e).__name__} : {e}")
        return

    ctype = r.headers.get("Content-Type", "?").split(";")[0]
    taille = len(r.content)
    marque = "OK  " if r.status_code == 200 else "FAIL"
    print(f"    [{marque}] {r.status_code}  |  {ctype}  |  {taille} octets")

    if r.status_code != 200:
        print(f"    corps : {r.text[:150]}")
        return

    if taille < 200:
        print("    /!\\ reponse tres courte : probablement vide ou une erreur deguisee")

    extrait = r.text[:300].replace("\n", " ").replace("\r", "")
    print(f"    debut  : {extrait}")


if __name__ == "__main__":
    print("Sondage des sources alternatives")
    print("=" * 60)
    for nom, url, espoir in SOURCES:
        sonder(nom, url, espoir)
    print("\n" + "=" * 60)
    print("Envoie cette sortie complete : on choisira la source viable.")