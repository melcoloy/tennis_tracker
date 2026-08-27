"""
figer.py -- fabrique une version statique du site, publiable sur
GitHub Pages.

GitHub Pages ne sert que des fichiers : pas de Python, donc pas d'API
et pas de telechargement a la demande. On pre-calcule donc un JSON par
joueur, et le front bascule automatiquement en mode statique.

    python figer.py                      # tous les joueurs en cache
    python figer.py ArthurFils CarlosAlcaraz

Le resultat va dans site/. Ce dossier est ce qu'on publie.
"""

import json
import shutil
import sys
import time
from pathlib import Path

import api
import cache

SORTIE = Path("site")


def figer_joueur(slug):
    """
    Rassemble en un seul objet ce que l'API sert en quatre endpoints.

    On passe TOUS les parametres explicitement : appelees en direct,
    les fonctions FastAPI recoivent sinon des objets Query au lieu des
    valeurs par defaut, que seul le framework sait resoudre.
    """
    return {
        "profil": api.profil(joueur=slug),
        "classement": api.classement(joueur=slug),
        "stats": api.stats(joueur=slug),
        "matchs": api.matchs(joueur=slug, annee=None, niveau=None,
                             resultat=None, adversaire=None, limite=2000),
    }


def construire(slugs):
    if not slugs:
        print("Aucun joueur en cache. Lance d'abord le serveur et "
              "consulte au moins un joueur.")
        return

    SORTIE.mkdir(exist_ok=True)
    dossier_donnees = SORTIE / "donnees"
    dossier_donnees.mkdir(exist_ok=True)

    # 1. le front, tel quel
    for f in Path("frontend").iterdir():
        if f.is_file():
            shutil.copy2(f, SORTIE / f.name)
    print(f"front copie dans {SORTIE}/")

    # 2. un fichier par joueur
    index = []
    for slug in slugs:
        try:
            data = figer_joueur(slug)
        except Exception as e:
            print(f"  [!] {slug} ignore : {type(e).__name__} -- {e}")
            continue

        chemin = dossier_donnees / f"{slug}.json"
        chemin.write_text(json.dumps(data, ensure_ascii=False),
                          encoding="utf-8")

        p = data["profil"]
        index.append({
            "slug": slug,
            "nom": p["fullname"],
            "pays": p.get("country", ""),
            "rang": p.get("currentrank"),
            "nb_matchs": p["nb_matchs"],
        })
        ko = chemin.stat().st_size / 1024
        print(f"  {p['fullname']:<26} {p['nb_matchs']:>4} matchs   {ko:>7.0f} Ko")

    if not index:
        print("Rien a publier.")
        return

    # 3. l'index : c'est sa presence qui fait basculer le front en
    #    mode statique. Pas de detection d'hote, pas de configuration.
    (dossier_donnees / "index.json").write_text(
        json.dumps({
            "genere_le": time.strftime("%Y-%m-%d %H:%M"),
            "joueurs": sorted(index, key=lambda j: j["nom"]),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8")

    # 4. desactive le traitement Jekyll de GitHub Pages, qui ignore
    #    par defaut les fichiers commencant par un underscore
    (SORTIE / ".nojekyll").write_text("", encoding="utf-8")

    total = sum(f.stat().st_size for f in SORTIE.rglob("*") if f.is_file())
    print(f"\n{len(index)} joueurs figes -- {total / 1024:.0f} Ko au total")
    print(f"""
Site construit dans {SORTIE}/.
Mise en ligne : GitHub Actions, chaque lundi ou a la demande.

Pour verifier en local avant publication :
  cd {SORTIE} && python -m http.server 8080
""")


if __name__ == "__main__":
    demandes = sys.argv[1:] or cache.joueurs_en_cache()
    construire(demandes)