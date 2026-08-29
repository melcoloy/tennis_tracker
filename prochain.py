"""
prochain.py -- prepare le tableau vierge du prochain tournoi.

Les tirages ne sont pas dans nos donnees : Tennis Abstract ne publie
que des matchs joues. On part donc d'un fichier texte que tu remplis,
tirage.txt, dans l'ordre du tableau (de haut en bas) :

    # Nom: US Open
    # Date: 20260831
    # Surface: Hard
    # Niveau: Grand Chelem
    Jannik Sinner
    Qualifier
    Adam Walton
    ...

Les lignes commencant par # portent les informations du tournoi, les
autres sont les joueurs. Une ligne vide vaut une place a determiner.

    python prochain.py

Ecrit site/donnees/prochain.json, lu par la page « Prochain tournoi ».
"""

import json
import sys
from pathlib import Path

import cache

SOURCE = Path("tirage.txt")
SORTIE = Path("site") / "donnees" / "prochain.json"


def lire(fichier=SOURCE):
    if not fichier.exists():
        raise SystemExit(
            f"{fichier} introuvable. Cree-le avec le tirage, un joueur par "
            f"ligne, dans l'ordre du tableau (voir l'en-tete de ce script)."
        )

    infos, joueurs = {}, []
    for ligne in fichier.read_text(encoding="utf-8").splitlines():
        t = ligne.strip()
        if t.startswith("#"):
            if ":" in t:
                cle, valeur = t.lstrip("#").split(":", 1)
                infos[cle.strip().lower()] = valeur.strip()
        elif t or joueurs:          # une ligne vide = place a determiner
            joueurs.append(t)

    while joueurs and not joueurs[-1]:
        joueurs.pop()

    return infos, joueurs


def completer(joueurs):
    """
    Complete jusqu'a la puissance de 2 superieure.

    Un tableau doit avoir 32, 64 ou 128 places : sans cela les tours ne
    tombent pas juste et l'arbre est faux des le depart.
    """
    n = 1
    while n < len(joueurs):
        n *= 2
    if n != len(joueurs):
        print(f"{len(joueurs)} joueurs lus -> complete a {n} places "
              f"({n - len(joueurs)} a determiner)")
        joueurs = joueurs + [""] * (n - len(joueurs))
    return joueurs


def construire():
    infos, joueurs = lire()
    joueurs = completer(joueurs)

    if len(joueurs) < 2:
        raise SystemExit("Il faut au moins deux joueurs.")

    connus = {s.lower() for s in cache.joueurs_en_cache()}

    entrees = []
    for nom in joueurs:
        slug = cache.slugifier(nom) if nom else ""
        entrees.append({
            "nom": nom,
            "slug": slug if slug.lower() in connus else None,
        })

    date = infos.get("date", "")
    data = {
        "nom": infos.get("nom", "Prochain tournoi"),
        "date": date,
        "date_fr": f"{date[6:]}/{date[4:6]}/{date[:4]}" if len(date) == 8 else "",
        "surface": infos.get("surface", ""),
        "niveau": infos.get("niveau", ""),
        "id": cache.slugifier(infos.get("nom", "tournoi")) + date,
        "joueurs": entrees,
    }

    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    reconnus = sum(1 for e in entrees if e["slug"])
    print(f"\n{data['nom']} -- {len(entrees)} places, "
          f"{reconnus} joueurs reconnus dans la base")
    print(f"-> {SORTIE}")
    print("\nRelance ensuite : python publier.py")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        SOURCE = Path(sys.argv[1])
    construire()