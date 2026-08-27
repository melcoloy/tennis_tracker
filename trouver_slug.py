"""
trouver_slug.py -- retrouver l'identifiant Tennis Abstract d'un joueur.

live-tennis.eu et Tennis Abstract n'ecrivent pas toujours les noms de
la meme facon (Aleksandr / Alexander, second nom de famille absent...).
Ce script essaie des variantes et dit lesquelles donnent une vraie page.

    python trouver_slug.py "Aleksandr Shevchenko"
    python trouver_slug.py "Daniel Merida" DanielMeridaAguilar

Les identifiants supplementaires passes en argument sont testes aussi.
"""

import json
import re
import sys
import time

import requests

import cache
from pathlib import Path

CORRECTIONS = Path("corrections.json")

PAUSE = 3.0

# Equivalences courantes entre translitterations
EQUIVALENCES = [
    ("Aleksandr", "Alexander"), ("Aleksandar", "Alexander"),
    ("Alexandr", "Alexander"), ("Aleksander", "Alexander"),
    ("Nikolay", "Nikoloz"), ("Sergiy", "Sergey"),
    ("Yevgeny", "Evgeny"), ("Dmitry", "Dmitri"),
]


def variantes(nom, supplementaires):
    """Fabrique une liste d'identifiants plausibles, sans doublon."""
    base = [nom]

    for a, b in EQUIVALENCES:
        if a.lower() in nom.lower():
            base.append(re.sub(a, b, nom, flags=re.I))
        if b.lower() in nom.lower():
            base.append(re.sub(b, a, nom, flags=re.I))

    mots = nom.split()
    if len(mots) > 2:
        base.append(f"{mots[0]} {mots[-1]}")        # sans le nom du milieu
        base.append(" ".join(mots[:-1]))            # sans le dernier

    slugs, vus = [], set()
    for v in [cache.slugifier(b) for b in base] + list(supplementaires):
        if v not in vus:
            vus.add(v)
            slugs.append(v)
    return slugs


def tester(slug):
    """Renvoie (verdict, detail) sans rien ecrire dans le cache."""
    url = cache.GABARIT_URL.format(slug=slug)
    try:
        r = requests.get(url, headers=cache.HEADERS, timeout=30)
    except Exception as e:
        return "ERREUR", type(e).__name__

    if r.status_code == 429:
        return "429", "limite de debit, relance plus tard"
    if r.status_code != 200:
        return "HTTP", str(r.status_code)

    texte = r.text
    if not re.search(r"var\s+matchmx\s*=\s*\[", texte):
        return "VIDE", f"{len(texte)} caracteres, pas de donnees"

    nom = re.search(r"var\s+fullname\s*=\s*['\"]([^'\"]+)", texte)
    matchs = len(re.findall(r"\[\"\d{8}\"", texte))
    return "OK", f"{nom.group(1) if nom else '?'} -- environ {matchs} matchs"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    nom = sys.argv[1]
    extras = sys.argv[2:]
    candidats = variantes(nom, extras)

    print(f"Recherche de « {nom} » -- {len(candidats)} variantes\n")

    trouves = []
    for slug in candidats:
        verdict, detail = tester(slug)
        marque = {"OK": "  OK  ", "VIDE": " vide ", "429": " 429  "}.get(verdict, " ---  ")
        print(f"[{marque}] {slug:<32} {detail}")
        if verdict == "OK":
            trouves.append(slug)
        time.sleep(PAUSE)

    print()
    if trouves:
        bon = trouves[0]
        table = (json.loads(CORRECTIONS.read_text(encoding="utf-8"))
                 if CORRECTIONS.exists() else {})

        # on enregistre chaque variante fausse -> la bonne, pour que
        # publier.py ne la retente jamais
        for mauvais in candidats:
            if mauvais != bon:
                table[mauvais] = bon
        CORRECTIONS.write_text(json.dumps(table, ensure_ascii=False, indent=2),
                               encoding="utf-8")

        print(f"Trouve : {bon}")
        print(f"Correspondance enregistree dans {CORRECTIONS.name} -- "
              f"publier.py l'appliquera tout seul.")
        print(f"Pour l'ajouter maintenant : python publier.py {bon}")
    else:
        print("Aucune variante ne marche. Cherche le joueur a la main sur")
        print("tennisabstract.com : l'identifiant est dans l'URL, apres 'p='.")
        print("Puis : python publier.py <identifiant>")