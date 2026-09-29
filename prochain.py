"""
prochain.py -- prepare les tableaux vierges des tournois a venir.

Les tirages ne sont pas dans nos donnees : Tennis Abstract ne publie
que des matchs joues. On part donc de fichiers texte que tu remplis.

Un fichier par tournoi dans le dossier tirages/ :

    tirages/tokyo.txt
    tirages/pekin.txt

Chacun au format suivant, dans l'ordre du tableau (de haut en bas) :

    # Nom: Tokyo
    # Date: 20260928
    # Surface: Hard
    # Niveau: ATP 500
    Jannik Sinner (1)
    Qualifier
    Adam Walton
    Arthur Fils (8)
    ...

Les lignes commencant par # portent les informations du tournoi, les
autres sont les joueurs. Une ligne vide vaut une place a determiner.
Les mentions (1), (Q), (WC), (LL) sont reconnues et affichees a part.

Le fichier tirage.txt a la racine reste accepte, pour compatibilite.

    python prochain.py

Ecrit site/donnees/prochain.json, lu par la page « Pronostics ».
"""

import json
import re
import sys
from pathlib import Path

import cache

DOSSIER = Path("tirages")
SOURCE = Path("tirage.txt")          # ancien emplacement, toujours lu
CORRECTIONS = Path("corrections.json")
SORTIE = Path("site") / "donnees" / "prochain.json"

# Tete de serie ou statut d'entree, colles au nom dans les tirages
# publies : « Alexander Zverev (1) », « Grigor Dimitrov (Q) ».
MARQUE = re.compile(r"\s*\((\d{1,3}|Q|WC|LL|PR|SE|ALT)\)\s*$", re.I)


def separer(ligne):
    """'Alexander Zverev (1)' -> ('Alexander Zverev', '1')"""
    t = ligne.strip()
    m = MARQUE.search(t)
    if not m:
        return t, ""
    return MARQUE.sub("", t).strip(), m.group(1).upper()


def lire(fichier):
    infos, joueurs = {}, []
    for ligne in fichier.read_text(encoding="utf-8").splitlines():
        t = ligne.strip()
        if t.startswith("#"):
            if ":" in t:
                cle, valeur = t.lstrip("#").split(":", 1)
                infos[cle.strip().lower()] = valeur.strip()
        elif t or joueurs:            # une ligne vide = place a determiner
            joueurs.append(t)

    while joueurs and not joueurs[-1]:
        joueurs.pop()

    return infos, joueurs


def completer(joueurs):
    """
    Complete jusqu'a la puissance de 2 superieure.

    Un tableau doit avoir 16, 32, 64 ou 128 places : sans cela les tours
    ne tombent pas juste et l'arbre est faux des le depart.
    """
    n = 1
    while n < len(joueurs):
        n *= 2
    if n != len(joueurs):
        print(f"      {len(joueurs)} joueurs -> complete a {n} places")
        joueurs = joueurs + [""] * (n - len(joueurs))
    return joueurs


def un_tournoi(fichier, connus, table):
    infos, joueurs = lire(fichier)
    joueurs = completer(joueurs)

    if len(joueurs) < 2:
        print(f"  [!] {fichier.name} ignore : moins de deux joueurs")
        return None

    entrees = []
    for ligne in joueurs:
        nom, marque = separer(ligne)
        slug = cache.slugifier(nom) if nom else ""
        slug = table.get(slug, slug) or ""      # table de correspondance
        entrees.append({
            "nom": nom,
            "marque": marque,
            "slug": slug if slug.lower() in connus else None,
        })

    date = infos.get("date", "")
    nom_t = infos.get("nom", fichier.stem.replace("-", " ").title())

    reconnus = sum(1 for e in entrees if e["slug"])
    inconnus = [e["nom"] for e in entrees if e["nom"] and not e["slug"]]

    print(f"  {nom_t:<22} {len(entrees):>3} places, {reconnus} reconnus")
    if inconnus:
        print(f"      non reconnus : {', '.join(inconnus[:6])}"
              + (" ..." if len(inconnus) > 6 else ""))

    return {
        "nom": nom_t,
        "date": date,
        "date_fr": f"{date[6:]}/{date[4:6]}/{date[:4]}" if len(date) == 8 else "",
        "surface": infos.get("surface", ""),
        "niveau": infos.get("niveau", ""),
        "id": cache.slugifier(nom_t) + date,
        "joueurs": entrees,
    }


def sources():
    """Tous les tirages a traiter : le dossier, puis l'ancien fichier."""
    trouves = sorted(DOSSIER.glob("*.txt")) if DOSSIER.is_dir() else []
    if SOURCE.exists():
        trouves.append(SOURCE)
    if not trouves:
        raise SystemExit(
            f"Aucun tirage trouve. Cree {DOSSIER}/<tournoi>.txt, un joueur "
            f"par ligne dans l'ordre du tableau (voir l'en-tete de ce script)."
        )
    return trouves


def construire():
    connus = {s.lower() for s in cache.joueurs_en_cache()}

    # Les tirages n'ecrivent pas les noms comme Tennis Abstract : sans
    # cette table, « Aleksandr Shevchenko » passe pour un inconnu alors
    # que sa fiche existe deja.
    table = (json.loads(CORRECTIONS.read_text(encoding="utf-8"))
             if CORRECTIONS.exists() else {})

    tournois = []
    for fichier in sources():
        t = un_tournoi(fichier, connus, table)
        if t:
            tournois.append(t)

    if not tournois:
        raise SystemExit("Aucun tirage exploitable.")

    tournois.sort(key=lambda t: t["date"])

    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(json.dumps({"tournois": tournois}, ensure_ascii=False),
                      encoding="utf-8")

    print(f"\n{len(tournois)} tournoi(s) -> {SORTIE}")
    print("\nRelance ensuite : python publier.py")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        SOURCE = Path(sys.argv[1])
        DOSSIER = Path("__aucun__")
    construire()